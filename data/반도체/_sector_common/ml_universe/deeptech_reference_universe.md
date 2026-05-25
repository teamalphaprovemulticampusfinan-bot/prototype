# Reference Universe from Valuation/Credit ML Overlay

## 1. 생성 요약
- 원천 CSV: `data\반도체\_sector_common\ml_universe\valuation_credit_ml_overlay_candidate.csv`
- 원천 후보 수: **208개**
- 선택 기업 수: **30개**
- 현재 focal 기업 수: **5개**
- reference peer 전용 기업 수: **25개**
- 현재 Chair 직접 실행 대상: **5개**

## 2. 분야별 요약
| 분야 | 선택 수 | Focal | Reference | 검토 필요 | 평균 선택점수 |
|---|---:|---:|---:|---:|---:|
| 소재 | 7 | 3 | 4 | 1 | 516.9343 |
| 후공정/패키징/테스트 | 6 | 2 | 4 | 1 | 425.789 |
| IDM/제조/메모리 | 4 | 0 | 4 | 0 | 101.5939 |
| 팹리스/설계 | 4 | 0 | 4 | 0 | 101.8687 |
| 장비 | 4 | 0 | 4 | 0 | 102.8217 |
| 부품/기판 | 4 | 0 | 4 | 0 | 91.2083 |
| 부품/웨이퍼캐리어 | 1 | 0 | 1 | 0 | 47.3145 |

## 3. 선택 Universe
| 순위 | 분야 | 기업 | 티커 | 시장 | 역할 | 선택점수 | 가치라벨 | 신용라벨 | 검토 |
|---:|---|---|---|---|---|---:|---|---|---|
| 1 | 소재 | 한솔케미칼 | 014680 | KOSPI | FOCAL_REPORT_TARGET | 1100.2721 | ATTRACTIVE | LOW_RISK | OK |
| 2 | 소재 | 엘티씨 | 170920 | KOSDAQ | FOCAL_REPORT_TARGET | 1090.7717 | FAIR | LOW_RISK | OK |
| 3 | 후공정/패키징/테스트 | 네패스 | 033640 | KOSDAQ | FOCAL_REPORT_TARGET | 1082.2960 | ATTRACTIVE | MEDIUM_RISK | OK |
| 4 | 후공정/패키징/테스트 | 한미반도체 | 042700 | KOSPI | FOCAL_REPORT_TARGET | 1071.7905 | FAIR | LOW_RISK | AUDITOR_REVIEW;CREDIT_ANOMALY_TOP15PCT |
| 5 | 소재 | 덕산테코피아 | 317330 | KOSDAQ | FOCAL_REPORT_TARGET | 1026.9482 | EXPENSIVE | HIGH_RISK | AUDITOR_REVIEW;CREDIT_ANOMALY_TOP15PCT |
| 6 | 소재 | 월덱스 | 101160 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 105.8433 | ATTRACTIVE | LOW_RISK | OK |
| 7 | IDM/제조/메모리 | 메카로 | 241770 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 104.6945 | ATTRACTIVE | LOW_RISK | OK |
| 8 | 팹리스/설계 | LX세미콘 | 108320 | KOSPI | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 104.1154 | ATTRACTIVE | LOW_RISK | OK |
| 9 | 장비 | 비아트론 | 141000 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 104.0061 | ATTRACTIVE | LOW_RISK | OK |
| 10 | 팹리스/설계 | 아이앤씨 | 052860 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 103.9195 | ATTRACTIVE | LOW_RISK | OK |
| 11 | 후공정/패키징/테스트 | 성우테크론 | 045300 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 103.7292 | ATTRACTIVE | LOW_RISK | OK |
| 12 | 소재 | 이엔에프테크놀로지 | 102710 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 102.8683 | ATTRACTIVE | LOW_RISK | OK |
| 13 | IDM/제조/메모리 | DB하이텍 | 000990 | KOSPI | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 102.7644 | ATTRACTIVE | LOW_RISK | OK |
| 14 | 장비 | 케이씨 | 029460 | KOSPI | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 102.7030 | ATTRACTIVE | LOW_RISK | OK |
| 15 | 장비 | KPX케미칼 | 025000 | KOSPI | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 102.5372 | ATTRACTIVE | LOW_RISK | OK |
| 16 | 팹리스/설계 | 매커스 | 093520 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 102.2068 | ATTRACTIVE | LOW_RISK | OK |
| 17 | 장비 | GST | 083450 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 102.0405 | ATTRACTIVE | LOW_RISK | OK |
| 18 | 후공정/패키징/테스트 | 링크제니시스 | 219420 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 101.6276 | ATTRACTIVE | LOW_RISK | OK |
| 19 | IDM/제조/메모리 | 엘디티 | 096870 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 100.8588 | ATTRACTIVE | LOW_RISK | OK |
| 20 | 후공정/패키징/테스트 | 프로텍 | 053610 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 98.1146 | FAIR | LOW_RISK | OK |
| 21 | IDM/제조/메모리 | 한양디지텍 | 078350 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 98.0580 | ATTRACTIVE | LOW_RISK | OK |
| 22 | 팹리스/설계 | 티에스이 | 131290 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 97.2329 | ATTRACTIVE | LOW_RISK | OK |
| 23 | 후공정/패키징/테스트 | 프로이천 | 321260 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 97.1758 | ATTRACTIVE | LOW_RISK | OK |
| 24 | 소재 | 원익머트리얼즈 | 104830 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 96.2459 | FAIR | LOW_RISK | OK |
| 25 | 부품/기판 | 인터플렉스 | 051370 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 96.2323 | FAIR | LOW_RISK | OK |
| 26 | 소재 | 솔브레인홀딩스 | 036830 | KOSDAQ GLOBAL | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 95.5907 | ATTRACTIVE | LOW_RISK | OK |
| 27 | 부품/기판 | 자화전자 | 033240 | KOSPI | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 94.2920 | FAIR | LOW_RISK | OK |
| 28 | 부품/기판 | 비에이치 | 090460 | KOSPI | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 87.4992 | FAIR | LOW_RISK | OK |
| 29 | 부품/기판 | 이수페타시스 | 007660 | KOSPI | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 86.8099 | FAIR | LOW_RISK | OK |
| 30 | 부품/웨이퍼캐리어 | 3S | 060310 | KOSDAQ | REFERENCE_PEER_FROM_VALUATION_CREDIT_ML | 47.3145 | EXPENSIVE | HIGH_RISK | OK |

## 4. 활용 원칙
- source CSV의 peer_group/semiconductor_tag를 sector_theme로 변환해 분야별 universe를 생성했습니다.
- selection_score는 valuation proxy, credit risk, confidence, data quality, auditor review flag를 함께 반영합니다.
- include_in_chair=1은 현재 5개 focal 기업만 의미합니다. 30개 전체 Chair 실행은 company.yaml 생성 단계 이후 확장합니다.
- include_in_chair=0인 기업은 개별 폴더 없이 reference peer clustering, cosine similarity, percentile 계산에 사용합니다.
