"""시뮬레이션용 분봉/시간봉 내려받기 (야후) → lab/data/*.pkl"""
import os, sys, pickle, datetime as dt, time
import pandas as pd, yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import kiwoom_autotrader as K

OUT = os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)
CODES = sorted(K.PRIOR_STOCK_TO_INDUSTRY)


def clean(df):
    idx = df.index.tz_convert(K.ET).tz_localize(None)
    out = pd.DataFrame({"ts": idx, "open": df["Open"].values, "high": df["High"].values, "low": df["Low"].values,
                        "close": df["Close"].values, "volume": df["Volume"].values})
    t = out["ts"].dt.time
    out = out[(t >= dt.time(9, 30)) & (t < dt.time(16, 0))].dropna()
    return out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def dl(interval, **kw):
    raw = yf.download(CODES, interval=interval, prepost=False, group_by="ticker", auto_adjust=False,
                      progress=False, threads=True, **kw)
    res = {}
    for c in CODES:
        try:
            d = raw[c].dropna(subset=["Close"])
            if len(d):
                res[c] = clean(d)
        except KeyError:
            pass
    return res


def merge(parts):
    out = {}
    for p in parts:
        for c, d in p.items():
            out[c] = pd.concat([out[c], d]) if c in out else d
    return {c: d.drop_duplicates("ts").sort_values("ts").reset_index(drop=True) for c, d in out.items()}


if __name__ == "__main__":
    t0 = time.time()
    h1 = dl("1h", period="730d")
    pickle.dump(h1, open(os.path.join(OUT, "bars_60m.pkl"), "wb"))
    print("60m", len(h1), {c: len(d) for c, d in list(h1.items())[:3]}, min(d.ts.min() for d in h1.values()))
    m5 = dl("5m", period="60d")
    pickle.dump(m5, open(os.path.join(OUT, "bars_5m.pkl"), "wb"))
    print("5m", len(m5), min(d.ts.min() for d in m5.values()), max(d.ts.max() for d in m5.values()))
    end = dt.date.today() + dt.timedelta(days=1)
    parts = []
    for k in range(4):
        e = end - dt.timedelta(days=7 * k)
        s = e - dt.timedelta(days=7)
        try:
            parts.append(dl("1m", start=s.isoformat(), end=e.isoformat()))
        except Exception as ex:
            print("1m chunk fail", s, e, ex)
    m1 = merge(parts)
    pickle.dump(m1, open(os.path.join(OUT, "bars_1m.pkl"), "wb"))
    print("1m", len(m1), min(d.ts.min() for d in m1.values()), max(d.ts.max() for d in m1.values()))
    spy = yf.Ticker("SPY").history(start="2015-01-01", interval="1d", auto_adjust=True)["Close"]
    spy.index = spy.index.tz_localize(None).normalize()
    spy.to_pickle(os.path.join(OUT, "spy_daily.pkl"))
    ex = {}
    for c in CODES:
        try:
            ex[c] = yf.Ticker(c).fast_info["exchange"]
        except Exception as e2:
            ex[c] = f"ERR {e2}"
    pickle.dump(ex, open(os.path.join(OUT, "exchanges.pkl"), "wb"))
    print("exchanges", ex)
    print("done", round(time.time() - t0), "s")
