# UMAP 2D Tech Peer Map

## 1. 생성 요약
- 생성 시각: 2026-05-07T22:05:59
- 입력 universe: `data\반도체\_sector_common\ml_universe\deeptech_reference_universe.csv`
- 입력 cluster: `data\반도체\_sector_common\ml_universe\tech_peer_clusters.json`
- 분석 기업 수: **30개**
- 차원축소 방법: **UMAP**
- UMAP 사용 여부: **True**
- 벡터화/임베딩: **TF-IDF + TruncatedSVD(20) + Normalizer**
- TF-IDF 피처 수: **5000개**
- PNG 저장: `data\반도체\_sector_common\ml_universe\tech_peer_map.png`

## 2. Cluster별 2D Map 요약
| Cluster | 기업 수 | Focal | Reference | 중심 X | 중심 Y | 주요 분야 | 핵심 용어 |
|---|---:|---:|---:|---:|---:|---|---|
| 0 | 4 | 0 | 4 | 12.54356408 | 14.55258441 | 장비 | 장비 장비, 장비, attractive, low_risk, ok, attractive low_risk, reference, high |
| 1 | 4 | 0 | 4 | 18.25505209 | 2.17014173 | 후공정/패키징/테스트 | 후공정/패키징/테스트, 후공정/패키징/테스트 후공정/패키징/테스트, low_risk, ok, reference, high, attractive, attractive low_risk |
| 2 | 4 | 0 | 4 | 1.17263071 | 7.72817468 | 소재 | 소재, 소재 소재, low_risk, ok, reference, attractive, attractive low_risk, high |
| 3 | 4 | 0 | 4 | -14.00861979 | 8.45804596 | IDM/제조/메모리 | idm/제조/메모리, idm/제조/메모리 idm/제조/메모리, attractive, low_risk, ok, attractive low_risk, high, reference |
| 4 | 4 | 0 | 4 | 12.95131278 | 15.7352798 | 팹리스/설계 | 팹리스/설계, 팹리스/설계 팹리스/설계, attractive, low_risk, ok, attractive low_risk, high, reference |
| 5 | 5 | 0 | 5 | 11.93568401 | 13.39549332 | 부품/기판, 부품/웨이퍼캐리어 | 부품/기판, 부품/기판 부품/기판, ok, reference, fair, fair low_risk, low_risk, high |
| 6 | 5 | 5 | 0 | 18.90498085 | 13.26858082 | 소재, 후공정/패키징/테스트 | 상기, 발명은, 포함하는, 주식회사, 관한, 반도체, 이를, 있다 |

## 3. Focal 기업 좌표
| 기업 | 티커 | Cluster | X | Y | 같은 기술군 해석 |
|---|---|---|---:|---:|---|
| 한솔케미칼 | 014680 | 6 | 18.67626953 | 13.19345951 | 소재 / 소재 |
| 엘티씨 | 170920 | 6 | 19.11967468 | 13.13209057 | 소재 / 소재 |
| 네패스 | 033640 | 6 | 18.77897453 | 13.53509045 | 후공정/패키징/테스트 / 후공정/패키징/테스트 |
| 한미반도체 | 042700 | 6 | 18.70637512 | 13.00663567 | 후공정/패키징/테스트 / 후공정/패키징/테스트 |
| 덕산테코피아 | 317330 | 6 | 19.24361038 | 13.4756279 | 소재 / 소재 |

## 4. 활용 원칙
- 이 지도는 투자 추천 지도가 아니라 특허/기술 텍스트 기반 peer map입니다.
- 가까울수록 기술 텍스트 포트폴리오가 유사하다는 의미이며, 재무 안정성이나 주가 방향을 직접 의미하지 않습니다.
- 발표에서는 focal 기업이 reference universe 안에서 어느 기술군에 놓이는지 보여주는 ML 시각화 근거로 사용합니다.
- Chair 보고서에는 이 결과를 기술 peer 위치 근거로만 반영하고, 최종 추천은 재무·시장·현금흐름 근거와 함께 판단합니다.
