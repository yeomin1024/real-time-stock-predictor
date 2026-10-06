"""새 옵션 검증: 가상 신용(매수 가능 금액·이자) · 국면 켜기/끄기 · 모멘텀 상위 · MARKET 매핑 · 종목별 배율"""
import os, sys, math, datetime as dt, tempfile
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kiwoom_autotrader as K

# 1) 신용: 레버리지 1이면 현금 한도, 2면 자산의 2배까지 + 이자
c1 = K.Config(position_pct=150.0, leverage=1.0, fee_pct=0.0, slippage_pct=0.0, symbols={"A": "ND"})
b1 = K.Book(c1, verbose=False)
assert b1.order_qty(100.0) == 100, b1.order_qty(100.0)
c2 = K.Config(position_pct=150.0, leverage=2.0, fee_pct=0.0, slippage_pct=0.0, margin_rate_pct=7.0, symbols={"A": "ND"})
b2 = K.Book(c2, verbose=False)
assert b2.order_qty(100.0) == 150
b2.new_day(dt.date(2026, 1, 5))
b2.apply_fill("A", "BUY", 150, 100.0, dt.datetime(2026, 1, 5, 10))
b2.get("A").last_price = 100.0
assert abs(b2.cash + 5000) < 1e-9 and abs(b2.equity() - 10000) < 1e-9
b2.new_day(dt.date(2026, 1, 6))
assert abs(b2.interest - 5000 * 0.07 / 252) < 1e-9, b2.interest
assert b2.order_qty(100.0) == int((b2.cash + b2.equity()) // 100)          # 남은 매수 가능 금액만큼
print("leverage OK", round(b2.interest, 4))

# 2) 국면 켜기/끄기 + MARKET 매핑(섹터 필터 통과)
d = tempfile.mkdtemp()
pd.DataFrame({"날짜": ["2026-01-02"], "목표비중": [0.4]}).to_csv(os.path.join(d, "market_regime_daily.csv"), index=False)
pd.DataFrame({"날짜": ["2026-01-02"], "XLK 배분비중": [0.0], "XLY 배분비중": [0.3]}).to_csv(
    os.path.join(d, "sector_allocation_daily.csv"), index=False)
amap = dict(K.PRIOR_STOCK_TO_INDUSTRY, TQQQ="MARKET")
syms = {"NVDA": "ND", "TSLA": "ND", "TQQQ": "ND"}
s_scale = K.DailySignals(K.Config(signals_dir=d, symbols=syms, alloc_map=amap)).for_day(dt.date(2026, 1, 5))
s_gate = K.DailySignals(K.Config(signals_dir=d, symbols=syms, alloc_map=amap, regime_scale=False)).for_day(dt.date(2026, 1, 5))
assert s_scale.exposure == 0.4 and s_gate.exposure == 1.0
assert s_scale.eligible == {"TSLA", "TQQQ"}, s_scale.eligible                # NVDA(XLK 0) 제외, TQQQ는 섹터 필터 없음
print("regime gate / MARKET OK")

# 3) 모멘텀 상위: 전일까지 일봉으로만
cfg = K.Config(symbols={"A": "ND", "B": "ND", "C": "ND"}, mom_top=2, mom_days=3, regime="off", sector_filter=False,
               trend_ma_days=0)
eng = K.Engine(cfg, verbose=False)
for code, closes in (("A", [10, 10, 10, 13]), ("B", [10, 10, 10, 9]), ("C", [10, 10, 10, 11])):
    eng.book.get(code).daily.extend(closes)
eng.start_day(dt.date(2026, 1, 6))
assert eng.today.eligible == {"A", "C"}, eng.today.eligible
print("momentum OK")

# 4) 종목별 배율: 3배면 손절 폭도 3배
st = K.SymState("X"); st.qty, st.entry, st.entry_time, st.rsi = 10, 100.0, dt.datetime(2026, 1, 5, 10), 50
strat = K.LowHighStrategy(K.Config(stop_loss_pct=4.0, sym_scale={"X": 3.0}))
assert strat.decide(st, 95.0, dt.datetime(2026, 1, 5, 11))[0] is None             # −5%: 3배면 손절선 −12%
assert strat.decide(st, 87.9, dt.datetime(2026, 1, 5, 11))[0] == "SELL"
print("sym_scale OK")
# 5) 돌파 매수: 전일까지 20일 최고 종가를 넘으면 매수, 이후 돌파용 손절·추적청산
cfg = K.Config(symbols={"A": "ND"}, entry_mode="brk", brk_days=3, brk_stop_pct=8, brk_trail_pct=10, regime="off",
               sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0, entry_start="09:35")
eng = K.Engine(cfg, verbose=False)
eng.book.get("A").daily.extend([100, 104, 102, 103])           # 전일까지 3일 최고 = 104
eng.start_day(dt.date(2026, 1, 6))
assert eng.book.get("A").brk_level == 104
t = dt.datetime(2026, 1, 6, 10, 0)
eng.on_price("A", 103.5, t)
assert eng.book.get("A").qty == 0
eng.on_price("A", 104.5, t + dt.timedelta(minutes=1))
s = eng.book.get("A")
assert s.qty > 0 and s.mode == "brk", (s.qty, s.mode)
eng.on_price("A", 101.0, t + dt.timedelta(minutes=2))          # −3.3%: 저점매수 손절(4%)도 안 걸리고 돌파 손절(8%)도 아님
assert s.qty > 0
eng.on_price("A", 120.0, t + dt.timedelta(minutes=3))          # 고점 120
eng.on_price("A", 109.0, t + dt.timedelta(minutes=4))          # 고점 대비 −9.2% → 유지
assert s.qty > 0
eng.on_price("A", 107.9, t + dt.timedelta(minutes=5))          # −10.1% → 추적청산
assert s.qty == 0 and s.mode == "" and eng.book.trades[-1]["사유"].startswith("돌파 추적청산"), eng.book.trades[-1]
print("breakout OK")

# 6) 모멘텀 로테이션: 전일까지 3일 수익률 1위만 50% 보유, 순위가 바뀌면 다음 날 갈아탐
cfg = K.Config(symbols={"A": "ND", "B": "ND"}, entry_mode="rot", rot_top=1, rot_days=3, rot_every=1, rot_pct=50.0,
               regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0, daily_loss_pct=100.0)
eng = K.Engine(cfg, verbose=False)
eng.book.get("A").daily.extend([10, 10, 10, 13])
eng.book.get("B").daily.extend([10, 10, 10, 11])
d1 = dt.datetime(2026, 1, 6, 10, 0)
eng.on_price("A", 13.0, d1)
eng.on_price("B", 11.0, d1 + dt.timedelta(minutes=1))
a, b = eng.book.get("A"), eng.book.get("B")
assert eng.book.rot_target == {"A"} and a.qty == 384 and a.mode == "rot" and b.qty == 0, (eng.book.rot_target, a.qty, b.qty)
eng.on_price("A", 12.0, d1 + dt.timedelta(minutes=2))          # 저점매수 손절·익절 규칙은 로테이션 보유에 안 걸림
eng.on_price("B", 14.0, d1 + dt.timedelta(minutes=3))          # B 종가 14 → 3일 +40% > A 12/10 +20%
d2 = dt.datetime(2026, 1, 7, 10, 0)
eng.on_price("A", 12.0, d2)
assert eng.book.rot_target == {"B"} and a.qty == 0 and eng.book.trades[-1]["사유"].startswith("로테이션 제외")
eng.on_price("B", 14.0, d2 + dt.timedelta(minutes=1))
assert b.qty > 0 and b.mode == "rot"
print("rotation OK")

# 7) 변동성 맞춤: 일간 ±4% 종목은 폭이 약 2배(기준 2%)
cfg = K.Config(symbols={"V": "ND"}, vol_ref_pct=2.0, regime="off", sector_filter=False)
eng = K.Engine(cfg, verbose=False)
eng.book.get("V").daily.extend([100 if i % 2 == 0 else 104 for i in range(25)])
eng.refresh_trend()
assert 1.8 < eng.book.get("V").vk < 2.1, eng.book.get("V").vk
print("vol scale OK", round(eng.book.get("V").vk, 2))

# 8) 로테이션 버퍼: 들고 있는 A는 순위 2 안이면 유지, 3위로 밀리면 1위로 교체
cfg = K.Config(symbols={"A": "ND", "B": "ND", "C": "ND"}, entry_mode="rot", rot_top=1, rot_keep=2, rot_days=3,
               regime="off", sector_filter=False, trend_ma_days=0)
eng = K.Engine(cfg, verbose=False)
for code, closes in (("A", [10, 10, 10, 12]), ("B", [10, 10, 10, 13]), ("C", [10, 10, 10, 11])):
    eng.book.get(code).daily.extend(closes)
eng.book.get("A").qty, eng.book.get("A").mode = 10, "rot"
assert eng.rotation_pick() == {"A"}                          # B 1위지만 A가 2위 안 → 유지
eng.book.get("C").daily.append(14)                           # C 3일 +40% → 순위 C, B, A
assert eng.rotation_pick() == {"C"}
print("rotation buffer OK")

# 9) 이상 틱 vs 진짜 갭: 한 번 튄 값은 무시, 같은 수준이 3번 이어지면 받아들임(전에는 30% 넘는 갭 뒤로 가격이 영원히 멈춤)
cfg = K.Config(symbols={"G": "ND"}, regime="off", sector_filter=False, trend_ma_days=0)
eng = K.Engine(cfg, verbose=False)
t = dt.datetime(2026, 1, 6, 10, 0)
eng.on_price("G", 100.0, t)
eng.on_price("G", 200.0, t + dt.timedelta(minutes=1))           # 튄 값
eng.on_price("G", 101.0, t + dt.timedelta(minutes=2))
assert eng.book.get("G").last_price == 101.0
for i, p in enumerate((140.0, 140.5, 141.0, 141.2)):           # +40% 갭 지속
    eng.on_price("G", p, t + dt.timedelta(minutes=3 + i))
assert eng.book.get("G").last_price == 141.2, eng.book.get("G").last_price
print("gap acceptance OK")

# 10) 모멘텀 최근 k일 제외: 어제 급등한 A보다 꾸준히 오른 B
cfg = K.Config(symbols={"A": "ND", "B": "ND"}, entry_mode="rot", rot_top=1, rot_days=3, regime="off",
               sector_filter=False, trend_ma_days=0)
eng = K.Engine(cfg, verbose=False)
eng.book.get("A").daily.extend([10, 10, 10, 10, 20])
eng.book.get("B").daily.extend([10, 11, 12, 13, 13])
assert eng.rotation_pick() == {"A"}
cfg.rot_skip = 1
assert eng.rotation_pick() == {"B"}
print("rotation skip OK")

# 11) 물타기: 첫 매수가 -2%에서 같은 수량 추가, 평균가 기준 손절
st = K.SymState("W"); st.qty, st.entry, st.first_entry, st.init_qty = 10, 100.0, 100.0, 10
st.entry_time, st.rsi = dt.datetime(2026, 1, 5, 10), 50
strat = K.LowHighStrategy(K.Config(stop_loss_pct=4.0, add_drop_pct=2.0, add_max=1))
assert strat.decide(st, 98.5, dt.datetime(2026, 1, 5, 11))[0] is None
assert strat.decide(st, 97.9, dt.datetime(2026, 1, 5, 11))[0] == "ADD"
cfg = K.Config(symbols={"W": "ND"}, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0,
               add_drop_pct=2.0, add_max=1, stop_loss_pct=4.0, position_pct=20.0)
eng = K.Engine(cfg, verbose=False)
b = eng.book; b.new_day(dt.date(2026, 1, 5)); eng.day = dt.date(2026, 1, 5)
eng._fill("W", "BUY", 100.0, dt.datetime(2026, 1, 5, 10), "저점 테스트")
w = b.get("W"); q0 = w.qty
eng.on_price("W", 97.9, dt.datetime(2026, 1, 5, 10, 5))
assert w.qty == 2 * q0 and w.adds == 1 and abs(w.entry - 98.95) < 1e-6 and w.first_entry == 100.0, (w.qty, w.entry)
eng.on_price("W", 95.9, dt.datetime(2026, 1, 5, 10, 6))       # 평균 98.95의 -4% = 94.99 → 아직
assert w.qty == 2 * q0
eng.on_price("W", 94.9, dt.datetime(2026, 1, 5, 10, 7))
assert w.qty == 0 and b.trades[-1]["사유"].startswith("손절")
print("averaging down OK")

# 12) 낙폭 한도: 고점 대비 -3%면 전부 팔고 쉼, 쉬는 동안 매수 금지, 끝나면 고점 다시 잡음
cfg = K.Config(symbols={"D": "ND"}, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0,
               position_pct=100.0, stop_loss_pct=50.0, dd_hard_pct=3.0, dd_cool_days=1, daily_loss_pct=100.0)
eng = K.Engine(cfg, verbose=False)
eng.on_price("D", 100.0, dt.datetime(2026, 1, 5, 10))
eng._fill("D", "BUY", 100.0, dt.datetime(2026, 1, 5, 10), "저점 테스트")
eng.on_price("D", 96.0, dt.datetime(2026, 1, 5, 11))
eng.on_clock(dt.datetime(2026, 1, 5, 11, 1))
d = eng.book.get("D")
assert d.qty == 0 and eng.book.pause_until == dt.date(2026, 1, 6), eng.book.pause_until
assert eng.book.can_enter("D", dt.datetime(2026, 1, 5, 12))[1] == "낙폭 한도로 쉬는 중"
eng.on_price("D", 96.0, dt.datetime(2026, 1, 7, 10))          # 휴식 끝난 날
assert eng.book.pause_until is None and abs(eng.book.peak_eq - eng.book.equity()) < 1e-6
print("drawdown stop OK")

# 13) 국면 0인 날 당일 거래: 금액 × off_scale, 장마감 청산
cfg = K.Config(symbols={"O": "ND"}, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0,
               position_pct=20.0, off_scale=0.5)
eng = K.Engine(cfg, verbose=False)
eng.on_price("O", 50.0, dt.datetime(2026, 1, 5, 10))
eng.book.exposure = 0.0
eng._fill("O", "BUY", 50.0, dt.datetime(2026, 1, 5, 10, 1), "저점 테스트")
o = eng.book.get("O")
assert o.intraday and o.qty == 20, o.qty                        # $10,000 × 20% × 0.5 / 50
eng.on_clock(dt.datetime(2026, 1, 5, 15, 55))
assert o.qty == 0 and eng.book.trades[-1]["사유"].startswith("장마감 청산")
print("off-regime intraday OK")

# 14) 위험 기준 비중: 손절 4%, 1회 위험 0.5% → 12.5%
cfg = K.Config(symbols={"R": "ND"}, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0,
               position_pct=20.0, risk_pct=0.5, stop_loss_pct=4.0)
eng = K.Engine(cfg, verbose=False)
eng.on_price("R", 100.0, dt.datetime(2026, 1, 5, 10))
eng._fill("R", "BUY", 100.0, dt.datetime(2026, 1, 5, 10, 1), "저점 테스트")
assert eng.book.get("R").qty == 12, eng.book.get("R").qty
print("risk sizing OK")

# 15) K 주식층: 필터(비중 0 종목 제외)와 따라가기(비중만큼 보유)
dk = tempfile.mkdtemp()
pd.DataFrame({"날짜": ["2026-01-02"], "구분": ["실적"], "★ 합계": [0.3], "현금": [0.7], "NVDA": [0.2], "MU": [0.1],
              "KO": [0.0]}).to_csv(os.path.join(dk, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
syms = {"NVDA": "ND", "MU": "ND", "KO": "NY"}
sk = K.DailySignals(K.Config(signals_dir=dk, symbols=syms, regime="off", sector_filter=False, stock_filter=True))
r = sk.for_day(dt.date(2026, 1, 5))
assert r.eligible == {"NVDA", "MU"} and r.kw == {"NVDA": 0.2, "MU": 0.1}, (r.eligible, r.kw)
cfg = K.Config(signals_dir=dk, symbols=syms, regime="off", sector_filter=False, trend_ma_days=0, entry_mode="k",
               fee_pct=0, slippage_pct=0, max_positions=10)
eng = K.Engine(cfg, K.Book(cfg, verbose=False), K.DailySignals(cfg), verbose=False)
for code, p in (("NVDA", 100.0), ("MU", 50.0), ("KO", 60.0)):
    eng.on_price(code, p, dt.datetime(2026, 1, 5, 10))
q = {c: eng.book.get(c).qty for c in syms}
assert q == {"NVDA": 20, "MU": 20, "KO": 0}, q
print("K stock layer OK")

# 16) 시장 급락 스위치: SPY가 전일 대비 -1.5%면 저점매수 보유분 청산 + 그날 매수 중단(SPY 자체는 거래 안 함)
cfg = K.Config(symbols={"Q": "ND"}, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0,
               mkt_flat_pct=1.5, mkt_stop_pct=1.0)
eng = K.Engine(cfg, verbose=False)
eng.on_price("SPY", 500.0, dt.datetime(2026, 1, 5, 15, 59))
eng.on_price("Q", 100.0, dt.datetime(2026, 1, 6, 10))
assert eng.mkt_prev == 500.0 and "SPY" not in eng.book.st
eng._fill("Q", "BUY", 100.0, dt.datetime(2026, 1, 6, 10), "저점 테스트")
eng.on_price("SPY", 494.0, dt.datetime(2026, 1, 6, 11))          # -1.2%: 새 매수만 막힘
eng.on_clock(dt.datetime(2026, 1, 6, 11, 1))
assert eng.book.get("Q").qty > 0 and not eng.mkt_halt
eng.on_price("SPY", 491.0, dt.datetime(2026, 1, 6, 12))          # -1.8%: 청산
eng.on_clock(dt.datetime(2026, 1, 6, 12, 1))
assert eng.book.get("Q").qty == 0 and eng.mkt_halt and "시장 급락" in eng.book.trades[-1]["사유"]
print("market switch OK")

# 17) 당일 자산 손실 한도(평가 포함)
cfg = K.Config(symbols={"Y": "ND"}, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0,
               position_pct=100.0, stop_loss_pct=50.0, day_stop_pct=2.0)
eng = K.Engine(cfg, verbose=False)
eng.on_price("Y", 100.0, dt.datetime(2026, 1, 6, 10))
eng._fill("Y", "BUY", 100.0, dt.datetime(2026, 1, 6, 10), "저점 테스트")
eng.on_price("Y", 97.5, dt.datetime(2026, 1, 6, 11))
eng.on_clock(dt.datetime(2026, 1, 6, 11, 1))
assert eng.book.get("Y").qty == 0 and eng.mkt_halt
print("day stop OK")

# 18) 투자 상한 · 손절 뒤 쉬기 · 하루 손절 횟수
cfg = K.Config(symbols={"A1": "ND", "A2": "ND"}, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0,
               slippage_pct=0, position_pct=50.0, max_invest_pct=70.0, stop_cool_days=2, max_stops_day=1,
               daily_loss_pct=100.0)
eng = K.Engine(cfg, verbose=False)
eng.on_price("A1", 100.0, dt.datetime(2026, 1, 6, 10)); eng.on_price("A2", 100.0, dt.datetime(2026, 1, 6, 10))
eng._fill("A1", "BUY", 100.0, dt.datetime(2026, 1, 6, 10), "저점 테스트")
eng._fill("A2", "BUY", 100.0, dt.datetime(2026, 1, 6, 10), "저점 테스트")
assert eng.book.get("A1").qty == 50 and eng.book.get("A2").qty == 20, (eng.book.get("A1").qty, eng.book.get("A2").qty)
eng.on_price("A1", 95.9, dt.datetime(2026, 1, 6, 11))                       # 손절
assert eng.book.get("A1").stop_until == dt.date(2026, 1, 8) and eng.book.stops_today == 1
assert eng.book.can_enter("A1", dt.datetime(2026, 1, 8, 10))[0] is False or eng.book.day <= dt.date(2026, 1, 8)
print("caps OK")

# 19) K+로테이션 두 몫: 모멘텀 1위는 rot_pct, K 비중 종목은 K 비중 × k_rot_scale, 각자 기준으로 매도
dk2 = tempfile.mkdtemp()
pd.DataFrame({"날짜": ["2026-01-02"], "구분": ["실적"], "★ 합계": [0.3], "현금": [0.7], "A": [0.0], "B": [0.2], "C": [0.1]}
             ).to_csv(os.path.join(dk2, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
syms = {"A": "ND", "B": "ND", "C": "ND"}
cfg = K.Config(signals_dir=dk2, symbols=syms, entry_mode="k+rot", rot_top=1, rot_pct=50.0, rot_days=3, k_rot_scale=1.0,
               regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0, max_positions=10,
               rot_at_open=True, daily_loss_pct=100.0)
eng = K.Engine(cfg, K.Book(cfg, verbose=False), K.DailySignals(cfg), verbose=False)
for code, closes in (("A", [10, 10, 10, 13]), ("B", [10, 10, 10, 11]), ("C", [10, 10, 10, 10.5])):
    eng.book.get(code).daily.extend(closes)
for code, p in (("A", 100.0), ("B", 50.0), ("C", 20.0)):
    eng.on_price(code, p, dt.datetime(2026, 1, 5, 9, 30))
q = {c: (eng.book.get(c).qty, eng.book.get(c).mode) for c in syms}
assert q == {"A": (50, "rot"), "B": (40, "kf"), "C": (50, "kf")}, q
print("k+rot OK")

# 20) 변동성 맞춤: 연변동성 80% 종목에 목표 40% → 비중 절반
cfg = K.Config(symbols={"V": "ND"}, entry_mode="rot", rot_top=1, rot_pct=100.0, rot_days=3, rot_vol_target=40.0,
               regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0, slippage_pct=0, rot_at_open=True,
               max_positions=1, daily_loss_pct=100.0)
eng = K.Engine(cfg, verbose=False)
r = 0.8 / math.sqrt(252)
closes = [100.0]
for i in range(25):
    closes.append(closes[-1] * (1 + (r if i % 2 == 0 else -r)) * 1.002)
eng.book.get("V").daily.extend(closes)
eng.on_price("V", closes[-1], dt.datetime(2026, 1, 5, 9, 30))
inv = eng.book.get("V").qty * closes[-1] / 10000
assert 0.4 < inv < 0.6, inv
print("vol target OK", round(inv, 2))

# 21) K 몫: 비중 2% 미만은 안 삼, 비중 0이 3거래일 이어져야 팖 — 실시간처럼 매일 상태 저장·복원해도 같아야 함
dk3 = tempfile.mkdtemp()
dates = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]
pd.DataFrame({"날짜": dates, "구분": "실적", "★ 합계": 0.1, "현금": 0.9, "B": [0.05, 0, 0, 0, 0], "C": [0.01, 0.01, 0.01, 0.01, 0.01]}
             ).to_csv(os.path.join(dk3, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
cfg = K.Config(signals_dir=dk3, symbols={"B": "ND", "C": "ND"}, entry_mode="k+rot", rot_top=1, rot_pct=0.0, rot_days=300,
               k_min_weight=0.02, k_exit_days=3, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0,
               slippage_pct=0, max_positions=10, rot_at_open=True, daily_loss_pct=100.0)
stp = os.path.join(dk3, "acct.json")
held = []
for day in ("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"):   # 매일 새 엔진 + 상태 복원(실시간 방식)
    eng = K.Engine(cfg, K.Book(cfg, verbose=False), K.DailySignals(cfg), verbose=False)
    eng.book.load_state(stp)
    d0 = pd.Timestamp(day).to_pydatetime()
    eng.on_price("B", 50.0, d0.replace(hour=9, minute=30)); eng.on_price("C", 20.0, d0.replace(hour=9, minute=30))
    held.append((eng.book.get("B").qty, eng.book.get("C").qty))
    eng.end_day(); eng.book.save_state(stp)
# 1/5: B(5%) 삼, C(1%) 안 삼 / 1/6~1/8: B 비중 0이 1·2·3일째 → 1/8에 팖
assert held == [(10, 0), (10, 0), (10, 0), (0, 0), (0, 0)], held
print("K min weight / exit days OK")

# 22) 손실 중 매도 신호 → 본전까지 대기(국면 0이어도), 손실 한도 넘으면 바로 매도 — 매일 상태 저장·복원(실시간 방식)
dk4 = tempfile.mkdtemp()
dates = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]
pd.DataFrame({"날짜": dates, "구분": "실적", "★ 합계": 0.3, "현금": 0.7, "B": [0.2, 0, 0, 0, 0], "D": [0.2, 0, 0, 0, 0]}
             ).to_csv(os.path.join(dk4, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
cfg = K.Config(signals_dir=dk4, symbols={"B": "ND", "D": "ND"}, entry_mode="k+rot", rot_top=1, rot_pct=0.0, rot_days=300,
               hold_loser_days=5, hold_loser_riskoff=True, hold_loser_stop_pct=7.0, regime="off", sector_filter=False,
               trend_ma_days=0, fee_pct=0, slippage_pct=0, sell_fee_pct=0, max_positions=10, rot_at_open=True,
               daily_loss_pct=100.0)
stp = os.path.join(dk4, "acct.json")
px = {"2026-01-05": (50.0, 50.0), "2026-01-06": (49.0, 46.0), "2026-01-07": (49.5, 45.0), "2026-01-08": (50.2, 45.0)}
held = []
for day, (pb, pd_) in px.items():
    eng = K.Engine(cfg, K.Book(cfg, verbose=False), K.DailySignals(cfg), verbose=False)
    eng.book.load_state(stp)
    d0 = pd.Timestamp(day).to_pydatetime().replace(hour=9, minute=30)
    eng.on_price("B", pb, d0); eng.on_price("D", pd_, d0)
    held.append((eng.book.get("B").qty, eng.book.get("D").qty))
    eng.end_day(); eng.book.save_state(stp)
# B: 1/6 −2% → 대기, 1/7 −1% → 대기, 1/8 본전 넘음 → 매도(이익) / D: 1/6 −8% → 손실 한도로 바로 매도
assert held == [(40, 40), (40, 0), (40, 0), (0, 0)], held
tr = eng.book.trades
assert tr[-1]["종목"] == "B" and tr[-1]["손익($)"] > 0
print("hold-to-breakeven OK")

# 23) K 상위 N종 동일비중(k_top + k_equal_pct): K 비중과 상관없이 종목마다 자산의 같은 %
dk5 = tempfile.mkdtemp()
pd.DataFrame({"날짜": ["2026-01-02"], "구분": "실적", "★ 합계": 0.35, "현금": 0.65, "B": 0.2, "D": 0.1, "E": 0.05}
             ).to_csv(os.path.join(dk5, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
cfg = K.Config(signals_dir=dk5, symbols={"B": "ND", "D": "ND", "E": "ND"}, entry_mode="k+rot", rot_top=1, rot_pct=0.0,
               rot_days=300, k_top=2, k_equal_pct=25.0, regime="off", sector_filter=False, trend_ma_days=0, fee_pct=0,
               slippage_pct=0, sell_fee_pct=0, max_positions=10, rot_at_open=True, daily_loss_pct=100.0)
eng = K.Engine(cfg, K.Book(cfg, verbose=False), K.DailySignals(cfg), verbose=False)
d0 = pd.Timestamp("2026-01-05 09:30").to_pydatetime()
for c in ("B", "D", "E"):
    eng.on_price(c, 50.0, d0)
assert {c: eng.book.get(c).qty for c in "BDE"} == {"B": 50, "D": 50, "E": 0}
print("K top-N equal weight OK")


# 24) K v0.33+ 형식: 'ETF_XLK' 열 → XLK, 종목별 '다음날 하락확률', k_symbols(58종 + K 배분 종목)
def _kdir(rows):
    d = tempfile.mkdtemp()
    pd.DataFrame(rows).to_csv(os.path.join(d, "stock_allocation_daily.csv"), index=False, encoding="utf-8-sig")
    return d


dk6 = _kdir({"날짜": ["2026-01-02", "2026-01-05"], "구분": "실적", "★ 합계": 0.9, "현금": 0.1,
             "B": [0.4, 0.4], "B 다음날 하락확률(%)": [50.0, 50.0], "D": [0.4, 0.4], "D 다음날 하락확률(%)": [40.0, 40.0],
             "ETF_XLK": [0.1, 0.01], "ETF_XLK 다음날 하락확률(%)": [45.0, 45.0], "PLTR": [0.0, 0.01], "TQQQ": [0.0, 0.5]})
u = K.k_symbols(dk6, base={"B": "ND", "D": "ND"}, since=None, min_weight=0.02)
assert u == {"B": "ND", "D": "ND", "XLK": "NA"}, u                  # PLTR(1% < 2%)·TQQQ(레버리지) 제외
assert set(K.k_symbols(dk6, base={}, since=None, min_weight=0.0)) == {"B", "D", "XLK", "PLTR"}
cfg = K.Config(signals_dir=dk6, symbols={"B": "ND", "D": "ND", "XLK": "NA"}, entry_mode="k+rot", regime="off",
               sector_filter=False, trend_ma_days=0)
s = K.DailySignals(cfg).for_day(dt.date(2026, 1, 5))
assert s.kw == {"B": 0.4, "D": 0.4, "XLK": 0.1} and s.kp1 == {"B": 50.0, "D": 40.0, "XLK": 45.0}, (s.kw, s.kp1)
print("K v0.33 columns / k_symbols OK")


def _eng(d, **kw):
    base = dict(signals_dir=d, entry_mode="k+rot", rot_top=1, rot_pct=0.0, rot_days=300, regime="off", sector_filter=False,
                trend_ma_days=0, fee_pct=0, slippage_pct=0, sell_fee_pct=0, max_positions=10, rot_at_open=True,
                daily_loss_pct=100.0, k_exit_days=1)
    base.update(kw)
    cfg = K.Config(**base)
    return K.Engine(cfg, K.Book(cfg, verbose=False), K.DailySignals(cfg), verbose=False)


# 25) batch_buys: 같은 순간 매도 먼저 → 판 돈으로 매수(시세가 들어온 순서와 무관)
dk7 = _kdir({"날짜": ["2026-01-02", "2026-01-05"], "구분": "실적", "★ 합계": 0.9, "현금": 0.1,
             "B": [0.0, 0.9], "Z": [0.9, 0.0]})
qty = {}
for batch in (False, True):
    eng = _eng(dk7, symbols={"B": "ND", "Z": "ND"}, batch_buys=batch)
    t1, t2 = pd.Timestamp("2026-01-05 09:30").to_pydatetime(), pd.Timestamp("2026-01-06 09:30").to_pydatetime()
    eng.on_price("B", 50.0, t1); eng.on_price("Z", 50.0, t1); eng.flush_pending()
    assert eng.book.get("Z").qty == 180
    eng.on_price("B", 50.0, t2); eng.on_price("Z", 50.0, t2); eng.flush_pending()   # B(살 것)가 Z(팔 것)보다 먼저 들어옴
    assert eng.book.get("Z").qty == 0
    qty[batch] = eng.book.get("B").qty
assert qty[True] == 180 and qty[False] < 180, qty
print("batch buys (sell first) OK")

# 26) k_fit: K 몫 배율 = min(k_rot_scale, (1 − 모멘텀 몫) ÷ K 비중 합) / 27) k_drop1_max: 내일 하락확률 높은 K 종목은 안 삼
eng = _eng(dk6, symbols={"B": "ND", "D": "ND"}, k_fit=True, k_rot_scale=1.5, rot_pct=50.0)
t2 = pd.Timestamp("2026-01-06 09:30").to_pydatetime()
eng.on_price("B", 50.0, t2); eng.on_price("D", 50.0, t2)
assert abs(eng.book.k_scale_eff - 0.5 / 0.8) < 1e-9 and eng.book.get("B").qty == int(10000 * 0.4 * 0.625 / 50), eng.book.get("B").qty
eng = _eng(dk6, symbols={"B": "ND", "D": "ND"}, k_drop1_max=47.0)
eng.on_price("B", 50.0, t2); eng.on_price("D", 50.0, t2)
assert eng.book.get("B").qty == 0 and eng.book.get("D").qty == 80
print("k_fit / k_drop1_max OK")
print("ALL NEW OPTIONS OK")
