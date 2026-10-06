"""M05: 시간봉(60분봉) 3년 — 같은 지표 세트로 예측 모델, 월 단위 워크포워드.
IS(2023-11~2025-07)에서 설정 선택, OOS(2025-08~2026-10)는 확인만. 장중 청산형과 며칠 보유형을 함께 비교."""
import os, sys, pickle, time, math, warnings, datetime as dt
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import fastfeat as FF
import kiwoom_autotrader as K
import mres as R

warnings.filterwarnings("ignore")
DATA = os.path.join(HERE, "data")
IS_END = pd.Timestamp("2025-07-31")
H_INTRA = {"h1": 1, "h3": 3, "eod": 7}          # 장 안에서(넘으면 그날 마지막 봉)
H_SWING = {"s7": 7, "s14": 14, "s35": 35}       # 밤 넘김(약 1·2·5거래일)


def download_refs():
    import yfinance as yf
    path = os.path.join(DATA, "ref_60m.pkl")
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    tick = sorted({"SPY", "QQQ", "^VIX"} | set(K.PRIOR_STOCK_TO_INDUSTRY.values()) | set(K.PRIOR_INDUSTRY_TO_SECTOR.values()))
    raw = yf.download(tick, period="730d", interval="1h", prepost=False, group_by="ticker", auto_adjust=False,
                      progress=False, threads=True)
    out = {}
    for t in tick:
        try:
            d = raw[t].dropna(subset=["Close"])
        except KeyError:
            continue
        d.index = d.index.tz_convert(K.ET).tz_localize(None)
        tt = d.index.time
        out[t] = d[(tt >= dt.time(9, 30)) & (tt < dt.time(16, 0))]
    dd = yf.download(sorted(K.DEFAULT_UNIVERSE), period="5y", interval="1d", group_by="ticker", auto_adjust=False,
                     progress=False, threads=True)
    out["_daily"] = {c: dd[c]["Close"].dropna() for c in K.DEFAULT_UNIVERSE if c in dd.columns.get_level_values(0)}
    for c, s in out["_daily"].items():
        s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
    pickle.dump(out, open(path, "wb"))
    return out


def build_panel_h(force=False):
    path = os.path.join(DATA, "panel_60m.pkl")
    if os.path.exists(path) and not force:
        return pd.read_pickle(path)
    refs = download_refs()
    h1 = pickle.load(open(os.path.join(DATA, "bars_60m.pkl"), "rb"))
    frames = []
    for code in sorted(K.DEFAULT_UNIVERSE):
        if code not in h1 or len(h1[code]) < 1000:
            continue
        b = h1[code].set_index("ts").rename(columns=str.capitalize)[["Open", "High", "Low", "Close", "Volume"]]
        ind = K.PRIOR_STOCK_TO_INDUSTRY.get(code)
        sec = next((t for t in (ind, K.PRIOR_INDUSTRY_TO_SECTOR.get(ind or "")) if t and t in refs), "SPY")
        mkt = {"SPY": refs["SPY"]["Close"], "QQQ": refs["QQQ"]["Close"],
               "VIX": refs["^VIX"]["Close"] if "^VIX" in refs else None, "SECTOR": refs[sec]["Close"]}
        f = FF.minute_features(b, mkt, refs["_daily"].get(code), R.ref_series(code, b.index))
        o, c = b["Open"].to_numpy(float), b["Close"].to_numpy(float)
        n = len(b)
        last = pd.Series(np.arange(n)).groupby(b.index.normalize().to_numpy()).transform("max").to_numpy()
        ent = np.arange(n) + 1
        for name, H in {**H_INTRA, **H_SWING}.items():
            ext = np.minimum(np.arange(n) + H, last) if name in H_INTRA else np.arange(n) + H
            ok = (ent < n) & (ext < n) & ((ent <= last) if name in H_INTRA else True)
            r = np.full(n, np.nan)
            r[ok] = c[ext[ok]] / o[ent[ok]] - 1
            f[f"y_{name}"] = r.astype("float32")
        f["code"], f["ts"] = code, b.index
        f["next_open"] = np.r_[o[1:], np.nan].astype("float32")
        frames.append(f.reset_index(drop=True))
        print(code, len(f), flush=True)
    p = pd.concat(frames, ignore_index=True)
    p["day"] = p["ts"].dt.normalize()
    days = sorted(p["day"].unique())
    p["day_i"] = p["day"].map({d: i for i, d in enumerate(days)}).astype(int)
    p.to_pickle(path)
    return p


def trade_sim2(panel, pred, label, H, swing, thr, top_k=2, max_pos=5, fee=0.25, slip=0.05, cash0=10000.0,
               entry=("09:30", "15:00"), start=None, end=None):
    """봉 종가 예측 → 다음 봉 시가 매수(예측 ≥ thr 중 상위 top_k) → H봉 뒤 종가 매도(장중형은 그날 마지막 봉까지)."""
    df = panel.loc[pred.index, ["code", "ts", "day", f"y_{label}"]].assign(p=pred).dropna()
    if start is not None:
        df = df[(df["ts"] >= start) & (df["ts"] <= end + pd.Timedelta(days=1))]
    hm = df["ts"].dt.strftime("%H:%M")
    cand = df[(hm >= entry[0]) & (hm <= entry[1]) & (df["p"] >= thr)]
    fee_rt = 2 * fee / 100 + 2 * slip / 100
    ts_all = sorted(df["ts"].unique())
    pos_i = {t: i for i, t in enumerate(ts_all)}
    day_last = df.groupby("day")["ts"].max().to_dict()
    by_ts = {t: g.nlargest(top_k, "p") for t, g in cand.groupby("ts")}
    equity, openp, trades, eq_rows, cur = cash0, [], [], [], None
    for t in ts_all:
        d = pd.Timestamp(t).normalize()
        if cur is not None and d != cur:
            eq_rows.append((cur, equity))
        cur = d
        keep = []
        for ex, code, alloc, r in openp:
            if pos_i[t] >= ex:
                equity += alloc * (r - fee_rt)
                trades.append((t, code, (r - fee_rt) * 100, alloc * (r - fee_rt)))
            else:
                keep.append((ex, code, alloc, r))
        openp = keep
        if t in by_ts:
            held = {x[1] for x in openp}
            for _, row in by_ts[t].iterrows():
                if len(openp) >= max_pos:
                    break
                if row["code"] in held:
                    continue
                ex = pos_i[t] + H if swing else min(pos_i[t] + H, pos_i[day_last[d]])
                openp.append((ex, row["code"], equity / max_pos, float(row[f"y_{label}"])))
                held.add(row["code"])
    for ex, code, alloc, r in openp:
        equity += alloc * (r - fee_rt)
        trades.append((ts_all[-1], code, (r - fee_rt) * 100, alloc * (r - fee_rt)))
    eq_rows.append((cur, equity))
    eq = pd.Series([v for _, v in eq_rows], index=[d for d, _ in eq_rows])
    tr = pd.DataFrame(trades, columns=["청산", "종목", "수익률(%)", "손익($)"])
    r = eq.pct_change(); r.iloc[0] = eq.iloc[0] / cash0 - 1
    curve = pd.concat([pd.Series([cash0]), eq.reset_index(drop=True)])
    g, ls = (tr["손익($)"].clip(lower=0).sum(), -tr["손익($)"].clip(upper=0).sum()) if len(tr) else (0, 0)
    yrs = max(len(eq) / 252, 1e-9)
    return {"수익률(%)": round((eq.iloc[-1] / cash0 - 1) * 100, 2),
            "연환산(%)": round(((eq.iloc[-1] / cash0) ** (1 / yrs) - 1) * 100, 2),
            "샤프": round(r.mean() / r.std() * math.sqrt(252), 2) if r.std() > 0 else 0.0,
            "MDD(%)": round(float((curve / curve.cummax() - 1).min()) * 100, 2), "거래": len(tr),
            "승률(%)": round((tr["손익($)"] > 0).mean() * 100, 1) if len(tr) else None,
            "손익비": round(g / ls, 2) if ls > 0 else None,
            "평균거래(%)": round(tr["수익률(%)"].mean(), 3) if len(tr) else None}, eq, tr


if __name__ == "__main__":
    t0 = time.time()
    p = build_panel_h(force="--force" in sys.argv)
    print(p.shape, p["ts"].min(), p["ts"].max(), "IS 마지막 day_i", p.loc[p["day"] <= IS_END, "day_i"].max(),
          round(time.time() - t0), "s")
