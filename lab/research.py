"""라운드별 과거 실시간 시뮬레이션 — 목표치 대비 판정, 결과 파일 저장
사용: python research.py <라운드이름>   (라운드 정의는 ROUNDS 딕셔너리)
"""
import os, sys, json, pickle, time, math, dataclasses
from concurrent.futures import ProcessPoolExecutor
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import kiwoom_autotrader as K

DATA_DIR = os.path.join(HERE, "data")
SIG_DIR = os.path.join(HERE, "signals")                  # 이전 예측 결과(M v1.81.1 일별기록 · S · I CSV)
RES_DIR = os.path.join(ROOT, "results")
UNIVERSE = sorted(set(K.PRIOR_STOCK_TO_INDUSTRY) - {"AVB"})   # AVB: 야후 데이터 없음
PERIODS = {"IS": ("2023-11-01", "2025-07-31"), "OOS": ("2025-08-01", "2026-10-01")}

# ---- 사전에 정한 목표치 (OOS 기준) ----
TARGETS = {"연환산(%)": (">=", 10.0), "샤프": (">=", 1.0), "MDD(%)": (">=", -10.0), "손익비": (">=", 1.2),
           "청산횟수": (">=", 40)}

_DATA, _SPY = {}, None


def data(interval):
    if interval not in _DATA:
        d = pickle.load(open(os.path.join(DATA_DIR, f"bars_{interval}.pkl"), "rb"))
        _DATA[interval] = {c: d[c] for c in UNIVERSE if c in d}
    return _DATA[interval]


def spy():
    global _SPY
    if _SPY is None:
        _SPY = pd.read_pickle(os.path.join(DATA_DIR, "spy_daily.pkl"))
    return _SPY


def spy_regime():
    c = spy()
    ma, mom = c.rolling(200).mean(), c / c.shift(60) - 1
    e = np.where((c > ma) & (mom > 0), 1.0, np.where((c < ma) & (mom < 0), 0.0, 0.5))
    return pd.Series(e, index=c.index)[ma.notna()]


# 라운드들의 출발점(R01 기준선) — Config 기본값이 C1로 바뀌어도 재현되도록 여기 고정
R01_BASE = dict(bar_minutes=60, regime="off", sector_filter=False, industry_filter=False, rank_col="", watchlist_size=0,
                position_pct=30.0, max_positions=3, max_trades_per_symbol=3, stop_loss_pct=2.0, min_profit_pct=1.5,
                trail_pct=0.6, trend_ma_days=0, hold_overnight=False, max_hold_days=5, fee_pct=0.25)


def make_cfg(overrides):
    base = dict(symbols={c: K.PRIOR_STOCK_EXCHANGE.get(c, "ND") for c in UNIVERSE},
                market_hours_check=False, trade_log="", equity_log="", paper_state="", signals_dir=SIG_DIR, **R01_BASE)
    base.update(overrides)
    syms = base.pop("universe", None)
    if syms:
        base["symbols"] = {c: K.PRIOR_STOCK_EXCHANGE.get(c, "ND") for c in syms}
    return K.Config(**base)


def build_seed(start_ts, bar_minutes):
    """분봉 시뮬레이션 시작 전 지표 워밍업: 시간봉 데이터에서 시작 전 종가·일봉 종가를 넣는다."""
    seed = {}
    for c, df in data("60m").items():
        d = df[df["ts"] < start_ts]
        seed[c] = {"closes": d["close"].tolist() if bar_minutes == 60 else [],
                   "daily": d.groupby(d["ts"].dt.date)["close"].last().tolist()}
    return seed


def run_one(job):
    rnd, name, ov, interval = job
    t0 = time.time()
    ov = dict(ov)
    path = {"path_order": ov.pop("path_order", "auto"), "path_seed": ov.pop("path_seed", 0)}
    cfg = make_cfg(ov)
    needs = cfg.regime in ("M", "spy") or cfg.sector_filter or cfg.industry_filter or cfg.rank_col
    sig = K.DailySignals(cfg, spy_series=spy_regime() if cfg.regime == "spy" else None) if needs else None
    bars = data(interval)
    seed = None
    if interval != "60m":
        seed = build_seed(min(d["ts"].min() for d in bars.values()), cfg.bar_minutes)
    res = K.simulate(cfg, bars, sig, seed=seed, **path)
    out = {"라운드": rnd, "변형": name, "봉": interval, "초": round(time.time() - t0)}
    periods = PERIODS if interval == "60m" else {"전체": (None, None)}
    for p, (a, b) in periods.items():
        m = K.sim_metrics(res, a, b, spy_close=spy())
        out.update({f"{p}_{k}": v for k, v in m.items() if k not in ("시작", "끝")})
        out[f"{p}_기간"] = f"{m.get('시작')}~{m.get('끝')}"
    d = os.path.join(RES_DIR, rnd)
    K.save_sim(res, d, f"{name}_{interval}", out, cfg)
    return out


def judge(row, prefix="OOS"):
    fails = []
    for k, (op, v) in TARGETS.items():
        x = row.get(f"{prefix}_{k}")
        ok = x is not None and not (isinstance(x, float) and math.isnan(x)) and (x >= v if op == ">=" else x <= v)
        if not ok:
            fails.append(f"{k} {x}")
    return "✅ 달성" if not fails else "❌ " + ", ".join(fails)


def run_round(rnd, variants, intervals=("60m",), workers=3):
    jobs = [(rnd, n, ov, iv) for n, ov in variants for iv in intervals]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(run_one, jobs))
    df = pd.DataFrame(rows)
    if "OOS_샤프" in df:
        df["IS판정"] = [judge(r, "IS") for r in df.to_dict("records")]
        df["OOS판정"] = [judge(r, "OOS") for r in df.to_dict("records")]
    os.makedirs(RES_DIR, exist_ok=True)
    df.to_csv(os.path.join(RES_DIR, rnd, "round_summary.csv"), index=False, encoding="utf-8-sig")
    allp = os.path.join(RES_DIR, "all_rounds.csv")
    prev = pd.read_csv(allp, encoding="utf-8-sig") if os.path.exists(allp) else pd.DataFrame()
    prev = prev[prev.get("라운드", pd.Series(dtype=str)) != rnd] if len(prev) else prev
    pd.concat([prev, df], ignore_index=True).to_csv(allp, index=False, encoding="utf-8-sig")
    print(f"[{rnd}] {len(jobs)}건 {time.time() - t0:.0f}초")
    return df


SHOW = ["변형", "봉", "IS_수익률(%)", "IS_샤프", "IS_MDD(%)", "IS_청산횟수", "IS_승률(%)", "IS_손익비",
        "OOS_수익률(%)", "OOS_연환산(%)", "OOS_샤프", "OOS_MDD(%)", "OOS_청산횟수", "OOS_승률(%)", "OOS_손익비",
        "OOS_SPY수익률(%)", "OOS_SPY샤프", "OOS판정"]


def show(df):
    cols = [c for c in SHOW if c in df.columns] or list(df.columns)
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 60):
        print(df[cols].to_string(index=False))


ROUNDS = {}

if __name__ == "__main__":
    rnd = sys.argv[1]
    import rounds  # noqa: 라운드 정의
    variants, intervals = rounds.ROUNDS[rnd]
    show(run_round(rnd, variants, intervals, workers=int(os.environ.get("WORKERS", 3))))
