import pandas as pd
name = r"..\results_x\W15_pathfree_grid\PBR k0.7 저점5 국면0.5"
e = pd.read_csv(name + "_equity.csv", encoding="utf-8-sig"); e["날짜"] = pd.to_datetime(e["날짜"])
s = e.set_index("날짜")["자산($)"]; dd = s / s.cummax() - 1
t = dd.idxmin(); peak = s[:t].idxmax()
print("trough", t.date(), round(dd.min()*100, 2), "peak", peak.date())
print(e[(e["날짜"] >= peak - pd.Timedelta(days=3)) & (e["날짜"] <= t + pd.Timedelta(days=3))][["날짜", "자산($)", "현금($)", "당일실현($)", "국면노출", "보유종목"]].to_string())
tr = pd.read_csv(name + "_trades.csv", encoding="utf-8-sig"); tr["ts"] = pd.to_datetime(tr["시각(ET)"])
w = tr[(tr["ts"] >= peak) & (tr["ts"] <= t + pd.Timedelta(days=1))]
w = w.assign(kind=w["사유"].str.extract(r"^(\S+)")[0])
print(w[w["구분"] == "매도"].groupby("kind")["손익($)"].agg(["count", "sum"]).round(0))
print(w[w["구분"] == "매수"].assign(k2=w["사유"].str[:6]).groupby("k2").size())
