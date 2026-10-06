import os, sys, datetime as dt, tempfile
import pandas as pd
sys.path.insert(0, ".")
import kiwoom_autotrader as K
d = tempfile.mkdtemp()
pd.DataFrame({"티커": ["NVDA"], "발표일": ["2026-01-07"]}).to_csv(os.path.join(d, "earnings_dates.csv"), index=False, encoding="utf-8-sig")
cfg = K.Config(signals_dir=d, symbols={"NVDA": "ND", "MU": "ND"}, regime="off", sector_filter=False, trend_ma_days=0,
               earn_avoid=True, fee_pct=0, slippage_pct=0)
eng = K.Engine(cfg, K.Book(cfg, verbose=False), K.DailySignals(cfg), verbose=False)
eng.on_price("NVDA", 100.0, dt.datetime(2026, 1, 6, 10))                 # 다음 거래일(1/7) 발표 → 1/6 회피
assert eng.today.blackout == {"NVDA"} and "NVDA" not in eng.today.eligible
assert not eng.book.can_enter("NVDA", dt.datetime(2026, 1, 6, 10), eng.today.eligible)[0]
eng._fill("NVDA", "BUY", 100.0, dt.datetime(2026, 1, 6, 10), "테스트 보유")   # 이미 들고 있다면
eng.on_clock(dt.datetime(2026, 1, 6, 15, 55))
assert eng.book.get("NVDA").qty == 0 and eng.book.trades[-1]["사유"] == "실적 발표 전 청산"
eng.on_price("MU", 50.0, dt.datetime(2026, 1, 9, 10))                    # 발표 지나면 해제
assert not eng.today.blackout
print("earnings avoidance OK")
