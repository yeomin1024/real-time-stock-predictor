import pandas as pd, numpy as np
o = pd.read_csv(r"lab\signals\market_regime_daily.csv", encoding="utf-8-sig", low_memory=False)
n = pd.read_csv(r"lab\signals_v2\market_regime_daily.csv", encoding="utf-8-sig", low_memory=False)
for d in (o, n):
    d.index = pd.to_datetime(d.iloc[:, 0]); 
a = pd.concat([o["목표비중"].rename("old"), n["목표비중"].rename("new")], axis=1).loc["2023-11-01":"2026-10-02"].astype(float)
print("M 2023-11~: mean old %.2f new %.2f, days differ %.0f%%, zero-days old %.0f%% new %.0f%%" % (a.old.mean(), a.new.mean(), (a.old != a.new).mean()*100, (a.old==0).mean()*100, (a.new==0).mean()*100))
k = pd.read_csv(r"lab\signals_v2\stock_allocation_daily.csv", encoding="utf-8-sig")
k.index = pd.to_datetime(k.iloc[:, 0]); k = k.loc["2023-11-01":"2026-10-02"]
tick = [c for c in k.columns[4:] if not c.startswith("ETF_")]
print("K sum mean %.2f, stocks held per day mean %.1f, days with any stock %.0f%%" % (k["★ 합계"].mean(), (k[tick] > 0).sum(axis=1).mean(), ((k[tick] > 0).sum(axis=1) > 0).mean()*100))
print("ETF weight mean", round(k[[c for c in k.columns if c.startswith("ETF_")]].sum(axis=1).mean(), 2))
print((k[tick] > 0).mean().sort_values(ascending=False).head(10).round(2).to_dict())
