from __future__ import annotations

import argparse
import sys
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from tech_agent.chair_section import inject_compact_tech_section
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "tech_agent.chair_section에서 inject_compact_tech_section을 import하지 못했습니다. "
        "src/tech_agent/chair_section.py 파일이 있는지 확인하세요."
    ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test compact Tech section injection without running full Chair."
    )
    parser.add_argument("--company-dir", default="nepes", help="company slug, e.g. nepes")
    parser.add_argument("--company", default="네패스", help="display company name")
    args = parser.parse_args()

    report = f"""# {args.company} 종합 투자 보고서

## 4. 하위 에이전트 의견 요약

### 재무 분석
- **의견:** 보유
- 테스트용 재무 분석 본문입니다.

### 시장 분석
- **의견:** 보유
- 테스트용 시장 분석 본문입니다.

### 기술 분석
- **의견:** 보유
- 테스트용 기존 기술 분석 본문입니다.
- 이 문단은 compact Tech summary로 교체되어야 합니다.

### 이슈 분석
- **의견:** 보유
- 테스트용 이슈 분석 본문입니다.

### 거시경제
- **의견:** 매도
- 테스트용 거시경제 본문입니다.

## 5. 충돌 지점 및 해석
- 테스트입니다.
"""

    updated = inject_compact_tech_section(
        report,
        opinions=None,
        company_dir=args.company_dir,
        company=args.company,
    )

    out = field_agent_dir("tech") / f"{args.company_dir}_chair_compact_tech_test.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(updated, encoding="utf-8")

    compact_included = (
        "Tech Peer ML 통합 보정" in updated
        or "선택 ML 신호 요약" in updated
        or "Tech-to-Value" in updated
        or "Technology Differentiation" in updated
        or "상세 부록" in updated
    )
    old_text_removed = "테스트용 기존 기술 분석 본문" not in updated
    long_detail_not_forced = "#### 10) Technology Differentiation Score" not in updated

    print(f"COMPACT_INCLUDED: {compact_included}")
    print(f"OLD_TECH_TEXT_REMOVED: {old_text_removed}")
    print(f"LONG_DETAIL_NOT_FORCED: {long_detail_not_forced}")
    print(f"RESULT_FILE: {out}")
    print("RESULT:", "PASS" if compact_included and old_text_removed and long_detail_not_forced else "CHECK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
