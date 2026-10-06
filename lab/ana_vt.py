"""수익 한계선 끌어올리기 시험: 포트폴리오 변동성 목표(줄이기만), 종목별 역변동성, 넓은 유니버스 모멘텀"""
import os, sys, pickle, itertools
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xres
S = pickle.load(open(os.path.join(HERE, "data", "ana_streams.pkl"), "rb"))
D = pickle.load(open(os.path.join(HERE, "data", "ana_daily.pkl"), "rb"))
op, cl, exp, kw = D["op"], D["cl"], D["exp"], D["kw"]
days = op.index
oo = (op.shift(-1) / op - 1).fillna(0)
ON = exp > 0
IS = days < pd.Timestamp("2025-08-01")
COST = 0.0012
dret = cl.pct_change()


def run(w, oo_=oo, on=ON):
    w = w.where(on, 0.0, axis=0).fillna(0)
    w = w.div(w.sum(axis=1).clip(lower=1.0), axis=0)
    r = (w * oo_.reindex(columns=w.columns).fillna(0)).sum(axis=1) - (w - w.shift(1).fillna(0)).abs().sum(axis=1) * COST
    eq = (1 + r).cumprod()
    mdd = min((eq / eq.cummax() - 1).min(), (eq[IS] / eq[IS].cummax() - 1).min(), (eq[~IS] / eq[~IS].cummax() - 1).min())
    return round((eq.iloc[-2] - 1) * 100), round(mdd * 100, 2), round(r.mean() / r.std() * np.sqrt(252), 2)


def voltgt(w, tgt, lb):
    # 어제까지 보유 비중으로 본 포트폴리오 실현 변동성(종가 기준) → 오늘 시가 비중 줄이기만
    w0 = w.where(ON, 0.0, axis=0).fillna(0)
    w0 = w0.div(w0.sum(axis=1).clip(lower=1.0), axis=0)
    pr = (w0.shift(1) * dret.reindex(columns=w0.columns).fillna(0)).sum(axis=1)       # 근사
    # 오늘 비중으로 과거 lb일 수익을 다시 계산(현재 보유 묶음의 변동성)
    rv = pd.Series(index=days, dtype=float)
    dr = dret.reindex(columns=w0.columns).fillna(0)
    for i in range(lb + 1, len(days)):
        ww = w0.iloc[i]
        nz = ww[ww > 0]
        if len(nz) == 0:
            rv.iloc[i] = np.nan; continue
        hist = dr.iloc[i - lb:i][nz.index] @ nz.values
        rv.iloc[i] = hist.std() * np.sqrt(252)
    sc = (tgt / rv).clip(upper=1.0).fillna(1.0)
    return w0.mul(sc, axis=0)


rows = []
base = {"P4근사(K×0.9+모멘텀126-21상위2 각15%)": S["K×1"] * 0.9 + S["모멘텀126-21 상위2"] * 0.3,
        "K상위5×1.3+모멘텀189상위1×1.2": S["K 상위5 동일"] * 1.3 + S["모멘텀189-21 상위1"] * 1.2,
        "K×1.1+모멘텀189상위1×0.2": S["K×1"] * 1.1 + S["모멘텀189-21 상위1"] * 0.2,
        "모멘텀189상위1": S["모멘텀189-21 상위1"],
        "K 정규화": S["K 정규화(합 100%)"]}
for name, w in base.items():
    rows.append((name, "없음", *run(w)))
    for tgt in (0.2, 0.3, 0.4, 0.6):
        for lb in (10, 20):
            rows.append((name, f"변동성{int(tgt*100)}% {lb}일", *run(voltgt(w, tgt, lb))))
df = pd.DataFrame(rows, columns=["묶음", "변동성목표", "수익률", "MDD", "샤프"])
print(df.to_string(index=False))
df.to_csv(os.path.join(HERE, "data", "ana_vt.csv"), index=False, encoding="utf-8-sig")
