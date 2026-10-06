"""IS 구간으로 학습한 모델의 지표 중요도(정보이득) 상위"""
import os, sys
import pandas as pd, lightgbm as lgb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mres as R, mres_h as RH

panel = RH.build_panel_h()
tr = panel[panel["day"] <= RH.IS_END]
out = {}
for lab, ref in (("s14", True), ("s35", True), ("s35", False)):
    cols = R.feature_cols(panel, ref)
    d = tr[tr[f"y_{lab}"].notna()]
    lo, hi = d[f"y_{lab}"].quantile([0.01, 0.99])
    m = lgb.train(dict(objective="regression", learning_rate=0.05, num_leaves=15, min_data_in_leaf=1000,
                       feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=7,
                       num_threads=2), lgb.Dataset(d[cols], d[f"y_{lab}"].clip(lo, hi)), 200)
    imp = pd.Series(m.feature_importance("gain"), index=cols)
    imp = (imp / imp.sum() * 100).sort_values(ascending=False)
    out[f"{lab}{'_참고' if ref else ''}"] = imp
    print(f"== {lab}{'_참고' if ref else ''} 상위 15 (중요도 %) ==")
    print(imp.head(15).round(1).to_string())
pd.DataFrame(out).to_csv(os.path.join(R.RES, "M05", "importance.csv"), encoding="utf-8-sig")
