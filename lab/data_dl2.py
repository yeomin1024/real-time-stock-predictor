"""분봉 예측용 데이터: 종목 58 + 지표 풀 PEERS(ETF·지수) 5분봉 60일 / 1분봉 30일 (정규장, 뉴욕 시간)"""
import os, sys, pickle, datetime as dt, time
import pandas as pd, yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(HERE, "src"))
import kiwoom_autotrader as K
import indicator_pool as P

OUT = os.path.join(HERE, "data")
STOCKS = sorted(K.DEFAULT_UNIVERSE)
PEERS = sorted(set(P.PEERS) - set(STOCKS))
ALL = STOCKS + PEERS


def clean(d, index_like=False):
    idx = d.index.tz_convert(K.ET).tz_localize(None)
    out = pd.DataFrame({"Open": d["Open"].values, "High": d["High"].values, "Low": d["Low"].values,
                        "Close": d["Close"].values, "Volume": d["Volume"].values}, index=idx)
    t = out.index.time
    out = out[(t >= dt.time(9, 30)) & (t < dt.time(16, 0))]
    return out[~out.index.duplicated()].sort_index().dropna(subset=["Close"])


def dl(tickers, interval, **kw):
    res = {}
    for i in range(0, len(tickers), 40):
        part = tickers[i:i + 40]
        raw = yf.download(part, interval=interval, prepost=False, group_by="ticker", auto_adjust=False,
                          progress=False, threads=True, **kw)
        for c in part:
            try:
                d = raw[c].dropna(subset=["Close"])
            except KeyError:
                continue
            if len(d):
                res[c] = clean(d)
    return res


if __name__ == "__main__":
    t0 = time.time()
    m5 = dl(ALL, "5m", period="60d")
    pickle.dump(m5, open(os.path.join(OUT, "ohlcv_5m.pkl"), "wb"))
    print("5m", len(m5), "/", len(ALL), "missing", sorted(set(ALL) - set(m5)), round(time.time() - t0))
    end = dt.date.today() + dt.timedelta(days=1)
    parts = []
    for k in range(5):
        e = end - dt.timedelta(days=7 * k); s = e - dt.timedelta(days=7)
        if (end - s).days > 30:
            s = end - dt.timedelta(days=29)
        try:
            parts.append(dl(ALL, "1m", start=s.isoformat(), end=e.isoformat()))
        except Exception as ex:
            print("1m fail", s, e, ex)
    m1 = {}
    for p in parts:
        for c, d in p.items():
            m1[c] = pd.concat([m1[c], d]) if c in m1 else d
    m1 = {c: d[~d.index.duplicated()].sort_index() for c, d in m1.items()}
    pickle.dump(m1, open(os.path.join(OUT, "ohlcv_1m.pkl"), "wb"))
    print("1m", len(m1), min(d.index.min() for d in m1.values()), max(d.index.max() for d in m1.values()))
    dd = yf.download(STOCKS + ["SPY", "QQQ"], period="2y", interval="1d", group_by="ticker", auto_adjust=False,
                     progress=False, threads=True)
    daily = {c: dd[c].dropna(subset=["Close"]) for c in STOCKS + ["SPY", "QQQ"] if c in dd.columns.get_level_values(0)}
    for c, d in daily.items():
        d.index = d.index.tz_localize(None) if d.index.tz is not None else d.index
    pickle.dump(daily, open(os.path.join(OUT, "daily_2y.pkl"), "wb"))
    print("daily", len(daily), "done", round(time.time() - t0), "s")
