from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
import re

ROOT = Path.cwd()
REPORT = field_agent_dir("tech") / "nepes_chair_report.md"
TECH = field_agent_dir("tech") / "nepes_tech_high_quality_report.md"
BRIDGE = field_agent_dir("tech") / "nepes_tech_to_value_bridge.md"

report = REPORT.read_text(encoding="utf-8", errors="ignore")
tech = TECH.read_text(encoding="utf-8", errors="ignore") if TECH.exists() else ""
bridge = BRIDGE.read_text(encoding="utf-8", errors="ignore") if BRIDGE.exists() else ""

new_section = """### 기술 분석
- **의견:** 보유
- **Tech-to-Value Bridge:** 77.0/100 / **COMMERCIALIZATION_WATCH(사업화 추적형)**
- **등급 의미:** 기술성은 확인되지만, 고객 채택·양산·매출 전환·FCF 개선까지 이어지는 연결고리는 계속 추적해야 하는 상태입니다.
- **Chair 반영 원칙:** 기술 우위는 긍정 보조 근거로 반영하되, 단독 매수 근거로 과대평가하지 않습니다.

#### 1) 기술 포지션 요약
네패스는 원천 문서 기준 **WLP, FOWLP/PLP, Bumping, 반도체 패키징, 후공정**을 핵심 기술 축으로 보유한 기업입니다. 해당 기술은 스마트폰, 서버, 고성능컴퓨팅, 웨어러블, 자동차 등 다양한 칩셋 적용처와 연결됩니다.

#### 2) KIPRIS 특허/IP 정량 근거
- 회사 매칭 특허: **408건**
- 등록 특허: **303건**
- 존속 가능 특허: **236건**
- 최근 5년 특허: **107건**
- H01L 반도체 핵심 IPC 특허: **6건**
- 특허-기술 키워드 매칭: **563회**
- 특허 포트폴리오 범위: **1998~2025년**

#### 3) 해석
특허·기술 포트폴리오는 기술 지속성과 진입장벽을 뒷받침하는 강한 보조 근거입니다. 다만 현재 판정이 COMMERCIALIZATION_WATCH인 이유는 기술성 자체보다 **고객사 채택, 양산 규모, 제품별 매출 기여, FCF 개선 여부**를 추가로 확인해야 하기 때문입니다.

#### 4) 핵심 한계
- 특허 수 자체가 곧바로 매출 성장이나 주가 상승을 의미하지는 않습니다.
- 기술 우위가 가치평가 가산 요인이 되려면 양산·수주·매출 전환 근거가 함께 필요합니다.
- 최종 판단에서는 기술성보다 수익성, 현금흐름, 재무 안정성과의 연결 여부를 우선 확인해야 합니다.
"""

pattern = r"### 기술 분석\s*.*?(?=\n### 이슈 분석|\n### 거시경제|\n## 5\.|\Z)"
patched = re.sub(pattern, new_section, report, count=1, flags=re.DOTALL)

patched = patched.replace(
    '**재무 분석:** Tech-to-Value Bridge Score: 64.0/100, 판정=TECH_FINANCE_GAP.',
    '**기술-가치 연결 검증:** Tech-to-Value Bridge Score: 64.0/100, 판정=TECH_FINANCE_GAP.'
)

patched = re.sub(r'\]\((https?://[^)\s"]+)"\)', r'](\1)', patched)

REPORT.write_text(patched, encoding="utf-8")
print("[완료] Chair 보고서 기술 분석 섹션 고도화 반영:", REPORT)
