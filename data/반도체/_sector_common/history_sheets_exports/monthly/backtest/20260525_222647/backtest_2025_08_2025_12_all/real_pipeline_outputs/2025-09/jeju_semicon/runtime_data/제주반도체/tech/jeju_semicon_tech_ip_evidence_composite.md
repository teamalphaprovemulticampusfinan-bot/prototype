# 제주반도체 IP Evidence Composite Score

## 1. Summary
- status: OK
- ip_evidence_composite_score: 35.9
- ip_evidence_data_coverage_rate: 1.0
- bridge_adjustment_points: -1.0
- bridge_signal: IP_EVIDENCE_WEAK

## 2. Component Scores

| Component | Korean Label | Weight | Score | Contribution | Source Status | Bridge Signal |
|---|---:|---:|---:|---:|---|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 39.48 | 9.87 | OK | IP_LEGAL_STABILITY_WEAK |
| claim_defense | 청구항 방어 범위 | 0.3 | 54.35 | 16.3 | OK | IP_CLAIM_SCOPE_NEUTRAL |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 25.0 | 6.25 | OK | IP_CITATION_FALLBACK_ESTIMATED |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 17.38 | 3.48 | OK | IP_GLOBAL_EXTENSION_WEAK |

## 3. Formula

IP Evidence Composite Score = legal_stability*0.25 + claim_defense*0.30 + citation_influence*0.25 + global_extension*0.20. If a component score is missing, the score is normalized by available weight.

## 4. Tech-to-Value Bridge

- bridge_adjustment_points: -1.0
- bridge_signal: IP_EVIDENCE_WEAK
- usage_rule: Use this composite IP evidence score as the integrated IP-quality layer in Tech-to-Value Bridge. It summarizes legal stability, claim scope defense, citation influence, and global family expansion. It is not direct revenue evidence and should be combined with finance, market, and commercialization signals.

## 5. Strengths
- 별도 강점 문구 없음

## 6. Cautions
- IP 증거 강도가 낮아 Tech-to-Value Bridge에서 보수적 해석이 필요합니다.
