import sys, pandas as pd, numpy as np
sys.path.insert(0, "lab")
import xres
b = xres.bars_all()
rows = []
for c in xres.BASE58 + xres.SP100:
    d = b.get(c)
    if d is None: continue
    px = np.r_[d["open"].values, d["high"].values, d["low"].values]
    prev = d["close"].shift(1)
    for col in ("open", "high", "low"):
        r = d[col] / prev
        bad = d[(r > 1.3) | (r < 1 / 1.3)]
        if len(bad):
            rows.append((c, col, len(bad), str(bad["ts"].iloc[0])[:16], round(float(r[bad.index[0]]), 3)))
df = pd.DataFrame(rows, columns=["종목", "열", "건수", "처음", "비율"]).drop_duplicates("종목")
print(df.to_string(index=False))
