"""한 셀 Kaggle 실행기 검증(가짜 git·가짜 키움): 수집→push, 시뮬레이션→push, 가상계좌 복원, 토큰 비노출"""
import ast, asyncio, contextlib, io, json, os, shutil, subprocess, sys, types
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot   # 글꼴 캐시를 가짜 subprocess 전에 만듦(새 컨테이너)

WD = sys.argv[1]
CELL = open(os.path.join(WD, "kaggle_runner_onecell.py"), encoding="utf-8").read()
BASE = os.path.join(WD, "_k3"); shutil.rmtree(BASE, ignore_errors=True)
REPO = os.path.join(BASE, "repo"); REMOTE = os.path.join(BASE, "remote"); OUT = os.path.join(BASE, "working")
for d in (REPO, OUT):
    os.makedirs(d)
os.makedirs(os.path.join(REPO, "signals")); os.makedirs(os.path.join(REPO, "results", "kaggle", "paper", "P8"))
# E2E_REP=reports_v4/2026-10-06 → M v1.86 · S v1.02 · I v0.66 · K v0.36(숏 −1배 ETF) / 기본 reports_v3/2026-10-02(K v0.33)
E2E_REP = os.environ.get("E2E_REP", "reports_v3/2026-10-02")
REPD = os.path.join(REPO, "results", "reports", os.path.basename(E2E_REP)); os.makedirs(REPD)        # 파이프라인 최신 리포트(M·S·I·K)
for f in os.listdir(os.path.join(WD, "lab", E2E_REP)):
    shutil.copy(os.path.join(WD, "lab", E2E_REP, f), REPD)
for f in os.listdir(os.path.join(WD, "signals")):
    shutil.copy(os.path.join(WD, "signals", f), os.path.join(REPO, "signals"))
json.dump({"cash": 12345.6, "start_cash": 10000, "realized": 2345.6, "fees": 10, "positions": {}},
          open(os.path.join(REPO, "results", "kaggle", "paper", "P8", "paper_account.json"), "w"))
patch = '''
import pandas as _pd
def _fake_token(self, force=False):
    self.token = "T"; return "T"
def _fake_hist(self, code, exch, minutes=5, strt_dt=None, max_pages=300, log_first=False):
    if code == "SPY" and exch == "NA":
        raise KiwoomError("거래소 코드 오류(테스트)")
    rows = []
    for d in _pd.bdate_range("2026-09-28", periods=3):
        for m in range(0, 390, 5):
            et = d + _pd.Timedelta(hours=9, minutes=30 + m)
            rows.append({"cur_prc": "+100.5", "open_pric": "100", "high_pric": "101", "low_pric": "99", "trde_qty": "10",
                         "bus_dt": d.strftime("%Y%m%d"), "cntr_tm": et.strftime("%H%M%S")})
    return rows[::-1], 2
KiwoomUSAPI.get_token = _fake_token
KiwoomUSAPI.minute_history = _fake_hist
'''
src = open(os.path.join(WD, "kiwoom_autotrader.py"), encoding="utf-8").read().replace(
    "# %% [local-only]", patch + "\n# %% [local-only]")
open(os.path.join(REPO, "kiwoom_autotrader.py"), "w", encoding="utf-8").write(src)

CALLS, PUSHES = [], []
_real_run = subprocess.run
def fake_run(args, cwd=None, capture_output=True, text=True, check=False):
    if args[0] == sys.executable:
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    assert args[0] == "git"
    CALLS.append((args[1:], cwd))
    if args[1] == "clone":
        assert "ghp_TEST123" in args[-2], "clone URL에 토큰이 들어가야 push 가능"
        shutil.rmtree(args[-1], ignore_errors=True)
        shutil.copytree(REMOTE if os.path.exists(REMOTE) else REPO, args[-1])
        return types.SimpleNamespace(returncode=0, stdout="", stderr=f"Cloning into '{args[-1]}'... {args[-2]}")
    if args[1] == "commit":
        return types.SimpleNamespace(returncode=0, stdout="[main abc] " + args[-1], stderr="")
    if args[1] == "push":
        shutil.rmtree(REMOTE, ignore_errors=True); shutil.copytree(cwd, REMOTE)
        PUSHES.append([c for c in CALLS if c[0][0] == "commit"][-1][0][-1])
        return types.SimpleNamespace(returncode=0, stdout="", stderr="To github.com ghp_TEST123")
    return types.SimpleNamespace(returncode=0, stdout="", stderr="")

sys.modules["kaggle_secrets"] = types.SimpleNamespace(UserSecretsClient=lambda: types.SimpleNamespace(
    get_secret=lambda n: {"GITHUB_TOKEN": "ghp_TEST123", "KIWOOM_APPKEY": "ak", "KIWOOM_SECRETKEY": "sk"}[n]))
cell = CELL.replace("/tmp/kiwoom_src", os.path.join(BASE, "src").replace("\\", "/")) \
           .replace("/tmp/kiwoom_push", os.path.join(BASE, "push").replace("\\", "/")) \
           .replace('"/kaggle/working"', repr(OUT.replace("\\", "/")))
assert "RUN_COLLECT=False" in cell and "globals().setdefault" in cell
subprocess.run = fake_run
buf = io.StringIO()
# wget 실행 셀처럼: 설정을 먼저 정의한 뒤 받은 실행기를 같은 전역에서 실행 → 셀 값(수집·가상거래 켬)이 우선해야 함
ns = {"__name__": "__main__", "display": lambda x: print(x.to_string() if hasattr(x, "to_string") else x),
      "RUN_COLLECT": True, "RUN_PAPER": False, "STRATEGY": "R1"}   # 가상거래는 test_p8_live에서(장중이면 실제로 장 마감까지 돎)
loop = asyncio.new_event_loop()
try:
    with contextlib.redirect_stdout(buf):
        r = eval(compile(cell, "<cell>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), ns)
        if asyncio.iscoroutine(r):
            loop.run_until_complete(r)
finally:
    subprocess.run = _real_run
out = buf.getvalue()
print(out[-2500:])
assert "ghp_TEST123" not in out, "토큰이 출력에 노출됨"
assert any(p.startswith("키움 5분봉 기록") for p in PUSHES) and any(p.startswith("과거 시뮬레이션") for p in PUSHES), PUSHES
km = os.path.join(REMOTE, "data", "kiwoom_minute")
assert os.path.exists(os.path.join(km, "NVDA_5m.csv.gz")) and os.path.exists(os.path.join(km, "SPY_5m.csv.gz"))
sims = os.listdir(os.path.join(REMOTE, "results", "kaggle", "sim"))
assert sims and sims[0].endswith("_P8"), sims
assert "K 배분 종목 추가" in out and "STRATEGY 'R1' → 최신 추천 'P8'" in out and "stock_allocation_daily.csv     ← results" in out.replace("\\", "/")
assert {"sim_summary.json", "sim_equity.png", "sim_trades.csv", "sim_equity.csv"} <= set(os.listdir(os.path.join(REMOTE, "results", "kaggle", "sim", sims[0])))
summ = json.load(open(os.path.join(REMOTE, "results", "kaggle", "sim", sims[0], "sim_summary.json"), encoding="utf-8"))
assert summ["config"]["leverage"] == 1.0 and summ["config"]["entry_mode"] == "k+rot" and summ["config"]["rot_pct"] == 35.0 and summ["config"]["k_rot_scale"] == 1.5 and summ["config"]["batch_buys"] and summ["config"]["rot_base_only"] and {"XLK", "PLTR"} <= set(summ["config"]["symbols"]) and len(summ["config"]["symbols"]) >= 70 and summ["config"]["hold_loser_days"] == 20 and summ["config"]["hold_loser_stop_pct"] == 8.0 and summ["config"]["k_exit_days"] == 3 and "TQQQ" not in summ["config"]["symbols"] and "BTSG" in summ["config"]["symbols"]
print("SIM METRICS:", summ["metrics"])
assert "K 숏(−1배 ETF)" in out
if "v4" in E2E_REP:                                                       # K v0.36: 숏 ETF가 거래 대상에 들어감
    assert {"NVDD", "TSLS", "MAA"} <= set(summ["config"]["symbols"]) and "NVDD←NVDA" in out, summ["config"]["symbols"]
assert json.load(open(os.path.join(OUT, "paper_account.json")))["cash"] == 12345.6           # GitHub에서 이어 받음
assert "이어 쓰기: paper_account.json" in out
print("PUSHES:", PUSHES)
shutil.rmtree(BASE, ignore_errors=True)
print("ONE-CELL RUNNER OK")
