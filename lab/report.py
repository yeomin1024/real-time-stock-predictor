"""결과 묶음: results/시뮬레이션_결과.xlsx + 자산곡선 그림"""
import os, sys, json
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import kiwoom_autotrader as K
import research as R

FINAL = [("R05_prior_models", "A5+M+S", "C1 (채택)"), ("R05_prior_models", "A5+M+S+I", "C2"),
         ("R04_regime_div", "A", "A (필터 없음)"), ("R01_baseline", "기준", "R1 기준선")]


def equity(rnd, name, iv="60m"):
    e = pd.read_csv(os.path.join(RES, rnd, f"{name}_{iv}_equity.csv"), encoding="utf-8-sig")
    e["날짜"] = pd.to_datetime(e["날짜"])
    return e.set_index("날짜")["자산($)"]


def quarterly(rnd, name):
    s = equity(rnd, name)
    spy = R.spy()
    q = s.resample("QE").last()
    prev = q.shift(1)
    prev.iloc[0] = 10000.0
    out = pd.DataFrame({"전략(%)": (q / prev - 1) * 100})
    sq = spy.resample("QE").last()
    out["SPY(%)"] = (sq / sq.shift(1) - 1).reindex(out.index) * 100
    out.index = [f"{d.year}Q{(d.month - 1) // 3 + 1}" for d in out.index]
    return out.round(2)


def main():
    allr = pd.read_csv(os.path.join(RES, "all_rounds.csv"), encoding="utf-8-sig")
    tgt = pd.DataFrame([{"지표(OOS·IS 공통)": k, "조건": f"{op} {v}"} for k, (op, v) in R.TARGETS.items()])
    setup = pd.DataFrame([
        ("데이터", "야후 시간봉 2023-11-02~2026-10-01 (정밀도 검증: 5분봉 60일, 1분봉 17일)"),
        ("유니버스", f"이전 종목 예측 코드(K)의 {len(R.UNIVERSE)}종 (AVB 제외 — 데이터 없음)"),
        ("IS(설정 고르는 기간)", f"{R.PERIODS['IS'][0]} ~ {R.PERIODS['IS'][1]}"),
        ("OOS(확인만 하는 기간)", f"{R.PERIODS['OOS'][0]} ~ {R.PERIODS['OOS'][1]}"),
        ("시작 가상자산", "$10,000"),
        ("비용", "수수료 0.25%(매수·매도 각각) + SEC 0.003% + 슬리피지 0.05%"),
        ("M 국면", "market_regime_trader v1.81.1 01_일별기록 목표비중 (전날까지 확정된 값만)"),
        ("S 섹터 / I 산업", "sector_allocation_daily.csv(~2026-09-25) / industry_allocation_daily.csv·industry_daily.csv(~2026-10-01)"),
    ], columns=["항목", "내용"])
    curves = {}
    for rnd, name, label in FINAL:
        try:
            curves[label] = equity(rnd, name)
        except FileNotFoundError:
            pass
    cdf = pd.DataFrame(curves)
    spy = R.spy().reindex(cdf.index).ffill()
    cdf["SPY(같은 $10,000)"] = spy / spy.iloc[0] * 10000
    path = os.path.join(RES, "시뮬레이션_결과.xlsx")
    with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
        setup.to_excel(xw, "00_설정", index=False)
        tgt.to_excel(xw, "01_목표치", index=False)
        cols = [c for c in ["라운드", "변형", "봉", "IS_수익률(%)", "IS_연환산(%)", "IS_샤프", "IS_MDD(%)", "IS_청산횟수",
                            "IS_승률(%)", "IS_손익비", "IS판정", "OOS_수익률(%)", "OOS_연환산(%)", "OOS_샤프", "OOS_MDD(%)",
                            "OOS_청산횟수", "OOS_승률(%)", "OOS_손익비", "OOS판정", "IS_SPY수익률(%)", "IS_SPY샤프",
                            "OOS_SPY수익률(%)", "OOS_SPY샤프", "전체_기간", "전체_수익률(%)", "전체_샤프", "전체_MDD(%)",
                            "전체_청산횟수", "전체_SPY수익률(%)"] if c in allr.columns]
        allr[cols].to_excel(xw, "02_전체라운드", index=False)
        cdf.round(2).to_excel(xw, "03_자산곡선")
        for rnd, name, label in FINAL[:2]:
            quarterly(rnd, name).to_excel(xw, f"04_분기_{label.split()[0]}")
            t = pd.read_csv(os.path.join(RES, rnd, f"{name}_60m_trades.csv"), encoding="utf-8-sig")
            t.to_excel(xw, f"05_거래_{label.split()[0]}", index=False)
        ws = xw.sheets["03_자산곡선"]
        ch = xw.book.add_chart({"type": "line"})
        n = len(cdf)
        for i, col in enumerate(cdf.columns, start=1):
            ch.add_series({"name": ["03_자산곡선", 0, i], "categories": ["03_자산곡선", 1, 0, n, 0],
                           "values": ["03_자산곡선", 1, i, n, i], "line": {"width": 1.5}})
        ch.set_title({"name": "가상자산 곡선 ($10,000 시작)"})
        ch.set_size({"width": 960, "height": 480})
        ws.insert_chart("H2", ch)
    print("saved", path)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(11, 5))
        for col in cdf.columns:
            ax.plot(cdf.index, cdf[col], label=col, lw=1.6 if "C1" in col else 1.0)
        ax.axvline(pd.Timestamp(R.PERIODS["OOS"][0]), color="gray", ls="--", lw=1)
        ax.text(pd.Timestamp(R.PERIODS["OOS"][0]), ax.get_ylim()[1], " OOS(확인 기간) →", va="top", color="gray")
        ax.set_title("과거 실시간 시뮬레이션 — 가상자산 $10,000")
        ax.legend()
        ax.grid(alpha=.3)
        fig.tight_layout()
        fig.savefig(os.path.join(RES, "자산곡선.png"), dpi=120)
        print("saved png")
    except Exception as e:
        print("png 실패", e)


if __name__ == "__main__":
    main()
