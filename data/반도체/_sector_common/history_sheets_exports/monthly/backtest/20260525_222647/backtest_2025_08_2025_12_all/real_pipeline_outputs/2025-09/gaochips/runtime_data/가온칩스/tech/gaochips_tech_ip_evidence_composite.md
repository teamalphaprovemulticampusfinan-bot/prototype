# 가온칩스 IP Evidence Composite Score

## 1. Summary
- status: OK
- ip_evidence_composite_score: 69.78
- ip_evidence_data_coverage_rate: 1.0
- bridge_adjustment_points: 1.0
- bridge_signal: IP_EVIDENCE_POSITIVE

## 2. Component Scores

| Component | Korean Label | Weight | Score | Contribution | Source Status | Bridge Signal |
|---|---:|---:|---:|---:|---|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 95.0 | 23.75 | OK | IP_LEGAL_STABILITY_STRONG_POSITIVE |
| claim_defense | 청구항 방어 범위 | 0.3 | 79.25 | 23.77 | OK | IP_CLAIM_SCOPE_POSITIVE |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 45.0 | 11.25 | OK | IP_CITATION_FALLBACK_ESTIMATED |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 55.0 | 11.0 | OK | IP_FAMILY_FALLBACK_ESTIMATED |

## 3. Formula

IP Evidence Composite Score = legal_stability*0.25 + claim_defense*0.30 + citation_influence*0.25 + global_extension*0.20. If a component score is missing, the score is normalized by available weight.

## 4. Tech-to-Value Bridge

- bridge_adjustment_points: 1.0
- bridge_signal: IP_EVIDENCE_POSITIVE
- usage_rule: Use this composite IP evidence score as the integrated IP-quality layer in Tech-to-Value Bridge. It summarizes legal stability, claim scope defense, citation influence, and global family expansion. It is not direct revenue evidence and should be combined with finance, market, and commercialization signals.

## 5. Strengths
- IP 증거의 종합 강도가 양호하여 특허 포트폴리오의 질적 근거로 활용할 수 있습니다.

## 6. Cautions
- 별도 유의사항 없음
