# Company-level KMeans Tech Peer Group Report

## 1. 분석 개요
- 생성 시각: 2026-05-07T22:04:39
- 입력 universe: `data\반도체\_sector_common\ml_universe\deeptech_reference_universe.csv`
- 분석 기업 수: **30개**
- 방법: **Company-level TF-IDF/LSA + KMeans**
- 임베딩: **TF-IDF + TruncatedSVD(20) + Normalizer**
- 선택 K: **7개**
- Silhouette Score: **0.807701**
- TF-IDF 피처 수: **5000개**
- 해석: 이 cluster는 재무/주가 cluster가 아니라 특허·기술 텍스트와 reference universe 메타데이터 기반 기술 peer group입니다.

## 2. K 후보별 Silhouette 진단
| K | Silhouette Score | 비고 |
|---:|---:|---|
| 2 | 0.233057 | - |
| 3 | 0.353971 | - |
| 4 | 0.483069 | - |
| 5 | 0.609113 | - |
| 6 | 0.718984 | - |
| 7 | 0.807701 | - |
| 8 | 0.79707 | - |

## 3. Cluster Summary
| Cluster | 이름 | 기업 수 | Focal | Reference | 주요 분야 | 핵심 용어 | 해석 |
|---:|---|---:|---:|---:|---|---|---|
| 0 | 반도체 장비/본딩·검사 cluster | 4 | 0 | 4 | 장비 | 장비 장비, 장비, attractive, low_risk, attractive low_risk, credit_risk_score_0.0, low_risk attractive, human_review attractive | 반도체 장비/본딩·검사 cluster로 분류된 4개 기업의 특허/기술 텍스트 기반 peer group입니다. 현재 focal 기업은 없지만 reference universe의 기술 분포를 형성하는 보조 cluster입니다. |
| 1 | 반도체 후공정/패키징 cluster | 4 | 0 | 4 | 후공정/패키징/테스트 | 후공정/패키징/테스트, 후공정/패키징/테스트 후공정/패키징/테스트, low_risk, low_risk high, attractive, attractive low_risk, valuation attractive, low_risk attractive | 반도체 후공정/패키징 cluster로 분류된 4개 기업의 특허/기술 텍스트 기반 peer group입니다. 현재 focal 기업은 없지만 reference universe의 기술 분포를 형성하는 보조 cluster입니다. |
| 2 | 반도체 소재/전자재료 cluster | 4 | 0 | 4 | 소재 | 소재, 소재 소재, low_risk, attractive, attractive low_risk, credit_risk_score_0.0, attractive credit, valuation attractive | 반도체 소재/전자재료 cluster로 분류된 4개 기업의 특허/기술 텍스트 기반 peer group입니다. 현재 focal 기업은 없지만 reference universe의 기술 분포를 형성하는 보조 cluster입니다. |
| 3 | 기술 포트폴리오 혼합 cluster | 4 | 0 | 4 | IDM/제조/메모리 | idm/제조/메모리, idm/제조/메모리 idm/제조/메모리, attractive, low_risk, attractive low_risk, valuation attractive, low_risk attractive, human_review attractive | 기술 포트폴리오 혼합 cluster로 분류된 4개 기업의 특허/기술 텍스트 기반 peer group입니다. 현재 focal 기업은 없지만 reference universe의 기술 분포를 형성하는 보조 cluster입니다. |
| 4 | 기술 포트폴리오 혼합 cluster | 4 | 0 | 4 | 팹리스/설계 | 팹리스/설계, 팹리스/설계 팹리스/설계, attractive, low_risk, attractive low_risk, credit_risk_score_0.0, attractive credit, valuation attractive | 기술 포트폴리오 혼합 cluster로 분류된 4개 기업의 특허/기술 텍스트 기반 peer group입니다. 현재 focal 기업은 없지만 reference universe의 기술 분포를 형성하는 보조 cluster입니다. |
| 5 | 기술 포트폴리오 혼합 cluster | 5 | 0 | 5 | 부품/기판, 부품/웨이퍼캐리어 | 부품/기판, 부품/기판 부품/기판, valuation/credit ml, valuation/credit, fair, fair low_risk, low_risk, high high | 기술 포트폴리오 혼합 cluster로 분류된 5개 기업의 특허/기술 텍스트 기반 peer group입니다. 현재 focal 기업은 없지만 reference universe의 기술 분포를 형성하는 보조 cluster입니다. |
| 6 | 반도체 후공정/패키징 cluster | 5 | 5 | 0 | 소재, 후공정/패키징/테스트 | 있다, 있는, 반도체, 조성물, 제1, 패키지, 반도체 패키지, 한솔케미칼 | 반도체 후공정/패키징 cluster로 분류된 5개 기업의 특허/기술 텍스트 기반 peer group입니다. 현재 focal 기업 5개가 포함되어 Chair 기술 판단의 비교 기준으로 활용할 수 있습니다. |

## 4. Company Assignments
| 기업 | 티커 | 분야 | Cluster | Cluster 이름 | 중심거리 | 선택점수 | 역할 |
|---|---|---|---:|---|---:|---:|---|
| 한솔케미칼 | 014680 | 소재 | 6 | 반도체 후공정/패키징 cluster | 0.74441 | 1100.2721 | FOCAL_REPORT_TARGET |
| 엘티씨 | 170920 | 소재 | 6 | 반도체 후공정/패키징 cluster | 0.67768 | 1090.7717 | FOCAL_REPORT_TARGET |
| 네패스 | 033640 | 후공정/패키징/테스트 | 6 | 반도체 후공정/패키징 cluster | 0.701323 | 1082.296 | FOCAL_REPORT_TARGET |
| 한미반도체 | 042700 | 후공정/패키징/테스트 | 6 | 반도체 후공정/패키징 cluster | 0.70034 | 1071.7905 | FOCAL_REPORT_TARGET |
| 덕산테코피아 | 317330 | 소재 | 6 | 반도체 후공정/패키징 cluster | 0.789461 | 1026.9482 | FOCAL_REPORT_TARGET |
| 월덱스 | 101160 | 소재 | 2 | 반도체 소재/전자재료 cluster | 0.080752 | 105.8433 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 메카로 | 241770 | IDM/제조/메모리 | 3 | 기술 포트폴리오 혼합 cluster | 0.021379 | 104.6945 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| LX세미콘 | 108320 | 팹리스/설계 | 4 | 기술 포트폴리오 혼합 cluster | 0.0 | 104.1154 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 비아트론 | 141000 | 장비 | 0 | 반도체 장비/본딩·검사 cluster | 0.0 | 104.0061 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 아이앤씨 | 052860 | 팹리스/설계 | 4 | 기술 포트폴리오 혼합 cluster | 0.0 | 103.9195 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 성우테크론 | 045300 | 후공정/패키징/테스트 | 1 | 반도체 후공정/패키징 cluster | 0.078854 | 103.7292 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 이엔에프테크놀로지 | 102710 | 소재 | 2 | 반도체 소재/전자재료 cluster | 0.080752 | 102.8683 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| DB하이텍 | 000990 | IDM/제조/메모리 | 3 | 기술 포트폴리오 혼합 cluster | 0.021379 | 102.7644 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 케이씨 | 029460 | 장비 | 0 | 반도체 장비/본딩·검사 cluster | 0.0 | 102.703 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| KPX케미칼 | 025000 | 장비 | 0 | 반도체 장비/본딩·검사 cluster | 0.0 | 102.5372 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 매커스 | 093520 | 팹리스/설계 | 4 | 기술 포트폴리오 혼합 cluster | 0.0 | 102.2068 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| GST | 083450 | 장비 | 0 | 반도체 장비/본딩·검사 cluster | 0.0 | 102.0405 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 링크제니시스 | 219420 | 후공정/패키징/테스트 | 1 | 반도체 후공정/패키징 cluster | 0.078854 | 101.6276 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 엘디티 | 096870 | IDM/제조/메모리 | 3 | 기술 포트폴리오 혼합 cluster | 0.021379 | 100.8588 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 프로텍 | 053610 | 후공정/패키징/테스트 | 1 | 반도체 후공정/패키징 cluster | 0.236562 | 98.1146 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 한양디지텍 | 078350 | IDM/제조/메모리 | 3 | 기술 포트폴리오 혼합 cluster | 0.021379 | 98.058 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 티에스이 | 131290 | 팹리스/설계 | 4 | 기술 포트폴리오 혼합 cluster | 0.0 | 97.2329 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 프로이천 | 321260 | 후공정/패키징/테스트 | 1 | 반도체 후공정/패키징 cluster | 0.078854 | 97.1758 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 원익머트리얼즈 | 104830 | 소재 | 2 | 반도체 소재/전자재료 cluster | 0.23893 | 96.2459 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 인터플렉스 | 051370 | 부품/기판 | 5 | 기술 포트폴리오 혼합 cluster | 0.076124 | 96.2323 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 솔브레인홀딩스 | 036830 | 소재 | 2 | 반도체 소재/전자재료 cluster | 0.090465 | 95.5907 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 자화전자 | 033240 | 부품/기판 | 5 | 기술 포트폴리오 혼합 cluster | 0.076124 | 94.292 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 비에이치 | 090460 | 부품/기판 | 5 | 기술 포트폴리오 혼합 cluster | 0.086158 | 87.4992 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 이수페타시스 | 007660 | 부품/기판 | 5 | 기술 포트폴리오 혼합 cluster | 0.086158 | 86.8099 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |
| 3S | 060310 | 부품/웨이퍼캐리어 | 5 | 기술 포트폴리오 혼합 cluster | 0.293568 | 47.3145 | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML |

## 5. Focal 기업별 같은 Cluster 내 nearest peer
| Focal 기업 | Cluster | 가까운 peer |
|---|---|---|
| 한솔케미칼 | 6 | 엘티씨(49.49%); 덕산테코피아(28.84%); 한미반도체(26.18%); 네패스(26.0%) |
| 엘티씨 | 6 | 한솔케미칼(49.49%); 한미반도체(37.22%); 네패스(35.57%); 덕산테코피아(31.95%) |
| 네패스 | 6 | 한미반도체(57.55%); 엘티씨(35.57%); 덕산테코피아(26.97%); 한솔케미칼(26.0%) |
| 한미반도체 | 6 | 네패스(57.55%); 엘티씨(37.22%); 한솔케미칼(26.18%); 덕산테코피아(25.47%) |
| 덕산테코피아 | 6 | 엘티씨(31.95%); 한솔케미칼(28.84%); 네패스(26.97%); 한미반도체(25.47%) |

## 6. 활용 원칙
- 이 결과는 30개 reference universe를 기술 텍스트 기준으로 재분류한 peer group입니다.
- Chair에서는 같은 cluster 내 peer를 기술 비교 기준으로 사용하되, 재무·시장·현금흐름 판단과 혼동하지 않습니다.
- 개별 company 폴더가 없는 reference 기업은 universe CSV 메타데이터만 사용하므로, KIPRIS 원천 특허가 추가될수록 cluster 품질이 개선됩니다.
- 5단계에서는 이 결과를 UMAP 2D peer map으로 시각화하면 발표자료에서 ML 활용도가 더 잘 보입니다.
