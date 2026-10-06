import sys, os, pickle
sys.path.insert(0, "lab")
import xres
b = xres.bars_all()
def ew(codes, start="2023-11-01"):
    r = []
    for c in codes:
        d = b.get(c)
        if d is None: continue
        d = d[d.ts >= start]
        if len(d) < 100: continue
        r.append(d.close.iloc[-1] / d.close.iloc[0])
    import numpy as np
    r = np.array(r)
    return len(r), round((r.mean() - 1) * 100, 1), round((np.median(r) - 1) * 100, 1), sorted(zip(r.round(2), [c for c in codes if c in b]))[-6:]
print("K58 equal-weight B&H", ew(xres.BASE58))
print("SP100 equal-weight B&H", ew(xres.SP100))
