"""P7(K × 1.5 + 168일 모멘텀 1위 50% + 본전 대기 · 손실 8% 넘으면 매도) 실시간 경로 검증 — 날마다 실행기를 새로 켬"""
import asyncio, json, os, sys, tempfile, shutil, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kiwoom_autotrader as K

TMP = os.path.join(tempfile.gettempdir(), "kp7"); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
sd = os.path.join(TMP, "signals"); os.makedirs(sd)
t0 = K.now_et().replace(hour=10, minute=0, second=0, microsecond=0)
D1, D2, D3 = t0, t0 + dt.timedelta(days=1), t0 + dt.timedelta(days=2)
days = [d.date() for d in pd.bdate_range(end=t0.date() - dt.timedelta(days=1), periods=5)]
# D1까지는 국면 1·K 비중 있음, D1 장 마감 뒤 국면 0·K 비중 0 (D2부터 적용)
dates = days + [D1.date(), D2.date()]
pd.DataFrame({"날짜": dates, "목표비중": [1.0] * 5 + [0.0, 0.0]}).to_csv(
    os.path.join(sd, "market_regime_daily.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame({"날짜": dates, "구분": "실적", "★ 합계": [0.3] * 5 + [0, 0], "현금": [0.7] * 5 + [1, 1],
              "NVDA": [0.2] * 5 + [0, 0], "MU": [0.1] * 5 + [0, 0], "KO": [0.1] * 5 + [0, 0]}).to_csv(
    os.path.join(sd, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
daily = {"NVDA": list(np.linspace(100, 200, 200)), "MU": list(np.linspace(100, 150, 200)),
         "KO": list(np.linspace(100, 90, 200)), "SPY": list(np.linspace(500, 600, 200))}
K._daily_closes_yf = lambda codes, before: {c: daily[c] for c in codes}
K.load_bars_yf = lambda code, minutes=1, period="7d", start=None, end=None: pd.DataFrame(
    {"ts": [t0.replace(tzinfo=None) - dt.timedelta(hours=60 - i) for i in range(60)], "close": daily[code][-60:]})
cfg = K.Config(**K.PRESETS["P7"], symbols={"NVDA": "ND", "MU": "ND", "KO": "NY"}, signals_dir=sd, market_hours_check=False,
               paper_state=os.path.join(TMP, "st.json"), trade_log=os.path.join(TMP, "t.csv"),
               equity_log=os.path.join(TMP, "e.csv"), status_every_min=999)


def run_day(t, px):
    SIM = {"t": t + dt.timedelta(minutes=10)}
    r = K.LiveRunner(cfg, None, clock=lambda: SIM["t"])
    idx = pd.DatetimeIndex([t + dt.timedelta(minutes=i) for i in range(5)])
    raw = pd.concat({c: pd.DataFrame({"Open": p, "High": p, "Low": p, "Close": p, "Volume": 1}, index=idx)
                     for c, p in px.items()}, axis=1)
    r._yf_fetch = lambda: raw

    async def go():
        task = asyncio.create_task(r.run()); await asyncio.sleep(1.5); r.stop(); await asyncio.wait_for(task, 10)
    asyncio.run(go())
    return r, json.load(open(os.path.join(TMP, "st.json"), encoding="utf-8"))


# D1: 모멘텀 1위(NVDA) 50% + 나머지 K 비중 × 1.5
r, st = run_day(D1, {"NVDA": 200.0, "MU": 150.0, "KO": 90.0, "SPY": 601.0})
q = {k: p["qty"] for k, p in st["positions"].items() if p["qty"]}
assert q == {"NVDA": int(5000 // 200.1), "MU": int(10000 * 0.1 * 1.5 // 150.075), "KO": int(10000 * 0.1 * 1.5 // 90.045)}, q
# D2: 국면 0 → 이익 난 NVDA·MU는 팔고, 손실 중(−3%)인 KO는 본전 대기(대기 시작일 저장)
r, st = run_day(D2, {"NVDA": 210.0, "MU": 160.0, "KO": 87.0, "SPY": 590.0})
pos = st["positions"]
assert {k for k, p in pos.items() if p["qty"]} == {"KO"}, pos
assert pos["KO"]["exit_wait"] == str(D2.date()), pos["KO"]
# D3: KO가 진입가 대비 −8.05% → 손실 한도(8%) 넘어 바로 매도
r, st = run_day(D3, {"NVDA": 210.0, "MU": 160.0, "KO": 82.8, "SPY": 590.0})
assert not any(p["qty"] for p in st["positions"].values()), st["positions"]
tr = pd.read_csv(os.path.join(TMP, "t.csv"), encoding="utf-8-sig")
print(tr.to_string())
sells = tr[tr["구분"] == "매도"]
assert (sells[sells["종목"] != "KO"]["손익($)"] > 0).all()
ko = sells[sells["종목"] == "KO"].iloc[0]
assert ko["손익($)"] < 0 and "손실 8% 넘음" in ko["사유"], ko.to_dict()
shutil.rmtree(TMP, ignore_errors=True)
print("P7 LIVE PATH OK")
