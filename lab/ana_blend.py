"""두 묶음 섞기: a·W1 + b·W2 (합계 100% 넘으면 줄임) → MDD −10%(전체·IS·OOS) 안에서 최대 수익"""
import os, sys, pickle, itertools
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0]]
import importlib.util
spec = importlib.util.spec_from_file_location("scan", os.path.join(HERE, "ana_scan.py"))
S = pickle.load(open(os.path.join(HERE, "data", "ana_streams.pkl"), "rb"))
D = pickle.load(open(os.path.join(HERE, "data", "ana_daily.pkl"), "rb"))
op, exp = D["op"], D["exp"]
days = op.index
oo = (op.shift(-1) / op - 1).fillna(0)
ON = exp > 0
IS = days < pd.Timestamp("2025-08-01")
COST = 0.0012


def run(w):
    w = w.where(ON, 0.0, axis=0).fillna(0)
    w = w.div(w.sum(axis=1).clip(lower=1.0), axis=0)
    r = (w * oo).sum(axis=1) - (w - w.shift(1).fillna(0)).abs().sum(axis=1) * COST
    eq = (1 + r).cumprod()
    mdd = min((eq / eq.cummax() - 1).min(), (eq[IS] / eq[IS].cummax() - 1).min(), (eq[~IS] / eq[~IS].cummax() - 1).min())
    return (eq.iloc[-2] - 1) * 100, mdd * 100, r.mean() / r.std() * np.sqrt(252)


names = ["K×1", "K 정규화(합 100%)", "K 상위5 동일", "모멘텀189-21 상위2", "모멘텀189-21 상위3", "모멘텀126-21 상위2",
         "모멘텀126-21 상위1", "모멘텀189-21 상위1", "K∩모멘텀 상위3"]
grid = np.round(np.arange(0.0, 1.31, 0.1), 2)
best = []
for n1, n2 in itertools.combinations(names, 2):
    for a in grid:
        for b in grid:
            if a == 0 and b == 0:
                continue
            ret, mdd, sh = run(S[n1] * a + S[n2] * b)
            best.append((n1, a, n2, b, round(ret), round(mdd, 2), round(sh, 2)))
df = pd.DataFrame(best, columns=["묶음1", "a", "묶음2", "b", "수익률", "MDD", "샤프"])
ok = df[df["MDD"] >= -10].sort_values("수익률", ascending=False)
print("MDD −10% 안 상위 15")
print(ok.head(15).to_string(index=False))
print("\n제한 없이 상위 10")
print(df.sort_values("수익률", ascending=False).head(10).to_string(index=False))
for lim in (-15, -20, -25, -30, -40):
    r = df[df["MDD"] >= lim].sort_values("수익률", ascending=False).head(1)
    print(lim, r.to_dict("records"))
