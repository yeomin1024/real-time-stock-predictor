"""시장 국면 모델(M)만 실행 → lab/out/market_regime_daily.csv"""
import os, sys, time, dataclasses
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
os.chdir(os.path.join(HERE, "src"))
import market_regime_trader as M

base = os.path.join(HERE, "out")
t0 = time.time()
cfg = dataclasses.replace(M.CFG, CACHE_DIR=os.path.join(base, "cache_market_data"),
                          OUT_XLSX=os.path.join(base, "market_regime_report.xlsx"),
                          RESULT_BUNDLE_PATH=os.path.join(base, "market_regime_result.pkl.gz"),
                          DAILY_CSV_PATH=os.path.join(base, "market_regime_daily.csv"))
print("M", M.BUNDLE_VERSION, flush=True)
res = M.run(cfg)
print("RUN_DONE", round(time.time() - t0), flush=True)
print("EXPORT", M.export_result_bundle(res, cfg), round(time.time() - t0), flush=True)
nd = M.build_next_day_prediction(res, cfg)
print("NEXT", nd["다음거래일"], nd["확정국면"], nd["목표비중"], flush=True)
