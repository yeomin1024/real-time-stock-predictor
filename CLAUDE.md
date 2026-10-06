# real-time-stock-predictor — 작업 인수인계 (2026-10-06, 로컬 Claude Code 세션에서 옮김)

미국 주식 자동매매 연구·가상거래 프로젝트입니다. 키움 REST API(미국주식)를 쓰고, 지금은 **가상(페이퍼) 거래와 과거 실시간 시뮬레이션만** 합니다. 실행은 Kaggle에서 공개 저장소 **yeomin1024/stock**(main)의 코드를 wget으로 받아서 합니다. 이 저장소(real-time-stock-predictor, 비공개)에는 연구 작업 공간 전체가 들어 있습니다.

## 0. 처음 할 일
```bash
python restore_archives.py --reports   # archive/ 조각 zip → lab/data, lab/signals*, results_x 등 복원 + 파이프라인 리포트(xlsx) 받기
pip install pandas numpy openpyxl matplotlib yfinance websockets requests
PYTHONPATH=. python lab/test_x.py      # 단위 테스트(ALL NEW OPTIONS OK가 나와야 함)
```
- 5분봉·1분봉 대용량 데이터는 용량 때문에 올리지 않았습니다(압축 후 약 480MB). 5분봉 점검(`lab/fidelity.py`)과 예전 분봉 연구에만 쓰입니다.
  - 해당 파일: `lab/data/panel_5m.pkl`, `panel_60m.pkl`, `pool5m/*.pkl`, `ohlcv_1m.pkl`, `ohlcv_5m.pkl`
- 시간봉 데이터는 `lab/data/bars_60m*.pkl`에 있습니다(2023-11-03 ~ 2026-10-02, yfinance 730일).
  - yfinance 시간봉은 최근 730일만 주므로, 나중에 새로 받으면 시작일이 달라집니다.

## 1. 반드시 지킬 것 (사용자 지시)
- **실제 주문 금지**: `ALLOW_ORDERS=False` 유지. 주문 함수는 잠겨 있습니다.
- **레버리지 금지**: 신용과 레버리지 ETF를 쓰지 않습니다. 실행기가 `cfg.leverage == 1.0`과 `LEVERAGED_ETFS` 미포함을 assert합니다.
- **키·토큰을 코드·출력·커밋에 절대 넣지 않습니다.**
  - Kaggle Secrets 이름만 씁니다: `KIWOOM_APPKEY`, `KIWOOM_SECRETKEY`, `GITHUB_TOKEN`.
  - 사용자가 예전에 채팅에 키를 노출한 적이 있으니, 그 값을 다시 쓰지 마세요.
- **Kaggle 실행 셀은 바꾸지 않습니다.**
  - 셀은 `STRATEGY="R1"`이고, `PRESET_ALIAS = {"R1": "<최신 추천>"}`로 최신 전략을 가리킵니다(지금 **P8**).
- `kaggle_runner_onecell.py`는 **UTF-8 BOM 없이** 저장합니다. BOM이 붙으면 Kaggle에서 compile이 실패합니다.
- **작업 흐름**:
  - 코드를 바꾸면 yeomin1024/stock(main) 루트의 `kiwoom_autotrader.py`, `kaggle_runner_onecell.py`를 갱신합니다.
  - 연구 보고서는 `results/research/<프리셋>/`에 올립니다.
  - 사용자에게는 **wget 실행 셀만** 알려 줍니다("이거 나한테 알려주지말고 변경된 코드 모두 깃허브에 올리고 kaggle에서 그 코드들을 wget으로 받아서 실행하는 코드만 알려주면 돼").
- **답변 방식**: 한국어로, 짧게, 한계와 주의점은 솔직하게 씁니다.
- 사용자 이메일은 신원 확인용으로만 씁니다. 외부로 보내지 않습니다.

## 2. 파일 구조
| 경로 | 내용 |
|---|---|
| `kiwoom_autotrader.py` | 본체(~125KB). 키움 클라이언트·Config·PRESETS·DailySignals·Engine·Book·LiveRunner·simulate·리포트→신호 변환 |
| `kaggle_runner_onecell.py` | Kaggle 한 셀 실행기: 저장소 clone → 최신 리포트로 신호 → (K 확장 종목) → 시뮬레이션/가상거래 → 결과 push |
| `kaggle_wget_cell.py`, `kaggle_runner.ipynb` | 사용자가 Kaggle에 붙여 쓰는 셀(바꾸지 않음) |
| `lab/xres.py` | 연구 실행기. `SIG`(신호 폴더), `TARGET_MODE`(판정), `WORKERS` 환경변수 |
| `lab/xrounds.py` | 라운드 정의(X·Y·Z·W·V·U·T·S·Q·G). 최근은 `G01_v3` ~ `G10_robust_P8` |
| `lab/*report.py` | 라운드 결과 → `results_x/<P>_결과.xlsx`·자산곡선 png (`greport.py`가 P8) |
| `lab/ana_*.py` | 벡터 근사 분석(장중·밤사이 분해, 묶음 섞기, 변동성 목표) |
| `lab/test_*.py` | 테스트. `test_x`(옵션 단위), `test_p2~p8_live`(실시간 경로), `test_earn`, `test_e2e_runner`(실행기 전체) |
| `lab/src/` | 사용자 파이프라인 코드 사본(M·S·I·K, 예전 버전). 최신은 yeomin1024/stock 루트에 있음 |
| `lab/signals_v2`, `_v2_lag1` | M v1.83 · S v0.98 · I v0.63 · K v0.31 신호(CSV) / 하루 지연판 |
| `lab/signals_v3`, `_v3_lag1` | **M v1.85 · S v1.00 · I v0.65 · K v0.33** 신호(현재) / 하루 지연판 |
| `results_x/` | 모든 라운드 결과(`all_x_rounds.csv`, 라운드별 거래·자산·요약)와 보고서 md/xlsx |
| `archive/` | 위 데이터·결과의 조각 zip + `MANIFEST.json`(sha256) |

## 3. 신호와 시뮬레이션 규칙
- **신호 출처**: 사용자 파이프라인 리포트 `yeomin1024/stock/results/reports/<날짜>/*.xlsx`
  - 실행기의 `REPORT_SHEETS`와 `signals_from_reports`가 시트를 CSV로 바꿉니다.
  - 시트: M `01_일별기록`, S·I·K `13c_일별배분비중`, I·K `01Z_*`, K `05_어닝이벤트`
- **as-of 규칙: D일에는 날짜 < D인 행을 씁니다.** 2026-10-05에 K 13r로 다시 검증했습니다.
  - 13r의 t일 수익은 13c t−1행으로 가장 잘 맞습니다(상관 0.894).
- **K v0.33+는 S&P 500 전 종목에서 고릅니다.**
  - `k_symbols()`는 K 비중이 한 번이라도 `k_min_weight` 이상인 종목을 58종에 더합니다. 지금은 74종입니다.
  - K 리포트의 `ETF_XLK` 같은 열은 `XLK`로 읽습니다.
  - 모멘텀 후보는 58종만 씁니다(`rot_base_only`). 확장 목록에서 고르면 사후 선택이 생깁니다.
- **시뮬레이터**:
  - 시간봉 이벤트 방식이고, 실시간과 같은 Engine 코드를 씁니다.
  - IS 2023-11 ~ 2025-07, OOS 2025-08 ~ 2026-10입니다. `xres.END`가 2026-10-01입니다.
  - 비용: 수수료 0.07%, 슬리피지 0.05%, 매도 수수료 0.003%.
- **경로에 덜 민감한 설계만 씁니다.** 매매는 장 시작 가격(`rot_at_open`)이나 봉 시가·종가(`decide_on_bar`)로 합니다.
  - 봉 안 가격 순서를 가정하면 결과가 부풀었습니다(P1, 5분봉 점검으로 확인).
  - P8도 봉 안 가격 순서를 불리하게 가정하면 +5,419%에서 +4,632%로 줄어듭니다.
- **⚠️ 체결 순서 문제(2026-10-05 발견)**:
  - 같은 시각의 시세는 티커 알파벳 순서로 처리됩니다.
  - 현금이 모자라면 먼저 처리된 종목부터 사서 결과가 달라집니다.
  - P7의 MDD −13.9%는 이 효과 덕이었습니다. 순서 영향을 없애면 −20.7%입니다.
  - `batch_buys=True`는 같은 순간의 매도를 먼저 처리하고, 매수는 모멘텀 → K 비중 큰 순으로 처리합니다. 이 상태에서 `tick_order`(alpha/reverse/random)를 바꿔도 결과가 같은지 꼭 확인하세요.
- **견고성 점검 세트(라운드 *_robust_*)**:
  - 봉 안 가격 순서(`path_order="high_first"`)
  - 수수료·슬리피지 0.15%
  - 유니버스 절반 a/b
  - SPY 국면(`regime="spy"`)
  - 신호 하루 지연(`SIG=signals_v3_lag1`)
  - 파라미터 이웃
  - 처리 순서 무작위

```bash
SIG=signals_v3 TARGET_MODE=mdd15wr80 WORKERS=6 python lab/xres.py G10_robust_P8
SIG=signals_v3_lag1 TARGET_MODE=mdd15wr80 python lab/xres.py G10b_lag1
SIG=signals_v3 python lab/greport.py     # 보고서 xlsx/png
```
- `TARGET_MODE`: `mdd5`, `mdd10`, `r20k`(기본), `wr80`, `mdd15wr80`(현재 목표)
- `xres.SIG` 기본값은 `signals_v2`입니다. **지금 작업은 `SIG=signals_v3`로** 하세요.

## 4. 현재 상태 (2026-10-05)
- **사용자 목표 변화**:
  1. 1000% → 5000% → 20000%
  2. MDD −10%
  3. 승률 80%
  4. **MDD −15%까지 허용 · 승률 80% 유지 · 수익 최대** ← 현재
  5. 그다음 "새 M·S·I·K 코드에 맞게 수정"
- **추천 = P8** (`R1` → P8)
  - 구성: K(v0.33+) 비중 × 1.5(S&P 500 종목·섹터 ETF 포함) + 168일(1달 건너뜀) 모멘텀 1위(58종 중) 35% + 본전 대기 20거래일(국면 0·실적 때도, 손실 8% 넘으면 매도) + `batch_buys`
  - 결과: **+5,419%, MDD −14.79%, 승률 83.5%, 샤프 3.25**
  - 실행기 e2e에서 데이터를 새로 받으면 +4,794%, MDD −14.78%, 승률 83.1%
  - 수수료 0.15%: +4,463%, MDD −14.90%
  - 조건을 넘는 경우: 189일 −16.2%, SPY 국면 −35%, 신호 하루 지연 −17.3%
  - 이익의 48%가 SNDK에서 나옵니다. MDD는 −15% 경계에 가깝습니다.
- **20000%는 레버리지 없이 도달하지 못했습니다.**
  - MDD −10%에서는 약 +2,000%가 한계였습니다.
  - MDD 제한이 없을 때 최대는 1종목 모멘텀 +13,670%(MDD −35%)였고, 기간을 바꾸면 크게 흔들립니다.
  - 사후 선택이 없는 2023년 S&P100에서는 1종목 모멘텀이 +278 ~ 409%입니다.
- 다른 프리셋은 `PRESET_NOTES`에 있습니다(P2 MDD −5%, P5·P6 MDD −10% 등). P7 수치는 체결 순서 효과로 부풀어 있습니다.
- **열린 일**:
  - K v0.34.0 코드(예측 바구니, S&P 500 종목 '작게 넣기')는 저장소에 있지만 리포트가 아직 없습니다.
    - 리포트가 나오면 `signals_v4`를 만들어 P8을 다시 점검합니다(G01·G10 방식).
    - 2% 미만 비중은 `k_min_weight`로 무시됩니다.
  - 지금 M은 위험회피라 전 프리셋이 현금 대기입니다.

## 5. Kaggle 실행 셀 (사용자에게 줄 것 — 바꾸지 않음)
```python
# 미국주식 가상계좌 자동매매 — GitHub에서 실행기를 wget으로 받아 실행 (실제 주문 없음 · 레버리지 없음)
# 준비: Settings → Internet 켜기 / Add-ons → Secrets: GITHUB_TOKEN(결과 올리기), KIWOOM_APPKEY·KIWOOM_SECRETKEY(키움 쓸 때)
STRATEGY    = "R1"      # 'R1' 5000% 목표(1종목 모멘텀) / 'N2' 5종목 로테이션+저점매수 / 'A' 저점매수 / 'C0'
RUN_SIM     = True      # 과거 실시간 시뮬레이션 → GitHub results/kaggle/sim/<날짜>_<전략>/
RUN_PAPER   = False     # 실시간 가상거래(한국 18~22시에 Save & Run All) → GitHub results/kaggle/paper/<전략>/
RUN_COLLECT = False     # 키움 5분봉 기록 모으기(한 번) → GitHub data/kiwoom_minute/
KIWOOM_MOCK = True      # 키움 키가 모의투자 키면 True, 실전 키면 False
!wget -q --no-cache -O /tmp/kaggle_runner.py "https://raw.githubusercontent.com/yeomin1024/stock/main/kaggle_runner_onecell.py?$(date +%s)"
import ast, asyncio
_run = eval(compile(open("/tmp/kaggle_runner.py", encoding="utf-8").read(), "kaggle_runner.py", "exec",
                    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), globals())
if asyncio.iscoroutine(_run):
    await _run
```

## 6. 테스트
```bash
for t in test_x test_earn test_p2_live test_p3_live test_p4_live test_p5_live test_p6_live test_p7_live test_p8_live test_r1_live test_n2_live; do PYTHONPATH=. python lab/$t.py | tail -1; done
python lab/test_e2e_runner.py .    # 실행기 전체(가짜 git·키움, yfinance 실제 다운로드). lab/reports_v3/2026-10-02 필요
```
- `test_e2e_runner`는 `RUN_PAPER=False`입니다. 켜면 장중에 실제로 장 마감까지 돕니다.
- 알려진 일:
  - Kaggle과 로컬의 결과 차이는 yfinance가 받을 때마다 시가가 조금씩 달라서 생깁니다(P5에서 +1,176% vs +1,134%).
  - 같은 시각 매도 기록의 순서는 실행마다 바뀔 수 있지만 금액에는 영향이 없습니다.
