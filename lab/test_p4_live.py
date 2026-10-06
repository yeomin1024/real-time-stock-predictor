"""P4(K 주식층 따라가기 몫 + 6-1 모멘텀 상위 2종 몫, 장 시작 체결) 실시간 경로 검증"""
import asyncio, json, os, sys, tempfile, shutil, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kiwoom_autotrader as K

TMP = os.path.join(tempfile.gettempdir(), "kp4"); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
sd = os.path.join(TMP, "signals"); os.makedirs(sd)
days = pd.bdate_range(end=K.now_et().date() - dt.timedelta(days=1), periods=5)
pd.DataFrame({"날짜": [d.date() for d in days], "목표비중": 1.0}).to_csv(os.path.join(sd, "market_regime_daily.csv"),
                                                                   index=False, encoding="utf-8-sig")
pd.DataFrame({"날짜": [d.date() for d in days], "구분": "실적", "★ 합계": 0.3, "현금": 0.7, "NVDA": 0.2, "MU": 0.1,
              "KO": 0.1}).to_csv(os.path.join(sd, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
daily = {"NVDA": list(np.linspace(100, 200, 200)), "MU": list(np.linspace(100, 150, 200)),
         "KO": list(np.linspace(100, 90, 200)), "SPY": list(np.linspace(500, 600, 200))}
K._daily_closes_yf = lambda codes, before: {c: daily[c] for c in codes}
t0 = K.now_et().replace(hour=10, minute=0, second=0, microsecond=0)
K.load_bars_yf = lambda code, minutes=1, period="7d", start=None, end=None: pd.DataFrame(
    {"ts": [t0.replace(tzinfo=None) - dt.timedelta(hours=60 - i) for i in range(60)], "close": daily[code][-60:]})
px = {"NVDA": 200.0, "MU": 150.0, "KO": 90.0, "SPY": 601.0}
idx = pd.DatetimeIndex([t0 + dt.timedelta(minutes=i) for i in range(5)])
raw = pd.concat({c: pd.DataFrame({"Open": p, "High": p, "Low": p, "Close": p, "Volume": 1}, index=idx) for c, p in px.items()}, axis=1)
SIM = {"t": t0 + dt.timedelta(minutes=10)}
cfg = K.Config(**K.PRESETS["P4"], symbols={"NVDA": "ND", "MU": "ND", "KO": "NY"}, signals_dir=sd, market_hours_check=False,
               paper_state=os.path.join(TMP, "st.json"), trade_log=os.path.join(TMP, "t.csv"),
               equity_log=os.path.join(TMP, "e.csv"), status_every_min=999)
r = K.LiveRunner(cfg, None, clock=lambda: SIM["t"])
assert "SPY" not in r.exch
r._yf_fetch = lambda: raw


async def go():
    task = asyncio.create_task(r.run()); await asyncio.sleep(1.5); r.stop(); await asyncio.wait_for(task, 10)
asyncio.run(go())
tr = pd.DataFrame(r.book.trades)
print(tr.to_string() if len(tr) else "(거래 없음)")
assert r.book.rot_target == {"NVDA", "MU"}, r.book.rot_target
buys = tr[tr["구분"] == "매수"]
why = dict(zip(buys["종목"], buys["사유"].str[:4]))
assert why == {"NVDA": "로테이션", "MU": "로테이션", "KO": "K몫 매"}, why
q = dict(zip(buys["종목"], buys["수량"]))
assert q == {"NVDA": int(1500 // 200.1), "MU": int(1500 // 150.075), "KO": int(10000 * 0.1 * 0.9 // 90.045)}, q
assert "SPY" not in set(tr["종목"])
st = json.load(open(os.path.join(TMP, "st.json"), encoding="utf-8"))
assert {k: p["mode"] for k, p in st["positions"].items()} == {"NVDA": "rot", "MU": "rot", "KO": "kf"}
shutil.rmtree(TMP, ignore_errors=True)
print("P4 LIVE PATH OK")
