"""v1.1.0(2026-10-07) 단위 테스트 — K v0.36 '숏:<ETF>' 열(실제 −1배 ETF) · 기초 종목 실적 회피 · 작은 몫 → 섹터 ETF · 레버리지 차단
사용: PYTHONPATH=. python lab/test_v110.py   → 마지막 줄 'V110 OK'"""
import os, sys, tempfile, shutil
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kiwoom_autotrader as K

# 1) 열 이름
assert K._k_col("숏:NVDD") == "NVDD" and K._k_col("숏:NVDD 다음날 하락확률(%)") == "NVDD 다음날 하락확률(%)"
assert K._k_col("ETF_XLK") == "XLK" and K._k_col("NVDA") == "NVDA"
assert not (set(K.INVERSE_1X_ETFS) & K.LEVERAGED_ETFS) and {"TSLQ", "NVDS", "SMCZ"} <= K.LEVERAGED_ETFS
assert len(K.DEFAULT_UNIVERSE) == 59 and "MAA" in K.DEFAULT_UNIVERSE and "AVB" not in K.DEFAULT_UNIVERSE

# 2) 신호 파일: D0 NVDA 실적 전날 → NVDD(숏)도 회피, 풀 종목 APD 1% → XLB
TMP = os.path.join(tempfile.gettempdir(), "kv110"); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
days = list(pd.bdate_range("2026-03-02", periods=6))
pd.DataFrame({"날짜": days, "목표비중": 1.0}).to_csv(os.path.join(TMP, "market_regime_daily.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame({"날짜": days, "구분": "실적", "★ 합계": 0.3, "현금": 0.7, "MU": 0.10, "MU 다음날 하락확률(%)": 44.0,
              "KO": 0.01, "APD": 0.01, "ETF_XLB": 0.05, "숏:NVDD": 0.10, "숏:NVDD 다음날 하락확률(%)": 50.0,
              "숏:ORCS": 0.01, "TQQQ": 0.05}).to_csv(os.path.join(TMP, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame({"티커": ["NVDA"], "발표일": [days[3].date()]}).to_csv(os.path.join(TMP, "earnings_dates.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame({"티커": ["APD"], "이름": ["Air Products"], "섹터 ETF": ["XLB"]}).to_csv(os.path.join(TMP, "stock_pool_sector.csv"), index=False, encoding="utf-8-sig")

uni = K.k_symbols(TMP, base={"MU": "ND", "KO": "NY"}, since=None, min_weight=0.02)
assert uni == {"MU": "ND", "KO": "NY", "XLB": "NA", "NVDD": "ND", "TQQQ": uni.get("TQQQ")} or "TQQQ" not in uni, uni
assert "TQQQ" not in uni and "ORCS" not in uni and uni["NVDD"] == "ND", uni          # 레버리지 차단 · 2% 미만 숏은 안 넣음
print("[TEST] k_symbols", uni)

cfg = K.Config(**K.PRESETS["P8"], symbols=uni, signals_dir=TMP, market_hours_check=False, trade_log="", equity_log="", paper_state="")
sig = K.DailySignals(cfg)
d2 = sig.for_day(days[3].date())            # 실적 당일(D0) → 전날 행 사용 · NVDA 실적 → NVDD 회피
assert abs(d2.kw["NVDD"] - 0.10) < 1e-9 and "NVDD" in d2.blackout and "K 숏 NVDD(NVDA) 10.0%" in d2.note, (d2.kw, d2.blackout, d2.note)
assert d2.kp1.get("NVDD") == 50.0, d2.kp1
d4 = sig.for_day(days[5].date())
assert "NVDD" not in d4.blackout, d4.blackout
print("[TEST] for_day", d2.note)

# 3) 작은 몫 → 섹터 ETF(풀만 / 전부)
w, m = K.k_small_to_etf({"APD": 0.01, "KO": 0.01, "XLB": 0.05, "NVDD": 0.01}, 0.02, {"APD": "XLB", "KO": "XLP"}, keep=K.DEFAULT_UNIVERSE)
assert set(w) == {"KO", "XLB", "NVDD"} and abs(w["XLB"] - 0.06) < 1e-12 and abs(m - 0.01) < 1e-12, (w, m)
cfg2 = K.Config(**dict(K.PRESETS["P8"], k_small_to_etf=True, k_small_pool_only=True), symbols=K.k_symbols(TMP, base={"MU": "ND", "KO": "NY"},
                since=None, min_weight=0.02, small_to_etf=True), signals_dir=TMP, market_hours_check=False, trade_log="", equity_log="", paper_state="")
d = K.DailySignals(cfg2).for_day(days[3].date())
assert abs(d.kw["XLB"] - 0.06) < 1e-9 and "APD" not in d.kw and "KO" in d.kw and "K 작은몫→ETF 1.0%" in d.note, (d.kw, d.note)

# 4) 시뮬레이션: NVDD를 K 몫으로 사고, NVDA 실적 전날 팜(earn_avoid)
idx = []
for day in pd.bdate_range("2026-01-02", "2026-03-10"):
    idx += [day + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(hours=h) for h in range(7)]
ts = pd.Series(idx)
mk = lambda p: pd.DataFrame({"ts": ts, "open": p, "high": p * 1.001, "low": p * 0.999, "close": p, "volume": 1e6})
bars = {"MU": mk(np.linspace(100, 130, len(ts))), "KO": mk(np.linspace(60, 61, len(ts))), "XLB": mk(np.linspace(90, 95, len(ts))),
        "NVDD": mk(np.linspace(20, 19, len(ts)))}
cfg3 = K.Config(**dict(K.PRESETS["P8"], earn_hold_loser=False), symbols=uni, signals_dir=TMP, market_hours_check=False,
                trade_log="", equity_log="", paper_state="")
res = K.simulate(cfg3, bars, K.DailySignals(cfg3))
tr = res["trades"]; nv = tr[tr["종목"] == "NVDD"]
print(nv.to_string(index=False))
assert len(nv[nv["구분"] == "매수"]) >= 1 and "K몫 매수" in nv.iloc[0]["사유"], nv
dd = pd.to_datetime(nv["시각(ET)"]).dt.date
sold = nv[(nv["구분"] == "매도") & (dd == days[2].date())]                 # NVDA 실적(days[3]) 전날 장 마감 전 청산
assert len(sold) == 1 and "실적" in sold.iloc[0]["사유"], nv
assert not (dd == days[3].date()).any(), nv                               # 실적 당일엔 안 삼 → 다음 거래일 다시 삼
print("V110 OK")
