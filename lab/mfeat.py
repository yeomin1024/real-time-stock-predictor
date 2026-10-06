"""분봉 지표 피처: 사용자 지표 풀(indicator_pool.compute_features, ~4,700개) + 장중 전용 지표 + 일봉 맥락
모든 값은 그 봉 종가까지의 정보만 사용(인과). causality_check()로 검증."""
import os, sys, time, warnings
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import indicator_pool as P

warnings.filterwarnings("ignore")


# 장중에 의미 있는 비교 대상만(지표 풀 PEERS 중): 시장·스타일, 11개 섹터, 반도체·소프트웨어, 변동성, 금리·채권, 달러·원자재
INTRADAY_PEERS = ["SPY", "QQQ", "IWM", "DIA", "RSP", "XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU",
                  "XLRE", "XLC", "SMH", "SOXX", "IGV", "^VIX", "^VIX9D", "TLT", "IEF", "HYG", "^TNX", "UUP", "GLD",
                  "USO", "MTUM", "SPHB", "SPLV"]


def peer_closes(bars: dict, index, codes):
    cols = {c: bars[c]["Close"] for c in codes if c in bars}
    return pd.DataFrame(cols).reindex(index.union(pd.DatetimeIndex([]))).ffill().reindex(index)


def pool_features(code, bars: dict, peers: pd.DataFrame):
    P.TICKER = code
    df = bars[code]
    closes = peers.copy()
    closes[code] = df["Close"]
    f = P.compute_features({code: df}, closes, None, log_availability=False, log_health=False)
    f = f.replace([np.inf, -np.inf], np.nan)
    return f.astype("float32")


def intraday_features(code, bars: dict, daily: dict = None):
    """장중 전용: VWAP 괴리, 시가·전일 대비, 시가 범위, 당일 고저 거리, 시간대별 상대 거래량, SPY·QQQ 대비 상대수익."""
    df = bars[code]
    o, h, l, c, v = (df[k].astype(float) for k in ("Open", "High", "Low", "Close", "Volume"))
    day = pd.Series(df.index.normalize(), index=df.index)
    g = lambda s: s.groupby(day)
    tp = (h + l + c) / 3
    vwap = g(tp * v).cumsum() / g(v).cumsum().replace(0, np.nan)
    first_open = g(o).transform("first")
    prev_close = c.groupby(day).last().shift(1).reindex(day.values).values
    mins = (df.index.hour * 60 + df.index.minute) - (9 * 60 + 30)
    r1 = c.pct_change()
    f = pd.DataFrame(index=df.index)
    f["id_minutes"] = mins
    f["id_vwap_dev"] = c / vwap - 1
    f["id_vwap_dev_z"] = f["id_vwap_dev"] / r1.rolling(78).std()
    f["id_day_ret"] = c / first_open - 1
    f["id_gap"] = first_open / prev_close - 1
    f["id_from_prev_close"] = c / prev_close - 1
    hi_so_far, lo_so_far = g(h).cummax(), g(l).cummin()
    f["id_dist_day_high"] = c / hi_so_far - 1
    f["id_dist_day_low"] = c / lo_so_far - 1
    f["id_day_range_pos"] = (c - lo_so_far) / (hi_so_far - lo_so_far).replace(0, np.nan)
    or_mask = mins < 30
    or_hi = h.where(or_mask).groupby(day).cummax().groupby(day).ffill()
    or_lo = l.where(or_mask).groupby(day).cummin().groupby(day).ffill()
    f["id_or_pos"] = (c - or_lo) / (or_hi - or_lo).replace(0, np.nan)
    # 시간대별 상대 거래량: 같은 시각의 지난 10거래일 평균 대비(오늘 값은 제외 → shift)
    slot = pd.Series(mins, index=df.index)
    vol_slot_avg = v.groupby(slot).transform(lambda s: s.shift(1).rolling(10, min_periods=3).mean())
    f["id_rvol"] = v / vol_slot_avg.replace(0, np.nan)
    cumv = g(v).cumsum()
    cum_slot_avg = cumv.groupby(slot).transform(lambda s: s.shift(1).rolling(10, min_periods=3).mean())
    f["id_cum_rvol"] = cumv / cum_slot_avg.replace(0, np.nan)
    f["id_bar_range"] = (h - l) / c
    f["id_bar_body"] = (c - o) / c
    f["id_upvol_share12"] = (v.where(c >= o, 0)).rolling(12).sum() / v.rolling(12).sum().replace(0, np.nan)
    for m in ("SPY", "QQQ"):
        if m in bars:
            mc = bars[m]["Close"].reindex(df.index).ffill()
            for k in (1, 3, 6, 12):
                f[f"id_rel_{m}_{k}"] = c.pct_change(k) - mc.pct_change(k)
            f[f"id_{m}_day_ret"] = mc / g(bars[m]["Open"].reindex(df.index).ffill()).transform("first") - 1
    if daily and code in daily:
        d = daily[code]["Close"]
        ma20, ma50 = d.rolling(20).mean(), d.rolling(50).mean()
        ctx = pd.DataFrame({"dc_ma20": d / ma20 - 1, "dc_ma50": d / ma50 - 1, "dc_ret5": d.pct_change(5),
                            "dc_ret20": d.pct_change(20), "dc_vol20": d.pct_change().rolling(20).std()}).shift(1)  # 전날까지
        ctx.index = pd.DatetimeIndex(ctx.index).normalize()
        f = f.join(ctx.reindex(df.index.normalize()).set_index(df.index))
    return f.replace([np.inf, -np.inf], np.nan).astype("float32")


def labels(code, bars: dict, horizons=(6, 12)):
    """다음 봉 시가에 사서 H봉 뒤 종가에 판 수익(그날 장 안에서만 — 넘으면 그날 마지막 봉 종가)."""
    df = bars[code]
    o, c = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
    day = df.index.normalize().to_numpy()
    n = len(df)
    last_idx = pd.Series(np.arange(n)).groupby(day).transform("max").to_numpy()
    out = {}
    for H in horizons:
        ent = np.arange(n) + 1
        ext = np.minimum(np.arange(n) + H, last_idx)
        valid = (ent <= last_idx) & (ent < n)
        r = np.full(n, np.nan)
        r[valid] = c[ext[valid]] / o[ent[valid]] - 1
        out[f"fwd_{H}"] = r
    return pd.DataFrame(out, index=df.index)


def causality_check(code, bars, peers, cut_frac=0.7, n_rows=40, tol=1e-4):
    """앞부분만 잘라 계산한 값과 전체로 계산한 값이 같아야 인과적. 다른 열 = 미래 정보 사용."""
    df = bars[code]
    cut = df.index[int(len(df) * cut_frac)]
    full = pool_features(code, bars, peers).join(intraday_features(code, bars))
    trunc_bars = {k: v[v.index <= cut] for k, v in bars.items()}
    tp = peers[peers.index <= cut]
    part = pool_features(code, trunc_bars, tp).join(intraday_features(code, trunc_bars))
    rows = part.index[-n_rows:]
    a, b = full.loc[rows, part.columns], part.loc[rows]
    diff = ((a - b).abs() > tol * (1 + b.abs())) & ~(a.isna() & b.isna())
    nan_mismatch = a.isna() ^ b.isna()
    bad = sorted(set(diff.columns[diff.any()]) | set(nan_mismatch.columns[nan_mismatch.any()]))
    return bad, full.shape[1]


if __name__ == "__main__":
    import pickle
    bars = pickle.load(open(os.path.join(HERE, "data", "ohlcv_5m.pkl"), "rb"))
    code = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    which = sys.argv[2] if len(sys.argv) > 2 else "intraday"
    plist = INTRADAY_PEERS if which == "intraday" else P.PEERS
    peers = peer_closes(bars, bars[code].index, [k for k in plist if k in bars and k != code])
    t0 = time.time()
    f = pool_features(code, bars, peers)
    print("pool", f.shape, "peers", peers.shape[1], round(time.time() - t0, 1), "s", flush=True)
    t0 = time.time()
    fi = intraday_features(code, bars)
    print("intraday", fi.shape, round(time.time() - t0, 1), "s")
    t0 = time.time()
    bad, n = causality_check(code, bars, peers)
    print("causality", round(time.time() - t0, 1), "s | non-causal", len(bad), "/", n, bad[:40])
