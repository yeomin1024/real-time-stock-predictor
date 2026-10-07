"""signals_v4(M v1.86 · S v1.02 · I v0.66 · K v0.36) + 하루 지연판 + 새 K 종목(숏 −1배 ETF·MAA 등) 시간봉 → lab/data/bars_60m_k4.pkl
사용: python lab/build_v4.py   (2026-10-07)"""
import os, sys, glob, pickle, logging
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import kiwoom_autotrader as K
_h = logging.StreamHandler(); _h.setFormatter(logging.Formatter("[%(stage)s] %(asctime)s %(message)s"))
LOG = logging.getLogger("build_v4"); LOG.addHandler(_h); LOG.setLevel(os.environ.get("LOG_LEVEL", "INFO")); LOG.propagate = False
L = lambda st, msg: LOG.info(msg, extra={"stage": st})
REP = os.path.join(HERE, "reports_v4", "2026-10-06")
SIG, LAG = os.path.join(HERE, "signals_v4"), os.path.join(HERE, "signals_v4_lag1")
done = K.signals_from_reports(REP, SIG)
for k, v in done.items():
    L("LOAD", f"file={k} src={v}")
# 하루 지연판: 날짜 열을 다음 행 날짜로(= 신호가 하루 늦게 도착). 실적 발표일·풀 섹터표는 그대로 복사
os.makedirs(LAG, exist_ok=True)
for n in os.listdir(SIG):
    df = pd.read_csv(os.path.join(SIG, n), encoding="utf-8-sig", low_memory=False)
    if n not in ("earnings_dates.csv", "stock_pool_sector.csv"):
        d = pd.to_datetime(df.iloc[:, 0], errors="coerce")
        nxt = d.shift(-1).fillna(d.iloc[-1] + pd.offsets.BDay(1))
        df.iloc[:, 0] = nxt.dt.strftime("%Y-%m-%d")
    df.to_csv(os.path.join(LAG, n), index=False, encoding="utf-8-sig")
L("LOAD", f"lag1 files={len(os.listdir(LAG))}")
# 새 종목 시간봉
have = set()
OUTP = os.path.join(HERE, "data", "bars_60m_k4.pkl")
for f in glob.glob(os.path.join(HERE, "data", "bars_60m*.pkl")):
    if f == OUTP:
        continue                                  # 이 파일은 매번 새로 만듦(덮어쓰기로 종목이 빠지지 않게)
    have |= set(pickle.load(open(f, "rb")))
uni = K.k_symbols(SIG, base={c: "NA" for c in K.DEFAULT_UNIVERSE}, min_weight=0.02, small_to_etf=True)
need = sorted(set(uni) - have)
L("LOAD", f"universe={len(uni)} need_download={need}")
import yfinance as yf
out = {}
for t in need:
    try:
        d = yf.download(t, interval="1h", period="730d", prepost=False, auto_adjust=False, progress=False, multi_level_index=False)
        if d is None or d.empty:            # 상장 730일 안쪽이면 period 요청이 거부됨 → 날짜로(BTSG와 같은 방법)
            st = (pd.Timestamp.now() - pd.Timedelta(days=729)).strftime("%Y-%m-%d")
            d = yf.download(t, interval="1h", start=st, prepost=False, auto_adjust=False, progress=False, multi_level_index=False)
    except Exception as e:
        L("LOAD", f"ticker={t} ERROR={e} → 다음 실행에서 다시 받기"); continue
    if d is None or d.empty:
        L("LOAD", f"ticker={t} rows=0 WARNING(상장 전·데이터 없음)"); continue
    d.index = d.index.tz_convert(K.ET).tz_localize(None)
    df = pd.DataFrame({"ts": d.index, "open": d["Open"].values, "high": d["High"].values, "low": d["Low"].values,
                       "close": d["Close"].values, "volume": d["Volume"].values}).dropna(subset=["open", "close"])
    dup = int(df["ts"].duplicated().sum())
    df = df[~df["ts"].duplicated()].sort_values("ts").reset_index(drop=True)
    out[t] = df
    L("LOAD", f"ticker={t} rows={len(df)} start={df.ts.min()} end={df.ts.max()} dup={dup} nan={int(df.isna().sum().sum())}")
pickle.dump(out, open(OUTP, "wb"))
L("LOAD", f"saved bars_60m_k4.pkl n={len(out)}")
