"""분봉 지표 예측 연구: 패널 구성 → 주간 워크포워드 학습(LightGBM) → 신호 품질(IC) → 포트폴리오 가상거래
기간(사전 고정): 5분봉 60거래일 중 앞 45일 = 개발(워크포워드 OOS로 설정 선택), 뒤 15일 = 최종 확인(한 번만)"""
import os, sys, json, pickle, time, math, warnings
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import fastfeat as FF
import kiwoom_autotrader as K

warnings.filterwarnings("ignore")
DATA = os.path.join(HERE, "data")
RES = os.path.join(ROOT, "results_minute")
STOCKS = sorted(K.DEFAULT_UNIVERSE)
DEV_DAYS, HOLD_DAYS, INIT_TRAIN, FOLD = 45, 15, 20, 5


def sector_proxy(code, bars):
    ind = K.PRIOR_STOCK_TO_INDUSTRY.get(code)
    for t in (ind, K.PRIOR_INDUSTRY_TO_SECTOR.get(ind or ""), "SPY"):
        if t and t in bars:
            return t
    return "SPY"


def ref_series(code, index):
    """참고(M·S·I): 날짜 D에는 D보다 앞선 행의 값."""
    sig = os.path.join(HERE, "signals")
    out = {}
    day = pd.DatetimeIndex(index.normalize())

    def asof(path, col):
        df = K._dated_csv(os.path.join(sig, path))
        if col not in df.columns:
            return pd.Series(np.nan, index=index)
        s = pd.to_numeric(df[col], errors="coerce")
        s.index = s.index + pd.Timedelta(days=1)          # 다음 날부터 사용
        return pd.Series(s.reindex(day, method="ffill").to_numpy(), index=index)
    ind = K.PRIOR_STOCK_TO_INDUSTRY.get(code)
    out["M"] = asof("market_regime_daily.csv", "목표비중")
    out["S"] = asof("sector_allocation_daily.csv", f"{K.PRIOR_INDUSTRY_TO_SECTOR.get(ind, '')} 배분비중")
    out["I"] = asof("industry_allocation_daily.csv", ind or "")
    return out


def build_panel(interval="5m", force=False):
    path = os.path.join(DATA, f"panel_{interval}.pkl")
    if os.path.exists(path) and not force:
        return pd.read_pickle(path)
    bars = pickle.load(open(os.path.join(DATA, f"ohlcv_{interval}.pkl"), "rb"))
    daily = pickle.load(open(os.path.join(DATA, "daily_2y.pkl"), "rb"))
    frames = []
    for code in STOCKS:
        if code not in bars:
            continue
        df = bars[code]
        mkt = {"SPY": bars["SPY"]["Close"], "QQQ": bars["QQQ"]["Close"],
               "VIX": bars["^VIX"]["Close"] if "^VIX" in bars else None,
               "SECTOR": bars[sector_proxy(code, bars)]["Close"]}
        f = FF.minute_features(df, mkt, daily[code]["Close"] if code in daily else None, ref_series(code, df.index))
        o, c = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
        dayk = df.index.normalize()
        last = pd.Series(np.arange(len(df))).groupby(dayk.to_numpy()).transform("max").to_numpy()
        n = len(df)
        for H in (3, 6, 12, 24, 48, 78):            # 78 = 그날 장마감까지
            ent, ext = np.arange(n) + 1, np.minimum(np.arange(n) + H, last)
            ok = (ent <= last) & (ent < n)
            r = np.full(n, np.nan)
            r[ok] = c[ext[ok]] / o[np.minimum(ent, n - 1)[ok]] - 1
            f[f"y_{H}"] = r.astype("float32")
        f["code"] = code
        f["ts"] = df.index
        f["next_open"] = np.r_[o[1:], np.nan].astype("float32")
        frames.append(f.reset_index(drop=True))
        print(code, len(f), flush=True)
    panel = pd.concat(frames, ignore_index=True)
    panel["day"] = panel["ts"].dt.normalize()
    days = sorted(panel["day"].unique())
    panel["day_i"] = panel["day"].map({d: i for i, d in enumerate(days)}).astype(int)
    panel.to_pickle(path)
    return panel


def feature_cols(panel, use_ref=False):
    skip = {"code", "ts", "next_open", "day", "day_i"}
    cols = [c for c in panel.columns if c not in skip and not c.startswith("y_")]
    return cols if use_ref else [c for c in cols if not c.startswith("ref_")]


def add_cs_ranks(panel, cols):
    """같은 시각의 종목들 사이 순위(0~1) — 시장 전체 움직임을 빼고 '그 시각 상대적으로 어떤가'."""
    r = panel.groupby("ts")[cols].rank(pct=True).astype("float32")
    r.columns = [f"cs_{c}" for c in cols]
    return pd.concat([panel, r], axis=1), list(r.columns)


def walk_forward(panel, H, cols, start_day, end_day, params=None, init_train=INIT_TRAIN, fold=FOLD, train_from=0,
                 target="reg", cls_thr=0.0, return_model=False):
    """start_day~end_day(포함)의 예측을 주(fold일) 단위로: 그 전 날까지로만 학습.
    target='reg' → H봉 수익률 회귀 / 'cls' → 수익률 > cls_thr 일 확률"""
    import lightgbm as lgb
    p = dict(objective="regression" if target == "reg" else "binary", learning_rate=0.05, num_leaves=31,
             min_data_in_leaf=300, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=1.0,
             verbose=-1, seed=7, num_threads=2)
    p.update(params or {})
    n_rounds = p.pop("n_rounds", 300)
    y = f"y_{H}"
    preds, model = [], None
    d = start_day
    while d <= end_day:
        tr = panel[(panel["day_i"] >= train_from) & (panel["day_i"] < d) & panel[y].notna()]
        te = panel[(panel["day_i"] >= d) & (panel["day_i"] < min(d + fold, end_day + 1))]
        if target == "reg":
            lo, hi = tr[y].quantile([0.01, 0.99])
            lab = tr[y].clip(lo, hi)
        else:
            lab = (tr[y] > cls_thr).astype(int)
        model = lgb.train(p, lgb.Dataset(tr[cols], lab), num_boost_round=n_rounds)
        preds.append(pd.Series(model.predict(te[cols]), index=te.index))
        d += fold
    out = pd.concat(preds)
    return (out, model) if return_model else out


def signal_quality(panel, pred, H):
    y = panel.loc[pred.index, f"y_{H}"]
    df = pd.DataFrame({"p": pred, "y": y, "ts": panel.loc[pred.index, "ts"], "day": panel.loc[pred.index, "day"]}).dropna()
    ics = df.groupby("ts").apply(lambda g: g["p"].rank().corr(g["y"].rank()) if len(g) > 5 else np.nan).dropna()
    daily_ic = ics.groupby(ics.index.normalize()).mean()
    q = df.groupby("ts")["p"].rank(pct=True)
    top, bot = df.loc[q >= 0.9, "y"].mean(), df.loc[q <= 0.1, "y"].mean()
    return {"IC평균": round(ics.mean(), 4), "IC_t(일별)": round(daily_ic.mean() / daily_ic.std() * math.sqrt(len(daily_ic)), 2),
            "상위10%수익(%)": round(top * 100, 3), "하위10%수익(%)": round(bot * 100, 3),
            "전체평균(%)": round(df["y"].mean() * 100, 3), "표본": len(df)}


def trade_sim(panel, pred, H, thr=0.0, top_k=2, max_pos=5, fee=0.25, slip=0.05, entry=("09:45", "15:00"),
              cash0=10000.0):
    """봉 종가에 예측 → 다음 봉 시가에 매수(예측 상위 top_k, 예측 ≥ thr), H봉 뒤 종가(또는 그날 마지막 봉)에 매도."""
    df = panel.loc[pred.index, ["code", "ts", "day", "next_open", f"y_{H}"]].assign(p=pred).dropna()
    hm = df["ts"].dt.strftime("%H:%M")
    df = df[(hm >= entry[0]) & (hm <= entry[1]) & (df["p"] >= thr)]
    fee_rt = 2 * fee / 100 + 2 * slip / 100
    cash, eq_rows, trades = cash0, [], []
    open_pos = []                     # (exit_ts_index, code, alloc)
    ts_all = panel.loc[pred.index, "ts"].drop_duplicates().sort_values().to_list()
    pos_idx = {t: i for i, t in enumerate(ts_all)}
    by_ts = {t: g.nlargest(top_k, "p") for t, g in df.groupby("ts")}
    day_last = panel.loc[pred.index].groupby("day")["ts"].max().to_dict()
    equity = cash0
    cur_day = None
    for t in ts_all:
        d = t.normalize()
        if cur_day is not None and d != cur_day:
            eq_rows.append({"날짜": cur_day, "자산($)": equity})
        cur_day = d
        # 청산
        still = []
        for ex_i, code, alloc, r in open_pos:
            if pos_idx[t] >= ex_i:
                pnl = alloc * (r - fee_rt)
                equity += pnl
                trades.append({"청산": t, "종목": code, "수익률(%)": (r - fee_rt) * 100, "손익($)": pnl})
            else:
                still.append((ex_i, code, alloc, r))
        open_pos = still
        if t in by_ts:
            held = {p[1] for p in open_pos}
            for _, row in by_ts[t].iterrows():
                if len(open_pos) >= max_pos:
                    break
                if row["code"] in held:
                    continue
                exit_t = min(pos_idx[t] + H, pos_idx[day_last[d]])
                open_pos.append((exit_t, row["code"], equity / max_pos, float(row[f"y_{H}"])))
                held.add(row["code"])
    for ex_i, code, alloc, r in open_pos:
        equity += alloc * (r - fee_rt)
        trades.append({"청산": ts_all[-1], "종목": code, "수익률(%)": (r - fee_rt) * 100, "손익($)": alloc * (r - fee_rt)})
    eq_rows.append({"날짜": cur_day, "자산($)": equity})
    eq = pd.DataFrame(eq_rows).set_index("날짜")["자산($)"]
    tr = pd.DataFrame(trades)
    r = eq.pct_change(); r.iloc[0] = eq.iloc[0] / cash0 - 1
    curve = pd.concat([pd.Series([cash0]), eq.reset_index(drop=True)])
    g, ls = (tr["손익($)"].clip(lower=0).sum(), -tr["손익($)"].clip(upper=0).sum()) if len(tr) else (0, 0)
    return {"수익률(%)": round((eq.iloc[-1] / cash0 - 1) * 100, 2),
            "샤프": round(r.mean() / r.std() * math.sqrt(252), 2) if r.std() > 0 else 0.0,
            "MDD(%)": round(float((curve / curve.cummax() - 1).min()) * 100, 2),
            "거래": len(tr), "승률(%)": round((tr["손익($)"] > 0).mean() * 100, 1) if len(tr) else None,
            "손익비": round(g / ls, 2) if ls > 0 else None,
            "평균거래(%)": round(tr["수익률(%)"].mean(), 3) if len(tr) else None}, eq, tr


if __name__ == "__main__":
    t0 = time.time()
    p = build_panel("5m", force="--force" in sys.argv)
    print(p.shape, "days", p["day_i"].max() + 1, round(time.time() - t0, 1), "s")
