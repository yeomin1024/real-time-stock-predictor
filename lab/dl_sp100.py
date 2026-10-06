"""사후 선택 편향 점검용 유니버스: 2023년 말 S&P 100(대형주) 구성 — 2026년에 고른 K 유니버스와 달리 시작 시점에 정해진 목록
→ lab/data/bars_60m_sp.pkl (시간봉) + sp100_sector.pkl (야후 섹터)"""
import os, sys, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import kiwoom_autotrader as K
import yfinance as yf

SP100_2023 = ["AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN", "AVGO", "AXP", "BA", "BAC",
              "BK", "BKNG", "BLK", "BMY", "BRK-B", "C", "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM",
              "CSCO", "CVS", "CVX", "DE", "DHR", "DIS", "DOW", "DUK", "EMR", "EXC", "F", "FDX", "GD", "GE", "GILD",
              "GM", "GOOGL", "GS", "HD", "HON", "IBM", "INTC", "INTU", "JNJ", "JPM", "KHC", "KO", "LIN", "LLY", "LMT",
              "LOW", "MA", "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX", "NKE",
              "NVDA", "ORCL", "PEP", "PFE", "PG", "PM", "PYPL", "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT",
              "TMO", "TMUS", "TSLA", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM"]

if __name__ == "__main__":
    bars = K.download_hourly_yf(SP100_2023)
    tmp = os.path.join(HERE, "data", "bars_60m_sp.tmp")
    pickle.dump(bars, open(tmp, "wb"))
    os.replace(tmp, os.path.join(HERE, "data", "bars_60m_sp.pkl"))
    sec = {}
    for c in SP100_2023:
        try:
            sec[c] = yf.Ticker(c).info.get("sector", "")
        except Exception as e:
            sec[c] = ""
    pickle.dump(sec, open(os.path.join(HERE, "data", "sp100_sector.pkl"), "wb"))
    print(len(bars), "bars;", "missing", [c for c in SP100_2023 if c not in bars])
    print(sec)
