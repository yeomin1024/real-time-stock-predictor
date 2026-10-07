"""1000% 탐색 라운드 정의 — (변형이름, Config 덮어쓰기). 출발점 C0 = 현재 기본값(C1 + 수수료 0.07% + 보유 5일), 58종."""
ROUNDS = {}

# X01: 자금 활용 — C0는 장 마감 기준 평균 28%만 투자(국면 0인 날 33%, 신호 없는 날 많음). 신용 없이(현금 100% 한도) 비중·종목수·국면 사용법
ROUNDS["X01_utilization"] = [
    ("C0", {}),
    ("5종목×30%", {"position_pct": 30.0}),
    ("5종목×40%", {"position_pct": 40.0}),
    ("3종목×33%", {"max_positions": 3, "position_pct": 33.3}),
    ("8종목×20%", {"max_positions": 8, "position_pct": 20.0}),
    ("10종목×20%", {"max_positions": 10, "position_pct": 20.0}),
    ("국면켜기끄기", {"regime_scale": False}),
    ("국면켜기끄기+5×30%", {"regime_scale": False, "position_pct": 30.0}),
    ("일일손실한도끔", {"daily_loss_pct": 100.0}),
    ("종목당2회", {"max_trades_per_symbol": 2}),
    ("RSI35", {"rsi_buy": 35.0}),
    ("국면끔(지표만)", {"regime": "off"}),
]
# X02: 가상 신용(레버리지) — 매수 가능 금액 = 현금 + 자산×(L−1), 빌린 돈 연 7% 이자
ROUNDS["X02_leverage"] = [
    ("L1.5 5×30%", {"leverage": 1.5, "position_pct": 30.0}),
    ("L2 5×40%", {"leverage": 2.0, "position_pct": 40.0}),
    ("L3 5×60%", {"leverage": 3.0, "position_pct": 60.0}),
    ("L2 국면켜기끄기 5×40%", {"leverage": 2.0, "position_pct": 40.0, "regime_scale": False}),
    ("L2 8×25%", {"leverage": 2.0, "max_positions": 8, "position_pct": 25.0}),
    ("L2 10×20%", {"leverage": 2.0, "max_positions": 10, "position_pct": 20.0}),
    ("L3 10×30%", {"leverage": 3.0, "max_positions": 10, "position_pct": 30.0}),
    ("L2 5×40% 손실한도4%", {"leverage": 2.0, "position_pct": 40.0, "daily_loss_pct": 4.0}),
]

# X03: 신호 늘리기 — 유니버스에 레버리지 ETF(실계좌로도 살 수 있는 '레버리지') · 산업/섹터 ETF 추가
from xres import ETF_LEV, IND_ETFS
LEV15 = sorted(ETF_LEV)
LEV_IDX = ["TQQQ", "UPRO", "SOXL", "TECL"]
sc1 = {k: 1.0 for k in LEV15}
sc_half = {k: v / 2 for k, v in ETF_LEV.items()}
sc_ind = {k: 0.5 for k in IND_ETFS}
L2 = {"leverage": 2.0, "position_pct": 40.0, "daily_loss_pct": 4.0}
ROUNDS["X03_universe"] = [
    ("C0+3배지수4", {"add": LEV_IDX}),
    ("C0+레버ETF15", {"add": LEV15}),
    ("C0+레버ETF15 폭×배율/2", {"add": LEV15, "sym_scale": sc_half}),
    ("레버ETF15만", {"universe": LEV15}),
    ("레버ETF15만 폭×배율/2", {"universe": LEV15, "sym_scale": sc_half}),
    ("C0+2배개별3", {"add": ["NVDL", "TSLL", "CONL"]}),
    ("C0+산업ETF38 폭×0.5", {"add": IND_ETFS, "sym_scale": sc_ind}),
    ("C0+산업ETF38", {"add": IND_ETFS}),
    ("L2손실4+레버ETF15", dict(L2, add=LEV15)),
    ("L2손실4+산업ETF38 폭×0.5", dict(L2, add=IND_ETFS, sym_scale=sc_ind)),
]
# X04: 모멘텀 상위만(강한 종목의 눌림목) + 신용 조합
ROUNDS["X04_momentum_combo"] = [
    ("C0+모멘텀60 상위10", {"mom_top": 10, "mom_days": 60}),
    ("C0+모멘텀60 상위20", {"mom_top": 20, "mom_days": 60}),
    ("C0+모멘텀120 상위15", {"mom_top": 15, "mom_days": 120}),
    ("C0+모멘텀20 상위15", {"mom_top": 15, "mom_days": 20}),
    ("L2손실4", L2),
    ("L2손실4+모멘텀60 상위20", dict(L2, mom_top=20, mom_days=60)),
    ("L2손실4+8×25%", dict(L2, max_positions=8, position_pct=25.0)),
    ("L2손실4+종목당2회", dict(L2, max_trades_per_symbol=2)),
    ("L2손실4+8×30%+2회", dict(L2, max_positions=8, position_pct=30.0, max_trades_per_symbol=2)),
    ("L2.5 5×50% 손실5%", {"leverage": 2.5, "position_pct": 50.0, "daily_loss_pct": 5.0}),
    ("L3 5×60% 손실6%", {"leverage": 3.0, "position_pct": 60.0, "daily_loss_pct": 6.0}),
    ("L2손실4+국면끔", dict(L2, regime="off")),
]

# X05: 견고성 — IS로 처음 목표를 넘은 X1 = L2.5(가상 신용 2.5배) · 5종목×50% · 일일 손실한도 5%
import random
from xres import BASE58, SP100
X1 = {"leverage": 2.5, "position_pct": 50.0, "daily_loss_pct": 5.0}
_h = list(BASE58)
random.Random(1).shuffle(_h)
ROUNDS["X05_robust"] = [
    ("X1", X1),
    ("X1 고가먼저", dict(X1, path_order="high_first")),
    ("X1 무작위1", dict(X1, path_order="random", path_seed=1)),
    ("X1 무작위2", dict(X1, path_order="random", path_seed=2)),
    ("X1 수수료0.15", dict(X1, fee_pct=0.15)),
    ("X1 슬리피지0.15", dict(X1, slippage_pct=0.15)),
    ("X1 이자10%", dict(X1, margin_rate_pct=10.0)),
    ("X1 절반a", dict(X1, universe=sorted(_h[:29]))),
    ("X1 절반b", dict(X1, universe=sorted(_h[29:]))),
    ("X1 SP100(2023)", dict(X1, universe=SP100)),
    ("C0 SP100(2023)", {"universe": SP100}),
    ("X1 SPY국면(M 대신)", dict(X1, regime="spy")),
    ("X1 국면·섹터끔", dict(X1, regime="off", sector_filter=False)),
    ("X1 익2.5", dict(X1, min_profit_pct=2.5)), ("X1 익3.5", dict(X1, min_profit_pct=3.5)),
    ("X1 손3.5", dict(X1, stop_loss_pct=3.5)), ("X1 손4.5", dict(X1, stop_loss_pct=4.5)),
    ("X1 보4", dict(X1, max_hold_days=4)), ("X1 보6", dict(X1, max_hold_days=6)),
    ("X1+종목당2회", dict(X1, max_trades_per_symbol=2)),
]

# X06: 새 로직 — 돌파 매수(일봉 N일 최고 종가 돌파 → 넓은 추적청산으로 큰 추세를 끝까지). 저점매수는 이익을 +3%대에서 끊음
B20 = {"entry_mode": "brk", "brk_days": 20, "brk_stop_pct": 8.0, "brk_trail_pct": 10.0, "brk_hold_days": 40}
ROUNDS["X06_breakout"] = [
    ("C0(재현)", {}),
    ("돌파20", B20),
    ("돌파55", dict(B20, brk_days=55)),
    ("돌파20 추적15 보유60", dict(B20, brk_trail_pct=15.0, brk_hold_days=60)),
    ("돌파20 손6 추적8", dict(B20, brk_stop_pct=6.0, brk_trail_pct=8.0)),
    ("돌파20 10×10%", dict(B20, max_positions=10, position_pct=10.0)),
    ("돌파20 3×33%", dict(B20, max_positions=3, position_pct=33.3)),
    ("돌파20 국면끔", dict(B20, regime="off")),
    ("저점+돌파20", dict(B20, entry_mode="both")),
    ("저점+돌파20 8×20%", dict(B20, entry_mode="both", max_positions=8)),
    ("돌파20 +레버ETF15", dict(B20, add=LEV15)),
    ("돌파20 SP100(2023)", dict(B20, universe=SP100)),
]

# X07: 신용 없이 좋아진 것들 합치기(U = C0 + 레버리지 ETF 15 + 종목당 2회) → 1000%에 필요한 최소 신용 배율 찾기
U = {"add": LEV15, "max_trades_per_symbol": 2}
ROUNDS["X07_combo"] = [
    ("U", U),
    ("U 8×20%", dict(U, max_positions=8)),
    ("U 손실한도끔", dict(U, daily_loss_pct=100.0)),
    ("U L1.5 5×30% 손실3", dict(U, leverage=1.5, position_pct=30.0, daily_loss_pct=3.0)),
    ("U L2 5×40% 손실4", dict(U, leverage=2.0, position_pct=40.0, daily_loss_pct=4.0)),
    ("U L2 8×25% 손실4", dict(U, leverage=2.0, max_positions=8, position_pct=25.0, daily_loss_pct=4.0)),
    ("U L2.5 5×50% 손실5", dict(U, leverage=2.5, position_pct=50.0, daily_loss_pct=5.0)),
    ("U SP100", dict(U, universe=SP100)),
    ("U SP100 8×20%", dict(U, universe=SP100, max_positions=8)),
    ("U L2 SP100", dict(U, universe=SP100, leverage=2.0, position_pct=40.0, daily_loss_pct=4.0)),
    ("U L2.5 SP100", dict(U, universe=SP100, leverage=2.5, position_pct=50.0, daily_loss_pct=5.0)),
    ("X1+종목당2회 SP100", dict(X1, universe=SP100, max_trades_per_symbol=2)),
]

# X08: 견고성 — X2 = U + 신용 2배(5종목×40%, 일일 손실한도 4%). X07에서 IS로 목표를 넘은 것 중 신용 배율이 가장 낮음
X2 = dict(U, leverage=2.0, position_pct=40.0, daily_loss_pct=4.0)
LEV_IDX12 = [k for k in LEV15 if k not in ("NVDL", "TSLL", "CONL")]
ROUNDS["X08_robust_X2"] = [
    ("X2", X2),
    ("X2 고가먼저", dict(X2, path_order="high_first")),
    ("X2 무작위1", dict(X2, path_order="random", path_seed=1)),
    ("X2 무작위2", dict(X2, path_order="random", path_seed=2)),
    ("X2 수수료0.15", dict(X2, fee_pct=0.15)),
    ("X2 슬리피지0.15", dict(X2, slippage_pct=0.15)),
    ("X2 이자10%", dict(X2, margin_rate_pct=10.0)),
    ("X2 절반a", dict(X2, universe=sorted(_h[:29]))),
    ("X2 절반b", dict(X2, universe=sorted(_h[29:]))),
    ("X2 SPY국면(M 대신)", dict(X2, regime="spy")),
    ("X2 개별2배ETF뺌", dict(X2, add=LEV_IDX12)),
    ("X2 익2.5", dict(X2, min_profit_pct=2.5)), ("X2 익3.5", dict(X2, min_profit_pct=3.5)),
    ("X2 손3.5", dict(X2, stop_loss_pct=3.5)), ("X2 손4.5", dict(X2, stop_loss_pct=4.5)),
    ("X2 보4", dict(X2, max_hold_days=4)), ("X2 보6", dict(X2, max_hold_days=6)),
    ("X2 손실한도끔", dict(X2, daily_loss_pct=100.0)),
]

# ===== 사용자 지시(2026-10-03): 레버리지 사용 금지 → 신용 1배(현금 안) · 레버리지 ETF 제외, 주식만 =====
# Y01: 저점매수 개선 조합 + 변동성 맞춤 폭(종목마다 최근 변동성에 맞춰 손절·익절 폭 조정)
A = {"max_trades_per_symbol": 2, "daily_loss_pct": 100.0}
ROUNDS["Y01_dip_nolev"] = [
    ("C0", {}),
    ("A(2회·손실한도끔)", A),
    ("A 5×30%", dict(A, position_pct=30.0)),
    ("A 5×40%", dict(A, position_pct=40.0)),
    ("A 국면켜기끄기", dict(A, regime_scale=False)),
    ("A 변동성2.0", dict(A, vol_ref_pct=2.0)),
    ("A 변동성2.5", dict(A, vol_ref_pct=2.5)),
    ("A 변동성3.0", dict(A, vol_ref_pct=3.0)),
    ("A 5×40% 변동성2.5", dict(A, position_pct=40.0, vol_ref_pct=2.5)),
    ("A SP100", dict(A, universe=SP100)),
    ("A 변동성2.5 SP100", dict(A, vol_ref_pct=2.5, universe=SP100)),
]
# Y02: 새 로직 — 모멘텀 로테이션(일봉 N일 수익률 상위 종목을 같은 비중으로 들고, 정해진 날마다 갈아탐). M·S·50일선 필터 유지
ROT = {"entry_mode": "rot", "rot_top": 5, "rot_pct": 20.0, "max_positions": 5, "rot_days": 63, "rot_every": 5,
       "daily_loss_pct": 100.0}
ROUNDS["Y02_rotation"] = [
    ("로테이션 상위5 63일 5일마다", ROT),
    ("상위3", dict(ROT, rot_top=3, rot_pct=33.3, max_positions=3)),
    ("상위10", dict(ROT, rot_top=10, rot_pct=10.0, max_positions=10)),
    ("126일", dict(ROT, rot_days=126)),
    ("21일", dict(ROT, rot_days=21)),
    ("21일마다", dict(ROT, rot_every=21)),
    ("고점대비-15% 손절", dict(ROT, rot_stop_pct=15.0)),
    ("국면켜기끄기", dict(ROT, regime_scale=False)),
    ("국면·섹터끔", dict(ROT, regime="off", sector_filter=False)),
    ("상위5 SP100", dict(ROT, universe=SP100)),
    ("상위3 SP100", dict(ROT, rot_top=3, rot_pct=33.3, max_positions=3, universe=SP100)),
    ("126일 SP100", dict(ROT, rot_days=126, universe=SP100)),
]
# Y03: 로테이션 + M 켜기·끄기(G)를 중심으로 조합
G = dict(ROT, regime_scale=False)
ROUNDS["Y03_rot_combo"] = [
    ("G(로테이션·M켜기끄기)", G),
    ("G 126일", dict(G, rot_days=126)),
    ("G 상위4", dict(G, rot_top=4, rot_pct=25.0, max_positions=4)),
    ("G 상위3", dict(G, rot_top=3, rot_pct=33.3, max_positions=3)),
    ("G 3일마다", dict(G, rot_every=3)),
    ("G 10일마다", dict(G, rot_every=10)),
    ("G 섹터끔", dict(G, sector_filter=False)),
    ("G 50일선끔", dict(G, trend_ma_days=0)),
    ("G 손절20", dict(G, rot_stop_pct=20.0)),
    ("G+저점매수(남는 현금)", dict(G, entry_mode="rot+dip", max_positions=8, max_trades_per_symbol=2)),
    ("G SP100", dict(G, universe=SP100)),
    ("G 상위3 SP100", dict(G, rot_top=3, rot_pct=33.3, max_positions=3, universe=SP100)),
    ("G 126일 SP100", dict(G, rot_days=126, universe=SP100)),
]
# Y04: IS가 가장 좋았던 G 126일을 중심으로 + 남는 현금 저점매수 · 50일선 · 종목 수 · 주기 · 모멘텀 기간 이웃
G126 = dict(G, rot_days=126)
GD = dict(G126, entry_mode="rot+dip", max_positions=8, max_trades_per_symbol=2)
ROUNDS["Y04_rot126_combo"] = [
    ("G126+저점", GD),
    ("G126 50일선끔", dict(G126, trend_ma_days=0)),
    ("G126+저점 50일선끔", dict(GD, trend_ma_days=0)),
    ("G126 상위4", dict(G126, rot_top=4, rot_pct=25.0, max_positions=4)),
    ("G126+저점 상위4", dict(GD, rot_top=4, rot_pct=25.0, max_positions=7)),
    ("G126 10일마다", dict(G126, rot_every=10)),
    ("G100", dict(G, rot_days=100)),
    ("G150", dict(G, rot_days=150)),
    ("G100+저점", dict(GD, rot_days=100)),
    ("G150+저점", dict(GD, rot_days=150)),
    ("G126+저점 SP100", dict(GD, universe=SP100)),
    ("G126 50일선끔 SP100", dict(G126, trend_ma_days=0, universe=SP100)),
]
# Y05: 견고성 — N1 = G126+저점 50일선끔 (레버리지 없이 IS가 가장 좋음: IS 연 122%, 샤프 3.30)
N1 = dict(GD, trend_ma_days=0)
ROUNDS["Y05_robust_N1"] = [
    ("N1", N1),
    ("N1 고가먼저", dict(N1, path_order="high_first")),
    ("N1 무작위1", dict(N1, path_order="random", path_seed=1)),
    ("N1 무작위2", dict(N1, path_order="random", path_seed=2)),
    ("N1 수수료0.15", dict(N1, fee_pct=0.15)),
    ("N1 슬리피지0.15", dict(N1, slippage_pct=0.15)),
    ("N1 절반a", dict(N1, universe=sorted(_h[:29]))),
    ("N1 절반b", dict(N1, universe=sorted(_h[29:]))),
    ("N1 SPY국면(M 대신)", dict(N1, regime="spy")),
    ("N1 섹터끔", dict(N1, sector_filter=False)),
    ("N1 국면·섹터끔", dict(N1, regime="off", sector_filter=False)),
    ("N1 100일", dict(N1, rot_days=100)), ("N1 150일", dict(N1, rot_days=150)),
    ("N1 상위4", dict(N1, rot_top=4, rot_pct=25.0, max_positions=7)),
    ("N1 상위6", dict(N1, rot_top=6, rot_pct=16.7, max_positions=9)),
    ("N1 3일마다", dict(N1, rot_every=3)), ("N1 10일마다", dict(N1, rot_every=10)),
    ("N1 저점 종목당1회", dict(N1, max_trades_per_symbol=1)),
    ("N1 SP100", dict(N1, universe=SP100)),
]
# Y06: N2 = N1 섹터필터 끔(Y05에서 IS 연 128.5%로 모든 목표 통과, S 모델 의존 제거) 견고성
N2 = dict(N1, sector_filter=False)
ROUNDS["Y06_robust_N2"] = [
    ("N2", N2),
    ("N2 고가먼저", dict(N2, path_order="high_first")),
    ("N2 무작위1", dict(N2, path_order="random", path_seed=1)),
    ("N2 수수료0.15", dict(N2, fee_pct=0.15)),
    ("N2 슬리피지0.15", dict(N2, slippage_pct=0.15)),
    ("N2 절반a", dict(N2, universe=sorted(_h[:29]))),
    ("N2 절반b", dict(N2, universe=sorted(_h[29:]))),
    ("N2 SPY국면(M 대신)", dict(N2, regime="spy")),
    ("N2 100일", dict(N2, rot_days=100)), ("N2 150일", dict(N2, rot_days=150)),
    ("N2 상위4", dict(N2, rot_top=4, rot_pct=25.0, max_positions=7)),
    ("N2 10일마다", dict(N2, rot_every=10)),
    ("N2 SP100", dict(N2, universe=SP100)),
]

# ===== 목표 5000% (2026-10-04), 레버리지 금지 유지 =====
# Z01: N2에서 더 모으기 — 로테이션 종목 수(집중), 버퍼(순위 안이면 계속 보유), 주기, 모멘텀 기간·점수, 저점매수 유무
ROUNDS["Z01_concentrate"] = [
    ("N2(재현)", N2),
    ("상위3", dict(N2, rot_top=3, rot_pct=33.3, max_positions=6)),
    ("상위2", dict(N2, rot_top=2, rot_pct=50.0, max_positions=5)),
    ("상위1", dict(N2, rot_top=1, rot_pct=100.0, max_positions=4)),
    ("버퍼10", dict(N2, rot_keep=10)),
    ("상위3 버퍼6", dict(N2, rot_top=3, rot_pct=33.3, max_positions=6, rot_keep=6)),
    ("상위2 버퍼5", dict(N2, rot_top=2, rot_pct=50.0, max_positions=5, rot_keep=5)),
    ("10일마다", dict(N2, rot_every=10)),
    ("63일", dict(N2, rot_days=63)),
    ("샤프점수", dict(N2, rot_score="sharpe")),
    ("상위3 63일", dict(N2, rot_top=3, rot_pct=33.3, max_positions=6, rot_days=63)),
    ("로테이션만", dict(N2, entry_mode="rot", max_positions=5)),
    ("상위3 10일마다", dict(N2, rot_top=3, rot_pct=33.3, max_positions=6, rot_every=10)),
    ("상위2 SP100", dict(N2, rot_top=2, rot_pct=50.0, max_positions=5, universe=SP100)),
]
# Z02: 엔진 결함 수정(±30% 넘는 진짜 갭 뒤로 가격이 멈추던 문제) 후 다시 기준 잡기 — 이전 숫자는 모두 이 결함 영향
T3 = dict(N2, rot_top=3, rot_pct=33.3, max_positions=6)
T2 = dict(N2, rot_top=2, rot_pct=50.0, max_positions=5)
ROUNDS["Z02_rebase_gapfix"] = [
    ("C0", {}),
    ("A", A),
    ("N2", N2),
    ("N2 SP100", dict(N2, universe=SP100)),
    ("상위3", T3),
    ("상위2", T2),
    ("상위1", dict(N2, rot_top=1, rot_pct=100.0, max_positions=4)),
    ("상위3 버퍼6", dict(T3, rot_keep=6)),
    ("상위2 버퍼5", dict(T2, rot_keep=5)),
    ("상위3 10일마다", dict(T3, rot_every=10)),
    ("상위2 10일마다", dict(T2, rot_every=10)),
    ("상위2 로테이션만", dict(T2, entry_mode="rot", max_positions=2)),
    ("상위3 SP100", dict(T3, universe=SP100)),
    ("상위2 SP100", dict(T2, universe=SP100)),
]
# Z03: 상위2(T2) 중심 — 모멘텀 기간, 최근 며칠 빼기, 국면 0일 때 보유 유지, 점수, 버퍼, 저점매수 몫
ROUNDS["Z03_top2"] = [
    ("T2 100일", dict(T2, rot_days=100)),
    ("T2 150일", dict(T2, rot_days=150)),
    ("T2 189일", dict(T2, rot_days=189)),
    ("T2 최근5일뺌", dict(T2, rot_skip=5)),
    ("T2 최근21일뺌", dict(T2, rot_skip=21)),
    ("T2 국면0 보유유지", dict(T2, rot_regime_exit=False)),
    ("T2 샤프점수", dict(T2, rot_score="sharpe")),
    ("T2 버퍼3", dict(T2, rot_keep=3)),
    ("T2 3일마다", dict(T2, rot_every=3)),
    ("T2 섹터필터켬", dict(T2, sector_filter=True)),
    ("T2 저점 30%", dict(T2, position_pct=30.0)),
    ("T2 저점 2자리", dict(T2, max_positions=4)),
    ("상위1 버퍼2", dict(N2, rot_top=1, rot_pct=100.0, max_positions=4, rot_keep=2)),
    ("T2 국면0 보유유지 SP100", dict(T2, rot_regime_exit=False, universe=SP100)),
]
# Z04: 견고성 — Q1 = 상위2 로테이션(126일 수익률, 최근 21일 제외 = 6-1 모멘텀) + 남는 현금 저점매수
Q1 = dict(T2, rot_skip=21)
ROUNDS["Z04_robust_Q1"] = [
    ("Q1", Q1),
    ("Q1 고가먼저", dict(Q1, path_order="high_first")),
    ("Q1 무작위1", dict(Q1, path_order="random", path_seed=1)),
    ("Q1 무작위2", dict(Q1, path_order="random", path_seed=2)),
    ("Q1 수수료0.15", dict(Q1, fee_pct=0.15)),
    ("Q1 슬리피지0.15", dict(Q1, slippage_pct=0.15)),
    ("Q1 절반a", dict(Q1, universe=sorted(_h[:29]))),
    ("Q1 절반b", dict(Q1, universe=sorted(_h[29:]))),
    ("Q1 SPY국면(M 대신)", dict(Q1, regime="spy")),
    ("Q1 최근10일뺌", dict(Q1, rot_skip=10)), ("Q1 최근15일뺌", dict(Q1, rot_skip=15)),
    ("Q1 최근30일뺌", dict(Q1, rot_skip=30)), ("Q1 최근42일뺌", dict(Q1, rot_skip=42)),
    ("Q1 100일", dict(Q1, rot_days=100)), ("Q1 150일", dict(Q1, rot_days=150)),
    ("Q1 상위3", dict(Q1, rot_top=3, rot_pct=33.3, max_positions=6)),
    ("Q1 3일마다", dict(Q1, rot_every=3)), ("Q1 10일마다", dict(Q1, rot_every=10)),
    ("Q1 SP100", dict(Q1, universe=SP100)),
    ("Q1 상위3 SP100", dict(Q1, rot_top=3, rot_pct=33.3, max_positions=6, universe=SP100)),
]
# Z05: 봉 안 가격 순서에 덜 흔들리는 후보 고르기 — 후보마다 경로 4가지(기본·고가먼저·무작위1·2) 중앙값으로 비교
_CANDS = {"Q1 10일마다": dict(Q1, rot_every=10), "Q1 3일마다": dict(Q1, rot_every=3), "Q1 30일뺌": dict(Q1, rot_skip=30),
          "Q1 100일": dict(Q1, rot_days=100), "상위1 버퍼2": dict(N2, rot_top=1, rot_pct=100.0, max_positions=4, rot_keep=2),
          "T2": T2}
_Z5 = []
for _n, _c in _CANDS.items():
    _Z5 += [(f"{_n} 고가먼저", dict(_c, path_order="high_first")),
            (f"{_n} 무작위1", dict(_c, path_order="random", path_seed=1)),
            (f"{_n} 무작위2", dict(_c, path_order="random", path_seed=2))]
Q1R = dict(Q1, entry_mode="rot", max_positions=2)            # 로테이션만(저점매수 없음)
_Z5 += [("Q1 로테이션만", Q1R), ("Q1 로테이션만 고가먼저", dict(Q1R, path_order="high_first")),
        ("Q1 로테이션만 무작위1", dict(Q1R, path_order="random", path_seed=1)),
        ("Q1 로테이션만 무작위2", dict(Q1R, path_order="random", path_seed=2))]
ROUNDS["Z05_path_median"] = _Z5
# Z06: 로테이션만 + 장 시작 가격에 사고팔기(봉 안 순서 가정과 무관) — 기본 경로·고가먼저 둘 다 돌려 무관한지 확인
RO = dict(Q1R, rot_at_open=True)
ROUNDS["Z06_rot_open"] = [
    ("RO", RO), ("RO 고가먼저", dict(RO, path_order="high_first")),
    ("RO 10일마다", dict(RO, rot_every=10)), ("RO 10일마다 고가먼저", dict(RO, rot_every=10, path_order="high_first")),
    ("RO 3일마다", dict(RO, rot_every=3)),
    ("RO 15일뺌", dict(RO, rot_skip=15)), ("RO 30일뺌", dict(RO, rot_skip=30)),
    ("RO 100일", dict(RO, rot_days=100)), ("RO 150일", dict(RO, rot_days=150)),
    ("RO 상위1 버퍼2", dict(RO, rot_top=1, rot_pct=100.0, max_positions=1, rot_keep=2)),
    ("RO 상위3", dict(RO, rot_top=3, rot_pct=33.3, max_positions=3)),
    ("RO 버퍼3", dict(RO, rot_keep=3)),
    ("RO SP100", dict(RO, universe=SP100)),
    ("RO 상위3 SP100", dict(RO, rot_top=3, rot_pct=33.3, max_positions=3, universe=SP100)),
]
# Z07: 견고성 — RO1 = 1종목 로테이션(6-1 모멘텀 1위, 2위 안이면 유지, 장 시작 가격) / RO2 = 2종목·10거래일마다
RO1 = dict(RO, rot_top=1, rot_pct=100.0, max_positions=1, rot_keep=2)
RO2 = dict(RO, rot_every=10)
ROUNDS["Z07_robust_RO"] = [
    ("RO1", RO1),
    ("RO1 수수료0.15", dict(RO1, fee_pct=0.15)), ("RO1 슬리피지0.15", dict(RO1, slippage_pct=0.15)),
    ("RO1 절반a", dict(RO1, universe=sorted(_h[:29]))), ("RO1 절반b", dict(RO1, universe=sorted(_h[29:]))),
    ("RO1 SPY국면(M 대신)", dict(RO1, regime="spy")),
    ("RO1 버퍼3", dict(RO1, rot_keep=3)), ("RO1 10일마다", dict(RO1, rot_every=10)),
    ("RO1 15일뺌", dict(RO1, rot_skip=15)), ("RO1 30일뺌", dict(RO1, rot_skip=30)),
    ("RO1 100일", dict(RO1, rot_days=100)), ("RO1 150일", dict(RO1, rot_days=150)),
    ("RO1 SP100", dict(RO1, universe=SP100)),
    ("RO2", RO2),
    ("RO2 절반a", dict(RO2, universe=sorted(_h[:29]))), ("RO2 절반b", dict(RO2, universe=sorted(_h[29:]))),
    ("RO2 SPY국면(M 대신)", dict(RO2, regime="spy")),
    ("RO2 100일", dict(RO2, rot_days=100)), ("RO2 버퍼3", dict(RO2, rot_keep=3)),
    ("RO2 SP100", dict(RO2, universe=SP100)),
]

# ===== 2026-10-04 사용자: MDD −5% 이내 · 거의 매일 거래 · 수익 최대, 최신 M v1.83·S v0.98·I v0.63·K v0.31 신호 =====
ROUNDS["W00_repro_oldsig"] = [("C0", {})]                     # SIG=signals 로 돌려 Z02 C0(+273.98%) 재현 확인
KF = dict(entry_mode="k", max_positions=30, daily_loss_pct=100.0, regime_scale=False, sector_filter=False,
          trend_ma_days=0, rot_at_open=True)
ROUNDS["W01_latest_signals"] = [
    ("C0", {}), ("A", A), ("N2", N2), ("R1", RO1),
    ("C0 K필터", dict(stock_filter=True)), ("A K필터", dict(A, stock_filter=True)),
    ("K따라", KF), ("K따라+저점", dict(KF, entry_mode="k+dip", position_pct=10.0)),
    ("A 국면0 당일거래", dict(A, off_scale=0.5)),
    ("A 5×10%", dict(A, position_pct=10.0)),
    ("A 낙폭한도4", dict(A, dd_hard_pct=4.0)),
    ("A 위험0.5%", dict(A, risk_pct=0.5)),
]
# W02: MDD −5% · 매일 거래 탐색 — 중심 KD = K따라+저점(샤프 4.11). 비중 축소 · 국면0 당일거래 · 낙폭 브레이크 · 위험 비중 · 물타기
KD = dict(KF, entry_mode="k+dip", position_pct=10.0)
AO = dict(A, off_scale=0.5)
ROUNDS["W02_mdd5"] = [
    ("A 국면0 당일거래", AO),
    ("A 7% 국면0", dict(AO, position_pct=7.0)),
    ("KD k0.6 저점7%", dict(KD, k_scale=0.6, position_pct=7.0)),
    ("KD k0.5 저점5%", dict(KD, k_scale=0.5, position_pct=5.0)),
    ("KD k0.7 저점7% 국면0", dict(KD, k_scale=0.7, position_pct=7.0, off_scale=0.5)),
    ("KD 국면0", dict(KD, off_scale=0.5)),
    ("KD 소프트브레이크2.5", dict(KD, dd_soft_pct=2.5, dd_soft_scale=0.5)),
    ("KD 위험0.4%", dict(KD, risk_pct=0.4)),
    ("KD 종목당2회", dict(KD, max_trades_per_symbol=2)),
    ("KD 손절3", dict(KD, stop_loss_pct=3.0)),
    ("KD 물타기2%×1", dict(KD, add_drop_pct=2.0, add_max=1)),
    ("KD k0.6 저점7% 국면0 소프트2", dict(KD, k_scale=0.6, position_pct=7.0, off_scale=0.5, dd_soft_pct=2.0)),
    ("KD k0.6 저점7% 국면0 2회", dict(KD, k_scale=0.6, position_pct=7.0, off_scale=0.5, max_trades_per_symbol=2)),
    ("KD 저점 15%", dict(KD, position_pct=15.0)),
]
# W03: 실적 발표 회피(당일·전날 청산·매수 금지) + K 비중 매일 맞추기 + 비중 조절
KDO = dict(KD, off_scale=0.5)
KDO7 = dict(KDO, k_scale=0.7, position_pct=7.0)
E = {"earn_avoid": True}
ROUNDS["W03_earnings"] = [
    ("KDO 실적회피", dict(KDO, **E)),
    ("KDO7 실적회피", dict(KDO7, **E)),
    ("AO 실적회피", dict(AO, **E)),
    ("AO 10% 실적회피", dict(AO, position_pct=10.0, **E)),
    ("KDO 실적회피 K맞춤20", dict(KDO, k_rebalance_pct=20.0, **E)),
    ("KDO7 실적회피 K맞춤20", dict(KDO7, k_rebalance_pct=20.0, **E)),
    ("KDO 실적회피 k0.7 저점8", dict(KDO, k_scale=0.7, position_pct=8.0, **E)),
    ("KDO 실적회피 k0.6 저점6", dict(KDO, k_scale=0.6, position_pct=6.0, **E)),
    ("KDO 실적회피 낙폭한도4", dict(KDO, dd_hard_pct=4.0, dd_cool_days=2, **E)),
    ("KDO 실적회피 손절3", dict(KDO, stop_loss_pct=3.0, **E)),
    ("KDO 실적회피 국면0×0.3", dict(KDO, off_scale=0.3, **E)),
    ("KDO 실적회피 국면0×0.7", dict(KDO, off_scale=0.7, **E)),
    ("KDO 실적회피 2회", dict(KDO, max_trades_per_symbol=2, **E)),
    ("KDO7 실적회피 2회 K맞춤20", dict(KDO7, max_trades_per_symbol=2, k_rebalance_pct=20.0, **E)),
]
# W04: 시장 급락 스위치(SPY 당일 하락 시 저점매수 중단·청산) + 당일 자산 손실 한도
M15 = {"mkt_flat_pct": 1.5, "mkt_stop_pct": 1.0}
M10 = {"mkt_flat_pct": 1.0, "mkt_stop_pct": 0.7}
ROUNDS["W04_market_switch"] = [
    ("KDO 시장1.5", dict(KDO, **M15)),
    ("KDO 시장1.0", dict(KDO, **M10)),
    ("KDO 당일-1.5", dict(KDO, day_stop_pct=1.5)),
    ("KDO 시장1.5 당일1.5", dict(KDO, day_stop_pct=1.5, **M15)),
    ("KDO7 시장1.5 당일1.5", dict(KDO7, day_stop_pct=1.5, **M15)),
    ("AO 시장1.5 당일1.5", dict(AO, day_stop_pct=1.5, **M15)),
    ("KDO 시장1.0 당일1.0", dict(KDO, day_stop_pct=1.0, **M10)),
    ("KDO7 시장1.0 당일1.0", dict(KDO7, day_stop_pct=1.0, **M10)),
    ("KDO 시장1.5 당일1.5 소프트2", dict(KDO, day_stop_pct=1.5, dd_soft_pct=2.0, **M15)),
    ("KDO k0.8 시장1.5 당일1.5", dict(KDO, k_scale=0.8, day_stop_pct=1.5, **M15)),
    ("KDO 시장2 당일2", dict(KDO, day_stop_pct=2.0, mkt_flat_pct=2.0, mkt_stop_pct=1.5)),
    ("KDO 시장1.5 당일1.5 실적회피", dict(KDO, day_stop_pct=1.5, **M15, **E)),
]
# W05: 급락 때 K 보유분도 정리(halt_all) + 전체 비중 축소로 IS MDD −5% 안에
KM = dict(KDO, **M15)
def _sc(cfg, f):                                              # K·저점·국면0 비중을 함께 f배
    return dict(cfg, k_scale=cfg.get("k_scale", 1.0) * f, position_pct=cfg["position_pct"] * f, off_scale=cfg["off_scale"] * f)
ROUNDS["W05_scale"] = [
    ("KM 전체정리", dict(KM, halt_all=True)),
    ("KM 시장1.0 전체정리", dict(KDO, halt_all=True, **M10)),
    ("KM 전체정리 당일1.5", dict(KM, halt_all=True, day_stop_pct=1.5)),
    ("KM ×0.7", _sc(KM, 0.7)),
    ("KM ×0.6", _sc(KM, 0.6)),
    ("KM 전체정리 ×0.8", _sc(dict(KM, halt_all=True), 0.8)),
    ("KM 전체정리 ×0.7", _sc(dict(KM, halt_all=True), 0.7)),
    ("K만 시장1.5 전체정리", dict(KF, halt_all=True, **M15)),
    ("저점만 AO 시장1.5", dict(AO, **M15)),
    ("KM 전체정리 소프트2", dict(KM, halt_all=True, dd_soft_pct=2.0)),
    ("KM 전체정리 K맞춤20", dict(KM, halt_all=True, k_rebalance_pct=20.0)),
    ("KM 2회 ×0.7", _sc(dict(KM, max_trades_per_symbol=2), 0.7)),
]
# W06: 총 투자 상한(현금 비중 확보) · 손절 종목 며칠 쉬기 · 하루 손절 횟수 브레이크 — 12월 2024처럼 하락장에서 저점매수 반복 손절 막기
SC3 = {"stop_cool_days": 3, "max_stops_day": 3}
ROUNDS["W06_caps"] = [
    ("KM 상한70", dict(KM, max_invest_pct=70.0)),
    ("KM 상한60", dict(KM, max_invest_pct=60.0)),
    ("KM 상한50", dict(KM, max_invest_pct=50.0)),
    ("KM 손절쉬기3", dict(KM, stop_cool_days=3)),
    ("KM 하루손절3", dict(KM, max_stops_day=3)),
    ("KM 상한70 쉬기3 하루3", dict(KM, max_invest_pct=70.0, **SC3)),
    ("KM 상한60 쉬기3 하루3", dict(KM, max_invest_pct=60.0, **SC3)),
    ("KM 상한60 저점8% 쉬기3 하루3", dict(KM, max_invest_pct=60.0, position_pct=8.0, **SC3)),
    ("AO 시장1.5 상한60 쉬기3 하루3", dict(AO, max_invest_pct=60.0, **M15, **SC3)),
    ("KM 상한70 쉬기5 하루2", dict(KM, max_invest_pct=70.0, stop_cool_days=5, max_stops_day=2)),
    ("KM 상한80 쉬기3 하루3", dict(KM, max_invest_pct=80.0, **SC3)),
    ("KM 상한60 쉬기3 하루3 전체정리", dict(KM, max_invest_pct=60.0, halt_all=True, **SC3)),
]
# W07: 첫 통과 C70(= KM + 투자상한 70% + 손절 3일 쉬기 + 하루 손절 3회) 주변에서 수익 올리기
C70 = dict(KM, max_invest_pct=70.0, **SC3)
ROUNDS["W07_push"] = [
    ("C75", dict(C70, max_invest_pct=75.0)),
    ("C80 소프트3", dict(C70, max_invest_pct=80.0, dd_soft_pct=3.0)),
    ("C80 전체정리", dict(C70, max_invest_pct=80.0, halt_all=True)),
    ("C70 2회", dict(C70, max_trades_per_symbol=2)),
    ("C70 K맞춤20", dict(C70, k_rebalance_pct=20.0)),
    ("C70 실적회피", dict(C70, earn_avoid=True)),
    ("C70 국면0×0.7", dict(C70, off_scale=0.7)),
    ("C70 저점12%", dict(C70, position_pct=12.0)),
    ("C70 k1.2", dict(C70, k_scale=1.2)),
    ("C75 2회 실적회피", dict(C70, max_invest_pct=75.0, max_trades_per_symbol=2, earn_avoid=True)),
    ("C70 손절3", dict(C70, stop_loss_pct=3.0)),
    ("C80 하루2 쉬기3", dict(C70, max_invest_pct=80.0, max_stops_day=2)),
]
# W08: 통과한 개선(종목당 2회 · 국면0 비중 0.7 · K 1.2배) 조합
C2 = dict(C70, max_trades_per_symbol=2)
C27 = dict(C2, off_scale=0.7)
ROUNDS["W08_combo"] = [
    ("C2 국면0.7", C27),
    ("C2 국면0.7 k1.2", dict(C27, k_scale=1.2)),
    ("C75 2회", dict(C2, max_invest_pct=75.0)),
    ("C75 2회 국면0.7", dict(C27, max_invest_pct=75.0)),
    ("C2 국면0.7 저점12", dict(C27, position_pct=12.0)),
    ("C70 3회", dict(C70, max_trades_per_symbol=3)),
    ("C2 국면0.7 쉬기2", dict(C27, stop_cool_days=2)),
    ("C2 국면0.7 하루4", dict(C27, max_stops_day=4)),
    ("C72 2회 국면0.7", dict(C27, max_invest_pct=72.0)),
    ("C2 국면0.8", dict(C2, off_scale=0.8)),
    ("C2 국면0.7 k1.1", dict(C27, k_scale=1.1)),
    ("C2 국면0.7 저점11", dict(C27, position_pct=11.0)),
]
# W09: 마지막 조합 — 종목당 3회(C3) 중심
C3 = dict(C70, max_trades_per_symbol=3)
ROUNDS["W09_c3"] = [
    ("C3 국면0.7", dict(C3, off_scale=0.7)),
    ("C72 3회", dict(C3, max_invest_pct=72.0)),
    ("C72 3회 국면0.7", dict(C3, max_invest_pct=72.0, off_scale=0.7)),
    ("C3 k1.1", dict(C3, k_scale=1.1)),
    ("C70 4회", dict(C70, max_trades_per_symbol=4)),
    ("C3 저점11", dict(C3, position_pct=11.0)),
]
# W10: 견고성 — P1 = C3 (K따라 + 시간봉 저점매수 + 국면0 당일거래 + 시장 급락 스위치 + 투자상한 70% + 손절 3일 쉬기 + 하루 손절 3회 + 종목당 3회)
P1 = C3
ROUNDS["W10_robust_P1"] = [
    ("P1", P1),
    ("P1 고가먼저", dict(P1, path_order="high_first")),
    ("P1 무작위1", dict(P1, path_order="random", path_seed=1)),
    ("P1 무작위2", dict(P1, path_order="random", path_seed=2)),
    ("P1 수수료0.15", dict(P1, fee_pct=0.15)),
    ("P1 슬리피지0.15", dict(P1, slippage_pct=0.15)),
    ("P1 절반a", dict(P1, universe=sorted(_h[:29]))),
    ("P1 절반b", dict(P1, universe=sorted(_h[29:]))),
    ("P1 SPY국면(M 대신)", dict(P1, regime="spy")),
    ("P1 상한65", dict(P1, max_invest_pct=65.0)), ("P1 상한75", dict(P1, max_invest_pct=75.0)),
    ("P1 쉬기2", dict(P1, stop_cool_days=2)), ("P1 쉬기4", dict(P1, stop_cool_days=4)),
    ("P1 하루2", dict(P1, max_stops_day=2)), ("P1 하루4", dict(P1, max_stops_day=4)),
    ("P1 시장1.0", dict(P1, mkt_flat_pct=1.0, mkt_stop_pct=0.7)), ("P1 시장2.0", dict(P1, mkt_flat_pct=2.0, mkt_stop_pct=1.5)),
]
ROUNDS["W10b_lag1"] = [("P1 신호1일지연", P1)]          # SIG=signals_v2_lag1 로 실행
# W11: 봉 안 가격 순서에 견디는 후보 고르기 — 후보마다 무작위 경로 2개 + 고가먼저(최악)
_W11C = {"P1 상한65": dict(P1, max_invest_pct=65.0), "P1 하루2": dict(P1, max_stops_day=2),
         "P1 상한60": dict(P1, max_invest_pct=60.0), "P1 상한60 국면0.3": dict(P1, max_invest_pct=60.0, off_scale=0.3),
         "P1 상한55": dict(P1, max_invest_pct=55.0)}
_W11 = []
for _n, _c in _W11C.items():
    _W11 += [(_n, _c), (f"{_n} 무작위1", dict(_c, path_order="random", path_seed=1)),
             (f"{_n} 무작위2", dict(_c, path_order="random", path_seed=2)),
             (f"{_n} 고가먼저", dict(_c, path_order="high_first"))]
ROUNDS["W11_path_robust"] = _W11
# W12: 봉 시가·종가에서만 판단(decide_on_bar) — 봉 안 가격 순서 가정과 무관한 결과에서 다시 최적화
PB = dict(P1, decide_on_bar=True)
ROUNDS["W12_bar_decide"] = [
    ("PB", PB), ("PB 고가먼저(무관 확인)", dict(PB, path_order="high_first")),
    ("PB 상한80", dict(PB, max_invest_pct=80.0)), ("PB 상한90", dict(PB, max_invest_pct=90.0)),
    ("PB 상한60", dict(PB, max_invest_pct=60.0)),
    ("PB 국면0.7", dict(PB, off_scale=0.7)), ("PB 저점12", dict(PB, position_pct=12.0)),
    ("PB k1.2", dict(PB, k_scale=1.2)), ("PB 시장1.0", dict(PB, mkt_flat_pct=1.0, mkt_stop_pct=0.7)),
    ("PB 쉬기2 하루2", dict(PB, stop_cool_days=2, max_stops_day=2)),
    ("PB 상한80 국면0.7", dict(PB, max_invest_pct=80.0, off_scale=0.7)),
    ("PB 손절3 익절2", dict(PB, stop_loss_pct=3.0, min_profit_pct=2.0)),
]
# W14: 정밀도 점검(W13: 시간봉 경로 가정이 저점매수 수익을 부풀림) 뒤 — 경로와 무관한 설계만으로 다시 최적화
#   K따라(장 시작 체결) · 봉 시가/종가 판단 저점매수(decide_on_bar) · K 비중 매일 맞추기(매일 거래)
KFB = dict(KF, decide_on_bar=True)
H15 = dict(M15, halt_all=True)
ROUNDS["W14_pathfree"] = [
    ("K따라", KFB),
    ("K따라 맞춤10", dict(KFB, k_rebalance_pct=10.0)),
    ("K따라 맞춤20", dict(KFB, k_rebalance_pct=20.0)),
    ("K따라 k0.7", dict(KFB, k_scale=0.7)),
    ("K따라 k0.6 맞춤10", dict(KFB, k_scale=0.6, k_rebalance_pct=10.0)),
    ("K따라 급락정리", dict(KFB, **H15)),
    ("K따라 급락정리 맞춤10", dict(KFB, k_rebalance_pct=10.0, **H15)),
    ("K따라 낙폭한도4", dict(KFB, dd_hard_pct=4.0, dd_cool_days=2)),
    ("K따라 실적회피", dict(KFB, earn_avoid=True)),
    ("K따라 k0.7 급락정리 맞춤10", dict(KFB, k_scale=0.7, k_rebalance_pct=10.0, **H15)),
    ("K따라 k0.8 급락정리 맞춤10 실적회피", dict(KFB, k_scale=0.8, k_rebalance_pct=10.0, earn_avoid=True, **H15)),
    ("PB 맞춤10", dict(PB, k_rebalance_pct=10.0)),
    ("PB 급락정리 맞춤10", dict(PB, k_rebalance_pct=10.0, halt_all=True)),
    ("PB k0.7 저점7 급락정리 맞춤10", dict(PB, k_scale=0.7, position_pct=7.0, k_rebalance_pct=10.0, halt_all=True)),
]
# W15: 경로 무관 설계에서 MDD −5%·매일 거래 동시 충족 찾기 — PB(봉 판단) + K 매일 맞추기, K·저점·국면0 비중 격자
PBR = dict(PB, k_rebalance_pct=10.0)
ROUNDS["W15_pathfree_grid"] = [
    ("PBR k0.6 저점5 국면0.5", dict(PBR, k_scale=0.6, position_pct=5.0)),
    ("PBR k0.7 저점5 국면0.5", dict(PBR, k_scale=0.7, position_pct=5.0)),
    ("PBR k0.65 저점6 국면0.5", dict(PBR, k_scale=0.65, position_pct=6.0)),
    ("PBR k0.7 저점4 국면0.5", dict(PBR, k_scale=0.7, position_pct=4.0)),
    ("PBR k0.6 저점6 국면0.7", dict(PBR, k_scale=0.6, position_pct=6.0, off_scale=0.7)),
    ("PBR k0.6 저점5 국면0.5 실적회피", dict(PBR, k_scale=0.6, position_pct=5.0, earn_avoid=True)),
    ("PBR k0.7 저점5 상한60", dict(PBR, k_scale=0.7, position_pct=5.0, max_invest_pct=60.0)),
    ("PBR k0.65 저점5 맞춤5", dict(PBR, k_scale=0.65, position_pct=5.0, k_rebalance_pct=5.0)),
    ("PBR k0.6 저점5 소프트3", dict(PBR, k_scale=0.6, position_pct=5.0, dd_soft_pct=3.0)),
    ("PBR k0.75 저점4 국면0.4", dict(PBR, k_scale=0.75, position_pct=4.0, off_scale=0.4)),
    ("PBR k0.8 저점3 국면0.5", dict(PBR, k_scale=0.8, position_pct=3.0)),
    ("PBR k0.7 저점5 손절3", dict(PBR, k_scale=0.7, position_pct=5.0, stop_loss_pct=3.0)),
]
# W16: 느린 하락(2024-12~2025-04)에 맞춰 낙폭이 커질수록 매수 금액 축소(소프트 브레이크) — 경로 무관 설계
def _pb(k, pos, off=0.5, **kw):
    return dict(PBR, k_scale=k, position_pct=pos, off_scale=off, **kw)
ROUNDS["W16_soft"] = [
    ("k0.6 저점5 소프트2.5×0.3", _pb(0.6, 5, dd_soft_pct=2.5, dd_soft_scale=0.3)),
    ("k0.7 저점4 소프트2.5×0.3", _pb(0.7, 4, dd_soft_pct=2.5, dd_soft_scale=0.3)),
    ("k0.8 저점3 소프트2.5×0.3", _pb(0.8, 3, dd_soft_pct=2.5, dd_soft_scale=0.3)),
    ("k0.7 저점4 상한55 소프트3", _pb(0.7, 4, max_invest_pct=55.0, dd_soft_pct=3.0)),
    ("k0.6 저점4 국면0.3", _pb(0.6, 4, off=0.3)),
    ("k0.55 저점4 국면0.4", _pb(0.55, 4, off=0.4)),
    ("k0.7 저점4 낙폭한도4.5", _pb(0.7, 4, dd_hard_pct=4.5, dd_cool_days=2)),
    ("k0.8 저점3 소프트2×0.4", _pb(0.8, 3, dd_soft_pct=2.0, dd_soft_scale=0.4)),
    ("k0.9 저점3 소프트2×0.3", _pb(0.9, 3, dd_soft_pct=2.0, dd_soft_scale=0.3)),
    ("k1.0 저점3 소프트2×0.3", _pb(1.0, 3, dd_soft_pct=2.0, dd_soft_scale=0.3)),
]
# W17: 견고성 — P2 = 경로 무관 설계로 MDD −5%·매일 거래 통과(k0.7 · 저점 4% · 국면0 0.5 · 투자상한 55% · 소프트 브레이크 3%)
P2 = _pb(0.7, 4, max_invest_pct=55.0, dd_soft_pct=3.0)
ROUNDS["W17_robust_P2"] = [
    ("P2", P2),
    ("P2 고가먼저", dict(P2, path_order="high_first")),
    ("P2 무작위1", dict(P2, path_order="random", path_seed=1)),
    ("P2 수수료0.15", dict(P2, fee_pct=0.15)),
    ("P2 슬리피지0.15", dict(P2, slippage_pct=0.15)),
    ("P2 절반a", dict(P2, universe=sorted(_h[:29]))),
    ("P2 절반b", dict(P2, universe=sorted(_h[29:]))),
    ("P2 SPY국면(M 대신)", dict(P2, regime="spy")),
    ("P2 상한50", dict(P2, max_invest_pct=50.0)), ("P2 상한60", dict(P2, max_invest_pct=60.0)),
    ("P2 k0.65", dict(P2, k_scale=0.65)), ("P2 k0.75", dict(P2, k_scale=0.75)),
    ("P2 소프트2.5", dict(P2, dd_soft_pct=2.5)), ("P2 소프트3.5", dict(P2, dd_soft_pct=3.5)),
]
ROUNDS["W17b_lag1"] = [("P2 신호1일지연", P2)]

# ===== 2026-10-04 사용자(2차): 수익 +20000% · MDD −10% 이내 · 거래 횟수 자유 — 경로 무관 설계만(장 시작 체결) =====
# V01: 6-1 모멘텀 로테이션 + K 주식층을 위험 필터로(K 비중 0 종목 제외, 매일 빠지면 매도)
KFIL = {"stock_filter": True, "rot_daily_filter": True}
ROUNDS["V01_rot_kfilter"] = [
    ("R1(기준)", RO1),
    ("R1 K필터", dict(RO1, stock_filter=True)),
    ("R1 K필터 매일", dict(RO1, **KFIL)),
    ("R1 K필터 매일 엄격", dict(RO1, k_strict=True, **KFIL)),
    ("상위2 K필터 매일", dict(RO1, rot_top=2, rot_pct=50.0, max_positions=2, rot_keep=4, **KFIL)),
    ("상위3 K필터 매일", dict(RO1, rot_top=3, rot_pct=33.3, max_positions=3, rot_keep=5, **KFIL)),
    ("R1 K필터 매일 10일마다", dict(RO1, rot_every=10, **KFIL)),
    ("R1 K필터 매일 3일마다", dict(RO1, rot_every=3, **KFIL)),
    ("R1 K필터 매일 급락정리", dict(RO1, halt_all=True, **M15, **KFIL)),
    ("R1 K필터 매일 낙폭한도8", dict(RO1, dd_hard_pct=8.0, dd_cool_days=3, **KFIL)),
    ("R1 K비중순(모멘텀 대신)", dict(RO1, rot_score="k", **KFIL)),
    ("R1 K필터 매일 63일", dict(RO1, rot_days=63, **KFIL)),
]
# V02: K 따라가기 몫 + 6-1 모멘텀 로테이션 몫(둘 다 장 시작 체결) · 로테이션 변동성 맞춤
KR = dict(RO1, entry_mode="k+rot", max_positions=30)
T2R = {"rot_top": 2, "rot_keep": 4}
ROUNDS["V02_k_plus_rot"] = [
    ("K+로테1 30%", dict(KR, rot_pct=30.0)),
    ("K+로테1 40%", dict(KR, rot_pct=40.0)),
    ("K+로테1 50% K0.8", dict(KR, rot_pct=50.0, k_rot_scale=0.8)),
    ("K+로테1 25%", dict(KR, rot_pct=25.0)),
    ("K+로테2 각20%", dict(KR, rot_pct=20.0, **T2R)),
    ("K+로테2 각25% K0.8", dict(KR, rot_pct=25.0, k_rot_scale=0.8, **T2R)),
    ("로테1 변동성40", dict(RO1, rot_vol_target=40.0)),
    ("로테1 변동성60", dict(RO1, rot_vol_target=60.0)),
    ("로테2 변동성50", dict(RO1, rot_top=2, rot_pct=50.0, max_positions=2, rot_keep=4, rot_vol_target=50.0)),
    ("로테3 변동성50", dict(RO1, rot_top=3, rot_pct=33.3, max_positions=3, rot_keep=5, rot_vol_target=50.0)),
    ("K+로테1 40% 변동성60", dict(KR, rot_pct=40.0, rot_vol_target=60.0)),
    ("K+로테2 각30% 변동성60 K0.8", dict(KR, rot_pct=30.0, rot_vol_target=60.0, k_rot_scale=0.8, **T2R)),
    ("K따라 k1.3", dict(KFB, k_scale=1.3)),
    ("K따라 k1.6", dict(KFB, k_scale=1.6)),
]
# V03: 가장 효율 좋은 K+로테2(각 20%, MDD −12.4%) 중심으로 MDD −10% 안에서 수익 키우기
KR2 = dict(KR, rot_pct=20.0, **T2R)
ROUNDS["V03_kr2"] = [
    ("K+로테2 각15%", dict(KR2, rot_pct=15.0)),
    ("K+로테2 각18%", dict(KR2, rot_pct=18.0)),
    ("K+로테2 각20% K1.2", dict(KR2, k_rot_scale=1.2)),
    ("K+로테2 각20% 급락정리", dict(KR2, halt_all=True, **M15)),
    ("K+로테2 각20% 소프트5", dict(KR2, dd_soft_pct=5.0, dd_soft_scale=0.5)),
    ("K+로테3 각15%", dict(KR2, rot_top=3, rot_keep=5, rot_pct=15.0)),
    ("K+로테3 각20%", dict(KR2, rot_top=3, rot_keep=5, rot_pct=20.0)),
    ("K+로테2 각20% 10일마다", dict(KR2, rot_every=10)),
    ("K+로테2 각20% K1.3", dict(KR2, k_rot_scale=1.3)),
    ("K+로테2 각20% 63일", dict(KR2, rot_days=63)),
    ("K+로테2 각20% 실적회피", dict(KR2, earn_avoid=True)),
    ("K+로테2 각20% 낙폭한도9", dict(KR2, dd_hard_pct=9.0, dd_cool_days=3)),
]
# V04: MDD −10% 경계 촘촘히 — 실적 발표 회피 + 로테이션 몫 15~20% + K 배율
KRE = dict(KR2, earn_avoid=True)
ROUNDS["V04_frontier"] = [
    ("KRE 각16%", dict(KRE, rot_pct=16.0)),
    ("KRE 각17%", dict(KRE, rot_pct=17.0)),
    ("KRE 각18%", dict(KRE, rot_pct=18.0)),
    ("KRE 각20% K0.9", dict(KRE, k_rot_scale=0.9)),
    ("KRE 각18% K1.2", dict(KRE, rot_pct=18.0, k_rot_scale=1.2)),
    ("KRE 각15% K1.3", dict(KRE, rot_pct=15.0, k_rot_scale=1.3)),
    ("KRE 3종목 각12% K1.2", dict(KRE, rot_top=3, rot_keep=5, rot_pct=12.0, k_rot_scale=1.2)),
    ("KRE 각18% 소프트6", dict(KRE, rot_pct=18.0, dd_soft_pct=6.0, dd_soft_scale=0.5)),
    ("KRE 각20% 급락정리", dict(KRE, halt_all=True, **M15)),
    ("KRE 1종목 15% K1.2", dict(KRE, rot_top=1, rot_keep=2, rot_pct=15.0, k_rot_scale=1.2)),
]
# V05: 견고성 — P3 = K 따라가기(×1.2) + 6-1 모멘텀 상위 2종(각 18%) + 실적 발표 회피, 전부 장 시작 체결
P3 = dict(KRE, rot_pct=18.0, k_rot_scale=1.2)
ROUNDS["V05_robust_P3"] = [
    ("P3", P3),
    ("P3 고가먼저", dict(P3, path_order="high_first")),
    ("P3 수수료0.15", dict(P3, fee_pct=0.15)),
    ("P3 슬리피지0.15", dict(P3, slippage_pct=0.15)),
    ("P3 절반a", dict(P3, universe=sorted(_h[:29]))),
    ("P3 절반b", dict(P3, universe=sorted(_h[29:]))),
    ("P3 SPY국면(M 대신)", dict(P3, regime="spy")),
    ("P3 각16%", dict(P3, rot_pct=16.0)), ("P3 각20%", dict(P3, rot_pct=20.0)),
    ("P3 K1.1", dict(P3, k_rot_scale=1.1)), ("P3 K1.3", dict(P3, k_rot_scale=1.3)),
    ("P3 100일", dict(P3, rot_days=100)), ("P3 150일", dict(P3, rot_days=150)),
    ("P3 SP100(2023)", dict(P3, universe=SP100)),
]
ROUNDS["V05b_lag1"] = [("P3 신호1일지연", P3)]

# ===== 2026-10-04 사용자(3차): 승률·수익 더 높이기(MDD −10% 유지, 레버리지 없음, 장 시작 체결) =====
# U01: K 몫 잦은 매매 줄이기 — 작은 비중 매수 안 함 · 비중 0이 며칠 이어져야 매도 · 상위 N종만
ROUNDS["U01_k_churn"] = [
    ("P3(재현)", P3),
    ("K최소1%", dict(P3, k_min_weight=0.01)),
    ("K최소2%", dict(P3, k_min_weight=0.02)),
    ("K최소1% K1.4", dict(P3, k_min_weight=0.01, k_rot_scale=1.4)),
    ("K최소2% K1.5", dict(P3, k_min_weight=0.02, k_rot_scale=1.5)),
    ("K제외2일", dict(P3, k_exit_days=2)),
    ("K최소1% 제외2일", dict(P3, k_min_weight=0.01, k_exit_days=2)),
    ("K상위10", dict(P3, k_top=10)),
    ("K상위8 K1.5", dict(P3, k_top=8, k_rot_scale=1.5)),
    ("로테3 각15%", dict(P3, rot_top=3, rot_keep=5, rot_pct=15.0)),
    ("K최소1% 로테 각20%", dict(P3, k_min_weight=0.01, rot_pct=20.0)),
    ("K최소1% 제외2일 K1.3", dict(P3, k_min_weight=0.01, k_exit_days=2, k_rot_scale=1.3)),
    ("K최소2% 제외2일 K1.5", dict(P3, k_min_weight=0.02, k_exit_days=2, k_rot_scale=1.5)),
    ("K제외3일", dict(P3, k_exit_days=3)),
]
# U02: 승률 오른 설정(K 최소비중·제외 지연)을 MDD −10% 안으로 — 비중 살짝 낮추기 · 낙폭 브레이크
ROUNDS["U02_k_churn_mdd"] = [
    ("K최소2% 로테16", dict(P3, k_min_weight=0.02, rot_pct=16.0)),
    ("K최소2% K1.1", dict(P3, k_min_weight=0.02, k_rot_scale=1.1)),
    ("K최소2% 제외2일 K1.1 로테16", dict(P3, k_min_weight=0.02, k_exit_days=2, k_rot_scale=1.1, rot_pct=16.0)),
    ("K제외3일 K1.0 로테15", dict(P3, k_exit_days=3, k_rot_scale=1.0, rot_pct=15.0)),
    ("K제외3일 K최소1% K1.0 로테15", dict(P3, k_exit_days=3, k_min_weight=0.01, k_rot_scale=1.0, rot_pct=15.0)),
    ("K최소2% 제외3일 K1.1 로테15", dict(P3, k_min_weight=0.02, k_exit_days=3, k_rot_scale=1.1, rot_pct=15.0)),
    ("K최소2% 소프트8", dict(P3, k_min_weight=0.02, dd_soft_pct=8.0, dd_soft_scale=0.5)),
    ("K제외3일 소프트7", dict(P3, k_exit_days=3, dd_soft_pct=7.0, dd_soft_scale=0.5)),
    ("K최소3%", dict(P3, k_min_weight=0.03)),
    ("K최소3% K1.3 로테16", dict(P3, k_min_weight=0.03, k_rot_scale=1.3, rot_pct=16.0)),
    ("K최소2% 제외2일 소프트8", dict(P3, k_min_weight=0.02, k_exit_days=2, dd_soft_pct=8.0, dd_soft_scale=0.5)),
    ("K제외3일 K1.1 로테16 소프트8", dict(P3, k_exit_days=3, k_rot_scale=1.1, rot_pct=16.0, dd_soft_pct=8.0, dd_soft_scale=0.5)),
]
# U03: 승률 66%대(K 최소비중 + 3일 연속 0일 때 매도) 설정을 MDD −10% 안으로 촘촘히
def _u(mw, ex, k, r, **kw):
    return dict(P3, k_min_weight=mw, k_exit_days=ex, k_rot_scale=k, rot_pct=r, **kw)
ROUNDS["U03_exit3_grid"] = [
    ("최소2 제외3 K1.0 로테14", _u(0.02, 3, 1.0, 14.0)),
    ("최소2 제외3 K0.9 로테15", _u(0.02, 3, 0.9, 15.0)),
    ("최소2 제외3 K1.0 로테13", _u(0.02, 3, 1.0, 13.0)),
    ("최소1 제외3 K0.9 로테15", _u(0.01, 3, 0.9, 15.0)),
    ("최소1 제외3 K1.0 로테14", _u(0.01, 3, 1.0, 14.0)),
    ("최소2 제외3 K1.1 로테13", _u(0.02, 3, 1.1, 13.0)),
    ("최소3 제외3 K1.1 로테14", _u(0.03, 3, 1.1, 14.0)),
    ("최소2 제외4 K1.0 로테14", _u(0.02, 4, 1.0, 14.0)),
    ("최소2 제외3 K1.0 로테15 소프트8", _u(0.02, 3, 1.0, 15.0, dd_soft_pct=8.0, dd_soft_scale=0.5)),
    ("최소2 제외2 K1.0 로테15", _u(0.02, 2, 1.0, 15.0)),
    ("최소2 제외3 K0.8 로테16", _u(0.02, 3, 0.8, 16.0)),
    ("최소2 제외5 K0.9 로테14", _u(0.02, 5, 0.9, 14.0)),
]
# U04: P4 후보(최소2 제외3 K0.9 로테15) + K 매수에 상승 추세 조건 · 실적 회피 끔 · 주기
P4c = _u(0.02, 3, 0.9, 15.0)
ROUNDS["U04_kmom"] = [
    ("P4c", P4c),
    ("P4c K추세20", dict(P4c, k_mom_days=20)),
    ("P4c K추세63", dict(P4c, k_mom_days=63)),
    ("P4c K추세126", dict(P4c, k_mom_days=126)),
    ("P4c K추세63 K1.0", dict(P4c, k_mom_days=63, k_rot_scale=1.0)),
    ("P4c K추세63 K1.1 로테16", dict(P4c, k_mom_days=63, k_rot_scale=1.1, rot_pct=16.0)),
    ("P4c 실적회피끔", dict(P4c, earn_avoid=False)),
    ("P4c 로테 10일마다", dict(P4c, rot_every=10)),
    ("P4c 로테 버퍼5", dict(P4c, rot_keep=5)),
    ("P4c K추세20 K1.0 로테16", dict(P4c, k_mom_days=20, k_rot_scale=1.0, rot_pct=16.0)),
]
# U05: 견고성 — P4 = P3 + K 최소비중 2% + K 비중 3일 연속 0일 때 매도 + K 0.9배 + 모멘텀 각 15%
P4 = P4c
ROUNDS["U05_robust_P4"] = [
    ("P4", P4),
    ("P4 고가먼저", dict(P4, path_order="high_first")),
    ("P4 수수료0.15", dict(P4, fee_pct=0.15)),
    ("P4 슬리피지0.15", dict(P4, slippage_pct=0.15)),
    ("P4 절반a", dict(P4, universe=sorted(_h[:29]))),
    ("P4 절반b", dict(P4, universe=sorted(_h[29:]))),
    ("P4 SPY국면(M 대신)", dict(P4, regime="spy")),
    ("P4 최소1%", dict(P4, k_min_weight=0.01)), ("P4 최소3%", dict(P4, k_min_weight=0.03)),
    ("P4 제외2일", dict(P4, k_exit_days=2)), ("P4 제외4일", dict(P4, k_exit_days=4)),
    ("P4 K0.8", dict(P4, k_rot_scale=0.8)), ("P4 K1.0", dict(P4, k_rot_scale=1.0)),
    ("P4 로테14", dict(P4, rot_pct=14.0)), ("P4 로테16", dict(P4, rot_pct=16.0)),
]
ROUNDS["U05b_lag1"] = [("P4 신호1일지연", P4)]

# ===== 2026-10-04 사용자(4차): 승률 80% · 수익 목표 · (MDD −10% 유지) =====
# T01: 손실 중 매도 신호면 본전 회복 대기 · K 몫 이익 실현 · 고확신 K만
ROUNDS["T01_winrate"] = [
    ("P4", P4),
    ("본전대기5", dict(P4, hold_loser_days=5)),
    ("본전대기10", dict(P4, hold_loser_days=10)),
    ("본전대기20", dict(P4, hold_loser_days=20)),
    ("K익절8", dict(P4, k_take_profit_pct=8.0)),
    ("K익절5", dict(P4, k_take_profit_pct=5.0)),
    ("K익절8 본전대기10", dict(P4, k_take_profit_pct=8.0, hold_loser_days=10)),
    ("K익절12 본전대기10", dict(P4, k_take_profit_pct=12.0, hold_loser_days=10)),
    ("K최소5%", dict(P4, k_min_weight=0.05)),
    ("K최소5% 본전대기10", dict(P4, k_min_weight=0.05, hold_loser_days=10)),
    ("K익절5 본전대기20", dict(P4, k_take_profit_pct=5.0, hold_loser_days=20)),
    ("K익절10 쉬기10 본전대기10", dict(P4, k_take_profit_pct=10.0, k_tp_cool_days=10, hold_loser_days=10)),
]
# T02: 남은 손실 매도의 71%가 '국면 0 일괄 정리' → 국면 0이어도 손실분은 본전 대기(손실 한도 둠), 실적 발표 때 손실분 유지
HL = dict(P4, hold_loser_days=20, hold_loser_riskoff=True)
ROUNDS["T02_riskoff_hold"] = [
    ("국면0대기20", HL),
    ("국면0대기20 손절10", dict(HL, hold_loser_stop_pct=10.0)),
    ("국면0대기20 손절8", dict(HL, hold_loser_stop_pct=8.0)),
    ("국면0대기20 실적보유", dict(HL, earn_hold_loser=True)),
    ("국면0대기20 손절10 실적보유", dict(HL, hold_loser_stop_pct=10.0, earn_hold_loser=True)),
    ("국면0대기40 손절10", dict(HL, hold_loser_days=40, hold_loser_stop_pct=10.0)),
    ("국면0대기20 손절10 K최소5%", dict(HL, hold_loser_stop_pct=10.0, k_min_weight=0.05)),
    ("국면0대기30 손절12 실적보유", dict(HL, hold_loser_days=30, hold_loser_stop_pct=12.0, earn_hold_loser=True)),
    ("국면0대기20 손절6", dict(HL, hold_loser_stop_pct=6.0)),
    ("국면0대기60 손절15", dict(HL, hold_loser_days=60, hold_loser_stop_pct=15.0)),
]
# T03: 승률 80%+ 설정의 MDD를 비중 축소로 −10% 안에
HLS10E = dict(HL, hold_loser_stop_pct=10.0, earn_hold_loser=True)
HLS8E = dict(HL, hold_loser_stop_pct=8.0, earn_hold_loser=True)
ROUNDS["T03_scale"] = [
    ("손절10 실적보유 K0.6 로테10", dict(HLS10E, k_rot_scale=0.6, rot_pct=10.0)),
    ("손절10 실적보유 K0.7 로테11", dict(HLS10E, k_rot_scale=0.7, rot_pct=11.0)),
    ("손절10 실적보유 K0.65 로테12", dict(HLS10E, k_rot_scale=0.65, rot_pct=12.0)),
    ("손절없음 K0.6 로테10", dict(HL, k_rot_scale=0.6, rot_pct=10.0)),
    ("손절없음 K0.55 로테10", dict(HL, k_rot_scale=0.55, rot_pct=10.0)),
    ("손절8 실적보유 K0.7 로테12", dict(HLS8E, k_rot_scale=0.7, rot_pct=12.0)),
    ("손절8 실적보유 K0.6 로테10", dict(HLS8E, k_rot_scale=0.6, rot_pct=10.0)),
    ("손절10 실적보유 K0.7 로테12 소프트6", dict(HLS10E, k_rot_scale=0.7, rot_pct=12.0, dd_soft_pct=6.0, dd_soft_scale=0.5)),
    ("손절10 실적보유 K0.8 로테13 소프트5", dict(HLS10E, k_rot_scale=0.8, rot_pct=13.0, dd_soft_pct=5.0, dd_soft_scale=0.5)),
    ("손절없음 실적보유 K0.6 로테10", dict(HL, earn_hold_loser=True, k_rot_scale=0.6, rot_pct=10.0)),
]
# T04: 승률 80%·MDD −10% 경계 촘촘히 — 대기 중 손실 한도 6~8% × K 배율 × 모멘텀 몫
def _t(stop, k, r, earn=True, **kw):
    return dict(HL, hold_loser_stop_pct=stop, earn_hold_loser=earn, k_rot_scale=k, rot_pct=r, **kw)
ROUNDS["T04_grid"] = [
    ("손절8 실적보유 K0.65 로테11", _t(8, 0.65, 11)),
    ("손절8 실적보유 K0.7 로테11", _t(8, 0.7, 11)),
    ("손절7 실적보유 K0.7 로테12", _t(7, 0.7, 12)),
    ("손절7 실적보유 K0.75 로테12", _t(7, 0.75, 12)),
    ("손절8 실적보유 K0.65 로테12 소프트7", _t(8, 0.65, 12, dd_soft_pct=7.0, dd_soft_scale=0.5)),
    ("손절6 실적보유 K0.8 로테13", _t(6, 0.8, 13)),
    ("손절7 K0.7 로테12", _t(7, 0.7, 12, earn=False)),
    ("손절8 실적보유 K0.6 로테12", _t(8, 0.6, 12)),
    ("손절6 실적보유 K0.7 로테12", _t(6, 0.7, 12)),
    ("손절7 실적보유 K0.65 로테13", _t(7, 0.65, 13)),
]
# T05: 견고성 — P5 = P4 + 손실 중 매도 신호면 본전까지 최대 20거래일 대기(국면 0 때도, 손실 7% 넘으면 바로 매도)
#                   + 실적 발표 때 손실분 유지 + K 0.7배 + 모멘텀 각 12%
P5 = _t(7, 0.7, 12)
ROUNDS["T05_robust_P5"] = [
    ("P5", P5),
    ("P5 고가먼저", dict(P5, path_order="high_first")),
    ("P5 수수료0.15", dict(P5, fee_pct=0.15)),
    ("P5 슬리피지0.15", dict(P5, slippage_pct=0.15)),
    ("P5 절반a", dict(P5, universe=sorted(_h[:29]))),
    ("P5 절반b", dict(P5, universe=sorted(_h[29:]))),
    ("P5 SPY국면(M 대신)", dict(P5, regime="spy")),
    ("P5 손절6", dict(P5, hold_loser_stop_pct=6.0)), ("P5 손절8", dict(P5, hold_loser_stop_pct=8.0)),
    ("P5 대기10", dict(P5, hold_loser_days=10)), ("P5 대기30", dict(P5, hold_loser_days=30)),
    ("P5 K0.65", dict(P5, k_rot_scale=0.65)), ("P5 로테11", dict(P5, rot_pct=11.0)),
    ("P4+본전대기20(국면1만)", dict(P4, hold_loser_days=20)),
]
ROUNDS["T05b_lag1"] = [("P5 신호1일지연", P5)]
# S01: 목표 20000% 재탐색 — 벡터 근사로 찾은 '100% 투자 한도 안 수익 한계선' 점들을 실제 시뮬레이션으로 확인
#   (근사: MDD −10% → +2,085%, −15% → +5,400%, −20% → +9,550%, 제한 없음 → +10,900%; 20000%는 어떤 MDD에서도 안 나옴)
KT5 = dict(P4, k_top=5, k_equal_pct=10.4, k_min_weight=0.0)
ROUNDS["S01_frontier"] = [
    ("P4", P4),
    ("P4 모멘텀189", dict(P4, rot_days=189)),
    ("한계10: K×1.1+모멘텀189 1위 20%", dict(P4, k_rot_scale=1.1, rot_top=1, rot_keep=2, rot_pct=20.0, rot_days=189)),
    ("한계10b: K×1.0+모멘텀189 상위3 각10%", dict(P4, k_rot_scale=1.0, rot_top=3, rot_keep=5, rot_pct=10.0, rot_days=189)),
    ("한계15: K상위5 각10.4%+모멘텀126 상위2 각24%", dict(KT5, rot_pct=24.0)),
    ("한계20: K상위5 각10.4%+모멘텀189 1위 48%", dict(KT5, rot_top=1, rot_keep=2, rot_pct=48.0, rot_days=189)),
    ("한계25: K상위5 각8.7%+모멘텀189 1위 56%", dict(KT5, k_equal_pct=8.7, rot_top=1, rot_keep=2, rot_pct=56.0, rot_days=189)),
    ("모멘텀189 1위 100%", dict(P4, k_rot_scale=0.0, rot_top=1, rot_keep=2, rot_pct=99.0, rot_days=189)),
    ("모멘텀126 1위 100%", dict(P4, k_rot_scale=0.0, rot_top=1, rot_keep=2, rot_pct=99.0)),
]
# S02: '한계10'(K×1.1 + 모멘텀189 1위 20%, +2,879%, MDD −11.1%)을 MDD −10% 안으로 — K 배율 × 1위 몫 × 기간
ROUNDS["S02_top1_grid"] = [
    (f"K{k} 1위{r}% {d}일", dict(P4, k_rot_scale=k, rot_top=1, rot_keep=2, rot_pct=float(r), rot_days=d))
    for k in (0.9, 1.0, 1.1) for r in (15, 18, 20, 25) for d in (189, 168)
]
# S03: 수익 큰 1위 몫 조합 + 낙폭 브레이크(고점 대비 N% 빠지면 새 매수 금액 축소)로 MDD −10% 안에
_S3 = {"K1.1 1위25% 168일": dict(P4, k_rot_scale=1.1, rot_top=1, rot_keep=2, rot_pct=25.0, rot_days=168),
       "K1.0 1위25% 168일": dict(P4, k_rot_scale=1.0, rot_top=1, rot_keep=2, rot_pct=25.0, rot_days=168),
       "K1.1 1위20% 168일": dict(P4, k_rot_scale=1.1, rot_top=1, rot_keep=2, rot_pct=20.0, rot_days=168),
       "K1.0 1위20% 168일": dict(P4, k_rot_scale=1.0, rot_top=1, rot_keep=2, rot_pct=20.0, rot_days=168)}
ROUNDS["S03_ddbrake"] = [(f"{n} 낙폭{p}%→×{s}", dict(v, dd_soft_pct=float(p), dd_soft_scale=s))
                         for n, v in _S3.items() for p in (5, 7) for s in (0.5, 0.7)]
# S04: 후보 P6 = P4의 모멘텀 몫을 '168일 모멘텀 1위 20%'로 (K 0.9배) — 견고성 + MDD 제한 없는 최대 수익 확인
P6 = dict(P4, k_rot_scale=0.9, rot_top=1, rot_keep=2, rot_pct=20.0, rot_days=168)
_R1 = dict(entry_mode="rot", rot_top=1, rot_pct=100.0, max_positions=1, rot_keep=2, rot_skip=21, rot_every=5,
           rot_at_open=True, daily_loss_pct=100.0, regime_scale=False, max_trades_per_symbol=2, trend_ma_days=0,
           sector_filter=False)
ROUNDS["S04_robust_P6"] = [
    ("P6", P6),
    ("P6 고가먼저", dict(P6, path_order="high_first")),
    ("P6 수수료0.15", dict(P6, fee_pct=0.15)),
    ("P6 슬리피지0.15", dict(P6, slippage_pct=0.15)),
    ("P6 절반a", dict(P6, universe=sorted(_h[:29]))),
    ("P6 절반b", dict(P6, universe=sorted(_h[29:]))),
    ("P6 SPY국면(M 대신)", dict(P6, regime="spy")),
    ("P6 1위 몫 18%", dict(P6, rot_pct=18.0)), ("P6 1위 몫 22%", dict(P6, rot_pct=22.0)),
    ("P6 147일", dict(P6, rot_days=147)), ("P6 189일", dict(P6, rot_days=189)),
    ("P6 2위까지 유지(버퍼3)", dict(P6, rot_keep=3)),
    ("P6+본전대기20", dict(P6, hold_loser_days=20)),
    ("1종목 모멘텀 100% 126일(R1_5000)", dict(_R1, rot_days=126)),
    ("1종목 모멘텀 100% 168일", dict(_R1, rot_days=168)),
    ("1종목 모멘텀 100% 189일", dict(_R1, rot_days=189)),
    ("1종목 모멘텀 100% 147일", dict(_R1, rot_days=147)),
    ("1종목 모멘텀 100% 168일 국면무시", dict(_R1, rot_days=168, regime="off")),
]
ROUNDS["S04b_lag1"] = [("P6 신호1일지연", P6)]
# Q01: MDD −15% 허용 · 승률 80% 유지 · 수익 최대 — 본전 대기(국면 0·실적 때도) × K 배율 × 모멘텀 몫 구조 × 손실 한도
def _q(stop, k, top, pct, days, **kw):
    return dict(HL, hold_loser_stop_pct=float(stop), earn_hold_loser=True, k_rot_scale=k, rot_top=top,
                rot_keep=top + 1 if top == 1 else 4, rot_pct=float(pct), rot_days=days, **kw)
ROUNDS["Q01_mdd15"] = [
    (f"손절{s} K{k} {'1위' if t == 1 else '상위2'} {p}% {d}일", _q(s, k, t, p, d))
    for s in (7, 10) for k in (0.9, 1.1, 1.3) for t, p, d in ((2, 15, 126), (1, 25, 168), (1, 35, 168))
] + [("손절7 K1.5 1위 25% 168일", _q(7, 1.5, 1, 25, 168)), ("손절10 K1.5 1위 25% 168일", _q(10, 1.5, 1, 25, 168))]
# Q02: 더 키우기 — K 배율 1.3 ~ 2.0 × 1위 몫 35 ~ 50% (손실 한도 7%)
ROUNDS["Q02_push"] = [(f"손절7 K{k} 1위 {p}% 168일", _q(7, k, 1, p, 168)) for k in (1.3, 1.5, 1.7, 2.0) for p in (35, 40, 45, 50)]
# Q03: K1.5 · 1위 50% 기준으로 승률 여유 만들기(손실 한도·대기 일수) + 리밸런싱 주기
QB = _q(7, 1.5, 1, 50, 168)
ROUNDS["Q03_margin"] = [
    ("기준 K1.5 1위50%", QB),
    ("손절8", dict(QB, hold_loser_stop_pct=8.0)), ("손절9", dict(QB, hold_loser_stop_pct=9.0)),
    ("손절10", dict(QB, hold_loser_stop_pct=10.0)),
    ("대기30", dict(QB, hold_loser_days=30)), ("대기40", dict(QB, hold_loser_days=40)),
    ("손절8 대기30", dict(QB, hold_loser_stop_pct=8.0, hold_loser_days=30)),
    ("손절9 대기30", dict(QB, hold_loser_stop_pct=9.0, hold_loser_days=30)),
    ("주기3일", dict(QB, rot_every=3)), ("주기10일", dict(QB, rot_every=10)),
    ("K1.3 1위50% 손절8", dict(_q(8, 1.3, 1, 50, 168))),
    ("K1.7 1위50% 손절8", dict(_q(8, 1.7, 1, 50, 168))),
]
# Q04: 견고성 — P7 = K 비중 × 1.5 + 168일 모멘텀 1위 50% + 본전 대기 20일(국면 0·실적 때도, 손실 8% 넘으면 매도)
P7 = _q(8, 1.5, 1, 50, 168)
ROUNDS["Q04_robust_P7"] = [
    ("P7", P7),
    ("P7 고가먼저", dict(P7, path_order="high_first")),
    ("P7 수수료0.15", dict(P7, fee_pct=0.15)),
    ("P7 슬리피지0.15", dict(P7, slippage_pct=0.15)),
    ("P7 절반a", dict(P7, universe=sorted(_h[:29]))),
    ("P7 절반b", dict(P7, universe=sorted(_h[29:]))),
    ("P7 SPY국면(M 대신)", dict(P7, regime="spy")),
    ("P7 147일", dict(P7, rot_days=147)), ("P7 189일", dict(P7, rot_days=189)), ("P7 126일", dict(P7, rot_days=126)),
    ("P7 K1.3", dict(P7, k_rot_scale=1.3)), ("P7 K1.7", dict(P7, k_rot_scale=1.7)),
    ("P7 1위45%", dict(P7, rot_pct=45.0)), ("P7 1위55%", dict(P7, rot_pct=55.0)),
    ("P7 손절7", dict(P7, hold_loser_stop_pct=7.0)), ("P7 손절9", dict(P7, hold_loser_stop_pct=9.0)),
    ("P7 대기10", dict(P7, hold_loser_days=10)), ("P7 대기30", dict(P7, hold_loser_days=30)),
]
ROUNDS["Q04b_lag1"] = [("P7 신호1일지연", P7)]
# Q05: 모멘텀 몫을 1위 1종목 대신 상위 2종으로 나누면? (K1.5, 손실 한도 8%)
ROUNDS["Q05_top2"] = [(f"K1.5 상위2 각{p}% {d}일", _q(8, 1.5, 2, p, d)) for p in (25, 30, 35) for d in (126, 168)]
# G01: 국면·섹터·산업·주식층 최신 버전(M v1.85 · S v1.00 · I v0.65 · K v0.33, signals_v3)으로 P7 다시 확인
#      K가 S&P 500 전 종목에서 고르게 됨 → 58종 밖 K 종목도 따라가기 · K '다음날 하락확률'로 새 매수 거르기
from xres import KUNI
ROUNDS["G01_v3"] = [
    ("P7 v3 58종만", P7),
    ("P7 v3 +K종목", dict(P7, universe=KUNI)),
    ("P7 v3 +K종목 모멘텀58만", dict(P7, universe=KUNI, rot_base_only=True)),
] + [(f"P7 v3 +K종목 모멘텀58만 하락확률<{p}", dict(P7, universe=KUNI, rot_base_only=True, k_drop1_max=p))
     for p in (48.0, 47.0, 46.0, 45.0, 44.0)]
# G02: K 확장 종목 포함(모멘텀은 58종) 조건에서 K 배율 × 1위 몫 다시 맞추기
ROUNDS["G02_kx_grid"] = [(f"+K종목 K{k} 1위{p}%", dict(P7, universe=KUNI, rot_base_only=True, k_rot_scale=k, rot_pct=float(p)))
                         for k in (1.0, 1.3, 1.5, 1.7, 2.0) for p in (40, 50, 60)]
# G03: K 몫을 남은 현금에 맞춤(k_fit — 체결 순서와 무관) × K 배율 상한 × 1위 몫
ROUNDS["G03_kfit"] = [(f"+K종목 맞춤 K≤{k} 1위{p}%", dict(P7, universe=KUNI, rot_base_only=True, k_fit=True, k_rot_scale=k, rot_pct=float(p)))
                      for k in (1.5, 2.0, 3.0) for p in (40, 50, 60, 70)] + \
                     [(f"58종만 맞춤 K≤{k} 1위{p}%", dict(P7, k_fit=True, k_rot_scale=k, rot_pct=float(p))) for k, p in ((1.5, 50), (3.0, 60))]
# G04: 체결 순서 점검 — 같은 P7인데 종목 처리 순서만 바꿈(알파벳 역순 · 무작위 3가지)
import random as _rnd
def _shuf(seed):
    u = list(BASE58); _rnd.Random(seed).shuffle(u); return u
ROUNDS["G04_order"] = [("P7 알파벳순(기본)", P7), ("P7 역순", dict(P7, universe=sorted(BASE58, reverse=True)))] + \
                      [(f"P7 무작위순{s}", dict(P7, universe=_shuf(s))) for s in (1, 2, 3)] + \
                      [("P7 맞춤(k_fit) 알파벳순", dict(P7, k_fit=True)), ("P7 맞춤(k_fit) 역순", dict(P7, k_fit=True, universe=sorted(BASE58, reverse=True)))]
# G05: 같은 순간 시세 처리 순서(현금이 모자랄 때 누가 먼저 사나) 점검 — 역순 · 무작위 3가지
ROUNDS["G05_tickorder"] = [("P7 알파벳순", P7), ("P7 역순", dict(P7, tick_order="reverse"))] + \
    [(f"P7 무작위{s}", dict(P7, tick_order="random", path_seed=s)) for s in (1, 2, 3)] + \
    [("P7 맞춤(k_fit)", dict(P7, k_fit=True)), ("P7 맞춤(k_fit) 무작위1", dict(P7, k_fit=True, tick_order="random", path_seed=1)),
     ("+K종목 K1.7 1위60% 알파벳순", dict(P7, universe=KUNI, rot_base_only=True, k_rot_scale=1.7, rot_pct=60.0)),
     ("+K종목 K1.7 1위60% 무작위1", dict(P7, universe=KUNI, rot_base_only=True, k_rot_scale=1.7, rot_pct=60.0, tick_order="random", path_seed=1)),
     ("+K종목 K1.7 1위60% 무작위2", dict(P7, universe=KUNI, rot_base_only=True, k_rot_scale=1.7, rot_pct=60.0, tick_order="random", path_seed=2))]
# G06: k_fit(순서 무관) + K 확장 종목 + 모멘텀 58종 — K 상한 × 1위 몫, 알파벳순·무작위순 모두
def _g6(k, p, **kw):
    return dict(P7, universe=KUNI, rot_base_only=True, k_fit=True, k_rot_scale=k, rot_pct=float(p), **kw)
ROUNDS["G06_fit_grid"] = [(f"맞춤 K≤{k} 1위{p}% {o}", _g6(k, p, **({} if o == "알파벳" else dict(tick_order="random", path_seed=1))))
                          for k in (1.5, 2.0, 2.5) for p in (45, 50, 55) for o in ("알파벳", "무작위")]
# G07: 매도 먼저 · 매수 모아서 우선순위대로(batch_buys) — 처리 순서를 바꿔도 같은지
_O = [("알파벳", {}), ("역순", dict(tick_order="reverse")), ("무작위1", dict(tick_order="random", path_seed=1)), ("무작위2", dict(tick_order="random", path_seed=2))]
PB = dict(P7, batch_buys=True)
KB = dict(P7, universe=KUNI, rot_base_only=True, batch_buys=True)
ROUNDS["G07_batch"] = [(f"P7+batch {n}", dict(PB, **o)) for n, o in _O] + \
                      [(f"P7+batch+fit {n}", dict(PB, k_fit=True, **o)) for n, o in _O[::2]] + \
                      [(f"+K종목 batch {n}", dict(KB, **o)) for n, o in _O[::2]] + \
                      [(f"+K종목 batch+fit K≤2 {n}", dict(KB, k_fit=True, k_rot_scale=2.0, **o)) for n, o in _O[::2]]
# G08: 순서 무관(batch_buys) + K 확장 종목 + 모멘텀 58종 — K 배율 × 1위 몫 다시 맞추기
ROUNDS["G08_batch_grid"] = [(f"batch +K종목 K{k} 1위{p}%", dict(KB, k_rot_scale=k, rot_pct=float(p)))
                            for k in (1.0, 1.3, 1.5, 1.7) for p in (35, 40, 45, 50)]
# G09: K1.5 · 1위 35% 주변 다듬기(MDD 여유)
_B9 = dict(KB, k_rot_scale=1.5, rot_pct=35.0)
ROUNDS["G09_refine"] = [
    ("기준 K1.5 1위35%", _B9), ("손절7", dict(_B9, hold_loser_stop_pct=7.0)), ("1위30%", dict(_B9, rot_pct=30.0)),
    ("K1.4", dict(_B9, k_rot_scale=1.4)), ("K1.6", dict(_B9, k_rot_scale=1.6)), ("대기30", dict(_B9, hold_loser_days=30)),
    ("K2.0 1위30%", dict(_B9, k_rot_scale=2.0, rot_pct=30.0)), ("K1.7 1위30%", dict(_B9, k_rot_scale=1.7, rot_pct=30.0)),
    ("손절7 K1.7 1위35%", dict(_B9, hold_loser_stop_pct=7.0, k_rot_scale=1.7)),
]
# G10: 견고성 — P8 = K 확장 종목 따라가기(모멘텀은 58종) + 매수 순서 고정 + K×1.5 + 168일 모멘텀 1위 35% + 본전 대기(손실 8%)
P8 = dict(KB, k_rot_scale=1.5, rot_pct=35.0)
_KX = [c for c in KUNI if c not in BASE58]
ROUNDS["G10_robust_P8"] = [
    ("P8", P8),
    ("P8 고가먼저", dict(P8, path_order="high_first")),
    ("P8 수수료0.15", dict(P8, fee_pct=0.15)), ("P8 슬리피지0.15", dict(P8, slippage_pct=0.15)),
    ("P8 절반a", dict(P8, universe=sorted(_h[:29]) + _KX)), ("P8 절반b", dict(P8, universe=sorted(_h[29:]) + _KX)),
    ("P8 SPY국면(M 대신)", dict(P8, regime="spy")),
    ("P8 147일", dict(P8, rot_days=147)), ("P8 189일", dict(P8, rot_days=189)), ("P8 126일", dict(P8, rot_days=126)),
    ("P8 58종만(K 확장 안 함)", dict(P8, universe=BASE58)),
    ("P8 무작위순", dict(P8, tick_order="random", path_seed=3)),
]
ROUNDS["G10b_lag1"] = [("P8 신호1일지연", P8)]

# H01 (2026-10-07): M v1.86 · S v1.02 · I v0.66 · K v0.36(숏 = 실제 −1배 ETF · AVB→MAA) — SIG=signals_v4 로 실행
#   기준(같은 코드): 숏 열 무시(= v1.0.0 실행기 동작) / 숏 따라가기(실제 봉만) / 숏 + 상장 전 가상 −1배 / 작은 K 몫 → 섹터 ETF
from xres import KUNI_S, K, SIG_DIR as SIG_DIR_
_INVS = set(K.INVERSE_1X_ETFS)
_P8v = dict(P8, universe=KUNI)
_OLD58 = [c for c in BASE58 if c != "MAA"]
ROUNDS["H01_v4"] = [
    ("P8 v4 숏 무시(v1.0.0 동작)", dict(P8, universe=[c for c in KUNI if c not in _INVS])),
    ("P8 v4 숏 따라감", _P8v),
    ("P8 v4 숏 따라감+상장전 가상", dict(_P8v, inv_synth=True)),
    ("P8 v4 숏 따라감 · 작은몫→섹터ETF", dict(P8, universe=KUNI_S, k_small_to_etf=True)),
    ("P8 v4 숏 · 작은몫→섹터ETF+가상", dict(P8, universe=KUNI_S, k_small_to_etf=True, inv_synth=True)),
]
ROUNDS["H00_v3_regress"] = [("P8", P8)]          # SIG=signals_v3: 코드 v1.1.0이 예전 결과(+5,419%)를 그대로 내는지
ROUNDS["H02_mix"] = [("P8 숏 따라감", P8)]          # SIG=signals_mix_v3K4 / signals_mix_v4K3 로 각각: v3→v4 변화가 M·S·I 때문인지 K 때문인지
# H03: K v0.34+ 작은 바구니(풀 종목 < 2%) 처리 — 풀 몫만 섹터 ETF로 되돌리기 · 최소 비중 낮추기
ROUNDS["H03_small"] = [
    ("풀 작은몫→섹터ETF", dict(_P8v, universe=KUNI_S, k_small_to_etf=True, k_small_pool_only=True)),
    ("풀 작은몫→섹터ETF+가상", dict(_P8v, universe=KUNI_S, k_small_to_etf=True, k_small_pool_only=True, inv_synth=True)),
    ("최소비중1%", dict(_P8v, universe=sorted(K.k_symbols(SIG_DIR_, base={c: "NA" for c in BASE58}, min_weight=0.01)), k_min_weight=0.01)),
    ("최소비중0.5%", dict(_P8v, universe=sorted(K.k_symbols(SIG_DIR_, base={c: "NA" for c in BASE58}, min_weight=0.005)), k_min_weight=0.005)),
]
# H04: v4 신호에서 K 배율 × 모멘텀 1위 몫 다시 맞추기(숏 따라감 · 실제 봉) — 판정 mdd15wr80
ROUNDS["H04_grid"] = [(f"K{k} 1위{p}%", dict(_P8v, k_rot_scale=k, rot_pct=float(p))) for k in (1.3, 1.5, 1.7) for p in (30, 35, 40)]
# H05: 견고성 — P8 × v4 신호(숏 따라감). G10과 같은 세트 + 상장 전 가상 숏 + 처리 순서
_KX4 = [c for c in KUNI if c not in BASE58]
ROUNDS["H05_robust_P8v4"] = [
    ("P8", _P8v), ("P8 +상장전 가상숏", dict(_P8v, inv_synth=True)),
    ("P8 고가먼저", dict(_P8v, path_order="high_first")),
    ("P8 수수료0.15", dict(_P8v, fee_pct=0.15)), ("P8 슬리피지0.15", dict(_P8v, slippage_pct=0.15)),
    ("P8 절반a", dict(_P8v, universe=sorted(_h[:29]) + _KX4)), ("P8 절반b", dict(_P8v, universe=sorted(_h[29:]) + _KX4)),
    ("P8 SPY국면(M 대신)", dict(_P8v, regime="spy")),
    ("P8 147일", dict(_P8v, rot_days=147)), ("P8 189일", dict(_P8v, rot_days=189)), ("P8 126일", dict(_P8v, rot_days=126)),
    ("P8 58종만(K 확장 안 함)", dict(_P8v, universe=BASE58)),
    ("P8 역순", dict(_P8v, tick_order="reverse")), ("P8 무작위순", dict(_P8v, tick_order="random", path_seed=3)),
]
ROUNDS["H05b_lag1"] = [("P8 신호1일지연", _P8v)]
