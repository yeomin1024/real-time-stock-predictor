"""M05 예측의 신호 품질만 빠르게(IS / OOS)"""
import os, sys, glob
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mres as R, mres_h as RH

panel = RH.build_panel_h()
is_last = int(panel.loc[panel["day"] <= RH.IS_END, "day_i"].max())
rows = []
for f in sorted(glob.glob(os.path.join(R.RES, "M05", "*_pred.pkl"))):
    name = os.path.basename(f)[:-9]
    lab = name.split("_")[0]
    pred = pd.read_pickle(f)["pred"]
    di = panel.loc[pred.index, "day_i"]
    for per, mask in (("IS", di <= is_last), ("OOS", di > is_last)):
        q = R.signal_quality(panel, pred[mask], lab)
        rows.append({"변형": name, "기간": per, **{k: q[k] for k in ("IC평균", "IC_t(일별)", "상위10%수익(%)", "하위10%수익(%)", "전체평균(%)")}})
df = pd.DataFrame(rows)
with pd.option_context("display.width", 200):
    print(df.pivot_table(index="변형", columns="기간", values=["IC평균", "IC_t(일별)", "상위10%수익(%)", "하위10%수익(%)"]).round(3).to_string())
