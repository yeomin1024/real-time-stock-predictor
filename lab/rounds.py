"""라운드 정의 — (변형 목록, 봉 목록). 변형 = (이름, Config 덮어쓰기)
판단은 IS(2023-11~2025-07)로만 하고, OOS(2025-08~2026-10)는 결과 보고용."""
ROUNDS = {
    # R1: 기준선 — 현재 규칙 그대로(시간봉), 필터 없음. 비용 민감도
    "R01_baseline": ([
        ("기준", {}),
        ("기준_수수료0.07", {"fee_pct": 0.07}),
        ("기준_SPY국면", {"regime": "spy"}),
    ], ("60m",)),
    # R2: 구조 진단 — 경로 해상도 개선 후 재측정 + 시초 회피·일봉 추세·스윙·깊은 과매도
    "R02_structure": ([
        ("기준(경로0.2%)", {}),
        ("진입10:30", {"entry_start": "10:30"}),
        ("추세50", {"trend_ma_days": 50}),
        ("스윙5일", {"hold_overnight": True, "max_hold_days": 5}),
        ("추세50+스윙5일", {"trend_ma_days": 50, "hold_overnight": True, "max_hold_days": 5}),
        ("추세50+스윙5일+10:30", {"trend_ma_days": 50, "hold_overnight": True, "max_hold_days": 5,
                                "entry_start": "10:30"}),
        ("깊은과매도+1회", {"rsi_buy": 25, "bb_k": 2.5, "max_trades_per_symbol": 1}),
    ], ("60m",)),
}

# R3: 추세50+스윙 고정, 회전율을 줄이는 청산 폭 격자(IS로 고름)
_R3 = []
for mp, tr in ((1.5, 0.6), (3.0, 1.0), (3.0, 2.0), (5.0, 2.0)):
    for sl in (2.0, 4.0):
        for hd in (5, 10):
            _R3.append((f"익{mp}_트{tr}_손{sl}_보{hd}",
                        {"trend_ma_days": 50, "hold_overnight": True, "max_hold_days": hd,
                         "min_profit_pct": mp, "trail_pct": tr, "stop_loss_pct": sl, "max_trades_per_symbol": 1}))
ROUNDS["R03_exits"] = (_R3, ("60m",))

# R4: R3의 IS 1·2위에 국면(SPY)·분산(5종목×20%)·장기 추세(100일)
BASE_A = {"trend_ma_days": 50, "hold_overnight": True, "max_hold_days": 10, "min_profit_pct": 3.0,
          "trail_pct": 1.0, "stop_loss_pct": 4.0, "max_trades_per_symbol": 1}
BASE_B = dict(BASE_A, trail_pct=2.0)
_R4 = []
for bn, b in (("A", BASE_A), ("B", BASE_B)):
    _R4 += [(f"{bn}", b),
            (f"{bn}+SPY국면", dict(b, regime="spy")),
            (f"{bn}+5종목20%", dict(b, max_positions=5, position_pct=20.0)),
            (f"{bn}+SPY국면+5종목20%", dict(b, regime="spy", max_positions=5, position_pct=20.0)),
            (f"{bn}+추세100", dict(b, trend_ma_days=100))]
ROUNDS["R04_regime_div"] = (_R4, ("60m",))

# R5: 이전 예측 코드 연결 — M 국면 목표비중 · S 섹터 배분 · I 산업 배분 · I 점수 순위
BASE_A5 = dict(BASE_A, max_positions=5, position_pct=20.0)
_R5 = []
for bn, b in (("A", BASE_A), ("A5", BASE_A5)):
    _R5 += [(f"{bn}+M", dict(b, regime="M")),
            (f"{bn}+M+S", dict(b, regime="M", sector_filter=True)),
            (f"{bn}+M+I", dict(b, regime="M", industry_filter=True)),
            (f"{bn}+M+S+I", dict(b, regime="M", sector_filter=True, industry_filter=True)),
            (f"{bn}+M+I순위15", dict(b, regime="M", rank_col="P(상승,ML)", watchlist_size=15))]
_R5 += [("A+SPY+S", dict(BASE_A, regime="spy", sector_filter=True)),
        ("A+S", dict(BASE_A, sector_filter=True)),
        ("A+I순위15", dict(BASE_A, rank_col="P(상승,ML)", watchlist_size=15))]
ROUNDS["R05_prior_models"] = (_R5, ("60m",))

# R6: 견고성 — 비용·슬리피지·유니버스 절반·파라미터 이웃 (후보 C1 = A5+M+S, C2 = A5+M+S+I)
import random
from research import UNIVERSE
C1 = dict(BASE_A5, regime="M", sector_filter=True)
C2 = dict(C1, industry_filter=True)
_halves = []
for seed in (1, 2):
    u = list(UNIVERSE)
    random.Random(seed).shuffle(u)
    _halves += [(f"절반{seed}a", sorted(u[: len(u) // 2])), (f"절반{seed}b", sorted(u[len(u) // 2:]))]
_R6 = []
for cn, c in (("C1", C1), ("C2", C2)):
    _R6 += [(f"{cn}_수수료0.07", dict(c, fee_pct=0.07)), (f"{cn}_수수료0.35", dict(c, fee_pct=0.35))]
    _R6 += [(f"{cn}_{hn}", dict(c, universe=hu)) for hn, hu in _halves]
_R6 += [("C1_슬리피지0.15", dict(C1, slippage_pct=0.15)),
        ("C1_익2.5", dict(C1, min_profit_pct=2.5)), ("C1_익3.5", dict(C1, min_profit_pct=3.5)),
        ("C1_트0.8", dict(C1, trail_pct=0.8)), ("C1_트1.2", dict(C1, trail_pct=1.2)),
        ("C1_손3.5", dict(C1, stop_loss_pct=3.5)), ("C1_손4.5", dict(C1, stop_loss_pct=4.5)),
        ("C1_보8", dict(C1, max_hold_days=8)), ("C1_보12", dict(C1, max_hold_days=12)),
        ("C1_추세40", dict(C1, trend_ma_days=40)), ("C1_추세60", dict(C1, trend_ma_days=60)),
        ("C1_RSI25", dict(C1, rsi_buy=25)), ("C1_반등0.3", dict(C1, rebound_pct=0.3))]
ROUNDS["R06_robust"] = (_R6, ("60m",))
# R7: 정밀도 — 같은 설정을 5분봉(60일)·1분봉(17일)으로(시간봉 지표는 그대로, 봉 안 가격 경로만 실제에 가깝게)
ROUNDS["R07_fidelity"] = ([("C1", C1), ("C2", C2)], ("5m", "1m"))
# R8: 봉 안 가격 순서 가정 검증 — 불리한 순서(항상 고가 먼저)·무작위 순서에서도 버티나
_R8 = []
for cn, c in (("C1", C1), ("C2", C2), ("A5", BASE_A5), ("A5+M", dict(BASE_A5, regime="M")),
              ("A5+S", dict(BASE_A5, sector_filter=True)), ("A5+SPY+S", dict(BASE_A5, regime="spy", sector_filter=True))):
    _R8.append((f"{cn}_고가먼저", dict(c, path_order="high_first")))
for sd in (1, 2, 3):
    _R8.append((f"C1_무작위{sd}", dict(C1, path_order="random", path_seed=sd)))
ROUNDS["R08_path_order"] = (_R8, ("60m",))
# 재현 확인: 코드 정리 후에도 C1이 R05와 똑같이 나오는지 + Config 기본값(=C1) 그대로 돌린 결과
import kiwoom_autotrader as _K
_DEF = {k: getattr(_K.Config(), k) for k in ("bar_minutes", "regime", "sector_filter", "position_pct", "max_positions",
                                             "max_trades_per_symbol", "stop_loss_pct", "min_profit_pct", "trail_pct",
                                             "trend_ma_days", "hold_overnight", "max_hold_days")}
ROUNDS["R09_repro"] = ([("C1_재현", C1), ("Config기본값", _DEF)], ("60m",))
# R10: 실제 수수료 0.07%로 다시 — 비용이 낮아지면 더 자주/더 많이 거래하는 쪽이 나은지(IS로 고름)
F7 = {"fee_pct": 0.07}
ROUNDS["R10_fee007"] = ([
    ("C1", dict(C1, **F7)),
    ("C1_종목당2회", dict(C1, max_trades_per_symbol=2, **F7)),
    ("C1_익2.0", dict(C1, min_profit_pct=2.0, **F7)),
    ("C1_익2.0_트0.8", dict(C1, min_profit_pct=2.0, trail_pct=0.8, **F7)),
    ("C1_8종목12.5%", dict(C1, max_positions=8, position_pct=12.5, **F7)),
    ("C1_보5", dict(C1, max_hold_days=5, **F7)),
    ("C1_지표만(M·S끔)", dict(BASE_A5, **F7)),
    ("C1_SPY국면+S", dict(C1, regime="spy", **F7)),
], ("60m",))
