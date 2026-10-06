"""분봉 지표 재테스트 결과 → results_minute/분봉지표_재테스트_결과.xlsx"""
import os, glob
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(os.path.dirname(HERE), "results_minute")

sheets = {}
p = os.path.join(RES, "all_minute_rounds.csv")
if os.path.exists(p):
    sheets["01_5분봉_M01~M03"] = pd.read_csv(p, encoding="utf-8-sig")
p = os.path.join(RES, "M04_pool", "summary.csv")
if os.path.exists(p):
    sheets["02_지표풀3380_M04"] = pd.read_csv(p, encoding="utf-8-sig")
p = os.path.join(RES, "all_hourly_rounds.csv")
if os.path.exists(p):
    sheets["03_시간봉모델_M05"] = pd.read_csv(p, encoding="utf-8-sig")
p = os.path.join(RES, "M05", "importance.csv")
if os.path.exists(p):
    sheets["04_지표중요도"] = pd.read_csv(p, encoding="utf-8-sig", index_col=0).round(2).reset_index().rename(columns={"index": "지표"})
m6 = [pd.read_csv(f, encoding="utf-8-sig") for f in glob.glob(os.path.join(RES, "M06_meta", "summary_*.csv"))]
if m6:
    sheets["05_메타라벨_M06"] = pd.concat(m6)
m7 = [pd.read_csv(f, encoding="utf-8-sig") for f in glob.glob(os.path.join(RES, "M07_model_entry", "summary_*.csv"))]
if m7:
    sheets["06_모델매수_M07"] = pd.concat(m7)
sheets["07_미래정보지표"] = pd.DataFrame({"지표 풀에서 미래 정보를 쓰는 지표(분봉 인과성 검사)": [
    "cycl_regime_ret_in_high_vix", "def_regime_ret_in_high_vix", "fin_regime_ret_in_high_vix",
    "hlth_regime_ret_in_high_vix", "reit_regime_ret_in_high_vix", "overnight_neg_gap_zscore_60",
    "reitx_shock_day_ret", "vp_highvol_down_ratio_20d"]})
out = os.path.join(RES, "분봉지표_재테스트_결과.xlsx")
with pd.ExcelWriter(out, engine="xlsxwriter") as xw:
    for n, df in sheets.items():
        df.to_excel(xw, sheet_name=n[:31], index=False)
print("saved", out, list(sheets))
