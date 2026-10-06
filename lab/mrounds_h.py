"""시간봉 지표 예측 라운드. 사용: python mrounds_h.py M05"""
import os, sys, time
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mres as R
import mres_h as RH

TARGETS = {"IC_t(일별)": 2.0, "연환산(%)": 10.0, "샤프": 1.0, "MDD(%)": -10.0, "손익비": 1.2, "거래": 40}
REG = {"num_leaves": 15, "min_data_in_leaf": 1000, "n_rounds": 200}
INIT, FOLD = 120, 21


def judge(row):
    bad = [f"{k} {row.get(k)}" for k, v in TARGETS.items()
           if row.get(k) is None or row.get(k) != row.get(k) or row.get(k) < v]
    return "✅" if not bad else "❌ " + ", ".join(bad)


def run(rnd, variants):
    out = os.path.join(R.RES, rnd); os.makedirs(out, exist_ok=True)
    panel = RH.build_panel_h()
    is_last = int(panel.loc[panel["day"] <= RH.IS_END, "day_i"].max())
    nd = int(panel["day_i"].max())
    periods = {"IS": (INIT, is_last), "OOS": (is_last + 1, nd)}
    rows = []
    for name, v in variants:
        t0 = time.time()
        cols = R.feature_cols(panel, v.get("use_ref", False))
        if v.get("drop"):
            cols = [c for c in cols if not any(c.startswith(x) for x in v["drop"])]
        lab = v["label"]
        swing = lab in RH.H_SWING
        H = {**RH.H_INTRA, **RH.H_SWING}[lab]
        pp_path = os.path.join(out, f"{name}_pred.pkl")
        if os.path.exists(pp_path):
            pred = pd.read_pickle(pp_path)["pred"]
        else:
            pred = R.walk_forward(panel, lab, cols, INIT, nd, {**REG, **v.get("params", {})}, fold=FOLD,
                                  train_from=v.get("train_from", 0))
            pred.to_frame("pred").to_pickle(pp_path)
        for per, (a, b) in periods.items():
            pp = pred[panel.loc[pred.index, "day_i"].between(a, b)]
            q = R.signal_quality(panel, pp, lab)
            for fee in (0.25, 0.07):
                for thr in v["thrs"]:
                    m, eq, tr = RH.trade_sim2(panel, pp, lab, H, swing, thr, top_k=v.get("top_k", 2),
                                              max_pos=v.get("max_pos", 5), fee=fee)
                    row = {"라운드": rnd, "변형": name, "기간": per, "라벨": lab, "수수료": fee, "문턱": thr, **q, **m,
                           "초": round(time.time() - t0)}
                    row["판정"] = judge(row)
                    rows.append(row)
                    eq.to_csv(os.path.join(out, f"{name}_{per}_f{fee}_t{thr}_equity.csv"), encoding="utf-8-sig")
                    tr.to_csv(os.path.join(out, f"{name}_{per}_f{fee}_t{thr}_trades.csv"), index=False, encoding="utf-8-sig")
        print(name, "done", round(time.time() - t0), "s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, "summary.csv"), index=False, encoding="utf-8-sig")
    allp = os.path.join(R.RES, "all_hourly_rounds.csv")
    prev = pd.read_csv(allp, encoding="utf-8-sig") if os.path.exists(allp) else pd.DataFrame()
    if len(prev):
        prev = prev[prev["라운드"] != rnd]
    pd.concat([prev, df], ignore_index=True).to_csv(allp, index=False, encoding="utf-8-sig")
    show = df.pivot_table(index=["변형", "수수료", "문턱"], columns="기간",
                          values=["IC평균", "IC_t(일별)", "연환산(%)", "샤프", "MDD(%)", "손익비", "거래"], aggfunc="first")
    show.columns = [f"{p}_{m}" for m, p in show.columns]
    cols = [c for p in ("IS", "OOS") for c in show.columns if c.startswith(p)]
    with pd.option_context("display.width", 300, "display.max_columns", 30, "display.max_rows", 200):
        print(show[cols].to_string())
    return df


ROUNDS = {
    "M05": [(f"{lab}{'_참고' if ref else ''}", {"label": lab, "use_ref": ref,
                                                "thrs": (0.002, 0.004, 0.006) if lab in RH.H_INTRA else (0.005, 0.01, 0.015)})
            for lab in ("h3", "eod", "s7", "s14", "s35") for ref in (False, True)],
}

if __name__ == "__main__":
    # python mrounds_h.py M05 [pred]  — 'pred'면 예측만 하나씩(프로세스당 1개), 아니면 저장된 예측으로 요약
    rnd = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "pred":
        name = sys.argv[3]
        run(rnd + "_tmp", [v for v in ROUNDS[rnd] if v[0] == name]) if False else None
        panel = RH.build_panel_h()
        v = dict(ROUNDS[rnd])[name]
        out = os.path.join(R.RES, rnd); os.makedirs(out, exist_ok=True)
        pp_path = os.path.join(out, f"{name}_pred.pkl")
        if not os.path.exists(pp_path):
            cols = R.feature_cols(panel, v.get("use_ref", False))
            if v.get("drop"):
                cols = [c for c in cols if not any(c.startswith(x) for x in v["drop"])]
            t0 = time.time()
            pred = R.walk_forward(panel, v["label"], cols, INIT, int(panel["day_i"].max()),
                                  {**REG, **v.get("params", {})}, fold=FOLD, train_from=v.get("train_from", 0))
            pred.to_frame("pred").to_pickle(pp_path)
            print(name, "pred", round(time.time() - t0), "s", flush=True)
    else:
        run(rnd, ROUNDS[rnd])
