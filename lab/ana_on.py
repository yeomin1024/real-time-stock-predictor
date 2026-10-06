"""수익원 분해: P4 비슷한 보유(K × 0.9 + 6-1 모멘텀 상위 2 × 15%, M 0이면 현금)를 장중(시가→종가)과 밤사이(종가→다음 시가)로 나눔"""
import os, sys, pickle
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xres
K = xres.K

bars = xres.bars_all()
U = [c for c in xres.BASE58 if c in bars]
op = pd.DataFrame({c: bars[c].groupby(bars[c]["ts"].dt.normalize())["open"].first() for c in U})
cl = pd.DataFrame({c: bars[c].groupby(bars[c]["ts"].dt.normalize())["close"].last() for c in U})
days = op.index
cfg = xres.make_cfg(dict(entry_mode="k+rot", earn_avoid=True))
sig = K.DailySignals(cfg)
rows = []
for d in days:
    s = sig.for_day(d.date())
    rows.append((d, s.exposure, s.kw or {}, s.blackout if hasattr(s, "blackout") else set()))
exp = pd.Series({d: e for d, e, _, _ in rows})
kw = pd.DataFrame({d: k for d, _, k, _ in rows}).T.reindex(columns=U).fillna(0.0)
mom = cl.shift(21) / cl.shift(126) - 1          # 6-1 모멘텀(전날 종가까지) → 오늘 시가에 매매
mom = mom.shift(1)
intra = cl / op - 1                              # 오늘 시가→종가
night = op.shift(-1) / cl - 1                    # 오늘 종가→내일 시가


def port(wk, wr, on=exp > 0):
    w = (wk + wr).where(on, 0.0, axis=0).fillna(0)
    ri = (w * intra.fillna(0)).sum(axis=1)
    rn = (w * night.fillna(0)).sum(axis=1)
    return w, ri, rn


def top_n(m, n, pct):
    r = m.rank(axis=1, ascending=False)
    return (r <= n).astype(float) * pct


def stats(r, name):
    eq = (1 + r).cumprod()
    mdd = (eq / eq.cummax() - 1).min() * 100
    vol = r.std() * np.sqrt(252) * 100
    return dict(구분=name, 수익률=round((eq.iloc[-1] - 1) * 100, 1), MDD=round(mdd, 2), 연변동성=round(vol, 1),
                샤프=round(r.mean() / r.std() * np.sqrt(252), 2) if r.std() else None)


wk = kw.where(kw >= 0.02, 0) * 0.9
wr = top_n(mom, 2, 0.15)
w, ri, rn = port(wk, wr)
out = [stats(ri + rn, "P4 근사 전체"), stats(ri, "P4 근사 장중만"), stats(rn, "P4 근사 밤사이만")]
print("평균 투자비중", round(w.sum(axis=1).mean(), 3))
# 종목군별
eqw = pd.DataFrame(1.0 / len(U), index=days, columns=U)
for name, ww in [("58종 동일비중", eqw), ("K 비중만(×1)", kw), ("모멘텀 상위2(각 50%)", top_n(mom, 2, 0.5)),
                 ("모멘텀 상위5(각 20%)", top_n(mom, 5, 0.2))]:
    for on_name, on in [("국면무시", pd.Series(True, index=days)), ("M>0", exp > 0)]:
        _, a, b = port(ww, 0 * ww, on)
        out += [stats(a + b, f"{name} {on_name} 전체"), stats(a, f"{name} {on_name} 장중"), stats(b, f"{name} {on_name} 밤사이")]
df = pd.DataFrame(out)
print(df.to_string(index=False))
pickle.dump(dict(op=op, cl=cl, exp=exp, kw=kw, mom=mom), open(os.path.join(HERE, "data", "ana_daily.pkl"), "wb"))
