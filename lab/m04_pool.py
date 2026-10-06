"""M04: 사용자 지표 풀(3,380개)이 빠른 세트(137개)보다 분봉 예측을 더 잘하나 — 같은 12종목, 같은 워크포워드
풀 지표 고르기는 처음 20일(학습 시작 구간)만 보고 한다(이후 구간 정보 사용 안 함). 미래정보 지표 8개 제외."""
import os, sys, glob, time
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mres as R
import mrounds as MR

NONCAUSAL = {"cycl_regime_ret_in_high_vix", "def_regime_ret_in_high_vix", "fin_regime_ret_in_high_vix",
             "hlth_regime_ret_in_high_vix", "overnight_neg_gap_zscore_60", "reit_regime_ret_in_high_vix",
             "reitx_shock_day_ret", "vp_highvol_down_ratio_20d"}
TOPN = int(os.environ.get("TOPN", 300))


def main():
    files = sorted(glob.glob(os.path.join(HERE, "data", "pool5m", "*.pkl")))
    codes = [os.path.basename(f)[:-4] for f in files]
    panel = R.build_panel("5m")
    sub = panel[panel["code"].isin(codes)].copy()
    pools = {c: pd.read_pickle(f) for c, f in zip(codes, files)}
    common = sorted(set.intersection(*[set(p.columns) for p in pools.values()]) - NONCAUSAL)
    parts = []
    for c in codes:
        p = pools[c][common].copy()
        p.columns = [f"pool_{x}" for x in common]
        idx = sub.index[sub["code"] == c]
        p.index = idx[: len(p)] if len(p) == len(idx) else idx
        parts.append(p)
    pool = pd.concat(parts)
    sub = sub.join(pool)
    pcols = list(pool.columns)
    print("종목", codes, "| 풀 공통 지표", len(pcols), flush=True)
    rows = []
    for H in (12, 48):
        y = f"y_{H}"
        early = sub[(sub["day_i"] < R.INIT_TRAIN) & sub[y].notna()]
        yr = early[y].rank()
        ic = early[pcols].rank().corrwith(yr).abs().sort_values(ascending=False)
        top = list(ic.index[:TOPN])
        print(f"H{H} 처음 20일 IC 상위:", [(t[5:], round(ic[t], 3)) for t in top[:15]], flush=True)
        fast = R.feature_cols(sub, False)
        fast = [c for c in fast if not c.startswith("pool_")]
        for name, cols in (("빠른세트137", fast), (f"풀상위{TOPN}", top), (f"빠른+풀{TOPN}", fast + top)):
            t0 = time.time()
            pred = R.walk_forward(sub, H, cols, R.INIT_TRAIN, R.DEV_DAYS - 1, MR.REG)
            q = R.signal_quality(sub, pred, H)
            for fee in (0.25, 0.07):
                m, _, _ = R.trade_sim(sub, pred, H, thr=0.004, top_k=1, max_pos=3, fee=fee)
                rows.append({"H": H, "세트": name, "지표수": len(cols), "수수료": fee, **q, **m, "초": round(time.time() - t0)})
            print(H, name, q, flush=True)
    df = pd.DataFrame(rows)
    os.makedirs(os.path.join(R.RES, "M04_pool"), exist_ok=True)
    df.to_csv(os.path.join(R.RES, "M04_pool", "summary.csv"), index=False, encoding="utf-8-sig")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(df[["H", "세트", "지표수", "수수료", "IC평균", "IC_t(일별)", "상위10%수익(%)", "하위10%수익(%)",
                  "수익률(%)", "샤프", "거래", "승률(%)", "손익비"]].to_string(index=False))


if __name__ == "__main__":
    main()
