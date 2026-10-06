"""M06 메타 라벨링: 지표 규칙 전략(A)의 매수 신호마다 '그때 지표 137개'로 성공 확률을 예측해 높은 것만 산다.
- 모델은 매달 '그 달 전에 끝난 거래'로만 다시 학습(워크포워드) → 예측은 직전에 닫힌 시간봉의 지표로
- IS(2023-11~2025-07)로 문턱을 고르고, OOS(2025-08~2026-10)는 확인만
사용: python m06_meta.py [lgb|logit] [base=A|C1]"""
import os, sys, time, json
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import kiwoom_autotrader as K
import research as RS
import rounds as RD
import mres as R
import mres_h as RH

OUT = os.path.join(ROOT, "results_minute", "M06_meta")
os.makedirs(OUT, exist_ok=True)


def pair_events(trades):
    t = trades.copy()
    t["ts"] = pd.to_datetime(t["시각(ET)"])
    ev = []
    for code, g in t.groupby("종목"):
        g = g.sort_values("ts")
        buy = None
        for _, r in g.iterrows():
            if r["구분"] == "매수":
                buy = r
            elif buy is not None:
                ev.append({"code": code, "entry": buy["ts"], "exit": r["ts"], "ret": float(r["수익률(%)"])})
                buy = None
    return pd.DataFrame(ev).sort_values("entry").reset_index(drop=True)


class Lookup:
    """(종목, 시각) → 직전에 닫힌 시간봉의 값"""
    def __init__(self, panel, values: pd.Series):
        self.d = {}
        for code, g in panel.loc[values.index, ["code", "ts"]].assign(v=values).groupby("code"):
            g = g.sort_values("ts")
            self.d[code] = (g["ts"].to_numpy(), g["v"].to_numpy())

    def get(self, code, ts, default=np.nan):
        if code not in self.d:
            return default
        t, v = self.d[code]
        bar_start = np.datetime64(K.bar_bucket(ts, 60).replace(tzinfo=None))
        i = np.searchsorted(t, bar_start, side="left") - 1          # 시작 시각이 지금 봉보다 앞인 마지막 봉 = 닫힌 봉
        return v[i] if i >= 0 else default


def main(kind="lgb", base="A"):
    t0 = time.time()
    panel = RH.build_panel_h()
    cols = R.feature_cols(panel, use_ref=False)
    base_ov = RD.BASE_A if base == "A" else RD.C1
    cfg = RS.make_cfg(base_ov)
    sig = K.DailySignals(cfg) if (cfg.regime == "M" or cfg.sector_filter) else None
    bars = RS.data("60m")
    res = K.simulate(cfg, bars, sig)
    ev = pair_events(res["trades"])
    print("기준 거래", len(ev), "건", round(time.time() - t0), "s", flush=True)
    # 이벤트 지표 = 진입 직전 닫힌 봉의 지표
    row_lu = Lookup(panel, pd.Series(panel.index, index=panel.index))
    ev["row"] = [row_lu.get(c, e.to_pydatetime().replace(tzinfo=K.ET)) for c, e in zip(ev["code"], ev["entry"])]
    ev = ev.dropna(subset=["row"])
    ev["row"] = ev["row"].astype(int)
    X = panel.loc[ev["row"], cols].to_numpy()
    y = (ev["ret"] > 0).astype(int).to_numpy()
    # 월별 워크포워드: 그 달 시작 전에 '끝난' 거래로 학습 → 그 달의 모든 봉에 확률
    months = pd.period_range(panel["ts"].min(), panel["ts"].max(), freq="M")
    probs = pd.Series(np.nan, index=panel.index, dtype=float)
    imp = None
    for m in months:
        ms, me = m.start_time, m.end_time
        tr = (ev["exit"] < ms).to_numpy()
        if tr.sum() < 80:
            continue
        rows = panel.index[(panel["ts"] >= ms) & (panel["ts"] <= me)]
        if kind == "lgb":
            import lightgbm as lgb
            mdl = lgb.train(dict(objective="binary", learning_rate=0.05, num_leaves=7, min_data_in_leaf=20,
                                 feature_fraction=0.5, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0,
                                 verbose=-1, seed=7, num_threads=2), lgb.Dataset(X[tr], y[tr]), 150)
            probs.loc[rows] = mdl.predict(panel.loc[rows, cols].to_numpy())
            imp = pd.Series(mdl.feature_importance("gain"), index=cols)
        else:
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import make_pipeline
            from sklearn.preprocessing import StandardScaler
            from sklearn.impute import SimpleImputer
            mdl = make_pipeline(SimpleImputer(), StandardScaler(), LogisticRegression(C=0.05, max_iter=500))
            mdl.fit(X[tr], y[tr])
            probs.loc[rows] = mdl.predict_proba(panel.loc[rows, cols].to_numpy())[:, 1]
    print("확률 계산", probs.notna().sum(), "봉", round(time.time() - t0), "s", flush=True)
    lu = Lookup(panel, probs.fillna(1.0))           # 모델이 아직 없던 초기 몇 달은 통과
    # 이벤트 수준 진단: 예측 확률 vs 실제 결과(워크포워드 확률)
    ev["p"] = [lu.get(c, e.to_pydatetime().replace(tzinfo=K.ET)) for c, e in zip(ev["code"], ev["entry"])]
    is_m = ev["entry"] <= RS.PERIODS["IS"][1]
    diag = {}
    for per, msk in (("IS", is_m), ("OOS", ~is_m)):
        e = ev[msk & (ev["p"] < 1.0)]
        if len(e) > 20:
            hi = e["p"] >= e["p"].median()
            diag[per] = {"거래": len(e), "확률-수익 상관": round(e["p"].corr(e["ret"], method="spearman"), 3),
                         "확률 상위절반 평균(%)": round(e.loc[hi, "ret"].mean(), 3),
                         "하위절반 평균(%)": round(e.loc[~hi, "ret"].mean(), 3)}
    print("이벤트 진단", diag, flush=True)
    rows = []
    for tau in (None, 0.45, 0.5, 0.55, 0.6):
        f = None if tau is None else (lambda code, ts, s, tau=tau: lu.get(code, ts, 1.0) >= tau)
        r = K.simulate(cfg, bars, sig, entry_filter=f)
        name = f"{base}_{kind}_" + ("필터없음" if tau is None else f"p{tau}")
        row = {"변형": name}
        for per, (a, b) in RS.PERIODS.items():
            mm = K.sim_metrics(r, a, b, spy_close=RS.spy())
            row.update({f"{per}_{k}": v for k, v in mm.items() if k not in ("시작", "끝")})
        row["IS판정"], row["OOS판정"] = RS.judge(row, "IS"), RS.judge(row, "OOS")
        rows.append(row)
        K.save_sim(r, OUT, name, row, cfg)
        print(name, {k: row[k] for k in ("IS_수익률(%)", "IS_샤프", "IS_MDD(%)", "OOS_수익률(%)", "OOS_샤프", "OOS_MDD(%)")},
              round(time.time() - t0), "s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, f"summary_{base}_{kind}.csv"), index=False, encoding="utf-8-sig")
    if imp is not None:
        imp.sort_values(ascending=False).head(30).to_csv(os.path.join(OUT, f"importance_{base}_{kind}.csv"), encoding="utf-8-sig")
    json.dump(diag, open(os.path.join(OUT, f"diag_{base}_{kind}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(df[["변형", "IS_수익률(%)", "IS_샤프", "IS_MDD(%)", "IS_청산횟수", "IS_손익비", "OOS_수익률(%)", "OOS_샤프",
                  "OOS_MDD(%)", "OOS_청산횟수", "OOS_손익비", "IS판정", "OOS판정"]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "lgb", sys.argv[2] if len(sys.argv) > 2 else "A")
