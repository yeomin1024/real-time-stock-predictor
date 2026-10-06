import pandas as pd, numpy as np, sys
name = sys.argv[1]
t = pd.read_csv(fr"..\results_x\T01_winrate\{name}_trades.csv", encoding="utf-8-sig")
t["ts"] = pd.to_datetime(t["시각(ET)"])
rows, last = [], {}
for r in t.itertuples(index=False):
    d = r._asdict() if hasattr(r, "_asdict") else None
for _, r in t.iterrows():
    if r["구분"] == "매수":
        last[r["종목"]] = (r["사유"], r["ts"])
    else:
        why, bts = last.get(r["종목"], ("?", r["ts"]))
        rows.append({"sleeve": "K몫" if str(why).startswith("K몫") else "로테이션", "pnl": r["손익($)"], "ret": r["수익률(%)"],
                     "exit": str(r["사유"]).split("(")[0][:14], "days": np.busday_count(bts.date(), r["ts"].date())})
d = pd.DataFrame(rows); d["win"] = d.pnl > 0
print(d.groupby(["sleeve", "exit"]).agg(n=("pnl", "size"), win=("win", "mean"), pnl=("pnl", "sum"), avg=("ret", "mean")).round(3).to_string())
print("losers by exit:", d[~d.win].groupby("exit").size().to_dict())
