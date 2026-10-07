"""−1배 ETF 가상 시간봉(기초 종목 시간봉 → 날마다 다시 맞추는 −1배, 보수 0.9%/년) + 실제 봉과 이어 붙이기 · 검증
사용: python lab/inv_synth.py → lab/data/bars_60m_invsyn.pkl (실제 봉이 없는 구간만 가상으로 채운 표)
룩어헤드 없음: t 시각 값 = 전일 ETF 종가 × (2 − U_t / U_전일종가) — t 이전 정보만 씀."""
import os, sys, glob, pickle, logging
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import kiwoom_autotrader as K
_h = logging.StreamHandler(); _h.setFormatter(logging.Formatter("[%(stage)s] %(asctime)s %(message)s"))
LOG = logging.getLogger("inv_synth"); LOG.addHandler(_h); LOG.setLevel("INFO"); LOG.propagate = False
L = lambda st, msg: LOG.info(msg, extra={"stage": st})
FEE_DAY = 0.009 / 252

def load_all():
    d = {}
    for f in sorted(glob.glob(os.path.join(HERE, "data", "bars_60m*.pkl"))):
        if f.endswith("invsyn.pkl"):
            continue
        for c, df in pickle.load(open(f, "rb")).items():
            d.setdefault(c, df)
    return d

def synth(u: pd.DataFrame) -> pd.DataFrame:
    u = u.sort_values("ts").reset_index(drop=True)
    day = u["ts"].dt.normalize()
    dclose = u.groupby(day)["close"].last()
    prev = dclose.shift(1).reindex(day).values               # 전일 기초 종가(첫날은 NaN → 버림)
    ok = ~np.isnan(prev)
    u, day, prev = u[ok].reset_index(drop=True), day[ok].reset_index(drop=True), prev[ok]
    r_close = 1 - (u.groupby(day)["close"].last() / pd.Series(prev, index=day).groupby(level=0).first() - 1) - FEE_DAY
    e_prev = r_close.cumprod().shift(1).fillna(1.0)          # 전일 ETF 종가(100 기준 아닌 1 기준)
    ep = e_prev.reindex(day).values
    f = lambda col: ep * (2 - u[col].values / prev) - ep * FEE_DAY
    return pd.DataFrame({"ts": u["ts"], "open": f("open"), "high": f("low"), "low": f("high"), "close": f("close"),
                         "volume": 0.0})

def main():
    bars = load_all()
    out, rows = {}, []
    for etf, und in K.INVERSE_1X_ETFS.items():
        if und not in bars:
            L("FEATURE", f"etf={etf} underlying={und} WARNING 기초 종목 시간봉 없음 → 건너뜀"); continue
        s = synth(bars[und])
        real = bars.get(etf)
        if real is not None and len(real):
            real = real.sort_values("ts").reset_index(drop=True)
            first = real["ts"].iloc[0]
            m = pd.merge(s, real, on="ts", suffixes=("_s", "_r"))
            rs, rr = m["close_s"].pct_change(), m["close_r"].pct_change()
            dly = m.groupby(m.ts.dt.normalize()).last()
            ds, dr = dly["close_s"].pct_change(), dly["close_r"].pct_change()
            rows.append({"ETF": etf, "기초": und, "실제 시작": first, "겹친 봉": len(m),
                         "시간봉 수익 상관": round(float(rs.corr(rr)), 4), "일간 상관": round(float(ds.corr(dr)), 4),
                         "일간 차 평균(bp)": round(float((dr - ds).mean() * 1e4), 2), "일간 차 표준편차(bp)": round(float((dr - ds).std() * 1e4), 1)})
            # 이어 붙이기: 실제 첫 봉 앞은 가상(실제 첫 봉의 '전 봉' 가상 종가에 맞춰 크기 조정)
            pre = s[s["ts"] < first]
            if len(pre):
                k = float(real["open"].iloc[0]) / float(pre["close"].iloc[-1]) if pre["close"].iloc[-1] > 0 else 1.0
                pre = pre.assign(**{c: pre[c] * k for c in ("open", "high", "low", "close")})
            sp = pd.concat([pre, real], ignore_index=True)
        else:
            sp = s.assign(**{c: s[c] * 100 for c in ("open", "high", "low", "close")})
            rows.append({"ETF": etf, "기초": und, "실제 시작": None, "겹친 봉": 0})
        out[etf] = sp.reset_index(drop=True)
        L("FEATURE", f"etf={etf} underlying={und} synth_bars={len(s)} spliced={len(sp)} real_start={rows[-1]['실제 시작']}")
    rep = pd.DataFrame(rows)
    print(rep.to_string(index=False))
    rep.to_csv(os.path.join(HERE, "data", "invsyn_check.csv"), index=False, encoding="utf-8-sig")
    pickle.dump(out, open(os.path.join(HERE, "data", "bars_60m_invsyn.pkl"), "wb"))

if __name__ == "__main__":
    main()
