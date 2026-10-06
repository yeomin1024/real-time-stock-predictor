"""archive/ 의 조각난 zip을 합쳐 원래 위치(lab/data, lab/signals*, results_x, ...)로 풉니다.

사용:
    python restore_archives.py                 # 전부(signals, data_core, results_x, older_outputs)
    python restore_archives.py signals data_core   # 고른 묶음만
    python restore_archives.py --reports       # + 파이프라인 리포트(xlsx)를 공개 저장소 yeomin1024/stock에서 받기
"""
import hashlib, io, json, os, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
ARC = os.path.join(ROOT, "archive")
REPORT_URL = "https://raw.githubusercontent.com/yeomin1024/stock/main/results/reports/2026-10-02/"
OLD = ["market_regime_report_v1.83.0.xlsx", "sector_regime_report_v0.98.0.xlsx",          # lab/reports (signals_v2)
       "industry_regime_report_v0.63.0.xlsx", "stock_regime_report_v0.31.0.xlsx"]
NEW = ["market_regime_report_v1.85.0.xlsx", "sector_regime_report_v1.00.0.xlsx",          # lab/reports_v3 (signals_v3)
       "industry_regime_report_v0.65.0.xlsx", "stock_regime_report_v0.33.0.xlsx"]


def restore(name, info):
    data = b"".join(open(os.path.join(ARC, p), "rb").read() for p in info["parts"])
    if hashlib.sha256(data).hexdigest() != info["sha256"]:
        raise SystemExit(f"❌ {name}: sha256이 맞지 않습니다(조각이 빠졌거나 깨짐)")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(ROOT)
    print(f"✅ {name}: {info['files']}개 파일 복원")


def reports():
    for sub, names in (("lab/reports", OLD), ("lab/reports_v3/2026-10-02", NEW)):
        d = os.path.join(ROOT, sub); os.makedirs(d, exist_ok=True)
        for n in names:
            p = os.path.join(d, n)
            if not os.path.exists(p):
                urllib.request.urlretrieve(REPORT_URL + n, p)
            print(f"✅ {sub}/{n}")


if __name__ == "__main__":
    man = json.load(open(os.path.join(ARC, "MANIFEST.json"), encoding="utf-8"))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for name in (args or list(man)):
        restore(name, man[name])
    if "--reports" in sys.argv:
        reports()
