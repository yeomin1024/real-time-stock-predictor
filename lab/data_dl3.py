"""추가 시간봉: BTSG(상장 730일 안쪽이라 period 요청이 거부됨 → 날짜로) + 레버리지 ETF·지수 ETF → lab/data/bars_60m_x.pkl"""
import os, sys, pickle, datetime as dt, logging
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from data_dl import clean

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
OUT = os.path.join(HERE, "data")
EXTRA = ["SPY", "QQQ", "TQQQ", "QLD", "SOXL", "USD", "TECL", "ROM", "UPRO", "SSO", "SPXL", "TNA", "LABU", "FAS",
         "NVDL", "TSLL", "CONL", "SMH", "SOXX"]

res = {}
raw = yf.download(EXTRA, interval="1h", period="730d", prepost=False, group_by="ticker", auto_adjust=False,
                  progress=False, threads=True)
for c in EXTRA:
    try:
        d = raw[c].dropna(subset=["Close"])
        if len(d):
            res[c] = clean(d)
    except KeyError:
        pass
start = (dt.date.today() - dt.timedelta(days=729)).isoformat()
d = yf.download("BTSG", interval="1h", start=start, prepost=False, auto_adjust=False, progress=False, multi_level_index=False)
if len(d):
    res["BTSG"] = clean(d.dropna(subset=["Close"]))
pickle.dump(res, open(os.path.join(OUT, "bars_60m_x.pkl"), "wb"))
for c, d in res.items():
    print(c, len(d), d.ts.min(), d.ts.max())
missing = [c for c in EXTRA + ["BTSG"] if c not in res]
print("missing", missing)
