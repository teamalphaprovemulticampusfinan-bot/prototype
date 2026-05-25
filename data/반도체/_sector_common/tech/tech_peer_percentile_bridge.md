# Tech Peer Percentile Bridge Correction

- 목적: 30개 reference universe와 focal 5개 기업의 상대적 기술/IP 위치를 이용해 Tech-to-Value Bridge 점수를 보정합니다.
- 주의: 이 보정은 미래 수익률 예측이나 투자성과 검증이 아니라, 기술 포트폴리오의 peer-relative strength를 Chair에 반영하기 위한 보조 ML 신호입니다.

| 기업 | Cluster | Base Bridge | Peer Percentile | 보정점 | Peer-adjusted Bridge | 판정 | 해석 |
|---|---|---:|---:|---:|---:|---|---|
| 한솔케미칼 | 반도체 후공정/패키징 cluster | 73.00 | 80.58 | +4.89 | 77.89 | COMMERCIALIZATION_WATCH | peer 상위권 |
| 엘티씨 | 반도체 후공정/패키징 cluster | 64.00 | 76.17 | +4.19 | 68.19 | TECH_FINANCE_GAP | peer 중상위권 |
| 네패스 | 반도체 후공정/패키징 cluster | 77.00 | 72.08 | +3.53 | 80.53 | COMMERCIALIZATION_WATCH | peer 중상위권 |
| 한미반도체 | 반도체 후공정/패키징 cluster | 84.00 | 70.81 | +3.33 | 87.33 | VALUE_CONVERSION_CONFIRMED | peer 중상위권 |
| 덕산테코피아 | 반도체 후공정/패키징 cluster | 80.00 | 59.23 | +1.48 | 81.48 | COMMERCIALIZATION_WATCH | peer 중위권 |

## 보정 방식

1. universe percentile: selection_score, patent_rows, document_chars, distance_to_centroid를 30개 reference universe 안에서 백분위로 환산합니다.
2. same-cluster/sector/focal percentile: 같은 cluster, 같은 sector, focal 5개 안에서 보조 백분위를 계산합니다.
3. nearest similarity와 cluster density를 보조 신호로 반영합니다.
4. composite percentile 50을 중립점으로 하여 최대 +8점, -10점 범위에서 Bridge 점수를 보정합니다.
5. COMMERCIALIZATION_WATCH 또는 TECH_FINANCE_GAP 상태에서는 고객 채택·양산·매출·FCF 근거가 확인되기 전까지 보수 cap을 적용합니다.