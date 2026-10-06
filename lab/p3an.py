import pandas as pd, numpy as np
t = pd.read_csv(r"results_x\V05_robust_P3\P3_trades.csv", encoding="utf-8-sig")
t["ts"] = pd.to_datetime(t["시각(ET)"])
rows, last = [], {}
for r in t.itertuples():
    if r.구분 == "매수":
        last[r.종목] = (r.사유, r.ts, r.가격_ if hasattr(r, "가격_") else r[5])
    else:
        why, bts, bpx = last.get(r.종목, ("?", r.ts, np.nan))
        rows.append({"sleeve": "K몫" if str(why).startswith("K몫") else "로테이션" if str(why).startswith("로테이션") else "?",
                     "pnl": r.손익_ if hasattr(r, "손익_") else r[6], "ret": r[7], "days": np.busday_count(bts.date(), r.ts.date()),
                     "exit": str(r.사유)[:12], "code": r.종목, "buy_why": why})
d = pd.DataFrame(rows)
d["win"] = d["pnl"] > 0
print(d.groupby("sleeve").agg(n=("pnl", "size"), win=("win", "mean"), pnl=("pnl", "sum"), avg_ret=("ret", "mean"), med_days=("days", "median")).round(3))
k = d[d.sleeve == "K몫"].copy()
k["w"] = k["buy_why"].str.extract(r"비중 ([\d.]+)%")[0].astype(float)
k["wbin"] = pd.cut(k["w"], [0, 1, 2, 3, 5, 10, 100])
print(k.groupby("wbin", observed=True).agg(n=("pnl", "size"), win=("win", "mean"), pnl=("pnl", "sum"), avg_ret=("ret", "mean")).round(3))
k["dbin"] = pd.cut(k["days"], [-1, 0, 1, 3, 7, 20, 500])
print(k.groupby("dbin", observed=True).agg(n=("pnl", "size"), win=("win", "mean"), pnl=("pnl", "sum"), avg_ret=("ret", "mean")).round(3))
print(k.groupby("exit").agg(n=("pnl", "size"), win=("win", "mean"), pnl=("pnl", "sum")).round(2))
