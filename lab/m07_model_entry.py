"""M07: 지표 예측 모델(M05 워크포워드 예측)로 매수 + 규칙으로 매도(손절 4% · 고점 +3% 뒤 1% 하락 익절 · 최대 N일)
같은 실시간 엔진으로 과거를 흘림. IS로 고르고 OOS는 확인만. 사용: python m07_model_entry.py <M05예측이름> [보유일]"""
import os, sys, time
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import kiwoom_autotrader as K
import research as RS
import mres as R, mres_h as RH
from m06_meta import Lookup

OUT = os.path.join(ROOT, "results_minute", "M07_model_entry")
os.makedirs(OUT, exist_ok=True)


def main(pred_name, hold=10):
    t0 = time.time()
    panel = RH.build_panel_h()
    pred = pd.read_pickle(os.path.join(R.RES, "M05", f"{pred_name}_pred.pkl"))["pred"]
    lu = Lookup(panel, pred)
    q = pred.quantile([0.9, 0.95, 0.98]).round(4).to_dict()
    bars = RS.data("60m")
    rows = []
    for qn, thr in q.items():
        for pos, pct in ((5, 20.0), (8, 12.5)):
            ov = dict(trend_ma_days=0, hold_overnight=True, max_hold_days=hold, min_profit_pct=3.0, trail_pct=1.0,
                      stop_loss_pct=4.0, max_trades_per_symbol=1, max_positions=pos, position_pct=pct)
            cfg = RS.make_cfg(ov)
            sig = lambda code, ts, s: (lambda v: None if v != v else float(v))(lu.get(code, ts))
            r = K.simulate(cfg, bars, None, entry_signal=sig, entry_thr=thr)
            name = f"{pred_name}_상위{int(round((1 - qn) * 100))}%_{pos}종목_보유{hold}"
            row = {"변형": name, "문턱": thr}
            for per, (a, b) in RS.PERIODS.items():
                mm = K.sim_metrics(r, a, b, spy_close=RS.spy())
                row.update({f"{per}_{k}": v for k, v in mm.items() if k not in ("시작", "끝")})
            row["IS판정"], row["OOS판정"] = RS.judge(row, "IS"), RS.judge(row, "OOS")
            rows.append(row)
            K.save_sim(r, OUT, name, row, cfg)
            print(name, {k: row.get(k) for k in ("IS_연환산(%)", "IS_샤프", "IS_MDD(%)", "OOS_연환산(%)", "OOS_샤프", "OOS_MDD(%)")},
                  round(time.time() - t0), "s", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, f"summary_{pred_name}_{hold}.csv"), index=False, encoding="utf-8-sig")
    with pd.option_context("display.width", 260, "display.max_columns", 30):
        print(df[["변형", "IS_연환산(%)", "IS_샤프", "IS_MDD(%)", "IS_청산횟수", "IS_손익비", "OOS_연환산(%)", "OOS_샤프",
                  "OOS_MDD(%)", "OOS_청산횟수", "OOS_손익비", "IS판정", "OOS판정"]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10)
