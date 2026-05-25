from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path


README_START = "<!-- ALPHAPROVE_DOCS_MANAGED_START -->"
README_END = "<!-- ALPHAPROVE_DOCS_MANAGED_END -->"
OPEN_START = "<!-- ALPHAPROVE_OPEN_FIRST_MANAGED_START -->"
OPEN_END = "<!-- ALPHAPROVE_OPEN_FIRST_MANAGED_END -->"


README_BLOCK = r"""<!-- ALPHAPROVE_DOCS_MANAGED_START -->

# AlphaProve 최신 운영 가이드: Data Intake부터 Chair까지

이 섹션은 현재 프로젝트의 최신 실행 구조를 기준으로 추가된 운영 가이드입니다. 기존 README의 소개, 설치, 프로젝트 설명은 유지하고, 실제 팀원이 실행할 때 필요한 **Data Intake → 5개 에이전트 → First Auditor → Chair** 흐름을 아래 기준으로 따릅니다.

---

## 1. 현재 기준 전체 구조

AlphaProve는 딥테크 상장기업의 신용·가치평가를 위해 5개 전문 에이전트와 Chair Agent를 사용하는 멀티에이전트 프레임워크입니다.

```text
Data Intake
→ Finance Agent
→ Market Agent
→ Macro Agent
→ Issue Agent
→ Tech Agent
→ First Auditor
→ Chair Agent
→ 최종 기업 보고서
```

현재 목표는 단순히 각 에이전트를 따로 실행하는 것이 아니라, **Chair 실행 한 번으로 Data Intake부터 최종 Chair 보고서까지 한 사이클이 자동으로 이어지는 구조**입니다.

---

## 2. 현재 기준 대상 기업

현재 반도체 섹터 5개 기업을 기본 대상으로 사용합니다.

| company-dir | 기업명 | 비고 |
|---|---|---|
| `nepes` | 네패스 | 기준 완성 기업 |
| `hanmi` | 한미반도체 | 5개 기업 일괄 실행 대상 |
| `hansol` | 한솔케미칼 | 5개 기업 일괄 실행 대상 |
| `duksan` | 덕산테코피아 | 5개 기업 일괄 실행 대상 |
| `ltc` | 엘티씨 | 5개 기업 일괄 실행 대상 |

실행 시 `--company-dir`에는 영문 slug를, `--company`에는 표시명을 넣습니다.

```powershell
python main.py chair --company-dir nepes --company "네패스"
```

---

## 3. 최신 폴더 구조 원칙

현재 기준은 `workspace/`가 아니라 `data/` 구조입니다.

```text
project-root/
  main.py
  .env
  README.md
  OPEN_FIRST.txt

  src/
    common/
    data_intake/
    finance_agent/
    market_agent/
    macro_agent/
    issue_agent/
    tech_agent/
    auditor_agent/
    chair_agent/

  scripts/

  data/
    _global_common/
      macro/

    반도체/
      _sector_common/
        data/
        source_data/
        templates/
        tech/

      네패스/
        intake/
        finance/
        market/
        macro/
        issue/
        tech/
        chair/
        auditor/

      한미반도체/
      한솔케미칼/
      덕산테코피아/
      엘티씨/
```

중요 원칙은 다음과 같습니다.

```text
1. workspace/는 새 구조에서 사용하지 않습니다.
2. 공통 거시 데이터는 data/_global_common/macro에 둡니다.
3. 반도체 섹터 공통 데이터는 data/반도체/_sector_common에 둡니다.
4. 기업별 결과는 data/반도체/<기업명>/<agent>에 둡니다.
5. Tech 템플릿은 data/반도체/_sector_common/templates를 참조합니다.
6. 템플릿 엑셀은 덮어쓰지 않습니다.
7. .env, API 키, .venv, __pycache__, workspace는 GitHub에 올리지 않습니다.
```

---

## 4. 처음 실행 전 PowerShell 공통 설정

VS Code PowerShell에서 아래를 먼저 실행합니다.

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
```

가상환경이 꺼져 있으면 켭니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책 오류가 나면 현재 터미널에서만 임시 허용합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 5. `.env` 최신 설정 구조

실제 API 키는 각자 로컬 `.env`에만 넣고 GitHub에는 올리지 않습니다.

### 5-1. 공통 실행 설정

```env
MAX_CONTEXT_CHARS=10000
REQUEST_TIMEOUT=80
```

`REQUEST_TIMEOUT`을 너무 짧게 두면 NVIDIA, Gemini, 뉴스/거시 수집에서 timeout이 날 수 있습니다. 단, 너무 길면 전체 Chair cycle이 느려집니다.

---

### 5-2. 하위 5개 에이전트 공용 LLM

Finance, Market, Macro, Issue, Tech는 공용 라우팅 설정을 사용합니다.

```env
PARALLEL_LLM_PROVIDER=gemini
# PARALLEL_LLM_PROVIDER=nvidia
```

Gemini 백업용:

```env
GEMINI_API_KEY=여기에_실제_Gemini_API_Key
GEMINI_PARALLEL_MODEL=gemini-2.5-flash-lite
GEMINI_PARALLEL_MAX_TOKENS=4096
GEMINI_TEMPERATURE=0
GEMINI_TIMEOUT=60
```

NVIDIA 사용 시:

```env
NVIDIA_PARALLEL_API_KEY=nvapi-여기에_실제키
NVIDIA_PARALLEL_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_PARALLEL_MODEL=qwen/qwen3.5-397b-a17b
```

NVIDIA에서 429 또는 timeout이 자주 나면, 하위 5개 에이전트만 Gemini로 돌릴 수 있습니다.

```env
PARALLEL_LLM_PROVIDER=gemini
```

NVIDIA로 되돌리려면 다음처럼 바꿉니다.

```env
PARALLEL_LLM_PROVIDER=nvidia
```

---

### 5-3. Chair 전용 LLM

Chair는 하위 5개 에이전트보다 최종 종합 품질이 중요하므로 별도 LLM을 사용합니다.

```env
CHAIR_LLM_PROVIDER=nvidia
CHAIR_LLM_API_KEY=nvapi-여기에_실제키
CHAIR_LLM_BASE_URL=https://integrate.api.nvidia.com/v1
CHAIR_LLM_MODEL=deepseek-ai/deepseek-v4-pro

CHAIR_REPORT_MAX_TOKENS=6000
CHAIR_MIN_REPORT_CHARS=2000
CHAIR_REPORT_MAX_RETRIES=1
```

---

### 5-4. Auditor 전용 LLM

First Auditor는 별도 모델을 사용합니다.

```env
AUDITOR_LLM_PROVIDER=anthropic
AUDITOR_PROVIDER=anthropic

ANTHROPIC_API_KEY=sk-ant-여기에_실제키
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_AUDITOR_MODEL=claude-sonnet-4-6
ANTHROPIC_MAX_TOKENS=2048
ANTHROPIC_TEMPERATURE=0
```

Gemini로 임시 전환할 때는 아래 둘 중 하나만 `gemini`로 바꿔도 됩니다. 둘 다 있으면 `AUDITOR_LLM_PROVIDER`가 우선합니다.

```env
AUDITOR_LLM_PROVIDER=gemini
AUDITOR_PROVIDER=gemini
AUDITOR_GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_API_KEY=AIza-여기에_실제키
```

NVIDIA/OpenAI-compatible Auditor 백업용 설정도 남겨둘 수 있습니다.

```env
NVIDIA_API_KEY=nvapi-여기에_실제키
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_AUDITOR_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
```

---

### 5-5. First Auditor 정책

```env
AUDITOR_FAST_MODE=0
AUDITOR_FIRST_ENABLE_LLM_JUDGE=1
AUDITOR_FIRST_MAX_ROUNDS=2
AUDITOR_FIRST_PASS_THRESHOLD=0.80
AUDITOR_FIRST_FAIL_OPEN=1
CHAIR_EXCLUDE_SUPPLEMENTAL_FINANCE_ML_FROM_AUDIT=1
```

설명:

```text
AUDITOR_FIRST_PASS_THRESHOLD=0.80
→ 현재는 속도와 안정성 균형을 위해 0.80 권장

AUDITOR_FIRST_FAIL_OPEN=1
→ Auditor가 실패해도 Chair 보고서는 생성
→ 발표/시연 중 전체 파이프라인 중단을 막기 위한 설정

CHAIR_EXCLUDE_SUPPLEMENTAL_FINANCE_ML_FROM_AUDIT=1
→ Finance ML 보조 산출물이 Auditor 통과를 방해하지 않도록 제외
```

---

### 5-6. Chair 실행 전 Data Intake 자동 실행

Chair 실행 전 자동으로 Data Intake를 돌리려면 아래를 사용합니다.

```env
CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS=1
CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS=0
CHAIR_DATA_INTAKE_AGENTS=macro,market,issue,finance,tech
CHAIR_DATA_INTAKE_FIELD=반도체
```

Tech Intake는 Chair cycle 안에서 중복 실행되지 않도록 기본적으로 데이터 준비만 하게 둡니다.

```env
CHAIR_TECH_INTAKE_SKIP_AGENT=1
```

KIPRIS Plus 유료 endpoint가 아직 준비되지 않았으면 네트워크 수집은 끕니다.

```env
CHAIR_TECH_INTAKE_SKIP_NETWORK=1
CHAIR_TECH_INTAKE_FORCE_FETCH=0
```

KIPRIS Plus 유료 수집까지 수행하려면:

```env
CHAIR_TECH_INTAKE_SKIP_NETWORK=0
CHAIR_TECH_INTAKE_FORCE_FETCH=1
```

---

### 5-7. Tech Intake 설정

```env
TECH_INTAKE_MAX_PATENTS=0
TECH_INTAKE_SLEEP_SEC=0.6
TECH_INTAKE_TIMEOUT=60
TECH_INTAKE_FORCE_FETCH=0
TECH_INTAKE_SKIP_NETWORK=1
TECH_INTAKE_SKIP_AGENT=0
TECH_INTAKE_COPY_NEPES_REFERENCE_SCHEMA=1
```

의미:

```text
TECH_INTAKE_MAX_PATENTS=0
→ normalized CSV에 있는 특허 전체 사용

TECH_INTAKE_SKIP_NETWORK=1
→ KIPRIS Plus 유료 endpoint 없이 로컬/엑셀/fallback 기반 생성

TECH_INTAKE_SKIP_AGENT=0
→ Intake 후 Tech Agent까지 실행

TECH_INTAKE_COPY_NEPES_REFERENCE_SCHEMA=1
→ 네패스 기준 schema를 참고하되, 값은 기업별로 새로 생성
```

KIPRIS Plus 설정:

```env
KIPRIS_PLUS_API_KEY=여기에_실제키
KIPRIS_API_KEY=여기에_실제키

KIPRIS_PLUS_CLAIMS_ENDPOINT=http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo
KIPRIS_PLUS_CLAIMS_API_KEY_ENV=KIPRIS_PLUS_API_KEY
KIPRIS_PLUS_CLAIMS_KEY_PARAM=accessKey
KIPRIS_PLUS_CLAIMS_APP_PARAM=applicationNumber

KIPRIS_PLUS_FAMILY_KEY_PARAM=ServiceKey
KIPRIS_PLUS_APPNO_PARAM=applicationNumber
KIPRIS_PLUS_EXTRA_PARAMS_JSON={"format":"xml"}
```

---

### 5-8. Macro Intake 설정

```env
MACRO_REUSE_TODAY_OUTPUTS=1
MACRO_FORCE_REFRESH=0

MACRO_ENABLE_GDELT=1
MACRO_GDELT_MIN_INTERVAL_SEC=6
MACRO_GDELT_MAXRECORDS=5
MACRO_GDELT_RETRY_ON_429=0
MACRO_GDELT_PRE_WAIT=0
MACRO_GDELT_LOOP_SLEEP_SEC=0.5

MACRO_ENABLE_SERPER=0

MACRO_ENABLE_SMM=0
MACRO_SMM_PUBLIC_TRY=0
MACRO_ENABLE_MATERIAL_PRICE_NEWS_PROXY=1

MACRO_MATERIAL_READ_TIMEOUT=60
MACRO_MATERIAL_RETRIES=2
MACRO_MATERIAL_RETRY_SLEEP_SEC=2
MACRO_RARE_EARTH_FRED_SERIES=IP28
MACRO_RARE_EARTH_FRED_LABEL=희토류수입가격지수

MACRO_ENABLE_WORLDMONITOR_RSS=1
MACRO_ENABLE_WORLDMONITOR_REG_FALLBACK=1
MACRO_ENABLE_FEDERAL_REGISTER_API=1
MACRO_ENABLE_PORTWATCH=1
MACRO_ENABLE_MATERIAL_RISK_STATIC=1
```

설명:

```text
MACRO_REUSE_TODAY_OUTPUTS=1
→ 같은 날 이미 수집한 거시 데이터는 재사용

MACRO_ENABLE_GDELT=1
→ GDELT는 유용하지만 429가 잦으므로 non-blocking으로 사용

MACRO_ENABLE_SMM=0
→ SMM은 로그인/권한이 필요하므로 기본 OFF

MACRO_ENABLE_MATERIAL_PRICE_NEWS_PROXY=1
→ 직접 가격 수집이 안 되면 뉴스/공급망 리스크 proxy 사용
```

---

## 6. 실행 전 점검

문법 확인:

```powershell
python -m compileall .\src .\scripts -q
```

LLM 라우팅 확인:

```powershell
python .\scripts\check_llm_routing.py
```

기대 구조:

```text
Finance / Market / Macro / Issue / Tech
→ PARALLEL_LLM_PROVIDER 기준

Chair
→ CHAIR_LLM_MODEL 기준

Auditor
→ AUDITOR_PROVIDER 기준
```

---

## 7. 한 기업 실행 방법

### 7-1. Chair full cycle 실행

네패스:

```powershell
python main.py chair --company-dir nepes --company "네패스"
```

한미반도체:

```powershell
python main.py chair --company-dir hanmi --company "한미반도체"
```

한솔케미칼:

```powershell
python main.py chair --company-dir hansol --company "한솔케미칼"
```

덕산테코피아:

```powershell
python main.py chair --company-dir duksan --company "덕산테코피아"
```

엘티씨:

```powershell
python main.py chair --company-dir ltc --company "엘티씨"
```

이 명령은 설정에 따라 다음을 수행합니다.

```text
Data Intake
→ 5개 에이전트 실행
→ First Auditor
→ Chair 최종 보고서
```

---

### 7-2. Data Intake만 실행

전체 intake:

```powershell
python main.py intake --company-dir nepes --company "네패스" --agents macro,market,issue,finance,tech
```

Tech intake만:

```powershell
python main.py intake --company-dir nepes --company "네패스" --agents tech --tech-max-patents 0 --tech-skip-network --tech-skip-agent
```

Macro intake만:

```powershell
python main.py intake --company-dir nepes --company "네패스" --agents macro
```

---

### 7-3. 개별 에이전트 실행

Finance:

```powershell
python main.py finance --company-dir nepes --company "네패스"
```

Market:

```powershell
python main.py market --company-dir nepes --company "네패스"
```

Macro:

```powershell
python main.py macro --company-dir nepes --company "네패스"
```

Macro 빠른 확인:

```powershell
python main.py macro --company-dir nepes --company "네패스" --no-llm
```

Issue:

```powershell
python main.py issue --company-dir nepes --company "네패스"
```

Tech:

```powershell
python main.py tech --company-dir nepes --company "네패스"
```

---

## 8. 5개 기업 전체 실행 방법

### 8-1. Tech 엑셀 정량 근거 생성

```powershell
python .\scripts\build_tech_excel_quantified_metrics.py --all
```

이 단계는 `data/반도체/_sector_common/templates`의 엑셀 템플릿을 읽어 기업별 Tech 정량 근거 파일을 생성합니다.

생성 예시:

```text
data/반도체/<기업명>/tech/tech_excel_frame_full.json
data/반도체/<기업명>/tech/tech_excel_frame_summary.md
data/반도체/<기업명>/tech/tech_excel_frame_items.csv
data/반도체/<기업명>/tech/tech_excel_frame_metrics.csv
data/반도체/<기업명>/tech/quantified_metrics.csv
data/반도체/<기업명>/tech/quanified_metrix.csv
```

---

### 8-2. Tech Intake 5개 기업 실행

KIPRIS Plus 유료 endpoint 준비 전:

```powershell
python .\scripts\run_tech_intake_5companies.py --max-patents 0 --skip-network
```

PowerShell wrapper가 있을 때:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_tech_intake_5companies.ps1 -MaxPatents 0 -SkipNetwork
```

KIPRIS Plus 유료 결제 후 전체 수집:

```powershell
python .\scripts\run_tech_intake_5companies.py --max-patents 0 --force-fetch
```

PowerShell wrapper가 있을 때:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_tech_intake_5companies.ps1 -MaxPatents 0 -ForceFetch
```

---

### 8-3. Tech 투자자용 scorecard 재병합

이미 생성된 Tech 산출물을 기준으로 최종 scorecard와 Chair summary를 다시 병합할 때 사용합니다.

```powershell
python .\scripts\sync_tech_investor_scorecards.py --all
```

반영 대상:

```text
data/반도체/<기업명>/tech/tech_investor_scorecard.json
data/반도체/<기업명>/tech/<slug>_tech_investor_scorecard.md
data/반도체/<기업명>/tech/tech_chair_summary.json
data/반도체/<기업명>/tech/<slug>_tech_chair_summary.md
```

---

### 8-4. Macro 5개 기업 실행

빠른 확인:

```powershell
python .\scripts\run_macro_5companies.py --no-llm
```

LLM 포함 실행:

```powershell
python .\scripts\run_macro_5companies.py
```

특정 기업만:

```powershell
python .\scripts\run_macro_5companies.py --only nepes --only hanmi --no-llm
```

---

### 8-5. Chair full cycle 5개 기업 실행

스크립트가 있을 때:

```powershell
python .\scripts\run_chair_cycle_5companies.py
```

스크립트가 없으면 직접 순차 실행합니다.

```powershell
python main.py chair --company-dir nepes --company "네패스"
python main.py chair --company-dir hanmi --company "한미반도체"
python main.py chair --company-dir hansol --company "한솔케미칼"
python main.py chair --company-dir duksan --company "덕산테코피아"
python main.py chair --company-dir ltc --company "엘티씨"
```

---

## 9. Tech Agent 최신 해석 구조

Tech는 단순 기술 요약이 아니라 **투자자용 최종 Tech 점수**를 중심으로 봅니다.

```text
Final Investor Tech Score
→ Tech-to-Value Bridge
→ IP Evidence Composite
→ Excel-frame 정량 근거
→ Evidence Confidence
→ Technology Differentiation
→ Patent Momentum
→ Data Coverage
```

보고서에서는 여러 점수를 길게 나열하기보다 다음 구조를 우선합니다.

```text
1. 최종 Tech 점수
2. 한 줄 투자자 해석
3. 점수 구성요소별 기여도
4. 핵심 근거 카드
5. 데이터 품질
6. 상세 appendix 경로
```

`확인 제한`은 가능한 한 아래 상태로 구분합니다.

```text
- 직접 수집 OK
- 로컬 대체
- API 권한 제한
- 원천 미공개
- 미수집
```

---

## 10. Macro Agent 최신 해석 구조

Macro도 Tech처럼 최종 투자자용 점수 구조를 사용합니다.

```text
Final Macro Environment Score
→ 금리·신용·유동성
→ 환율·에너지·소재
→ 글로벌 경기·수요 사이클
→ 물가·고용·정책
→ 공급망·지정학 리스크
→ 데이터 품질
```

기존 macro decision score를 유지하면서, 그 위에 투자자용 scorecard를 추가하는 구조입니다.

---

## 11. 주요 산출물 위치

### 11-1. Tech

```text
data/반도체/<기업명>/tech/tech_chair_summary.json
data/반도체/<기업명>/tech/<slug>_tech_chair_summary.md
data/반도체/<기업명>/tech/tech_investor_scorecard.json
data/반도체/<기업명>/tech/<slug>_tech_investor_scorecard.md
data/반도체/<기업명>/tech/<slug>_tech_full_appendix.md
data/반도체/<기업명>/tech/quantified_metrics.csv
data/반도체/<기업명>/tech/quanified_metrix.csv
```

### 11-2. Macro

```text
data/반도체/<기업명>/macro/<slug>_macro_agent_packet.json
data/반도체/<기업명>/macro/<slug>_macro_investor_scorecard.json
data/반도체/<기업명>/macro/<slug>_macro_investor_scorecard.md
```

### 11-3. Chair / Auditor

```text
data/반도체/<기업명>/chair/
data/반도체/<기업명>/auditor/
```

---

## 12. 자주 나는 오류와 해결

### 12-1. NVIDIA 429 또는 timeout

하위 5개 에이전트만 Gemini로 전환합니다.

```env
PARALLEL_LLM_PROVIDER=gemini
```

다시 NVIDIA로 복귀:

```env
PARALLEL_LLM_PROVIDER=nvidia
```

---

### 12-2. PowerShell `.ps1` 디지털 서명 오류

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_tech_intake_5companies.ps1 -MaxPatents 0 -SkipNetwork
```

또는 현재 세션에서만 허용:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

### 12-3. `ModuleNotFoundError: No module named 'common'`

스크립트 직접 실행 시 `src` 경로가 잡히지 않은 경우입니다. 최신 스크립트는 내부에서 `src`를 `sys.path`에 추가해야 합니다.

확인:

```powershell
python .\scripts\build_tech_excel_quantified_metrics.py --all
```

---

### 12-4. `workspace`가 다시 생김

새 구조에서는 `workspace`를 쓰지 않습니다.

확인:

```powershell
Test-Path .\workspace
Get-ChildItem -Recurse -File .\src,.\scripts | Select-String -Pattern "workspace"
```

`src` 또는 `scripts`에서 workspace 경로가 나오면 새 `data/` 구조로 바꿔야 합니다.

---

## 13. GitHub 업로드 전 확인

```powershell
git status
git diff --stat
python -m compileall .\src .\scripts -q
```

올리면 안 되는 것:

```text
.env
API 키
.venv/
workspace/
__pycache__/
개인 로컬 절대경로가 박힌 파일
대용량 원본 데이터
```

올릴 수 있는 것:

```text
src/ 수정 코드
scripts/ 수정 코드
README.md
OPEN_FIRST.txt
docs/
.env.example
```

---

## 14. 팀원용 최소 실행 순서

### 한 기업만 실행

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"

python -m compileall .\src .\scripts -q
python .\scripts\check_llm_routing.py

python main.py chair --company-dir nepes --company "네패스"
```

### 5개 기업 전체 실행

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"

python -m compileall .\src .\scripts -q
python .\scripts\check_llm_routing.py

python .\scripts\build_tech_excel_quantified_metrics.py --all
python .\scripts\sync_tech_investor_scorecards.py --all
python .\scripts\run_chair_cycle_5companies.py
```

`run_chair_cycle_5companies.py`가 없으면 직접 실행합니다.

```powershell
python main.py chair --company-dir nepes --company "네패스"
python main.py chair --company-dir hanmi --company "한미반도체"
python main.py chair --company-dir hansol --company "한솔케미칼"
python main.py chair --company-dir duksan --company "덕산테코피아"
python main.py chair --company-dir ltc --company "엘티씨"
```

<!-- ALPHAPROVE_DOCS_MANAGED_END -->
"""

OPEN_FIRST_BLOCK = r"""<!-- ALPHAPROVE_OPEN_FIRST_MANAGED_START -->

# OPEN_FIRST 최신 실행 가이드

이 파일은 팀원이 프로젝트를 열었을 때 가장 먼저 보는 실행 안내입니다.

---

## 1. 가장 먼저 실행

```powershell
cd C:\Agent_6.8
chcp 65001
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\Activate.ps1
```

PowerShell 정책 오류가 나면:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 2. `.env`에서 확인할 것

하위 5개 에이전트 LLM:

```env
PARALLEL_LLM_PROVIDER=gemini
# PARALLEL_LLM_PROVIDER=nvidia
```

Gemini:

```env
GEMINI_API_KEY=실제키
GEMINI_PARALLEL_MODEL=gemini-2.5-flash-lite
```

NVIDIA:

```env
NVIDIA_PARALLEL_API_KEY=nvapi-실제키
NVIDIA_PARALLEL_MODEL=qwen/qwen3.5-397b-a17b
```

Chair:

```env
CHAIR_LLM_MODEL=deepseek-ai/deepseek-v4-pro
```

Auditor:

```env
AUDITOR_LLM_PROVIDER=anthropic
AUDITOR_PROVIDER=anthropic
ANTHROPIC_AUDITOR_MODEL=claude-sonnet-4-6
```

Chair 실행 전 Data Intake 자동 실행:

```env
CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS=1
CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS=0
CHAIR_DATA_INTAKE_AGENTS=macro,market,issue,finance,tech
CHAIR_DATA_INTAKE_FIELD=반도체
```

---

## 3. 정상 확인

```powershell
python -m compileall .\src .\scripts -q
python .\scripts\check_llm_routing.py
```

---

## 4. 한 기업 전체 실행

```powershell
python main.py chair --company-dir nepes --company "네패스"
```

다른 기업:

```powershell
python main.py chair --company-dir hanmi --company "한미반도체"
python main.py chair --company-dir hansol --company "한솔케미칼"
python main.py chair --company-dir duksan --company "덕산테코피아"
python main.py chair --company-dir ltc --company "엘티씨"
```

---

## 5. Data Intake만 실행

전체:

```powershell
python main.py intake --company-dir nepes --company "네패스" --agents macro,market,issue,finance,tech
```

Tech만:

```powershell
python main.py intake --company-dir nepes --company "네패스" --agents tech --tech-max-patents 0 --tech-skip-network --tech-skip-agent
```

Macro만:

```powershell
python main.py intake --company-dir nepes --company "네패스" --agents macro
```

---

## 6. 개별 에이전트 실행

```powershell
python main.py finance --company-dir nepes --company "네패스"
python main.py market --company-dir nepes --company "네패스"
python main.py macro --company-dir nepes --company "네패스"
python main.py macro --company-dir nepes --company "네패스" --no-llm
python main.py issue --company-dir nepes --company "네패스"
python main.py tech --company-dir nepes --company "네패스"
```

---

## 7. 5개 기업 전체 실행

```powershell
python .\scripts\build_tech_excel_quantified_metrics.py --all
python .\scripts\sync_tech_investor_scorecards.py --all
python .\scripts\run_chair_cycle_5companies.py
```

`run_chair_cycle_5companies.py`가 없으면:

```powershell
python main.py chair --company-dir nepes --company "네패스"
python main.py chair --company-dir hanmi --company "한미반도체"
python main.py chair --company-dir hansol --company "한솔케미칼"
python main.py chair --company-dir duksan --company "덕산테코피아"
python main.py chair --company-dir ltc --company "엘티씨"
```

---

## 8. 주요 결과 파일

```text
data/반도체/<기업명>/tech/tech_chair_summary.json
data/반도체/<기업명>/tech/<slug>_tech_chair_summary.md
data/반도체/<기업명>/tech/tech_investor_scorecard.json

data/반도체/<기업명>/macro/<slug>_macro_agent_packet.json
data/반도체/<기업명>/macro/<slug>_macro_investor_scorecard.md

data/반도체/<기업명>/chair/
data/반도체/<기업명>/auditor/
```

---

## 9. 절대 올리면 안 되는 것

```text
.env
API 키
.venv/
workspace/
__pycache__/
개인 로컬 절대경로가 박힌 파일
```

<!-- ALPHAPROVE_OPEN_FIRST_MANAGED_END -->
"""


def _replace_or_append(original: str, block: str, start: str, end: str) -> str:
    if start in original and end in original:
        before = original.split(start, 1)[0].rstrip()
        after = original.split(end, 1)[1].lstrip()
        return before + "\n\n" + block.strip() + "\n\n" + after

    # README가 이미 길다면 맨 뒤에 최신 운영 가이드를 추가한다.
    return original.rstrip() + "\n\n" + block.strip() + "\n"


def _backup(path: Path) -> None:
    if path.exists():
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_suffix(path.suffix + f".bak_{stamp}")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def update_file(path: Path, block: str, start: str, end: str, dry_run: bool = False) -> None:
    if path.exists():
        original = path.read_text(encoding="utf-8")
    else:
        original = ""

    updated = _replace_or_append(original, block, start, end)

    if dry_run:
        print(f"[DRY RUN] would update: {path}")
        print(f"  original chars={len(original)} updated chars={len(updated)}")
        return

    _backup(path)
    path.write_text(updated, encoding="utf-8")
    print(f"[UPDATED] {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Append/update AlphaProve README and OPEN_FIRST managed sections.")
    parser.add_argument("--root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    update_file(root / "README.md", README_BLOCK, README_START, README_END, dry_run=args.dry_run)
    update_file(root / "OPEN_FIRST.txt", OPEN_FIRST_BLOCK, OPEN_START, OPEN_END, dry_run=args.dry_run)

    env_example = root / ".env.example"
    if not env_example.exists() and not args.dry_run:
        # .env.example은 실제 키 없이 생성한다.
        env_example.write_text("""# AlphaProve .env example
# 실제 키를 넣은 .env는 GitHub에 올리지 마세요.

MAX_CONTEXT_CHARS=10000
REQUEST_TIMEOUT=80

# 하위 5개 에이전트 LLM
PARALLEL_LLM_PROVIDER=gemini
# PARALLEL_LLM_PROVIDER=nvidia

NVIDIA_PARALLEL_API_KEY=nvapi-
NVIDIA_PARALLEL_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_PARALLEL_MODEL=qwen/qwen3.5-397b-a17b

GEMINI_API_KEY=
GEMINI_PARALLEL_MODEL=gemini-2.5-flash-lite
GEMINI_PARALLEL_MAX_TOKENS=4096
GEMINI_TEMPERATURE=0
GEMINI_TIMEOUT=60

# Chair 전용
CHAIR_LLM_PROVIDER=nvidia
CHAIR_LLM_API_KEY=nvapi-
CHAIR_LLM_BASE_URL=https://integrate.api.nvidia.com/v1
CHAIR_LLM_MODEL=deepseek-ai/deepseek-v4-pro
CHAIR_REPORT_MAX_TOKENS=6000
CHAIR_MIN_REPORT_CHARS=2000
CHAIR_REPORT_MAX_RETRIES=1

# Auditor 전용
AUDITOR_LLM_PROVIDER=anthropic
AUDITOR_PROVIDER=anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_AUDITOR_MODEL=claude-sonnet-4-6
ANTHROPIC_MAX_TOKENS=2048
ANTHROPIC_TEMPERATURE=0

# Auditor를 Gemini로 임시 전환할 때
# AUDITOR_LLM_PROVIDER=gemini
# AUDITOR_PROVIDER=gemini
# AUDITOR_GEMINI_MODEL=gemini-2.5-flash-lite

AUDITOR_FAST_MODE=0
AUDITOR_FIRST_ENABLE_LLM_JUDGE=1
AUDITOR_FIRST_MAX_ROUNDS=2
AUDITOR_FIRST_PASS_THRESHOLD=0.80
AUDITOR_FIRST_FAIL_OPEN=1
CHAIR_EXCLUDE_SUPPLEMENTAL_FINANCE_ML_FROM_AUDIT=1

# Chair full cycle
CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS=1
CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS=0
CHAIR_DATA_INTAKE_AGENTS=macro,market,issue,finance,tech
CHAIR_DATA_INTAKE_FIELD=반도체
CHAIR_TECH_INTAKE_SKIP_AGENT=1
CHAIR_TECH_INTAKE_SKIP_NETWORK=1
CHAIR_TECH_INTAKE_FORCE_FETCH=0

# Tech Intake
TECH_INTAKE_MAX_PATENTS=0
TECH_INTAKE_SLEEP_SEC=0.6
TECH_INTAKE_TIMEOUT=60
TECH_INTAKE_FORCE_FETCH=0
TECH_INTAKE_SKIP_NETWORK=1
TECH_INTAKE_SKIP_AGENT=0
TECH_INTAKE_COPY_NEPES_REFERENCE_SCHEMA=1

KIPRIS_PLUS_API_KEY=
KIPRIS_API_KEY=
KIPRIS_PLUS_CLAIMS_ENDPOINT=http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo
KIPRIS_PLUS_CLAIMS_API_KEY_ENV=KIPRIS_PLUS_API_KEY
KIPRIS_PLUS_CLAIMS_KEY_PARAM=accessKey
KIPRIS_PLUS_CLAIMS_APP_PARAM=applicationNumber
KIPRIS_PLUS_FAMILY_KEY_PARAM=ServiceKey
KIPRIS_PLUS_APPNO_PARAM=applicationNumber
KIPRIS_PLUS_EXTRA_PARAMS_JSON={"format":"xml"}

# Macro Intake
MACRO_REUSE_TODAY_OUTPUTS=1
MACRO_FORCE_REFRESH=0
MACRO_ENABLE_GDELT=1
MACRO_GDELT_MIN_INTERVAL_SEC=6
MACRO_GDELT_MAXRECORDS=5
MACRO_GDELT_RETRY_ON_429=0
MACRO_GDELT_PRE_WAIT=0
MACRO_GDELT_LOOP_SLEEP_SEC=0.5
MACRO_ENABLE_SERPER=0
MACRO_ENABLE_SMM=0
MACRO_SMM_PUBLIC_TRY=0
MACRO_ENABLE_MATERIAL_PRICE_NEWS_PROXY=1
MACRO_MATERIAL_READ_TIMEOUT=60
MACRO_MATERIAL_RETRIES=2
MACRO_MATERIAL_RETRY_SLEEP_SEC=2
MACRO_RARE_EARTH_FRED_SERIES=IP28
MACRO_RARE_EARTH_FRED_LABEL=희토류수입가격지수
MACRO_ENABLE_WORLDMONITOR_RSS=1
MACRO_ENABLE_WORLDMONITOR_REG_FALLBACK=1
MACRO_ENABLE_FEDERAL_REGISTER_API=1
MACRO_ENABLE_PORTWATCH=1
MACRO_ENABLE_MATERIAL_RISK_STATIC=1
""", encoding="utf-8")
        print(f"[CREATED] {env_example}")
    elif args.dry_run:
        print(f"[DRY RUN] would create if missing: {env_example}")

    print("\nNext checks:")
    print("  python -m compileall .\\src .\\scripts -q")
    print("  python .\\scripts\\check_llm_routing.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
