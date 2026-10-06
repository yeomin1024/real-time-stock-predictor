"""거래내역 진단: 청산 유형별 손익, 보유시간, 비용 전 수익률"""
import sys, os
import pandas as pd

P = "손익($)"


def diag(path, fee_rt=0.6):
    t = pd.read_csv(path, encoding="utf-8-sig")
    b = t[t["구분"] == "매수"].reset_index(drop=True)
    s = t[t["구분"] == "매도"].reset_index(drop=True)
    s["유형"] = s["사유"].str.extract(r"^(손절|장마감 청산|고점|그날)")[0].fillna("기타")
    print("=====", os.path.basename(path), "청산", len(s))
    g = s.groupby("유형").agg(건수=(P, "size"), 평균수익률=("수익률(%)", "mean"), 합계손익=(P, "sum"))
    print(g.round(3).to_string())
    n = min(len(b), len(s))
    hold = (pd.to_datetime(s["시각(ET)"][:n]) - pd.to_datetime(b["시각(ET)"][:n])).dt.total_seconds() / 60
    gross = (s["가격($)"][:n].values / b["가격($)"][:n].values - 1) * 100
    print(f"보유(분) 중앙값 {hold.median():.0f} | 가격만의 평균수익률(비용 전, 슬리피지 포함) {gross.mean():.3f}% "
          f"| 비용 포함 평균 {s['수익률(%)'].mean():.3f}%")
    print("매수 시각:", pd.to_datetime(b["시각(ET)"]).dt.hour.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    for p in sys.argv[1:]:
        diag(p)
