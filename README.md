# AlphaProve: 딥테크 상장기업 신용·가치평가 멀티에이전트 프레임워크

개인투자자가 접근하기 어려운 딥테크 상장기업의 **재무 체력, 시장성, 기술/IP, 독립 가치평가, 이슈, 거시환경**을 6개 전문 에이전트가 분석하고, **First Auditor**와 **Chair Agent**가 검증·통합해 설명 가능한 투자 보고서와 대시보드용 산출물을 생성하는 프로젝트입니다.

이 README는 기존 실행 흐름을 유지하되, 최신 구조인 **6개 전문 에이전트 + 3단계 First Auditor + 개인투자자용 Chair 보고서** 기준으로 보완한 실행 안내입니다.

---

## 1. 최신 전체 구조

```text
Data Intake
  ├─ Finance Intake        : 재무 CSV/주가/변동성/투자경고 등 기초 데이터
  ├─ Tech Intake           : KIPRIS/특허 CSV/Tech 템플릿/IP feature 수집
  ├─ Valuation Intake      : DART/주가/발행주식 수/피어/208개 반도체 universe
  ├─ Macro Intake          : 금리/환율/유가/거시 변수
  ├─ Market                : 별도 intake 없이 에이전트가 직접 원천 호출 가능
  └─ Issue                 : 별도 intake 없이 뉴스/RSS/API 기반 직접 실행 가능
        ↓
6 Specialist Agents
  ├─ Finance Agent         : 재무 안정성·수익성·현금흐름·부채 부담
  ├─ Market Agent          : 주가·시장·피어/시장 신호
  ├─ Tech Agent            : 기술성·KIPRIS/IP·Tech-to-Value Bridge
  ├─ Valuation Agent       : DCF/WACC/Peer/Football Field/Workbook/대시보드 payload
  ├─ Issue Agent           : 뉴스·RSS·이슈 신호
  └─ Macro Agent           : 금리·환율·경기·원자재·정책 환경
        ↓
First Auditor
  ├─ 1차: 숫자·단위·스케일·기업 범위·내부 일관성 검증
  ├─ 2차: 딥테크·IB·가치평가·특허/IP framework 검증
  └─ 3차: Chair 전달 전 매수/보유/매도 방향성 신호 생성
        ↓
Chair Agent
  └─ 각 에이전트 JSON 원본은 유지하고, 최종 보고서에서만 개인투자자용 쉬운 언어로 변환
```

---

## 2. 처음 실행 전 환경 설정

PowerShell 기준입니다.

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
```

가상환경 활성화:

```powershell
.\.venv\Scripts\Activate.ps1
```

### PowerShell 여러 줄 명령 주의

PowerShell의 백틱(`)은 줄의 맨 마지막 문자여야 합니다. 백틱 뒤에 공백이 하나라도 있으면 다음 줄이 새 명령으로 해석되어 `--frequency` 같은 옵션에서 `MissingExpressionAfterOperator` 오류가 납니다.

history Sheets-only 파이프라인은 백틱 실수를 피하려면 래퍼 스크립트를 쓰세요.

```powershell
.\scripts\run_history_sheets_only_pipeline.ps1 -Field "반도체" -AsOfDate "2025-01-31" -Frequency monthly -UniverseCsv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" -ContinueOnError
```

파이썬 스크립트를 직접 실행할 때는 한 줄로 실행하는 것도 안전합니다.

```powershell
python .\scripts\run_history_sheets_only_pipeline.py --field "반도체" --as-of-date "2025-01-31" --frequency monthly --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" --continue-on-error
```

가상환경이 없으면:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`.env`에는 실제 키 값을 넣되 GitHub에 올리지 않습니다. 키 이름은 유지하고 실제 값은 공유하지 마세요.

```text
DART_API_KEY=...
OPEN_DART_API_KEY=...        # 일부 intake는 DART_API_KEY를 자동 대체로 사용 가능
NVIDIA_PARALLEL_API_KEY=...
NVIDIA_API_KEY=...
KIPRIS_PLUS_API_KEY=...
NEWS_API_KEY=...
FRED_API_KEY=...
MARKET_WORKBOOK_URL=...      # 필요한 경우 raw GitHub URL, 코드 하드코딩 금지
NEWS_API_KEY=...
```

---

## 3. 5개 반도체 기본 기업명

| company-dir | company |
|---|---|
| nepes | 네패스 |
| hanmi | 한미반도체 |
| hansol | 한솔케미칼 |
| duksan | 덕산테코피아 |
| ltc | 엘티씨 |

---

## 4. 가장 권장되는 실행 방식

### 4-1. 단일 기업 전체 파이프라인

```powershell
python main.py pipeline --company-dir sfa --company "SFA반도체"
```

실행 순서:

```text
data_intake → finance/market/tech/valuation/issue/macro → auditor → chair
```

Auditor가 아직 조정 중이라 Chair 보고서 생성을 우선 확인하고 싶으면:

```powershell
python main.py pipeline --company-dir nepes --company "네패스" --fail-open
```

### 4-2. Chair 단독 실행

Chair는 내부적으로 필요 시 Data Intake와 6개 에이전트, Auditor를 호출합니다.

```powershell
python main.py chair --company-dir nepes --company "네패스"
```

이미 각 에이전트 산출물이 있고 Data Intake를 생략하고 싶으면:

```powershell
$env:CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS="1"
python main.py chair --company-dir nepes --company "네패스"
```

---

## 5. Data Intake 단계별 실행

### 5-1. Data Intake 전체

```powershell
python main.py data-intake --company-dir nepes --company "네패스"
```

### 5-2. 특정 intake만 실행

```powershell
python main.py data-intake --company-dir nepes --company "네패스" --agents "finance"
python main.py data-intake --company-dir nepes --company "네패스" --agents "tech"
python main.py data-intake --company-dir nepes --company "네패스" --agents "valuation"
python main.py data-intake --company-dir nepes --company "네패스" --agents "macro"
```

시장분석과 이슈분석은 별도 intake 없이 에이전트가 직접 실행될 수 있습니다.


```powershell
python main.py market --company-dir nepes --company "네패스"
python main.py issue --company-dir nepes --company "네패스"
```

---

## 6. 6개 전문 에이전트 개별 실행

### 6-1. Finance Agent

```powershell
python main.py finance --company "네패스"
```
python main.py finance --company "이엔에프테크놀로지"

주요 산출물:

```text
data\반도체\네패스\finance\
```

### 6-2. Market Agent

```powershell
python main.py market --company-dir nepes --company "네패스"
```

Market Agent는 `MARKET_WORKBOOK_URL` 또는 로컬 공통 파일을 참조할 수 있습니다. URL은 `.env`에서 읽고, 코드에 직접 하드코딩하지 않습니다.

### 6-3. Tech Intake + Tech Agent

KIPRIS Plus 승인이 아직 완료되지 않았거나 호출 제한이 있으면, 먼저 기존 특허 CSV/로컬 산출물 기반으로 실행하고, 승인 후 Plus components를 추가로 수집하는 방식이 안전합니다.

기본 Tech Intake:

```powershell
python main.py tech-intake --company-dir nepes --company "네패스" --max-patents 0
```

네트워크 없이 기존 파일만 사용:

```powershell
python main.py tech-intake --company-dir nepes --company "네패스" --skip-network
```

KIPRIS Plus 연결 소량 테스트:

```powershell
python main.py tech-intake --company-dir nepes --company "네패스" --max-patents 5 --force-fetch --kipris-plus-components claims,citation,family
```

Claims + Citation 전체 수집 예시:

```powershell
python main.py tech-intake --company-dir nepes --company "네패스" --max-patents 0 --force-fetch --kipris-plus-components claims,citation
```

Family는 호출량이 많을 수 있으므로 우선 일부만 권장:

```powershell
python main.py tech-intake --company-dir nepes --company "네패스" --max-patents 80 --force-fetch --kipris-plus-components family
```

Tech Agent 실행:

```powershell
python main.py tech --company-dir nepes --company-name "네패스"
```

주요 산출물:

```text
data\반도체\네패스\tech\tech_chair_summary.json
data\반도체\네패스\tech\nepes_tech_chair_summary.md
data\반도체\네패스\tech\tech_ip_evidence_composite.json
data\반도체\네패스\tech\tech_to_value_bridge_ip_evidence_adjusted.json
```

### 6-4. Valuation Intake + Valuation Agent

Valuation Agent는 finance_agent 결과를 재사용하지 않고, 자체 intake로 DART/주가/발행주식 수/피어/208개 반도체 reference universe를 구성합니다.

```powershell
python main.py valuation-intake --company-dir nepes --company "네패스"
python main.py valuation --company-dir nepes --company "네패스"
```

검증:

```powershell
python .\scripts\check_valuation_outputs.py --company-dir nepes --company "네패스"
```

주요 산출물:

```text
data\반도체\네패스\valuation\nepes_valuation_workbook.xlsx
data\반도체\네패스\valuation\nepes_valuation_metrics.json
data\반도체\네패스\valuation\nepes_dashboard_payload.json
data\반도체\네패스\valuation\nepes_valuation_validation.json
data\반도체\네패스\valuation\nepes_valuation_report.md
```

### 6-5. Issue Agent

```powershell
python main.py issue --company-dir nepes --company "네패스"
```

주의: PowerShell에서 긴 대시 `—`가 아니라 일반 하이픈 `--`를 사용해야 합니다.

### 6-6. Macro Agent

```powershell
python main.py macro --company-dir nepes --company "네패스"
```

FRED/OECD 등 외부 키가 없거나 제한되면 fallback 산출물이 생성될 수 있습니다.

macro_intake는 공통 시장 벤치마크도 함께 적재합니다. KOSPI, KOSDAQ, KOSPI200, KRX 반도체, NASDAQ, SOX 반도체, S&P500 지수와 1/5/20/60일 수익률, 20일 실현변동성, 20/60일 모멘텀, risk-off 비율을 `data\_global_common\macro`의 일별 매크로 데이터에 포함합니다. 개별 종목의 excess return 검증에서는 상장 시장은 KOSPI/KOSDAQ, 반도체 섹터는 KRX 반도체 지수를 우선 벤치마크로 사용합니다.

**⚠️ pykrx 주의**: KRX 지수(KOSPI, KOSDAQ, KRX 반도체 등) 수집 시 pykrx 라이브러리에서 JSON 파싱 오류가 발생할 수 있습니다. 이 경우 자동으로 Yahoo Finance fallback을 사용하거나, 프록시 ETF(KODEX 반도체)를 사용합니다. 네트워크/API 상태에 따라 컬럼 누락이 경고로 표시되지만 실행은 계속됩니다.

---

## 7. Auditor와 Chair 실행

### 7-1. Auditor 단독

```powershell
python main.py auditor --company-dir nepes --company "네패스" --json
```

Fail-open으로 확인:

```powershell
python main.py auditor --company-dir nepes --company "네패스" --json --fail-open
```

### 7-2. Chair 단독

```powershell
python main.py chair --company-dir nepes --company "네패스"
```

Chair 보고서 확인:

```powershell
notepad .\data\반도체\네패스\chair\nepes_chair_report.md
```

최신 Chair 보고서 정책:

```text
- 각 에이전트 JSON 원본은 수정하지 않음
- Chair 최종 보고서에서만 영어 key, 숫자 점수, 내부 검증 용어를 쉬운 언어로 변환
- signal과 weighted_signal은 각각 영역별 방향성 신호, 종합 방향성 신호로 한글 설명
- Tech 점수/IP 점수/grade는 점수 노출 대신 사업화 가능성·특허 품질 신호로 설명
- 대표 지표는 한글명, 단위, 콤마를 붙여 표시
```

---

## 8. 5개 반도체 기업 전체 파이프라인 실행

가장 단순한 방식:

```powershell
python main.py pipeline --company-dir nepes --company "네패스" --fail-open
python main.py pipeline --company-dir hanmi --company "한미반도체" --fail-open
python main.py pipeline --company-dir hansol --company "한솔케미칼" --fail-open
python main.py pipeline --company-dir duksan --company "덕산테코피아" --fail-open
python main.py pipeline --company-dir ltc --company "엘티씨" --fail-open
```

PowerShell 반복 실행:

```powershell
$companies = @(
  @{dir="nepes";  name="네패스"},
  @{dir="hanmi";  name="한미반도체"},
  @{dir="hansol"; name="한솔케미칼"},
  @{dir="duksan"; name="덕산테코피아"},
  @{dir="ltc";    name="엘티씨"}
)

foreach ($c in $companies) {
  python main.py pipeline --company-dir $c.dir --company $c.name --fail-open
}
```

---

## 9. 5개 기업을 에이전트별로 일괄 실행

Data Intake만 일괄:

```powershell
$companies = @(
  @{dir="nepes";  name="네패스"},
  @{dir="hanmi";  name="한미반도체"},
  @{dir="hansol"; name="한솔케미칼"},
  @{dir="duksan"; name="덕산테코피아"},
  @{dir="ltc";    name="엘티씨"}
)

foreach ($c in $companies) {
  python main.py data-intake --company-dir $c.dir --company $c.name
}
```

6개 Agent만 일괄:

```powershell
foreach ($c in $companies) {
  python main.py finance --company $c.name
  python main.py market --company-dir $c.dir --company $c.name
  python main.py tech --company-dir $c.dir --company-name $c.name
  python main.py valuation --company-dir $c.dir --company $c.name
  python main.py issue --company-dir $c.dir --company $c.name
  python main.py macro --company-dir $c.dir --company $c.name
}
```

Auditor + Chair만 일괄:

```powershell
foreach ($c in $companies) {
  python main.py auditor --company-dir $c.dir --company $c.name --json --fail-open
  python main.py chair --company-dir $c.dir --company $c.name
}
```

Valuation만 5개 기업 일괄:

```powershell
foreach ($c in $companies) {
  python main.py valuation-intake --company-dir $c.dir --company $c.name
  python main.py valuation --company-dir $c.dir --company $c.name
}

python .\scripts\check_valuation_5companies.py
```

---

## 10. 산출물 경로 규칙

```text
data\
  반도체\
    _sector_common\
    네패스\
      _company_common\
      finance\
      market\
      tech\
      valuation\
      issue\
      macro\
      auditor\
      chair\
```

대표 산출물:

```text
data\반도체\네패스\finance\
data\반도체\네패스\market\
data\반도체\네패스\tech\
data\반도체\네패스\valuation\
data\반도체\네패스\issue\
data\반도체\네패스\macro\
data\반도체\네패스\auditor\first_auditor\
data\반도체\네패스\chair\nepes_chair_report.md
```

---

## 11. 자주 나는 오류와 확인 방법

### 11-1. Finance Intake에서 `--mode` 오류

Data Intake runner가 finance intake를 호출할 때 `--mode`가 필요할 수 있습니다. 최신 패치에서는 finance intake 기본 모드를 보완했지만, 단독 실행 시에는 아래처럼 명시할 수 있습니다.

```powershell
python main.py data-intake --company-dir nepes --company "네패스" --agents "finance"
```

### 11-2. Market workbook이 로컬에 생기는 문제

`MARKET_WORKBOOK_URL`은 `.env`에 두고, 코드는 URL을 하드코딩하지 않습니다. 원격 xlsx는 가능하면 메모리에서 읽고 로컬 공통 폴더에 불필요하게 저장하지 않습니다.

확인:

```powershell
Test-Path .\data\반도체\_sector_common\data\Market_통합.xlsx
Test-Path .\data\반도체\_sector_common\source_data\Market_통합.xlsx
Test-Path .\data\Market_통합.xlsx
```

### 11-3. KIPRIS Plus 승인 전 Tech Intake

승인 전에는 `--skip-network` 또는 기존 특허 CSV 기반으로 실행하고, 승인 후 `claims,citation,family`를 단계적으로 추가 수집합니다.

### 11-4. Auditor 실패로 Chair가 멈출 때

개발 중에는 다음 옵션을 사용합니다.

```powershell
python main.py pipeline --company-dir nepes --company "네패스" --fail-open
```

또는:

```powershell
$env:AUDITOR_FIRST_FAIL_OPEN="1"
python main.py chair --company-dir nepes --company "네패스"
```

제출용/최종 실행에서는 fail-open을 끄고 Auditor 기준을 통과시키는 것이 좋습니다.

---

## 12. 정리해도 되는 런타임 파일

정리 전 dry-run:

```powershell
python .\scripts\clean_runtime_artifacts.py
```

실제 삭제:

```powershell
python .\scripts\clean_runtime_artifacts.py --apply
```

삭제해도 되는 대표 항목:

```text
.venv\
__pycache__\
*.pyc
.pytest_cache\
.mypy_cache\
.ruff_cache\
```

삭제하면 안 되는 항목:

```text
.env
src\
data\
main.py
README.md
OPEN_FIRST.txt
requirements.txt
```

`.env`는 절대 공유하거나 커밋하지 않습니다.

---

## 13. 25개 기업 실행 업데이트

기존 5개 기업 실행 방식은 그대로 유지하고, 25개 기업으로 확장할 때는 **기업 목록을 먼저 한 곳에 고정한 뒤 동일한 명령을 반복 실행**합니다.

권장 기업 목록 파일 형식은 다음과 같습니다.

```text
data\반도체\_sector_common\universe\selected_25_companies.csv
```

CSV 컬럼은 최소한 아래 2개를 포함합니다.

```csv
company_dir,company
nepes,네패스
hanmi,한미반도체
hansol,한솔케미칼
duksan,덕산테코피아
ltc,엘티씨
```

25개 기업 전체를 돌릴 때는 위 CSV에 25개 기업을 모두 넣은 뒤 아래 스크립트를 사용합니다.  
`company_dir`은 폴더명, `company`는 실제 기업명입니다.

---

### 13-1. 25개 기업 목록 불러오기

PowerShell에서 실행합니다.

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\Activate.ps1

$companies = Import-Csv ".\data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv"
```

목록이 제대로 읽혔는지 확인합니다.

```powershell
$companies | Format-Table company_dir, company
$companies.Count
```

정상이라면 `25`가 출력되어야 합니다.

---

### 13-2. 25개 기업 전체 파이프라인 실행

가장 단순한 실행 방식입니다.

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[PIPELINE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py pipeline --company-dir $c.company_dir --company $c.company --fail-open
}
```

`--fail-open`은 개발·점검 중 Auditor 실패로 전체 실행이 멈추는 것을 막기 위한 옵션입니다.  
최종 제출용 실행에서는 가능하면 Auditor 기준을 통과시킨 뒤 fail-open 없이 실행합니다.

```powershell
foreach ($c in $companies) {
  python main.py pipeline --company-dir $c.company_dir --company $c.company
}
```

---

### 13-3. 25개 기업 Data Intake만 일괄 실행

전체 agent 실행 전에 원천 데이터만 먼저 모으고 싶을 때 사용합니다.

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[DATA INTAKE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py data-intake --company-dir $c.company_dir --company $c.company
}
```

특정 intake만 실행할 수도 있습니다.

```powershell
foreach ($c in $companies) {
  python main.py data-intake --company-dir $c.company_dir --company $c.company --agents "finance"
}

foreach ($c in $companies) {
  python main.py data-intake --company-dir $c.company_dir --company $c.company --agents "tech"
}

foreach ($c in $companies) {
  python main.py data-intake --company-dir $c.company_dir --company $c.company --agents "valuation"
}

foreach ($c in $companies) {
  python main.py data-intake --company-dir $c.company_dir --company $c.company --agents "macro"
}
```

---

## 14. 25개 기업 에이전트별 실행 코드

25개 기업을 한 번에 돌릴 때도, 문제가 생긴 에이전트만 다시 돌릴 수 있도록 에이전트별 명령을 분리해 둡니다.

---

### 14-1. Finance Agent 25개 기업 실행

Finance는 현재 명령 구조상 `--company` 중심으로 실행합니다.

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[FINANCE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py finance --company $c.company
}
```

산출물 확인 예시:

```powershell
foreach ($c in $companies) {
  Get-ChildItem ".\data\반도체\$($c.company)\finance" -ErrorAction SilentlyContinue
}
```

---

### 14-2. Market Agent 25개 기업 실행

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[MARKET] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py market --company-dir $c.company_dir --company $c.company
}
```

Market Agent는 `.env`의 `MARKET_WORKBOOK_URL` 또는 로컬 공통 파일을 참조할 수 있습니다.  
URL은 코드에 하드코딩하지 않고 `.env`에서 관리합니다.

---

### 14-3. Tech Intake 25개 기업 실행

KIPRIS Plus 호출 전, 기존 파일 기반으로 빠르게 점검할 때는 아래처럼 실행합니다.

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[TECH INTAKE - SKIP NETWORK] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py tech-intake --company-dir $c.company_dir --company $c.company --skip-network
}
```

KIPRIS Plus 소량 테스트는 아래처럼 실행합니다.

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[TECH INTAKE - KIPRIS TEST] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py tech-intake --company-dir $c.company_dir --company $c.company --max-patents 5 --force-fetch --kipris-plus-components claims,citation,family
}
```

Claims + Citation을 넓게 수집할 때는 아래처럼 실행합니다.

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[TECH INTAKE - CLAIMS/CITATION] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py tech-intake --company-dir $c.company_dir --company $c.company --max-patents 0 --force-fetch --kipris-plus-components claims,citation
}
```

Family는 호출량이 많을 수 있으므로 먼저 일부만 실행합니다.

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[TECH INTAKE - FAMILY PARTIAL] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py tech-intake --company-dir $c.company_dir --company $c.company --max-patents 80 --force-fetch --kipris-plus-components family
}
```

---

### 14-4. Tech Agent 25개 기업 실행

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[TECH AGENT] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py tech --company-dir $c.company_dir --company-name $c.company
}
```

대표 산출물 확인:

```powershell
foreach ($c in $companies) {
  $summary = ".\data\반도체\$($c.company)\tech\tech_chair_summary.json"
  $md = ".\data\반도체\$($c.company)\tech\$($c.company_dir)_tech_chair_summary.md"

  Write-Host "$($c.company) summary json:" (Test-Path $summary)
  Write-Host "$($c.company) summary md:" (Test-Path $md)
}
```

---

### 14-5. Valuation Intake 25개 기업 실행

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[VALUATION INTAKE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py valuation-intake --company-dir $c.company_dir --company $c.company
}
```

---

### 14-6. Valuation Agent 25개 기업 실행

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[VALUATION AGENT] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py valuation --company-dir $c.company_dir --company $c.company
}
```

Valuation 산출물 확인:

```powershell
foreach ($c in $companies) {
  $validation = ".\data\반도체\$($c.company)\valuation\$($c.company_dir)_valuation_validation.json"
  $workbook = ".\data\반도체\$($c.company)\valuation\$($c.company_dir)_valuation_workbook.xlsx"

  Write-Host "$($c.company) validation:" (Test-Path $validation)
  Write-Host "$($c.company) workbook:" (Test-Path $workbook)
}
```

---

### 14-7. Issue Agent 25개 기업 실행

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[ISSUE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py issue --company-dir $c.company_dir --company $c.company
}
```

주의: PowerShell에서는 긴 대시 `—`가 아니라 일반 하이픈 `--`를 사용합니다.

---

### 14-8. Macro Agent 25개 기업 실행

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[MACRO] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py macro --company-dir $c.company_dir --company $c.company
}
```

FRED/OECD 등 외부 키가 없거나 제한되면 fallback 결과가 생성될 수 있습니다.

---

### 14-9. Auditor 25개 기업 실행

```powershell
foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[AUDITOR] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py auditor --company-dir $c.company_dir --company $c.company --json --fail-open
}
```

최종 제출용에서는 가능하면 `--fail-open` 없이 실행합니다.

```powershell
foreach ($c in $companies) {
  python main.py auditor --company-dir $c.company_dir --company $c.company --json
}
```

---

### 14-10. Chair 25개 기업 실행

이미 Data Intake와 각 에이전트, Auditor 결과가 존재하면 Chair에서 다시 오래 걸리는 intake를 돌리지 않도록 아래 환경변수를 사용합니다.

```powershell
$env:CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS="1"

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[CHAIR] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"

  python main.py chair --company-dir $c.company_dir --company $c.company
}
```

Chair 보고서 확인:

```powershell
foreach ($c in $companies) {
  $report = ".\data\반도체\$($c.company)\chair\$($c.company_dir)_chair_report.md"
  Write-Host "$($c.company) chair report:" (Test-Path $report)
}
```

---

## 15. 25개 기업 권장 실행 순서

25개 기업 전체를 안정적으로 돌릴 때는 아래 순서를 권장합니다.

```text
1. selected_25_companies.csv 준비
2. data-intake 전체 또는 agent별 intake 실행
3. finance / market / tech / valuation / issue / macro 실행
4. auditor 실행
5. chair 실행
6. chair report와 auditor_chair_packet 확인
```

PowerShell 전체 실행 예시는 아래와 같습니다.

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\Activate.ps1

$companies = Import-Csv ".\data\반도체\_sector_common\universe\selected_25_companies.csv"

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[1/8 DATA INTAKE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py data-intake --company-dir $c.company_dir --company $c.company
}

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[2/8 FINANCE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py finance --company $c.company
}

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[3/8 MARKET] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py market --company-dir $c.company_dir --company $c.company
}

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[4/8 TECH] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py tech --company-dir $c.company_dir --company-name $c.company
}

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[5/8 VALUATION] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py valuation-intake --company-dir $c.company_dir --company $c.company
  python main.py valuation --company-dir $c.company_dir --company $c.company
}

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[6/8 ISSUE] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py issue --company-dir $c.company_dir --company $c.company
}

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[7/8 MACRO] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py macro --company-dir $c.company_dir --company $c.company
}

foreach ($c in $companies) {
  Write-Host "============================================================"
  Write-Host "[8/8 AUDITOR + CHAIR] $($c.company) / $($c.company_dir)"
  Write-Host "============================================================"
  python main.py auditor --company-dir $c.company_dir --company $c.company --json --fail-open
  python main.py chair --company-dir $c.company_dir --company $c.company
}
```

---

## 16. 25개 기업 실행 결과 빠른 점검

25개 기업 실행 후 누락된 Chair 보고서를 확인합니다.

```powershell
$companies = Import-Csv ".\data\반도체\_sector_common\universe\selected_25_companies.csv"

foreach ($c in $companies) {
  $report = ".\data\반도체\$($c.company)\chair\$($c.company_dir)_chair_report.md"

  if (Test-Path $report) {
    Write-Host "[OK] $($c.company) chair report exists"
  } else {
    Write-Host "[MISSING] $($c.company) chair report missing"
  }
}
```

Auditor compact packet 확인:

```powershell
foreach ($c in $companies) {
  $packet = ".\data\반도체\$($c.company)\auditor\first_auditor\compact_agent_packets\auditor_chair_packet.json"

  if (Test-Path $packet) {
    Write-Host "[OK] $($c.company) auditor chair packet exists"
  } else {
    Write-Host "[MISSING] $($c.company) auditor chair packet missing"
  }
}
```

---

## 17. 성과평가용 weighted_signal 추출 준비

25개 기업 평가에서는 `final_recommendation`보다 `weighted_signal`을 성과평가 기준으로 사용합니다.  
각 기업별 `auditor_chair_packet.json`에서 아래 값을 추출합니다.

```text
company
company_dir
final_recommendation
weighted_signal
finance_signal
valuation_signal
tech_signal
market_signal
issue_signal
macro_signal
core_positive_count
core_negative_count
```

PowerShell에서 JSON 존재 여부만 먼저 확인합니다.

```powershell
$companies = Import-Csv ".\data\반도체\_sector_common\universe\selected_25_companies.csv"

foreach ($c in $companies) {
  $packet = ".\data\반도체\$($c.company)\auditor\first_auditor\compact_agent_packets\auditor_chair_packet.json"
  Write-Host "$($c.company):" (Test-Path $packet)
}
```

`created_at`과 실제 판단 기준일이 다를 수 있으므로, 과거 수익률 검증용 JSON에는 아래 메타데이터를 추가하는 것을 권장합니다.

```json
{
  "created_at": "실제 JSON 생성일",
  "evaluation_asof_date": "평가 기준일",
  "data_cutoff": "평가 기준일",
  "return_validation_start_date": "평가 기준일",
  "return_validation_end_date": "검증 종료일",
  "is_historical_snapshot": true
}
```

`created_at`은 실제 파일 생성일이고, `evaluation_asof_date`는 판단 기준일입니다.  
과거 데이터로 성과평가를 할 때는 `created_at`이 오늘이어도, 입력 데이터와 프롬프트가 `evaluation_asof_date` 기준으로 고정되어 있어야 합니다.

# 18. Google Sheets History Backend

이 패치는 기존 `data/agent_history.db` 방식 대신 Google Sheets를 history DB처럼 사용합니다.
입력 agent snapshot JSON과 Chair/Auditor 결과 JSON은 로컬 파일로 새로 만들지 않고 Google Sheets에 저장합니다.
로컬에는 특정 날짜의 auditor/chair 요약 CSV만 생성합니다.

## 1. 설치

```powershell
cd C:\Agent_6.8
.\.venv\Scripts\Activate.ps1
pip install google-api-python-client google-auth google-auth-httplib2
```

## 2. Google Sheets 준비

1. Google Cloud에서 Service Account를 만듭니다.
2. Service Account JSON 키를 내려받습니다.
3. Google Spreadsheet를 하나 만듭니다.
4. 해당 Spreadsheet를 Service Account 이메일에 편집 권한으로 공유합니다.
5. `.env` 또는 PowerShell에 아래 값을 설정합니다. 실제 키 파일은 절대 커밋하지 않습니다.

```powershell
$env:ALPHAPROVE_HISTORY_BACKEND="sheets"
$env:ALPHAPROVE_HISTORY_SPREADSHEET_ID="구글스프레드시트_ID"
$env:ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE="C:\\Agent_6.8\\secrets\\service_account.json"
```

## 3. 연결 확인

```powershell
python .\scripts\check_google_sheets_history_setup.py
```

성공하면 다음 4개 sheet가 자동 생성됩니다.

- `agent_snapshots`
- `agent_snapshot_chunks`
- `agent_run_results`
- `agent_run_result_chunks`

JSON payload는 gzip+base64로 압축한 뒤 30,000자 단위 chunk로 나누어 저장합니다. Google Sheets의 셀 글자 수 제한을 피하기 위한 구조입니다.

## 4. 2025-05-01 입력 snapshot 저장

단일 기업:

```powershell
python .\scripts\archive_agent_outputs_to_google_sheets.py `
  --field "반도체" `
  --company-dir nepes `
  --company "네패스" `
  --as-of-date "2025-05-01"
```

30개 기업:

```powershell
python .\scripts\archive_agent_outputs_to_google_sheets.py `
  --field "반도체" `
  --as-of-date "2025-05-01" `
  --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv"
```

## 5. Sheets snapshot을 입력으로 Chair 재실행 후 결과도 Sheets에 저장

```powershell
python .\scripts\run_chair_google_sheets_only_all.py `
  --field "반도체" `
  --as-of-date "2025-05-01" `
  --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" `
  --fail-open
```

이 모드에서는 `ALPHAPROVE_SHEETS_DB_ONLY=1`이 자동 설정됩니다. Chair/Auditor 결과 JSON/MD를 로컬에 쓰지 않고 Google Sheets에 저장합니다.

## 6. 해당 날짜의 auditor/chair CSV만 로컬로 추출

실행 로그에 나온 run_id를 사용합니다.

```powershell
python .\scripts\export_google_sheets_history_date_to_csv.py `
  --field "반도체" `
  --as-of-date "2025-05-01" `
  --run-id "chair_sheets_2025-05-01_실행시각"
```

생성 위치:

```text
data\반도체\_sector_common\history_sheets_exports\2025-05-01_실행시각\
```

생성 파일:

- `auditor_chair_packets_2025-05-01.csv`
- `chair_results_2025-05-01.csv`
- `auditor_chair_dataset_2025-05-01.csv`

## 7. 기존 DB 방식에서 정리해도 되는 것

아래는 더 이상 커밋하지 않습니다.

- `data\agent_history.db`
- `data\agent_history.db-*`
- `data\반도체\_sector_common\history_db_exports\`
- DB-only export 임시 CSV들

기존 DB 관련 스크립트는 팀 히스토리 보존 목적이면 남겨도 되지만, 새 흐름에서는 사용하지 않습니다.

- `scripts\archive_agent_outputs_to_history_db.py`
- `scripts\export_single_date_history_db_readonly.py`
- `scripts\export_auditor_chair_packets_to_csv.py`
- `scripts\run_chair_history_db_only_all.py`

`src\common\agent_history.py`는 삭제하지 마세요. 기존 import 호환을 유지하면서 Google Sheets backend로 라우팅하는 facade입니다.

# AlphaProve Exact Signal History Patch

목표는 다음 순서입니다.

1. 현재 `data/반도체/<기업>/<agent>`에 이미 만들어진 agent JSON을 그대로 인식하는지 확인한다.
2. 로컬 기존 `auditor_chair_packet.json`과 Chair JSON에서 각 agent signal 및 Chair 매수/보유/매도 값을 기존 CSV 형식으로 추출한다.
3. Google Sheets history를 사용할 때 fallback packet으로 진행하지 않고, snapshot 로드 실패 시 즉시 중단한다.
4. 2025-05-01~2025-05-20 같은 테스트 기간에 대해 일자별 Chair 결과를 Google Sheets에 저장하고, 로컬에는 CSV만 추출한다.

## 적용 파일

- `src/chair_agent/graph.py`
  - replay mode 로그를 `agent_history.db`가 아니라 실제 backend label로 표시합니다.
  - `ALPHAPROVE_USE_AGENT_HISTORY=1`일 때 기본적으로 `ALPHAPROVE_HISTORY_STRICT=1`로 동작하여 agent snapshot 로드 실패 시 fallback packet을 만들지 않고 중단합니다.
- `scripts/run_chair_google_sheets_only_all.py`
  - Google Sheets replay 실행 시 strict mode를 강제합니다.
- `scripts/check_local_agent_json_recognition.py`
  - 현재 로컬 agent JSON 인식 여부를 CSV로 점검합니다.
- `scripts/export_local_auditor_chair_signals_exact.py`
  - 로컬 기존 auditor/chair JSON에서 각 agent signal과 Chair 최종 의견을 추출합니다.
- `scripts/export_google_sheets_auditor_chair_signals_exact.py`
  - Google Sheets에 저장된 auditor/chair 결과에서 기존 CSV에 맞는 컬럼으로 추출합니다.
- `scripts/run_date_range_chair_to_google_sheets.py`
  - 지정 기간을 일자별로 돌려 auditor/chair 결과를 Google Sheets에 저장합니다.

## 먼저 실행할 것

```powershell
cd C:\Agent_6.8
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH=(Resolve-Path .\src).Path
$env:ALPHAPROVE_HISTORY_BACKEND="sheets"
$env:ALPHAPROVE_HISTORY_SPREADSHEET_ID="실제_스프레드시트_ID"
$env:ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE="C:\Agent_6.8\secrets\service_account.json"
```

## 1단계: 현재 agent JSON 인식 확인

```powershell
python .\scripts\check_local_agent_json_recognition.py `
  --field "반도체" `
  --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" `
  --limit 1
```

30개 전체:

```powershell
python .\scripts\check_local_agent_json_recognition.py `
  --field "반도체" `
  --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv"
```

## 2단계: 로컬 기존 auditor/chair JSON에서 signal CSV 추출

```powershell
python .\scripts\export_local_auditor_chair_signals_exact.py `
  --field "반도체" `
  --as-of-date "2025-05-01" `
  --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" `
  --run-id "local_existing_2025-05-01"
```

## 3단계: Google Sheets snapshot 기반 Chair 재실행

```powershell
python .\scripts\run_chair_google_sheets_only_all.py `
  --field "반도체" `
  --as-of-date "2025-05-01" `
  --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" `
  --limit 1 `
  --fail-open
```

중요: 이제 Google Sheets snapshot을 못 읽으면 fallback packet을 만들지 않고 중단합니다. 이게 정상입니다.

## 4단계: Google Sheets에서 signal CSV 추출

```powershell
python .\scripts\export_google_sheets_auditor_chair_signals_exact.py `
  --field "반도체" `
  --as-of-date "2025-05-01" `
  --run-id "실행_로그에_찍힌_run_id"
```

전체 run_id 중 최신/전체를 보려면:

```powershell
python .\scripts\export_google_sheets_auditor_chair_signals_exact.py `
  --field "반도체" `
  --as-of-date "2025-05-01" `
  --include-all-runs
```

## 5단계: 2025-05-01~2025-05-20 테스트 기간 실행

```powershell
python .\scripts\run_date_range_chair_to_google_sheets.py `
  --field "반도체" `
  --start-date "2025-05-01" `
  --end-date "2025-05-20" `
  --universe-csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" `
  --limit 1 `
  --fail-open
```

주의: 이 스크립트는 `FINANCE_AS_OF_DATE`, `MARKET_END_DATE`, `ISSUE_START_DATE`, `ISSUE_END_DATE`, `MACRO_AS_OF_DATE` 같은 공통 환경변수를 전달합니다. 각 agent 코드가 이 값을 실제로 읽도록 구현되어 있어야 완전한 과거 재계산입니다. 이 패치의 첫 목적은 기존 JSON 인식과 signal export를 먼저 안정화하는 것입니다.


# AlphaProve Macro Fast/Dual-Save Patch

## 적용 파일

- `src/data_intake/macro_intake/normalizer.py`
- `src/data_intake/macro_intake/runner.py`
- `src/data_intake/macro_intake/collector.py`
- `src/data_intake/macro_intake/material_collectors.py`
- `src/data_intake/macro_intake/worldmonitor_fallbacks.py`
- `src/macro_agent/loader.py`
- `src/macro_agent/preprocessor.py`
- `src/macro_agent/scorer.py`
- `src/macro_agent/decision.py`
- `src/macro_agent/runner.py`
- `src/auditor_agent/packet_sanitizer.py`
- `src/chair_agent/graph.py`
- `scripts/run_chair_google_sheets_only_all.py`
- `scripts/run_date_range_chair_to_google_sheets.py`

## 핵심 변경

1. `macro_공통.csv` 한글 mojibake 복구: `?ы넗瑜섏닔?낃?寃⑹???` → `희토류수입가격지수`.
2. Macro intake 기본 기간을 1900년부터가 아니라 2018년부터로 변경해 속도 개선. 필요하면 `MACRO_HISTORY_START_YEAR=1900`으로 전체 이력 재수집 가능.
3. HTTP retry/timeouts/sleep 기본값을 축소해 GDELT/뉴스/소재/WorldMonitor 단계 지연을 줄임.
4. `macro_일별.csv`와 `macro_월별.csv` 모두 동일 지표 universe를 갖도록 정렬.
   - 일별: 일별 원천 + 월별/분기별 값을 일별 축으로 forward-fill.
   - 월별: 일별 원천을 월말 값으로 resample + 월별/분기별 원천 병합.
5. Chair Google Sheets 실행 시 Sheets 저장 후 로컬 chair JSON/MD도 저장. Auditor는 기존 local compact packets/receipt 저장을 유지하면서 Sheets에도 저장.
6. Issue 문장이 중간에서 `…`로 끊기지 않도록 section 추출과 문장 경계 clip 보강.
7. Macro numeric 기준을 하드코딩 숫자 판단이 아니라 입력 이력의 경험적 분위수 기준으로 생성.
   - 기본: high=80분위, low=20분위.
   - 관측치가 30개 미만이면 기존 config/default threshold를 fallback으로 사용.

## 권장 실행 환경변수

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH=(Resolve-Path .\src).Path

# 속도 기본값. 더 빠르게 할 때는 timeout을 3~4초까지 낮출 수 있음.
$env:MACRO_HISTORY_START_YEAR="2018"
$env:MACRO_HTTP_TIMEOUT_SEC="5"
$env:MACRO_HTTP_RETRY_TOTAL="1"
$env:MACRO_GDELT_MIN_INTERVAL_SEC="0.8"
$env:MACRO_GDELT_MAXRECORDS="3"
$env:MACRO_GDELT_LOOP_SLEEP_SEC="0.05"
$env:MACRO_SHORT_SLEEP_SEC="0.05"
$env:MACRO_MATERIAL_RETRIES="1"
$env:MACRO_MATERIAL_CONNECT_TIMEOUT="3"
$env:MACRO_MATERIAL_READ_TIMEOUT="8"
```

## 주의

- 실제 3~4분 달성 여부는 네트워크/API 응답속도, yfinance/GDELT/ECOS/FRED 상태에 따라 달라진다.
- 이 패치는 과정을 생략하지 않고 기본 기간, timeout, retry, sleep을 줄이는 방식이다.
- full historical macro rebuild가 필요하면 `MACRO_HISTORY_START_YEAR=1900`으로 바꾸면 되지만 실행 시간은 크게 늘어난다.

# AlphaProve Macro B Patch v2 — 변화율/rolling 기준 추가

## 적용 대상

아래 파일을 `C:\Agent_6.8` 기준으로 덮어쓰면 됩니다.

```text
src\macro_agent\rolling_criteria.py
src\macro_agent\feature_builder.py
src\macro_agent\scorer.py
scripts\check_macro_rolling_criteria_features.py
```

## 추가된 기준

### 1. 변화율

- 일별 데이터: 1영업일, 5영업일, 20영업일, 60영업일 변화율
- 월별 데이터: 1개월, 3개월, 6개월, 12개월 변화율
- 금리/스프레드 계열은 pct 변화율 외에 bp 변화도 같이 생성

### 2. rolling z-score

현재값을 직전 rolling window의 평균/표준편차와 비교합니다.

- 일별 기본 window: 252영업일
- 월별 기본 window: 60개월
- watch: |z| >= 2
- extreme: |z| >= 3

현재값은 평균/표준편차 계산에서 제외하므로 미래 데이터 누수 없이 작동합니다.

### 3. 평균회귀 기준

- z <= -2: 평균 대비 낮은 구간 → 평균회귀 반등 여지
- z >= +2: 평균 대비 높은 구간 → 평균회귀 하락 압력

### 4. 급등/급락 cutoff

고정 숫자가 아니라 직전 rolling window의 경험적 분위수를 씁니다.

- watch 급락/급등: 5% / 95%
- extreme 급락/급등: 1% / 99%

급등은 변화율이 양수일 때만, 급락은 변화율이 음수일 때만 판정합니다. 완만한 우상향 시계열에서 작은 양(+)의 변화가 하위 분위수라는 이유만으로 급락으로 분류되는 오류를 막기 위한 객관적 방향성 방어입니다.

기본 모드는 속도 때문에 latest row 기준 cutoff만 계산합니다. as-of-date 파이프라인에서는 각 실행의 latest row가 기준일이므로 미래 데이터 누수가 없습니다.

전체 과거 row별 cutoff가 필요할 때만 아래를 켜면 됩니다.

```powershell
$env:MACRO_ROLLING_FULL_HISTORY="1"
```

단, 전체 row별 rolling quantile은 속도가 느려질 수 있으므로 3~4분 목표에서는 기본값 `0`을 권장합니다.

## 객관 기준 근거

- z-score는 현재값이 과거 평균에서 표준편차 몇 개만큼 벗어났는지를 보는 표준화 통계량입니다.
- ±3σ는 공정관리 control chart에서 널리 쓰이는 이상 신호 기준이며, NIST Engineering Statistics Handbook도 3σ control limit을 설명합니다.
- 급등/급락 cutoff는 고정 숫자 대신 해당 지표의 과거 경험분포 분위수로 계산합니다. 지표별 변동성이 다르기 때문에 원달러, 금리, 유가, 지수에 같은 절대 숫자 cutoff를 박지 않습니다.
- 1/5/20/60영업일은 투자/시장 데이터에서 전일·주간·월간·분기 흐름을 나누는 관측 horizon으로 사용합니다. 월별 데이터에는 영업일 기준을 억지 적용하지 않고 1/3/6/12개월 horizon으로 변환했습니다.

## 확인 명령

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH=(Resolve-Path .\src).Path

python -m py_compile .\src\macro_agent\rolling_criteria.py
python -m py_compile .\src\macro_agent\feature_builder.py
python -m py_compile .\src\macro_agent\scorer.py
python .\scripts\check_macro_rolling_criteria_features.py
```

## 속도 관련 권장값

3~4분 목표에서는 아래 기본값을 유지하세요.

```powershell
$env:MACRO_ROLLING_FULL_HISTORY="0"
```

과거 모든 row별 rolling cutoff가 필요한 백테스트 전용 실행에서만 `1`로 바꾸세요.

30개 CSV 기준 실행

.\scripts\run_pipeline_companies.ps1 `
  -Agent pipeline `
  -Csv "data\반도체\_sector_common\universe\universe_30_semiconductor_20260514.csv" `
  -ContinueOnError

DMA를 실제 과거 성과 기반으로 돌리려면 history CSV

$env:ALPHAPROVE_DMA_HISTORY_CSV="C:\Agent_6.8\data\반도체\_sector_common\history_sheets_exports\daily\signal_df_daily_2025-01.csv"
$env:ALPHAPROVE_DMA_ALPHA="0.99"

적용 후 기본실행

cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"

.\scripts\run_pipeline_companies.ps1 -Agent pipeline -DefaultFive -ContinueOnError
