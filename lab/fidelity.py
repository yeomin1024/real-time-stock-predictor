"""정밀도 점검: 같은 기간을 시간봉(봉 안 경로 가정) vs 5분봉(실제에 가까운 경로)으로 — 최근 60일"""
import os, sys, pickle, json
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import kiwoom_autotrader as K
import xres, xrounds

m5 = pickle.load(open(os.path.join(HERE, "data", "bars_5m.pkl"), "rb"))
start = max(d["ts"].min() for d in m5.values())
end = min(d["ts"].max() for d in m5.values())
spy5 = os.path.join(HERE, "data", "spy_5m.pkl")
if not os.path.exists(spy5):
    import yfinance as yf
    d = yf.download("SPY", period="60d", interval="5m", prepost=False, auto_adjust=False, progress=False, multi_level_index=False)
    idx = d.index.tz_convert(K.ET).tz_localize(None)
    s = pd.DataFrame({"ts": idx, "open": d["Open"].values, "high": d["High"].values, "low": d["Low"].values, "close": d["Close"].values})
    s = s[(s.ts.dt.time >= pd.Timestamp("09:30").time()) & (s.ts.dt.time < pd.Timestamp("16:00").time())]
    s.to_pickle(spy5)
spy_m5 = pd.read_pickle(spy5)
start = max(start.normalize() + pd.Timedelta(days=1), spy_m5["ts"].min().normalize() + pd.Timedelta(days=1))
print("window", start, "~", end)
allh = xres.bars_all()


def seed_from_hourly(codes):
    sd = {}
    for c in codes:
        d = allh.get(c)
        if d is None:
            continue
        d = d[d["ts"] < start]
        sd[c] = {"closes": d["close"].tolist(), "daily": d.groupby(d["ts"].dt.date)["close"].last().tolist()}
    return sd


def run(name, ov, use5):
    po = ov.pop("path_order", "auto") if isinstance(ov, dict) else "auto"
    ov = dict(ov); ov.pop("path_order", None)
    cfg = xres.make_cfg(ov)
    sig = K.DailySignals(cfg)
    codes = list(cfg.symbols) + [cfg.mkt_symbol]
    if use5:
        bars = {c: m5[c][(m5[c]["ts"] >= start) & (m5[c]["ts"] <= end)] for c in cfg.symbols if c in m5}
        bars[cfg.mkt_symbol] = spy_m5[(spy_m5["ts"] >= start) & (spy_m5["ts"] <= end)]
    else:
        bars = {c: allh[c][(allh[c]["ts"] >= start) & (allh[c]["ts"] <= end)] for c in codes if c in allh}
    res = K.simulate(cfg, bars, sig, seed=seed_from_hourly(codes), **({"path_order": po} if not use5 else {}))
    m = K.sim_metrics(res)
    out = {"변형": name, "봉": "5분" if use5 else "시간", **{k: m.get(k) for k in ("수익률(%)", "MDD(%)", "샤프", "청산횟수", "승률(%)")}}
    print(out, flush=True)
    return out


rows = []
SETS = (("P1", xrounds.P1), ("PB(봉판단)", xrounds.PB), ("A", xrounds.A), ("K따라", xrounds.KF), ("P2", xrounds.P2))
if len(sys.argv) > 1:
    SETS = tuple(s for s in SETS if s[0] in sys.argv[1:])
for nm, ov in SETS:
    ov = {k: v for k, v in ov.items() if k not in ("path_order", "path_seed")}
    rows.append(run(nm, ov, False))
    rows.append(run(nm, ov, True))
if len(sys.argv) == 1:
    rows.append(run("P1 고가먼저", dict(xrounds.P1, path_order="high_first"), False))
df = pd.DataFrame(rows)
print(df.to_string(index=False))
os.makedirs(os.path.join(xres.RES_DIR, "W13_fidelity"), exist_ok=True)
fn = "fidelity.csv" if len(sys.argv) == 1 else f"fidelity_{'_'.join(sys.argv[1:])}.csv"
df.to_csv(os.path.join(xres.RES_DIR, "W13_fidelity", fn), index=False, encoding="utf-8-sig")
