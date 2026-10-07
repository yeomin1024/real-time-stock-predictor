"""1000% 목표 탐색 라운드 — 과거 실시간 시뮬레이션(시간봉, 2023-11 ~ 2026-10)
사용: python xres.py <라운드이름>   (라운드 정의는 xrounds.py)

판정 규칙(테스트 전에 정함):
  목표  = 전체 수익률 ≥ +1000%  그리고  IS·OOS 각각 연환산 ≥ 128% (전체 1000%를 고르게 내는 속도)
  고르기 = IS(2023-11~2025-07) 결과로만, OOS(2025-08~2026-10)는 확인용
  참고  = 전체 MDD(낙폭)도 함께 기록 — 목표를 넘어도 MDD가 −35%보다 나쁘면 '위험 과다'로 표시
"""
import os, sys, json, pickle, time, math
from concurrent.futures import ProcessPoolExecutor
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import kiwoom_autotrader as K

DATA_DIR = os.path.join(HERE, "data")
SIG_DIR = os.path.join(HERE, os.environ.get("SIG", "signals_v2"))   # 2026-10-04부터 최신 M v1.83·S v0.98·I v0.63·K v0.31
RES_DIR = os.path.join(ROOT, "results_x")
PERIODS = {"ALL": (None, None), "IS": ("2023-11-01", "2025-07-31"), "OOS": ("2025-08-01", "2026-10-01")}
END = pd.Timestamp("2026-10-01 23:59")
BASE58 = sorted(K.DEFAULT_UNIVERSE)                      # 이전 종목 예측 코드(K)의 58종(BTSG 포함)
_T = float(os.environ.get("TARGET_PCT", 5000))           # 2026-10-04 사용자: 목표 5000% (그 전 라운드는 1000%)
_PACE = round(((1 + _T / 100) ** (252 / 730) - 1) * 100, 1)   # 전체 목표를 고르게 내는 연환산 속도(5000% → 연 289%)
TARGET = {"ALL_수익률(%)": _T, "IS_연환산(%)": _PACE, "OOS_연환산(%)": _PACE}
MDD_GUARD = -35.0

# 지수·레버리지 ETF: 섹터 필터용 산업 매핑(MARKET = 섹터 필터 없음)과 배율
ETF_MAP = {"SPY": "MARKET", "QQQ": "MARKET", "TQQQ": "MARKET", "QLD": "MARKET", "UPRO": "MARKET", "SSO": "MARKET",
           "SPXL": "MARKET", "TNA": "MARKET", "SOXL": "SOXX", "USD": "SOXX", "SMH": "SOXX", "SOXX": "SOXX",
           "TECL": "IGV", "ROM": "IGV", "LABU": "XBI", "FAS": "KBE", "NVDL": "SOXX", "TSLL": "CARZ", "CONL": "KCE"}
ETF_MAP.update({k: k for k in K.PRIOR_INDUSTRY_TO_SECTOR})            # 산업 ETF = 자기 산업
ETF_MAP.update({"XLK": "IGV", "XLV": "IBB", "XLY": "XRT", "XLP": "PBJ", "XLF": "KBE", "XLI": "ITA", "XLC": "IYZ",
                "XLRE": "REZ", "XLE": "XOP", "XLB": "XME"})                  # 섹터 ETF = 그 섹터의 산업 하나(섹터 필터용)
IND_ETFS = sorted(set(K.PRIOR_INDUSTRY_TO_SECTOR) | set(K.PRIOR_INDUSTRY_TO_SECTOR.values()))
# 2023년 말 S&P 100(사후 선택 편향 점검용): 야후 섹터 → 섹터 ETF(섹터 필터는 그 섹터의 배분비중으로)
SECTOR_ETF = {"Technology": "XLK", "Healthcare": "XLV", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
              "Financial Services": "XLF", "Industrials": "XLI", "Communication Services": "XLC", "Real Estate": "XLRE",
              "Energy": "XLE", "Basic Materials": "XLB", "Utilities": "XLU"}
for _s in SECTOR_ETF.values():
    K.PRIOR_INDUSTRY_TO_SECTOR.setdefault(_s, _s)
_secp = os.path.join(DATA_DIR, "sp100_sector.pkl")
SP_MAP = {c: SECTOR_ETF[s] for c, s in pickle.load(open(_secp, "rb")).items() if s} if os.path.exists(_secp) else {}
SP100 = sorted(SP_MAP)
# K v0.33+가 배분한 58종 밖 종목·섹터 ETF까지(비중 2% 이상 한 번이라도) — 2026-10-05 S&P 500 확장 대응
KUNI = sorted(K.k_symbols(SIG_DIR, base={c: "NA" for c in BASE58}, min_weight=0.02))
KUNI_S = sorted(K.k_symbols(SIG_DIR, base={c: "NA" for c in BASE58}, min_weight=0.02, small_to_etf=True))   # + 섹터 ETF 11
_INV = None


def inv_synth_bars():
    """−1배 ETF 실제 봉 + 실제 봉 없는 구간은 기초 종목 가상 −1배(lab/inv_synth.py)."""
    global _INV
    if _INV is None:
        _INV = {c: df[df["ts"] <= END].reset_index(drop=True)
                for c, df in pickle.load(open(os.path.join(DATA_DIR, "bars_60m_invsyn.pkl"), "rb")).items()}
    return _INV
ETF_LEV = {"TQQQ": 3, "QLD": 2, "UPRO": 3, "SSO": 2, "SPXL": 3, "TNA": 3, "SOXL": 3, "USD": 2, "TECL": 3, "ROM": 2,
           "LABU": 3, "FAS": 3, "NVDL": 2, "TSLL": 2, "CONL": 2}

_BARS, _SPY = None, None


def bars_all():
    global _BARS
    if _BARS is None:
        d = pickle.load(open(os.path.join(DATA_DIR, "bars_60m.pkl"), "rb"))
        for extra in ("bars_60m_x.pkl", "bars_60m_sp.pkl", "bars_60m_k3.pkl", "bars_60m_k4.pkl"):   # k4: K v0.36 숏 ETF·MAA 등
            p = os.path.join(DATA_DIR, extra)
            if os.path.exists(p):
                for c, df in pickle.load(open(p, "rb")).items():
                    if c not in d:
                        d[c] = df
        _BARS = {c: df[df["ts"] <= END].reset_index(drop=True) for c, df in d.items()}
    return _BARS


def spy():
    global _SPY
    if _SPY is None:
        _SPY = pd.read_pickle(os.path.join(DATA_DIR, "spy_daily.pkl"))
    return _SPY


def make_cfg(ov):
    ov = dict(ov)
    uni = list(ov.pop("universe", BASE58)) + list(ov.pop("add", []))
    amap = dict(SP_MAP, **K.PRIOR_STOCK_TO_INDUSTRY)
    amap.update(ETF_MAP)
    base = dict(symbols={c: K.PRIOR_STOCK_EXCHANGE.get(c, "NA") for c in uni}, market_hours_check=False,
                trade_log="", equity_log="", paper_state="", signals_dir=SIG_DIR, alloc_map=amap)
    base.update(ov)
    return K.Config(**base)


def run_one(job):
    rnd, name, ov = job
    t0 = time.time()
    ov = dict(ov)
    path = {"path_order": ov.pop("path_order", "auto"), "path_seed": ov.pop("path_seed", 0), "tick_order": ov.pop("tick_order", "alpha")}
    use_syn = ov.pop("inv_synth", False)
    cfg = make_cfg(ov)
    needs = cfg.regime in ("M", "spy") or cfg.sector_filter or cfg.industry_filter or cfg.rank_col
    sig = None
    if needs:
        import research as R
        sig = K.DailySignals(cfg, spy_series=R.spy_regime() if cfg.regime == "spy" else None)
    allb = bars_all()
    bars = {c: allb[c] for c in cfg.symbols if c in allb}
    if use_syn:                                              # 상장 전·데이터 없는 −1배 ETF 구간을 가상 −1배로
        bars.update({c: b for c, b in inv_synth_bars().items() if c in cfg.symbols})
    if cfg.mkt_stop_pct or cfg.mkt_flat_pct:
        bars[cfg.mkt_symbol] = allb[cfg.mkt_symbol]          # 시장 급락 판단용(거래 안 함)
    res = K.simulate(cfg, bars, sig, **path)
    out = {"라운드": rnd, "변형": name, "종목수": len(bars), "초": round(time.time() - t0)}
    tr = res["trades"]
    tdays = pd.to_datetime(tr["시각(ET)"]).dt.normalize() if len(tr) else pd.Series(dtype="datetime64[ns]")
    edays = pd.to_datetime(res["equity"]["날짜"]) if len(res["equity"]) else pd.Series(dtype="datetime64[ns]")
    for p, (a, b) in PERIODS.items():
        m = K.sim_metrics(res, a, b, spy_close=spy())
        out.update({f"{p}_{k}": v for k, v in m.items() if k not in ("시작", "끝")})
        lo, hi = pd.Timestamp(a or "1900-01-01"), pd.Timestamp(b or "2100-01-01")
        ed = edays[(edays >= lo) & (edays <= hi)]
        td = set(tdays[(tdays >= lo) & (tdays <= hi)])
        out[f"{p}_거래일비율"] = round(len(td) / len(ed), 3) if len(ed) else None
    eq = res["equity"]
    if len(eq):
        inv = 1 - eq["현금($)"] / eq["자산($)"]
        out["평균투자비중"] = round(float(inv.mean()), 2)
        out["최대투자비중"] = round(float(inv.max()), 2)
        out["이자($)"] = round(float(res["book"].interest), 0)
    K.save_sim(res, os.path.join(RES_DIR, rnd), "".join("_" if ch in '\\/:*?"<>|' else ch for ch in name), out, cfg)
    return out


MODE = os.environ.get("TARGET_MODE", "r20k")     # 2026-10-04 사용자(2차): 수익 +20000% 이상 · MDD −10% 이내 · 거래 횟수는 자유
MDD_CAP, DAY_MIN = -5.0, 0.8


def judge(r):
    if MODE == "mdd15wr80":             # 2026-10-04 사용자(6차): MDD −15%까지 허용 · 승률(80%) 유지 · 수익 최대
        fails = [f"{p} MDD {r.get(f'{p}_MDD(%)')}" for p in ("ALL", "IS", "OOS") if (r.get(f"{p}_MDD(%)") or -99) < -15.0]
        if (r.get("ALL_승률(%)") or 0) < 80:
            fails.append(f"승률 {r.get('ALL_승률(%)')}")
        return f"✅ 수익 {r.get('ALL_수익률(%)')}%" if not fails else "❌ " + ", ".join(fails)
    if MODE == "wr80":                 # 2026-10-04 사용자(4차): 승률 80% · 수익 목표(20000%) · MDD −10% 유지
        fails = [f"{p} MDD {r.get(f'{p}_MDD(%)')}" for p in ("ALL", "IS", "OOS") if (r.get(f"{p}_MDD(%)") or -99) < -10.0]
        if (r.get("ALL_승률(%)") or 0) < 80:
            fails.append(f"승률 {r.get('ALL_승률(%)')}")
        if (r.get("ALL_수익률(%)") or 0) < 20000:
            fails.append(f"수익 {r.get('ALL_수익률(%)')}")
        return "✅ 승률 80%·20000%·MDD 달성" if not fails else "❌ " + ", ".join(fails)
    if MODE == "mdd10":                 # 2026-10-04 사용자(3차): MDD −10% 안에서 승률·수익 더 높이기
        fails = [f"{p} MDD {r.get(f'{p}_MDD(%)')}" for p in ("ALL", "IS", "OOS") if (r.get(f"{p}_MDD(%)") or -99) < -10.0]
        return (f"✅ 승률 {r.get('ALL_승률(%)')}% · 수익 {r.get('ALL_수익률(%)')}%" if not fails
                else "❌ " + ", ".join(fails))
    if MODE == "r20k":
        fails = [f"{p} MDD {r.get(f'{p}_MDD(%)')}" for p in ("ALL", "IS", "OOS") if (r.get(f"{p}_MDD(%)") or -99) < -10.0]
        if (r.get("ALL_수익률(%)") or 0) < 20000:
            fails.append(f"수익 {r.get('ALL_수익률(%)')}")
        return "✅ 20000%·MDD−10% 달성" if not fails else "❌ " + ", ".join(fails)
    if MODE == "mdd5":
        fails = [f"{p} MDD {r.get(f'{p}_MDD(%)')}" for p in ("ALL", "IS", "OOS")
                 if (r.get(f"{p}_MDD(%)") or -99) < MDD_CAP]
        fails += [f"{p} 거래일 {r.get(f'{p}_거래일비율')}" for p in ("IS", "OOS")
                  if (r.get(f"{p}_거래일비율") or 0) < DAY_MIN]
        return f"✅ MDD·매일거래 충족 → 수익 {r.get('ALL_수익률(%)')}%" if not fails else "❌ " + ", ".join(fails)
    fails = [f"{k.split('_')[0]} {r.get(k)}" for k, v in TARGET.items()
             if r.get(k) is None or (isinstance(r.get(k), float) and math.isnan(r.get(k))) or r.get(k) < v]
    tag = f"✅ {_T:.0f}% 달성" if not fails else "❌ " + ", ".join(fails)
    if not fails and (r.get("ALL_MDD(%)") or 0) < MDD_GUARD:
        tag += f" ⚠️MDD {r.get('ALL_MDD(%)')}"
    return tag


def run_round(rnd, variants, workers=4):
    jobs = [(rnd, n, ov) for n, ov in variants]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(run_one, jobs))
    df = pd.DataFrame(rows)
    df["판정"] = [judge(r) for r in df.to_dict("records")]
    os.makedirs(os.path.join(RES_DIR, rnd), exist_ok=True)
    df.to_csv(os.path.join(RES_DIR, rnd, "round_summary.csv"), index=False, encoding="utf-8-sig")
    allp = os.path.join(RES_DIR, "all_x_rounds.csv")
    prev = pd.read_csv(allp, encoding="utf-8-sig") if os.path.exists(allp) else pd.DataFrame()
    if len(prev):
        prev = prev[prev["라운드"] != rnd]
    pd.concat([prev, df], ignore_index=True).to_csv(allp, index=False, encoding="utf-8-sig")
    print(f"[{rnd}] {len(jobs)}건 {time.time() - t0:.0f}초")
    return df


SHOW = ["변형", "ALL_수익률(%)", "ALL_MDD(%)", "ALL_샤프", "IS_수익률(%)", "IS_MDD(%)", "IS_샤프",
        "OOS_수익률(%)", "OOS_MDD(%)", "OOS_샤프", "ALL_청산횟수", "ALL_거래일비율", "ALL_승률(%)", "평균투자비중", "판정"]


def show(df):
    cols = [c for c in SHOW if c in df.columns]
    with pd.option_context("display.width", 300, "display.max_columns", 30, "display.max_colwidth", 50):
        print(df[cols].to_string(index=False))


if __name__ == "__main__":
    import xrounds
    rnd = sys.argv[1]
    show(run_round(rnd, xrounds.ROUNDS[rnd], workers=int(os.environ.get("WORKERS", 4))))
