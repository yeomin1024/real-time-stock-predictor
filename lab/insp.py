import pandas as pd, warnings
warnings.filterwarnings("ignore")
R = r"lab\reports"
spec = [("market_regime_report_v1.83.0.xlsx", ["01_일별기록"]),
        ("sector_regime_report_v0.98.0.xlsx", ["13c_일별배분비중", "01Z_섹터일별예측"]),
        ("industry_regime_report_v0.63.0.xlsx", ["13c_일별배분비중", "01Z_산업일별예측"]),
        ("stock_regime_report_v0.31.0.xlsx", ["13c_일별배분비중", "01Z_주식일별예측", "00W_물타기손절", "13_주식배분전략"])]
for f, sheets in spec:
    for sh in sheets:
        df = pd.read_excel(f"{R}\\{f}", sheet_name=sh, header=None, nrows=8)
        print("=====", f, sh)
        print(df.iloc[:6, :14].to_string())
