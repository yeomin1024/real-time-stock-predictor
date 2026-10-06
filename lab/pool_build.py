"""종목 1개의 지표 풀(5분봉) 계산 → data/pool5m/<종목>.pkl (float32). 사용: python pool_build.py NVDA"""
import os, sys, time, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mfeat as MF

code = sys.argv[1]
out = os.path.join(HERE, "data", "pool5m"); os.makedirs(out, exist_ok=True)
path = os.path.join(out, f"{code}.pkl")
if os.path.exists(path):
    print("skip", code); sys.exit(0)
bars = pickle.load(open(os.path.join(HERE, "data", "ohlcv_5m.pkl"), "rb"))
t0 = time.time()
peers = MF.peer_closes(bars, bars[code].index, [k for k in MF.INTRADAY_PEERS if k in bars and k != code])
f = MF.pool_features(code, bars, peers)
f.to_pickle(path)
print(code, f.shape, round(time.time() - t0), "s", flush=True)
