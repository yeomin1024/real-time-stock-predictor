"""빠른 벡터 근사: 보유 묶음(시가 매매, M 0이면 현금)별 수익·MDD·샤프, 비용(편도 0.12%) 반영"""
import os, sys, pickle, itertools
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
D = pickle.load(open(os.path.join(HERE, "data", "ana_daily.pkl"), "rb"))
op, cl, exp, kw, mom126 = D["op"], D["cl"], D["exp"], D["kw"], D["mom"]
days, U = op.index, op.columns
COST = 0.0012
# 시가에 바꾼 비중 w_D를 다음 시가까지 보유 → 수익 = 시가→다음 시가
oo = (op.shift(-1) / op - 1).fillna(0)
ON = exp > 0
IS = days < pd.Timestamp("2025-08-01")


def run(w, name, show=True):
    w = w.where(ON, 0.0, axis=0).fillna(0)
    tot = w.sum(axis=1)
    w = w.div(tot.clip(lower=1.0), axis=0)                  # 레버리지 없음: 합계 1 넘으면 줄임
    gross = (w * oo).sum(axis=1)
    # 비중 변화(가격 변동 반영 전 근사)만큼 비용
    turn = (w - w.shift(1).fillna(0)).abs().sum(axis=1)
    r = gross - turn * COST
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    res = dict(이름=name, 수익률=round((eq.iloc[-2] - 1) * 100, 0), MDD=round(dd.min() * 100, 2),
               IS_MDD=round(dd[IS].min() * 100, 2),
               OOS_MDD=round(((eq[~IS] / eq[~IS].cummax()) - 1).min() * 100, 2),
               샤프=round(r.mean() / r.std() * np.sqrt(252), 2), 투자=round(w.sum(axis=1)[ON].mean(), 2),
               회전=round(turn.mean(), 3))
    return res, r


def topn(score, n, each):
    rk = score.rank(axis=1, ascending=False, method="first")
    return (rk <= n).astype(float) * each


def mom(days_, skip):
    return (cl.shift(skip) / cl.shift(days_) - 1).shift(1)


out, streams = [], {}
def add(w, name):
    res, r = run(w, name); out.append(res); streams[name] = (w, r)


ksum = kw.sum(axis=1)
print("K 합계(M>0 날):", ksum[ON].describe().round(2).to_dict())
add(kw, "K×1")
add(kw.div(ksum.replace(0, np.nan), axis=0).fillna(0), "K 정규화(합 100%)")
for n in (1, 2, 3, 5):
    add(topn(kw.where(kw > 0), n, 1.0 / n), f"K 상위{n} 동일")
for L, s in [(126, 21), (63, 0), (126, 0), (252, 21), (189, 21), (21, 0), (42, 0)]:
    m = mom(L, s)
    for n in (1, 2, 3):
        add(topn(m, n, 1.0 / n), f"모멘텀{L}-{s} 상위{n}")
# K 고른 종목 안에서 모멘텀 순위
m = mom(126, 21)
for n in (1, 2, 3):
    add(topn(m.where(kw > 0), n, 1.0 / n), f"K∩모멘텀 상위{n}")
df = pd.DataFrame(out).sort_values("수익률", ascending=False)
with pd.option_context("display.width", 250):
    print(df.to_string(index=False))
pickle.dump({k: v[0] for k, v in streams.items()}, open(os.path.join(HERE, "data", "ana_streams.pkl"), "wb"))
