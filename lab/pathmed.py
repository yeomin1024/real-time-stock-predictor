"""후보별 경로 4가지(기본·고가먼저·무작위1·2) 결과 모아 중앙값으로 비교"""
import os, pandas as pd
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results_x")
d = pd.read_csv(os.path.join(RES, "all_x_rounds.csv"), encoding="utf-8-sig")
d = d[d["라운드"].str.startswith("Z") & (d["라운드"] != "Z01_concentrate")]   # Z01은 갭 결함 수정 전
base = {"Q1": ("Z04_robust_Q1", "Q1"), "Q1 10일마다": ("Z04_robust_Q1", "Q1 10일마다"),
        "Q1 3일마다": ("Z04_robust_Q1", "Q1 3일마다"), "Q1 30일뺌": ("Z04_robust_Q1", "Q1 최근30일뺌"),
        "Q1 100일": ("Z04_robust_Q1", "Q1 100일"), "상위1 버퍼2": ("Z03_top2", "상위1 버퍼2"), "T2": ("Z02_rebase_gapfix", "상위2"),
        "Q1 로테이션만": ("Z05_path_median", "Q1 로테이션만")}
rows = []
for name, (rnd, var) in base.items():
    names = [var] + [f"{name} {p}" for p in ("고가먼저", "무작위1", "무작위2")]
    if name == "Q1":
        names = ["Q1", "Q1 고가먼저", "Q1 무작위1", "Q1 무작위2"]
    sub = d[d["변형"].isin(names)].drop_duplicates("변형")
    if len(sub) < 4:
        print("missing", name, len(sub)); continue
    rows.append({"후보": name, "기본": sub[sub["변형"] == names[0]]["ALL_수익률(%)"].iloc[0],
                 "경로4 중앙값": sub["ALL_수익률(%)"].median(), "경로4 최저": sub["ALL_수익률(%)"].min(),
                 "MDD 최악": sub["ALL_MDD(%)"].min(), "IS연환산 중앙": sub["IS_연환산(%)"].median(),
                 "OOS연환산 중앙": sub["OOS_연환산(%)"].median(), "샤프 중앙": sub["ALL_샤프"].median()})
out = pd.DataFrame(rows).sort_values("경로4 중앙값", ascending=False)
print(out.round(1).to_string(index=False))
out.to_csv(os.path.join(RES, "Z05_path_median", "path_median_summary.csv"), index=False, encoding="utf-8-sig")
