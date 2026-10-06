import pandas as pd
for name in ("KD 국면0", "KD k0.7 저점7% 국면0", "A 국면0 당일거래"):
    e = pd.read_csv(fr"results_x\W02_mdd5\{name}_equity.csv", encoding="utf-8-sig")
    e["날짜"] = pd.to_datetime(e["날짜"]); s = e.set_index("날짜")["자산($)"]
    dd = s / s.cummax() - 1
    print("=====", name)
    # top drawdown episodes
    eps, in_dd, start = [], False, None
    for d, v in dd.items():
        if v < -0.03 and not in_dd: in_dd, start = True, d
        if in_dd and v == 0: eps.append((start, d, dd[start:d].min(), dd[start:d].idxmin())); in_dd = False
    if in_dd: eps.append((start, dd.index[-1], dd[start:].min(), dd[start:].idxmin()))
    for a, b, m, t in sorted(eps, key=lambda x: x[2])[:6]:
        print(f"  {a.date()}~{b.date()} 최저 {m*100:.1f}% @ {t.date()} 국면노출(최저일) {e.set_index('날짜').loc[t,'국면노출']}")
    t = pd.read_csv(fr"results_x\W02_mdd5\{name}_trades.csv", encoding="utf-8-sig")
    t["d"] = pd.to_datetime(t["시각(ET)"]).dt.normalize()
    worst = sorted(eps, key=lambda x: x[2])[0]
    w = t[(t["d"] >= worst[0] - pd.Timedelta(days=5)) & (t["d"] <= worst[3]) & (t["구분"] == "매도")]
    print("  worst-episode sells by reason:", w.groupby(w["사유"].str.extract(r"^(\S+)")[0])["손익($)"].agg(["count", "sum"]).round(0).to_dict())
    print("  by code:", w.groupby("종목")["손익($)"].sum().sort_values().head(6).round(0).to_dict())
