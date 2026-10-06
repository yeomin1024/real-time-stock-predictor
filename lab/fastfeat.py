"""분봉 빠른 지표 세트(실시간용) — 사용자 지표 풀(indicator_pool)의 계산식을 벡터화해 그대로 씀 + 장중 전용 지표
입력: 한 종목의 분봉 DataFrame(Open·High·Low·Close·Volume, 뉴욕 시간 인덱스, 정규장만)
모든 값은 그 봉 종가까지만 사용(인과)."""
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as _swv


# ---- 지표 풀 계산식(벡터화) ----
def _tr(h, l, c):
    pc = c.shift()
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def rsi(c, p):
    d = c.diff()
    g = d.clip(lower=0).ewm(com=p - 1, adjust=False).mean()
    ls = (-d.clip(upper=0)).ewm(com=p - 1, adjust=False).mean()
    return 100 - 100 / (1 + g / ls.replace(0, np.nan))


def _win(s, p):
    a = s.to_numpy(float)
    out = np.full((len(a), p), np.nan)
    if len(a) >= p:
        out[p - 1:] = _swv(a, p)
    return out


def cci(h, l, c, p):
    tp = (h + l + c) / 3
    w = _win(tp, p)
    ma = np.nanmean(w, axis=1)
    md = np.nanmean(np.abs(w - ma[:, None]), axis=1)
    return pd.Series((tp.to_numpy() - ma) / (0.015 * np.where(md == 0, np.nan, md)), index=c.index)


def pctrank(s, p):
    w = _win(s, p)
    last = w[:, -1:]
    less, eq = (w < last).sum(1), (w == last).sum(1)
    n = np.isfinite(w).sum(1)
    r = (less + (eq + 1) / 2) / np.where(n == 0, np.nan, n)
    r[~np.isfinite(w[:, -1])] = np.nan
    return pd.Series(r, index=s.index)


def linreg_slope(s, p):
    w = _win(s, p)
    t = np.arange(p) - (p - 1) / 2
    m = w.mean(1)
    slope = ((w - m[:, None]) * t).sum(1) / (t ** 2).sum()
    return pd.Series(slope / np.where(np.abs(m) == 0, 1, np.abs(m)), index=s.index)


def wma(s, p):
    w = np.arange(1, p + 1, dtype=float)
    return pd.Series(_win(s, p) @ w / w.sum(), index=s.index)


def hma(s, p):
    raw = 2 * wma(s, p // 2) - wma(s, p)
    return wma(raw, int(np.sqrt(p)))


def zscore(s, p):
    mp = max(2, p // 2)
    return (s - s.rolling(p, min_periods=mp).mean()) / s.rolling(p, min_periods=mp).std().replace(0, np.nan)


def adx(h, l, c, p):
    tr = _tr(h, l, c)
    ph, pl = h.shift(), l.shift()
    pdm = pd.Series(np.where((h - ph) > (pl - l), (h - ph).clip(lower=0), 0.0), index=c.index)
    mdm = pd.Series(np.where((pl - l) > (h - ph), (pl - l).clip(lower=0), 0.0), index=c.index)
    atr = tr.ewm(com=p - 1, adjust=False).mean()
    pdi = pdm.ewm(com=p - 1, adjust=False).mean() / atr * 100
    mdi = mdm.ewm(com=p - 1, adjust=False).mean() / atr * 100
    dx = (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan) * 100
    return dx.ewm(com=p - 1, adjust=False).mean(), pdi - mdi


def psar_dist(h, l, c):
    ha, la, ca = h.to_numpy(float), l.to_numpy(float), c.to_numpy(float)
    ps = np.full(len(ca), np.nan)
    if len(ca) < 3:
        return pd.Series(ps, index=c.index)
    af, bull, sar, ep = 0.02, True, la[0], ha[0]
    for i in range(1, len(ca)):
        sar = sar + af * (ep - sar)
        if bull:
            sar = min(sar, la[i - 1], la[max(0, i - 2)])
            if la[i] < sar:
                bull, sar, ep, af = False, ep, la[i], 0.02
            elif ha[i] > ep:
                ep, af = ha[i], min(af + 0.02, 0.2)
        else:
            sar = max(sar, ha[i - 1], ha[max(0, i - 2)])
            if ha[i] > sar:
                bull, sar, ep, af = True, ep, ha[i], 0.02
            elif la[i] < ep:
                ep, af = la[i], min(af + 0.02, 0.2)
        ps[i] = sar
    return pd.Series(ca / ps - 1, index=c.index)


def minute_features(df: pd.DataFrame, mkt: dict = None, daily_close: pd.Series = None, ref: dict = None) -> pd.DataFrame:
    """mkt: {'SPY': 종가, 'QQQ': 종가, 'VIX': 종가, 'SECTOR': 종목 섹터 ETF 종가} (같은 분봉 인덱스로 맞춰 줌)
    daily_close: 종목 일봉 종가(전날까지 맥락). ref: 참고용 {'M': 국면 노출, 'S': 섹터 비중, 'I': 산업 비중}(당일 상수)"""
    o, h, l, c, v = (df[k].astype(float) for k in ("Open", "High", "Low", "Close", "Volume"))
    idx = df.index
    F = {}
    r1 = c.pct_change()
    for k in (1, 2, 3, 6, 12, 24, 48, 78):
        F[f"ret_{k}"] = c.pct_change(k)
    for p in (20, 78):
        F[f"ret_z_{p}"] = zscore(r1, p)
        F[f"ret_pr_{p}"] = pctrank(r1, p)
    for p in (3, 5, 7, 9, 14, 21, 28):
        F[f"rsi_{p}"] = rsi(c, p)
    F["rsi_14_z20"] = zscore(F["rsi_14"], 20)
    for fa, sl, sg in ((5, 13, 4), (8, 17, 9), (12, 26, 9)):
        mc = c.ewm(span=fa, adjust=False).mean() - c.ewm(span=sl, adjust=False).mean()
        hist = mc - mc.ewm(span=sg, adjust=False).mean()
        F[f"macd_{fa}_{sl}_norm"] = mc / c
        F[f"macd_{fa}_{sl}_hist"] = hist / c
        F[f"macd_{fa}_{sl}_hist_ch"] = hist.diff() / c
    for p in (10, 20, 40):
        F[f"cci_{p}"] = cci(h, l, c, p)
    for p in (5, 9, 14, 21):
        ll, hh = l.rolling(p).min(), h.rolling(p).max()
        k = (c - ll) / (hh - ll).replace(0, np.nan) * 100
        F[f"stoch_k_{p}"] = k
        F[f"stoch_kd_{p}"] = k - k.rolling(3).mean()
    for p in (10, 28):
        hh, ll = h.rolling(p).max(), l.rolling(p).min()
        F[f"williams_{p}"] = (hh - c) / (hh - ll).replace(0, np.nan) * -100
    for p in (9, 14, 20):
        d = c.diff()
        su, sd = d.clip(lower=0).rolling(p).sum(), (-d.clip(upper=0)).rolling(p).sum()
        F[f"cmo_{p}"] = (su - sd) / (su + sd).replace(0, np.nan) * 100
    for p in (5, 10, 20, 40):
        F[f"linreg_{p}"] = linreg_slope(c, p)
    for p in (10, 20, 40):
        m, s = c.rolling(p).mean(), c.rolling(p).std()
        F[f"bb_pctb_{p}"] = (c - (m - 2 * s)) / (4 * s).replace(0, np.nan)
        F[f"bb_width_{p}"] = 4 * s / m
    for p in (10, 20, 55):
        hh, ll = h.rolling(p).max(), l.rolling(p).min()
        F[f"donchian_pos_{p}"] = (c - ll) / (hh - ll).replace(0, np.nan)
    atr14 = _tr(h, l, c).ewm(com=13, adjust=False).mean()
    ema20 = c.ewm(span=20, adjust=False).mean()
    F["keltner_pos_20"] = (c - ema20) / (2 * atr14).replace(0, np.nan)
    for p in (7, 14, 28):
        F[f"atr_pct_{p}"] = _tr(h, l, c).ewm(com=p - 1, adjust=False).mean() / c
    F["vol_ratio_12_78"] = r1.rolling(12).std() / r1.rolling(78).std().replace(0, np.nan)
    for p in (7, 14):
        a, di = adx(h, l, c, p)
        F[f"adx_{p}"], F[f"di_diff_{p}"] = a, di
    for p in (5, 9, 21, 50, 100, 200):
        F[f"ema_dist_{p}"] = c / c.ewm(span=p, adjust=False).mean() - 1
    F["ema_9_21"] = c.ewm(span=9, adjust=False).mean() / c.ewm(span=21, adjust=False).mean() - 1
    F["ema_21_50"] = c.ewm(span=21, adjust=False).mean() / c.ewm(span=50, adjust=False).mean() - 1
    for p in (9, 21):
        e1 = c.ewm(span=p, adjust=False).mean(); e2 = e1.ewm(span=p, adjust=False).mean()
        e3 = e2.ewm(span=p, adjust=False).mean()
        F[f"dema_dist_{p}"] = c / (2 * e1 - e2) - 1
        F[f"tema_dist_{p}"] = c / (3 * e1 - 3 * e2 + e3) - 1
        F[f"hma_dist_{p}"] = c / hma(c, p) - 1
    F["psar_dist"] = psar_dist(h, l, c)
    # 거래량
    for p in (20, 78):
        F[f"vol_z_{p}"] = zscore(np.log1p(v), p)
    obv = (np.sign(c.diff()).fillna(0) * v).cumsum()
    F["obv_slope_12"] = linreg_slope(obv - obv.rolling(78, min_periods=12).min() + 1, 12)
    tp = (h + l + c) / 3
    mf = tp * v
    pos, neg = mf.where(tp > tp.shift(), 0).rolling(14).sum(), mf.where(tp < tp.shift(), 0).rolling(14).sum()
    F["mfi_14"] = 100 - 100 / (1 + pos / neg.replace(0, np.nan))
    clv = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    F["cmf_20"] = (clv * v).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    F["upvol_share_12"] = v.where(c >= o, 0).rolling(12).sum() / v.rolling(12).sum().replace(0, np.nan)
    # 봉 모양
    rng = (h - l).replace(0, np.nan)
    F["bar_body"] = (c - o) / c
    F["bar_upper_wick"] = (h - np.maximum(o, c)) / rng
    F["bar_lower_wick"] = (np.minimum(o, c) - l) / rng
    up = (c > c.shift()).astype(int)
    F["up_streak"] = up.groupby((up != up.shift()).cumsum()).cumsum() * up - \
        (1 - up).groupby((up != up.shift()).cumsum()).cumsum() * (1 - up)
    # 장중 전용
    day = pd.Series(idx.normalize(), index=idx)
    g = lambda s: s.groupby(day)
    vwap = g(tp * v).cumsum() / g(v).cumsum().replace(0, np.nan)
    first_open = g(o).transform("first")
    prev_close = pd.Series(c.groupby(day).last().shift(1).reindex(day.values).values, index=idx)
    mins = pd.Series((idx.hour * 60 + idx.minute) - 570, index=idx)
    F["minutes"] = mins.astype(float)
    F["vwap_dev"] = c / vwap - 1
    F["vwap_dev_z"] = F["vwap_dev"] / r1.rolling(78).std().replace(0, np.nan)
    F["day_ret"] = c / first_open - 1
    F["gap"] = first_open / prev_close - 1
    hi_sf, lo_sf = g(h).cummax(), g(l).cummin()
    F["dist_day_high"] = c / hi_sf - 1
    F["dist_day_low"] = c / lo_sf - 1
    F["day_range_pos"] = (c - lo_sf) / (hi_sf - lo_sf).replace(0, np.nan)
    orm = mins < 30
    or_hi = h.where(orm).groupby(day).cummax().groupby(day).ffill()
    or_lo = l.where(orm).groupby(day).cummin().groupby(day).ffill()
    F["or_pos"] = (c - or_lo) / (or_hi - or_lo).replace(0, np.nan)
    slot_avg = v.groupby(mins).transform(lambda s: s.shift(1).rolling(10, min_periods=3).mean())
    F["rvol"] = v / slot_avg.replace(0, np.nan)
    cumv = g(v).cumsum()
    F["cum_rvol"] = cumv / cumv.groupby(mins).transform(lambda s: s.shift(1).rolling(10, min_periods=3).mean()).replace(0, np.nan)
    # 시장 대비
    for name, s in (mkt or {}).items():
        if s is None:
            continue
        s = s.reindex(idx).ffill()
        if name == "VIX":
            F["vix_lvl"] = s
            F["vix_ch_6"] = s.pct_change(6)
            F["vix_ch_24"] = s.pct_change(24)
            continue
        for k in (1, 3, 6, 12, 24):
            F[f"rel_{name}_{k}"] = c.pct_change(k) - s.pct_change(k)
        F[f"{name}_ret_6"] = s.pct_change(6)
        F[f"{name}_rsi_14"] = rsi(s, 14)
        F[f"{name}_day_ret"] = s / s.groupby(day).transform("first") - 1
    # 일봉 맥락(전날까지)
    if daily_close is not None and len(daily_close) > 60:
        d = daily_close.astype(float)
        ctx = pd.DataFrame({"d_ma20": d / d.rolling(20).mean() - 1, "d_ma50": d / d.rolling(50).mean() - 1,
                            "d_ret5": d.pct_change(5), "d_ret20": d.pct_change(20),
                            "d_vol20": d.pct_change().rolling(20).std(), "d_rsi14": rsi(d, 14)}).shift(1)
        ctx.index = pd.DatetimeIndex(ctx.index).normalize()
        ctx = ctx[~ctx.index.duplicated()].reindex(idx.normalize(), method="ffill")
        for col in ctx.columns:
            F[col] = pd.Series(ctx[col].to_numpy(), index=idx)
    for k, val in (ref or {}).items():
        F[f"ref_{k}"] = pd.Series(val, index=idx, dtype=float) if np.isscalar(val) else val.reindex(idx)
    out = pd.DataFrame(F, index=idx)
    return out.replace([np.inf, -np.inf], np.nan).astype("float32")
