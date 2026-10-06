"""P8(K S&P 500 종목·섹터 ETF까지 따라감 + 매도 먼저·정해진 매수 순서 + K × 1.5 + 168일 모멘텀 1위(58종) 35% + 본전 대기)
실시간 경로 검증 — 날마다 실행기를 새로 켬. K v0.33+ 열 형식('ETF_XLK', '다음날 하락확률')을 그대로 씀."""
import asyncio, json, os, sys, tempfile, shutil, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kiwoom_autotrader as K

TMP = os.path.join(tempfile.gettempdir(), "kp8"); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
sd = os.path.join(TMP, "signals"); os.makedirs(sd)
t0 = K.now_et().replace(hour=10, minute=0, second=0, microsecond=0)
D1, D2, D3 = t0, t0 + dt.timedelta(days=1), t0 + dt.timedelta(days=2)
days = [d.date() for d in pd.bdate_range(end=t0.date() - dt.timedelta(days=1), periods=5)]
# D1까지는 국면 1·K 비중 있음, D1 장 마감 뒤 국면 0·K 비중 0 (D2부터 적용)
dates = days + [D1.date(), D2.date()]
pd.DataFrame({"날짜": dates, "목표비중": [1.0] * 5 + [0.0, 0.0]}).to_csv(
    os.path.join(sd, "market_regime_daily.csv"), index=False, encoding="utf-8-sig")
on = lambda w: [w] * 5 + [0, 0]
pd.DataFrame({"날짜": dates, "구분": "실적", "★ 합계": on(0.5), "현금": on(0.5),
              "NVDA": on(0.2), "NVDA 다음날 하락확률(%)": 45.0, "MU": on(0.1), "MU 다음날 하락확률(%)": 44.0,
              "KO": on(0.1), "KO 다음날 하락확률(%)": 46.0, "ETF_XLK": on(0.1), "ETF_XLK 다음날 하락확률(%)": 43.0}).to_csv(
    os.path.join(sd, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
# XLK가 모멘텀은 가장 크지만 58종이 아니라서 모멘텀 몫으로는 안 사고 K 몫으로만 삼
daily = {"NVDA": list(np.linspace(100, 200, 200)), "MU": list(np.linspace(100, 150, 200)),
         "KO": list(np.linspace(100, 90, 200)), "XLK": list(np.linspace(100, 300, 200)), "SPY": list(np.linspace(500, 600, 200))}
K._daily_closes_yf = lambda codes, before: {c: daily[c] for c in codes}
K.load_bars_yf = lambda code, minutes=1, period="7d", start=None, end=None: pd.DataFrame(
    {"ts": [t0.replace(tzinfo=None) - dt.timedelta(hours=60 - i) for i in range(60)], "close": daily[code][-60:]})
uni = K.k_symbols(sd, base={"NVDA": "ND", "MU": "ND", "KO": "NY"}, since=None, min_weight=K.PRESETS["P8"]["k_min_weight"])
assert uni == {"NVDA": "ND", "MU": "ND", "KO": "NY", "XLK": "NA"}, uni
cfg = K.Config(**K.PRESETS["P8"], symbols=uni, signals_dir=sd, market_hours_check=False,
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


# D1: 모멘텀 1위(58종 중 NVDA) 35% 먼저 → K 비중 × 1.5 (MU·KO·XLK)
r, st = run_day(D1, {"NVDA": 200.0, "MU": 150.0, "KO": 90.0, "XLK": 300.0, "SPY": 601.0})
assert r.book.rot_target == {"NVDA"}, r.book.rot_target
q = {k: p["qty"] for k, p in st["positions"].items() if p["qty"]}
assert q == {"NVDA": int(3500 // 200.1), "MU": int(1500 // 150.075), "KO": int(1500 // 90.045), "XLK": int(1500 // 300.15)}, q
assert {k: p["mode"] for k, p in st["positions"].items() if p["qty"]} == {"NVDA": "rot", "MU": "kf", "KO": "kf", "XLK": "kf"}
# D2: 국면 0 → 이익 난 NVDA·MU·XLK는 팔고, 손실 중(−3%)인 KO는 본전 대기
r, st = run_day(D2, {"NVDA": 210.0, "MU": 160.0, "KO": 87.0, "XLK": 310.0, "SPY": 590.0})
pos = st["positions"]
assert {k for k, p in pos.items() if p["qty"]} == {"KO"}, pos
assert pos["KO"]["exit_wait"] == str(D2.date()), pos["KO"]
# D3: KO가 진입가 대비 −8.05% → 손실 한도(8%) 넘어 바로 매도
r, st = run_day(D3, {"NVDA": 210.0, "MU": 160.0, "KO": 82.8, "XLK": 310.0, "SPY": 590.0})
assert not any(p["qty"] for p in st["positions"].values()), st["positions"]
tr = pd.read_csv(os.path.join(TMP, "t.csv"), encoding="utf-8-sig")
print(tr.to_string())
assert list(tr[tr["구분"] == "매수"]["종목"])[0] == "NVDA"          # 모멘텀 몫이 먼저
sells = tr[tr["구분"] == "매도"]
assert (sells[sells["종목"] != "KO"]["손익($)"] > 0).all()
ko = sells[sells["종목"] == "KO"].iloc[0]
assert ko["손익($)"] < 0 and "손실 8% 넘음" in ko["사유"], ko.to_dict()
shutil.rmtree(TMP, ignore_errors=True)
print("P8 LIVE PATH OK")
