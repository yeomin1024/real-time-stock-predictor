"""빠른 지표 세트: 속도 + 인과성(앞부분만으로 계산한 값 = 전체로 계산한 값)"""
import os, sys, time, pickle
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fastfeat as FF

bars = pickle.load(open(os.path.join(HERE, "data", "ohlcv_5m.pkl"), "rb"))
daily = pickle.load(open(os.path.join(HERE, "data", "daily_2y.pkl"), "rb"))
code = "NVDA"
df = bars[code]
mkt = lambda cut=None: {k: (bars[t]["Close"] if cut is None else bars[t]["Close"][bars[t].index <= cut])
                        for k, t in (("SPY", "SPY"), ("QQQ", "QQQ"), ("VIX", "^VIX"), ("SECTOR", "SMH"))}
t0 = time.time()
full = FF.minute_features(df, mkt(), daily[code]["Close"], {"M": 1.0})
print("fast", full.shape, round(time.time() - t0, 2), "s")
bad = set()
for frac in (0.3, 0.55, 0.8):
    cut = df.index[int(len(df) * frac)]
    part = FF.minute_features(df[df.index <= cut], mkt(cut), daily[code]["Close"], {"M": 1.0})
    rows = part.index[-30:]
    a, b = full.loc[rows], part.loc[rows]
    d = ((a - b).abs() > 1e-4 * (1 + b.abs())) & ~(a.isna() & b.isna())
    bad |= set(d.columns[d.any()]) | set(a.columns[(a.isna() ^ b.isna()).any()])
print("non-causal:", sorted(bad))
t0 = time.time()
tail = df.iloc[-600:]
FF.minute_features(tail, {k: s.iloc[-600:] for k, s in mkt().items()}, daily[code]["Close"])
print("live-size(600 bars)", round(time.time() - t0, 3), "s")
