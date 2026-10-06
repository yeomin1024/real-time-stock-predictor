"""R1(1종목 6-1 모멘텀, 장 시작 가격) 실시간 경로 검증: 워밍업 일봉 → 로테이션 목표 → 전액 가상 매수 → 상태 저장·복원"""
import asyncio, json, os, sys, tempfile, shutil, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kiwoom_autotrader as K

TMP = os.path.join(tempfile.gettempdir(), "kr1"); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
sd = os.path.join(TMP, "signals"); os.makedirs(sd)
days = pd.bdate_range(end=K.now_et().date() - dt.timedelta(days=1), periods=10)
pd.DataFrame({"날짜": [d.date() for d in days], "목표비중": 0.4}).to_csv(os.path.join(sd, "market_regime_daily.csv"),
                                                                    index=False, encoding="utf-8-sig")
daily = {"NVDA": list(np.linspace(100, 200, 200)), "MU": list(np.linspace(100, 150, 200)),
         "KO": list(np.linspace(100, 90, 200))}                      # KO: 126일 수익률 음수 → 제외
K._daily_closes_yf = lambda codes, before: {c: daily[c] for c in codes}
t0 = K.now_et().replace(hour=10, minute=0, second=0, microsecond=0)
K.load_bars_yf = lambda code, minutes=1, period="7d", start=None, end=None: pd.DataFrame(
    {"ts": [t0.replace(tzinfo=None) - dt.timedelta(hours=60 - i) for i in range(60)], "close": daily[code][-60:]})
px = {"NVDA": 200.0, "MU": 150.0, "KO": 90.0}
idx = pd.DatetimeIndex([t0 + dt.timedelta(minutes=i) for i in range(5)])
raw = pd.concat({c: pd.DataFrame({"Open": p, "High": p, "Low": p, "Close": p, "Volume": 1}, index=idx) for c, p in px.items()}, axis=1)
SIM = {"t": t0 + dt.timedelta(minutes=10)}
cfg = K.Config(**K.PRESETS["R1_5000"], symbols={"NVDA": "ND", "MU": "ND", "KO": "NY"},
               signals_dir=sd, market_hours_check=False, paper_state=os.path.join(TMP, "st.json"),
               trade_log=os.path.join(TMP, "t.csv"), equity_log=os.path.join(TMP, "e.csv"), status_every_min=999)
r = K.LiveRunner(cfg, None, clock=lambda: SIM["t"])
r._yf_fetch = lambda: raw


async def go():
    task = asyncio.create_task(r.run()); await asyncio.sleep(1.5); r.stop(); await asyncio.wait_for(task, 10)
asyncio.run(go())
tr = pd.DataFrame(r.book.trades)
print(tr.to_string() if len(tr) else "(거래 없음)")
assert r.book.rot_target == {"NVDA"}, r.book.rot_target
assert r.engine.today.exposure == 1.0                                 # 국면 0.4 → 켜기·끄기라 1.0
buys = tr[tr["구분"] == "매수"]
assert list(buys["종목"]) == ["NVDA"] and all(buys["사유"].str.startswith("로테이션"))
assert abs(buys["수량"].iloc[0] * buys["가격($)"].iloc[0] - 10000) < 250  # 전액
st = json.load(open(os.path.join(TMP, "st.json"), encoding="utf-8"))
assert sorted(st["rot_target"]) == ["NVDA"] and all(p["mode"] == "rot" for p in st["positions"].values())
b2 = K.Book(cfg); b2.load_state(os.path.join(TMP, "st.json"))
assert b2.rot_target == {"NVDA"} and b2.get("NVDA").mode == "rot"
shutil.rmtree(TMP, ignore_errors=True)
print("R1 LIVE PATH OK")

