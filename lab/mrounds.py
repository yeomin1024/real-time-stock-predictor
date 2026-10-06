"""분봉 예측 라운드. 사용: python mrounds.py M01"""
import os, sys, json, time
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mres as R

# 사전 목표(개발 OOS 25일 · 최종확인 15일 공통)
TARGETS = {"IC_t(일별)": 2.0, "샤프": 1.5, "MDD(%)": -5.0, "손익비": 1.2, "거래": 50}


def judge(row):
    bad = []
    for k, v in TARGETS.items():
        x = row.get(k)
        if x is None or x != x or (x < v):
            bad.append(f"{k} {x}")
    return "✅" if not bad else "❌ " + ", ".join(bad)


def run(rnd, variants, period="dev"):
    out_dir = os.path.join(R.RES, rnd); os.makedirs(out_dir, exist_ok=True)
    panel = R.build_panel("5m")
    base_cols = R.feature_cols(panel, False)
    if any(v.get("cs") for _, v in variants):
        panel, cs_cols = R.add_cs_ranks(panel, base_cols)
    nd = panel["day_i"].max() + 1
    s, e = (R.INIT_TRAIN, R.DEV_DAYS - 1) if period == "dev" else (R.DEV_DAYS, nd - 1)
    rows = []
    for name, v in variants:
        t0 = time.time()
        cols = R.feature_cols(panel, v.get("use_ref", False))
        cols = [c for c in cols if not c.startswith("cs_")] + (cs_cols if v.get("cs") else [])
        if v.get("cs_only"):
            cols = [c for c in cols if c.startswith("cs_")] + ["minutes"]
        if v.get("drop"):
            cols = [c for c in cols if not any(c.startswith(x) for x in v["drop"])]
        pred = R.walk_forward(panel, v["H"], cols, s, e, v.get("params"), train_from=v.get("train_from", 0),
                              target=v.get("target", "reg"), cls_thr=v.get("cls_thr", 0.0))
        q = R.signal_quality(panel, pred, v["H"])
        for fee in v.get("fees", (0.25, 0.07)):
            for thr in v.get("thrs", (0.0,)):
                m, eq, tr = R.trade_sim(panel, pred, v["H"], thr=thr, top_k=v.get("top_k", 2),
                                        max_pos=v.get("max_pos", 5), fee=fee)
                row = {"라운드": rnd, "변형": name, "기간": period, "H": v["H"], "특징수": len(cols), "수수료": fee,
                       "문턱": thr, **q, **m, "초": round(time.time() - t0)}
                row["판정"] = judge(row)
                rows.append(row)
                eq.to_csv(os.path.join(out_dir, f"{name}_f{fee}_t{thr}_{period}_equity.csv"), encoding="utf-8-sig")
                tr.to_csv(os.path.join(out_dir, f"{name}_f{fee}_t{thr}_{period}_trades.csv"), index=False, encoding="utf-8-sig")
        pred.to_frame("pred").to_pickle(os.path.join(out_dir, f"{name}_{period}_pred.pkl"))
        print(name, q, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "summary.csv"), index=False, encoding="utf-8-sig")
    allp = os.path.join(R.RES, "all_minute_rounds.csv")
    prev = pd.read_csv(allp, encoding="utf-8-sig") if os.path.exists(allp) else pd.DataFrame()
    if len(prev):
        prev = prev[~((prev["라운드"] == rnd) & (prev["기간"] == period))]
    pd.concat([prev, df], ignore_index=True).to_csv(allp, index=False, encoding="utf-8-sig")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(df[["변형", "H", "수수료", "문턱", "IC평균", "IC_t(일별)", "상위10%수익(%)", "하위10%수익(%)", "수익률(%)",
                  "샤프", "MDD(%)", "거래", "승률(%)", "손익비", "평균거래(%)", "판정"]].to_string(index=False))
    return df


REG = {"num_leaves": 15, "min_data_in_leaf": 1000, "n_rounds": 200}
ROUNDS = {
    "M01": [(f"H{H}{'_참고' if ref else ''}", {"H": H, "use_ref": ref, "thrs": (0.0, 0.002)})
            for H in (3, 6, 12) for ref in (False, True)],
    # M02: 더 긴 보유(2시간·4시간·장마감) + 큰 예측만 + 규제 강화
    "M02": [(f"H{H}{'_참고' if ref else ''}", {"H": H, "use_ref": ref, "thrs": (0.002, 0.004, 0.006), "params": REG})
            for H in (24, 48, 78) for ref in (False, True)],
}
# M03: 목표를 '비용보다 크게 오를 확률'로 + 같은 시각 종목 간 순위 지표. 확률 문턱으로 거래
_M3 = []
for H in (24, 48, 78):
    _M3.append((f"H{H}_분류", {"H": H, "target": "cls", "cls_thr": 0.006, "thrs": (0.25, 0.35, 0.45), "params": REG}))
    _M3.append((f"H{H}_분류_순위", {"H": H, "target": "cls", "cls_thr": 0.006, "cs": True, "thrs": (0.25, 0.35, 0.45),
                                  "params": REG}))
    _M3.append((f"H{H}_회귀_순위", {"H": H, "cs": True, "thrs": (0.004, 0.006), "params": REG}))
ROUNDS["M03"] = _M3

if __name__ == "__main__":
    rnd = sys.argv[1]
    period = sys.argv[2] if len(sys.argv) > 2 else "dev"
    run(rnd, ROUNDS[rnd], period)
