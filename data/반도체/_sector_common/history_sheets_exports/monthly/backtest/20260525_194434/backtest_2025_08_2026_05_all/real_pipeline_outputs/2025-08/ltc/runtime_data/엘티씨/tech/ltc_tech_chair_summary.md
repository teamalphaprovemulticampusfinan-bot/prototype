# 엘티씨 Tech Chair Compact Summary

## 1. Chair 반영용 핵심 판단
- **의견:** 매수
- **Tech-to-Value:** base 63.00/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **Peer-adjusted:** 84.00/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **IP Evidence Composite:** 50.96/100 / IP 근거 중립형(IP_EVIDENCE_NEUTRAL)
- **ML 우선 반영:** Technology Differentiation Score + Tech-to-Value Evidence Confidence + IP Evidence Composite Score
- **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다.
- **루브릭 원천:** `src/tech_agent/prompts.py`
- **최종 Tech 점수 정책:** 개인투자자용 최종 Tech 점수는 기술-사업화 연결 가능성, IP 품질, Excel/DART 정량 근거, 근거 신뢰도, 딥테크 성장투자 지속성을 하나로 합성한다.

## 2. Excel-frame 핵심 요약
| 대분류 | 항목 | 정량화 | 근거 | 등급 | 비고 |
|---|---|---|---|---|---|
| 대표 기술 | 대표 기술 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 핵심 제품/서비스 | 핵심 제품/서비스 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 고객 구매 이유 | 고객 구매 이유 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 경쟁 우위/대체가능성 | 경쟁 우위/대체가능성 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 활용 및 확장 산업 | 활용 및 확장 산업 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 진입 부담/장벽 | 진입 부담/장벽 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| R&D 강도 | R&D 강도 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |

## 3. 선택 ML/IP 요약
| ML/IP 신호 | 값 | Chair 해석 |
|---|---:|---|
| Technology Differentiation Score | 56.62/100 / 30.00%ile | peer 대비 기술/IP 포트폴리오 차별성 |
| Evidence Confidence | 78.80/100 | 고객 채택·양산·매출·FCF 근거의 직접성 |
| Patent Momentum | 61.93/100 | 최근 특허 활동의 현재성·지속성 |
| IP Legal Stability | 64.18/100 | 등록률·존속률·소멸/거절/취하 비중 기반 권리 안정성 |
| IP Claim Defense | 57.13/100 | 청구항 수·독립항 수·수집 커버리지 기반 특허 방어력 |
| IP Citation Impact | 확인 제한 | 피인용·외부인용 기반 기술 영향력/시장 참조 가치 |
| IP Global Extension | 43.32/100 | 해외 패밀리·PCT/WO·미국/일본/유럽/중국 확장성 |
| IP Evidence Composite | 50.96/100 | 법적 안정성·청구항·인용·패밀리 특허를 통합한 종합 IP 근거 점수 |
| IP Evidence Bridge Signal | IP_EVIDENCE_NEUTRAL / 0.00점 | Tech-to-Value Bridge 보수적 보정 신호 |
| Peer-adjusted Bridge | 84.00/100 | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 |

## 4. KIPRIS/IP 정량 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 10,749건 |
| 회사 출원인/권리자 매칭 | 7,502건 |
| 등록 특허 | 2,412건 |
| 존속 가능 특허 | 4,708건 |
| 최근 5년 특허 | 1,805건 |
| IPC/CPC 다양성 | 275개 |
| H01L 등 핵심 IPC 특허 | 6건 |
| KIPRIS 등록률(추정) | 66.40% |
| 등록특허 중 존속률(추정) | 70.83% |
| 소멸·거절·취하 등 부정 처분 비중(추정) | 44.27% |
| 권리자 정보 반영률 | 100.00% |
| 초록/도면 반영률 | 100.00% / 89.53% |
| 청구항 수집 커버리지 | 100.00% |
| 수집 청구항 / 독립항(추정) | 3,914항 / 943항 |
| 특허당 평균 청구항 / 독립항 비중 | 7.74항 / 24.09% |
| 피인용 총합 / 외부 피인용 | 확인 제한 / 확인 제한 |
| 외부 피인용률 | 확인 제한 |
| 해외 패밀리 보유율 | 28.46% |
| PCT/WO / US / JP / EP / CN | 109건 / 102건 / 57건 / 65건 / 85건 |

## 5. IP Evidence Composite 세부 구성
| 구성 요소 | Weight | Score | Contribution | Status |
|---|---:|---:|---:|---|
| 등록·존속 안정성 | 0.25 | 64.18/100 | 16.05점 | OK |
| 청구항 방어 범위 | 0.3 | 57.13/100 | 17.14점 | OK |
| 인용 기반 기술 영향력 | 0.25 | 36.46/100 | 9.12점 | OK |
| 해외 패밀리 기반 글로벌 확장성 | 0.2 | 43.32/100 | 8.66점 | OK |

## 6. 사업화 연결 체크
| 연결 항목 | 상태 | 점수 | 직접 | 간접 | 확인 제한 |
|---|---|---:|---:|---:|---:|
| 고객 채택 | 직접 근거 | 88.00/100 | 6건 | 36건 | 0건 |
| 양산 | 직접 근거 | 88.00/100 | 5건 | 42건 | 0건 |
| 매출 전환 | 직접 근거 | 88.00/100 | 8건 | 32건 | 0건 |
| FCF/현금흐름 | 간접 근거 | 42.00/100 | 0건 | 1건 | 0건 |

## 7. Chair 반영 원칙
- Chair 최종 보고서에는 Tech 상세 표 전체를 붙이지 않고 compact summary만 반영합니다.
- 상세 Excel-frame/ML 표는 Tech Agent 산출물과 부록 파일에서 확인합니다.
- 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다.
- IP Evidence Composite Score는 직접 매출 근거가 아니라 특허 포트폴리오의 질적 보조 신호로만 사용합니다.
- prompts.py 기준에 따라 R&D 투입, 특허/IP 산출, 고객·양산·매출 결과를 분리해 해석합니다.
- CB/BW·유상증자·정부과제·기술이전은 성장투자와 희석/오버행 리스크를 분리한 watch point로만 사용합니다.

## 8. prompts.py 루브릭 연동
- **최종 점수 설명:** 개인투자자용 최종 Tech 점수는 기술-사업화 연결 가능성, IP 품질, Excel/DART 정량 근거, 근거 신뢰도, 딥테크 성장투자 지속성을 하나로 합성한다.
- **가중치:** {'tech_to_value_bridge': 0.4, 'ip_evidence_composite': 0.2, 'excel_quantified_evidence': 0.15, 'evidence_confidence': 0.15, 'commercialization_and_funding_signal': 0.1}
- **판정 임계값:** {'INVESTOR_TECH_CONVICTION': 82, 'TECH_TO_VALUE_READY': 68, 'COMMERCIALIZATION_WATCH': 52, 'EVIDENCE_WEAK_OR_EARLY': 0}
- **적용 원칙:** 특허 수보다 기술-사업화-가치평가 연결성을 우선하고, API/파일 권한 제한은 데이터 품질로 분리합니다.

<!-- IP_EVIDENCE_COMPOSITE_START -->

#### IP Evidence Composite Score

KIPRIS 기반 IP Feature 4종을 통합해 특허 포트폴리오의 질적 근거를 평가했습니다. 이 점수는 특허 수량이 아니라 등록·존속 안정성, 청구항 방어 범위, 인용 기반 기술 영향력, 해외 패밀리 확장성을 종합한 Tech-to-Value Bridge 보조 지표입니다.

- IP Evidence Composite Score: **50.96 / 100**
- Data Coverage Rate: **1.0**
- Bridge Signal: **IP_EVIDENCE_NEUTRAL**
- Bridge Adjustment Points: **0.0**

| Component | 의미 | Weight | Score | Contribution | Status |
|---|---|---:|---:|---:|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 64.18 | 16.05 | OK |
| claim_defense | 청구항 방어 범위 | 0.3 | 57.13 | 17.14 | OK |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 36.46 | 9.12 | OK |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 43.32 | 8.66 | OK |

해석:
- 법적 안정성과 청구항 방어력은 IP 포트폴리오의 방어력을 보여줍니다.
- 인용 영향력과 글로벌 패밀리 확장성은 시장 내 참조 가치와 해외 권리 확장성을 보여줍니다.
- 본 지표는 직접적인 매출·수주 증거가 아니므로, 사업화·고객 채택·양산·FCF 개선 근거와 함께 해석해야 합니다.

<!-- IP_EVIDENCE_COMPOSITE_END -->

<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->
## IP Evidence Composite → Tech-to-Value Bridge 반영

- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.
- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points

- IP Evidence Composite Score: 50.96
- IP Evidence Bridge Signal: IP_EVIDENCE_NEUTRAL
- IP Evidence Adjustment Points: 0.0
- Peer-adjusted Score Before IP Evidence: 84.0
- Final Bridge Score After IP Evidence: 84.0
- Source: `C:/Agent_6.9/data/반도체/엘티씨/tech/tech_ip_evidence_composite.json`

해석:
- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.
- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.
<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->

<!-- TECH_INVESTOR_SCORECARD_START -->
## 개인투자자용 Tech 최종 점수판

- **대상 기업:** 엘티씨
- **최종 Tech 점수:** 76.29/100
- **최종 판정:** 기술의 가치전환 준비도는 높지만 일부 고객·매출·마진 근거는 추가 확인 필요 `TECH_TO_VALUE_READY`
- **해석 원칙:** 특허 수, 기술 키워드 수, 뉴스 수를 각각 따로 과장하지 않고, 사업화 연결 가능성과 근거 직접성을 하나의 최종 점수로 통합했습니다.

### 1) 최종 점수 구성
| 구성요소 | 점수 | 가중치 | 가중 반영 | 의미 |
|---|---:|---:|---:|---|
| Tech-to-Value Bridge | 84.00 | 0.40 | 33.60 | 기술이 고객 채택·양산·매출 전환으로 이어질 가능성 |
| IP Evidence Composite | 50.96 | 0.20 | 10.19 | 권리 안정성·청구항·인용·패밀리 기반 특허 품질 |
| Excel 기반 정량 근거 | 85.00 | 0.15 | 12.75 | 템플릿/수식 기준에 맞춰 실제 기업별 근거가 얼마나 채워졌는지 |
| 근거 직접성·충분성 | 82.00 | 0.15 | 12.30 | Chair가 개인투자자에게 설명할 수 있는 근거의 직접성 |
| 사업화·성장자금 지속성 | 74.50 | 0.10 | 7.45 | R&D·특허·정부과제·기술이전·CAPEX/희석성 자금조달이 사업화와 연결되는 정도 |

### 2) 핵심 해석
- 엘티씨의 개인투자자용 Tech 최종 점수는 76.29/100이며, 판정은 기술의 가치전환 준비도는 높지만 일부 고객·매출·마진 근거는 추가 확인 필요입니다.
- 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(84.0)와 IP Evidence(50.96) 및 Excel 기반 정량 근거(85.0)를 함께 반영했습니다.
- 투자자가 확인할 핵심 근거는 9개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다.

### 3) 개인투자자가 확인할 근거
| ID | 출처 | 근거 | 값 | 강도 |
|---|---|---|---:|---|
| tech.inv.ev.001 | tech_to_value | **최종 Tech-to-Value Bridge**: 엘티씨의 최종 기술-사업화 연결 점수는 84.0이며, Chair에는 기술성보다 고객 채택·양산·매출 전환 가능성을 우선 반영합니다. | 84.0점 | 상 |
| tech.inv.ev.002 | kipris_ip_evidence | **IP Evidence Composite**: 법적 안정성·청구항 방어력·인용 영향력·해외 패밀리 확장성을 합성한 IP Evidence Composite Score는 50.96입니다. | 50.96점 | 상 |
| tech.inv.ev.003 | kipris_legal | **권리 안정성**: 등록률 0.664, 존속률 0.7083, 권리 안정성 점수 64.18를 확인했습니다. | 64.18점 | 중 |
| tech.inv.ev.004 | kipris_claim | **청구항 방어력**: 청구항 수 3914, 독립항 추정 943, claim defense score 57.13입니다. | 57.13점 | 중 |
| tech.inv.ev.005 | kipris_citation | **인용 영향력**: 전방/후방 인용 및 기술 영향력 점수 기준 IP_CITATION_FALLBACK_ESTIMATED입니다. | - | 중 |
| tech.inv.ev.006 | kipris_family | **글로벌 패밀리 확장성**: 해외 패밀리 비중 0.2846, 감지 지역 ['CN', 'EP', 'JP', 'US', 'WO'], global extension score 43.32입니다. | 43.32점 | 중 |
| tech.inv.ev.007 | tech_summary | **Tech Agent 핵심 해석**: 엘티씨의 개인투자자용 Tech 최종 점수는 76.29/100이며, 판정은 기술의 가치전환 준비도는 높지만 일부 고객·매출·마진 근거는 추가 확인 필요입니다. | - | 중 |
| tech.inv.ev.008 | tech_summary | **Tech Agent 핵심 해석**: 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(84.0)와 IP Evidence(50.96) 및 Excel 기반 정량 근거(85.0)를 함께 반영했습니다. | - | 중 |
| tech.inv.ev.009 | tech_summary | **Tech Agent 핵심 해석**: 투자자가 확인할 핵심 근거는 6개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다. | - | 중 |

### 4) 한계와 보완 필요사항
- 이 점수는 투자수익률 예측값이 아니라 기술-사업화 근거의 설명 가능성 점수입니다.
- KIPRIS Plus 유료 endpoint 접근 권한 또는 호출 제한으로 일부 청구항·패밀리·인용 데이터가 부족하면 보수적으로 반영합니다.
- Excel 템플릿 값은 복사 근거가 아니라 정량화 프레임이며, 실제 기업별 자료가 채워진 항목만 점수화합니다.
- CB/BW·유상증자·정부과제·기술이전 신호는 성장자금과 희석/오버행 리스크를 분리해 보조 레이어로만 해석합니다.
- R&D 비용은 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진은 commercial outcome으로 구분합니다.
<!-- TECH_INVESTOR_SCORECARD_END -->

<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->
# 엘티씨 Tech Intake Value Evidence Bridge

## 1. 요약
- 생성 시각: 2026-05-25T20:12:15
- 종합 점수: 79.89/100
- 종합 라벨: VALUE_EVIDENCE_STRONG
- 원천 문서 수: 168개

## 2. 기술 → 사업화 → 재무 연결 근거
| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |
|---|---|---:|---:|---:|---:|---|
| 고객 채택 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 고객 채택 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 양산 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 양산 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 매출 전환 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 매출 전환 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| IP 품질 | 직접 근거 확인 | 50.96 | 3 | 0 | 1 | KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. 특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다. |
| 마진·원가·현금흐름 연결 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 마진·원가·현금흐름 연결 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |

## 3. 대표 근거

### 고객 채택
- [DIRECT_EVIDENCE] 회사의 재무제표는 한국채택국제회계기준(이하 기업회계기준)에 따라 작성됐습니다.한국채택국제회계기준은 국제회계기준위원회("IASB")가 발표한 기준서와 해석서 중대한민국이 채택한 내용을 의미합니다. (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 한국채택국제회계기준은 재무제표 작성 시 중요한 회계추정의 사용을 허용하고 있으며, 회계정책을 적용함에 있어 경영진의 판단을 요구하고 있습니다. (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=채택, 적용, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 2.2.1 회사가 채택한 제ㆍ개정 기준서 및 해석서 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] (1) 기업회계기준서 제1021호 ‘환율변동효과’와 기업회계기준서 제1101호 ‘한국채택국제회계기준의 최초채택’ 개정 - 교환가능성 결여 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] (2) 한국채택국제회계기준 연차개선Volume 11 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### 양산
- [DIRECT_EVIDENCE] - **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. (source=data/반도체/엘티씨/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다. (source=data/반도체/엘티씨/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 | (source=data/반도체/엘티씨/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | 양산 | 직접 근거 | 88.00/100 | 17건 | 63건 | 0건 | (source=data/반도체/엘티씨/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/엘티씨/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 매출 전환
- [DIRECT_EVIDENCE] ㆍ회사의 손상평가 절차에 대한 통제 이해 및 설계, 운영의 효과성 평가ㆍ비금융자산 손상을 시사하는 징후가 존재하는지에 대한 판단 근거 검토ㆍ회수가능액의 측정을 위하여 경영진이 활용한 외부 전문가의 적격성 및 독립성 평가ㆍ경영진이 회수가능액 측정에 사용한 가치평가모델의 적정성 평가ㆍ가치평가전문가를 활용하여 경영진의 회수가능액 측정시 사용한 사업계획 및 과거 실적 비교를 통해 추정 매출성장률의 합리성 평가ㆍ투자자산의 손상평가에 사용한 할인율과 관측가능한 정보로 재계산한 할인율과의 비교를 통해 적용된 할인율의 적정성 평가ㆍ주요 가정의 변경이 회수가능액에 미치는 영향을 평가하기 위해 경영진이 수행한 할인율에 대한 민감도 분석결과 평가 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=매출, 성장, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 단, 매출채권 및 리스채권에 대해 회사는 채권의 최초 인식시점부터 전체기간 기대신용손실을 인식하는 간편법을 적용합니다(회사가 신용위험이 유의적으로 증가하였는지를 결정하는 방법은 주석 30 참조). (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 2.7 매출채권 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 매출채권은 유의적인 금융요소를 포함하지 않는 경우에는 무조건적인 대가의 금액으로, 유의적인 금융요소를 포함하는 경우에는 공정가치로 최초 인식합니다. (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 매출채권은 후속적으로 유효이자율법을 적용한 상각후원가에 손실충당금을 차감하여 측정됩니다(회사의 매출채권 회계처리에 대한 추가적인 사항은 주석 6, 손상에 대한 회계정책은 주석 2.5(3) 참조). (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### 마진·원가·현금흐름 연결
- [DIRECT_EVIDENCE] 영업활동으로 인한 현금흐름 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 투자활동으로 인한 현금흐름 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 재무활동으로 인한 현금흐름 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] ·계약상 현금흐름의 시기나 금액을 변경시키는 계약조건이 기업에 미치는 영향과 기업이 노출되는 정도를 금융상품의 각 종류별로 공시 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] ·기업회계기준서 제1007호‘현금흐름표’: 원가법 (source=data/반도체/엘티씨/tech/source/dart_latest_business_report.txt, keywords=현금흐름, 원가, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### IP 품질
- [DIRECT_EVIDENCE] legal_status: status=COLLECTED, count=None, score=0.664, signal=None (source=data/반도체/엘티씨/tech/ltc_tech_ip_legal_features.json, keywords=legal_status, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] claims: status=COLLECTED, count=3914.0, score=None, signal=None (source=data/반도체/엘티씨/tech/ltc_tech_ip_claim_features.json, keywords=claims, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [PARTIAL_EVIDENCE] citations: status=NO_CITATION_COLLECTED, count=0, score=None, signal=None (source=data/반도체/엘티씨/tech/ltc_tech_ip_citation_features.json, keywords=citations, NO_CITATION_COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] family: status=COLLECTED, count=109.0, score=None, signal=None (source=data/반도체/엘티씨/tech/ltc_tech_ip_family_features.json, keywords=family, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] composite: status=COLLECTED, count=None, score=50.96, signal=IP_EVIDENCE_NEUTRAL (source=data/반도체/엘티씨/tech/ltc_tech_ip_evidence_composite.json, keywords=composite, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)

## 4. 다음 확인 포인트
- 고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인
- 양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인
- 매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인
- IP 품질: citations 데이터 보강 후 청구항·인용·패밀리·존속 상태를 재점수화
- 마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인

## 5. URL 인식 결과 및 대체 조회 URL
- **KIPRIS**
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c930553ff19307a37d55fc13e99e493b823818adcf98717a65e69e57ac6cebd0afe7f8acc1ef278f0f789a5acaf2bf8409e2e781183deb11b82
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c935ffb7af845992d8639ddcdc131af6f232df02f34aa8d8462defd8f55ea32c30e335af7560f82962f182e6dff0f4d303800613cd08e8cedc9
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e001b0305aa79b8d4a69d7fccbf9601fc1c6d5d76ea6742992c72c70480fd22c0cc5fc4c9faeeee8fe6e142b6a0aebfcaaacb15f04fbfde05d5
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e00e83ff0c84936cf2334b06317acbd05874ed1d726913f88272d72b7d6cc759e6e145c1d9936bcffcf5e85afd7bfa8f077f62143db7434783d
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c937a2ac207a983da4300c04d4e923ea1531a66dfcb42b649f944ebe7da9fde77cddf4202d86d8b0580bc60523b0581acd9b8ff00951d34ea24
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e001a68c4fd164cf3d15673f40a510eb681792f530aa2f0525a4feb503bb150818a4adadac8be05dfbfa9bd44b40c8f9fff1953c987cd67d244
  - fallback: https://www.kipris.or.kr/khome/main.jsp
  - fallback: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+KIPRIS+%ED%8A%B9%ED%97%88
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC
- **TECH_OUTPUT**
  - detected: https://dart.fss.or.kr/dsab001/main.do?autoSearch=true&textCrpNm=170920
  - detected: https://finance.naver.com/item/main.naver?code=170920
  - detected: https://kind.krx.co.kr/external/dst/irReference/17081/250730_%EC%97%98%ED%8B%B0%EC%94%A8%20%EC%A3%BC%EC%A3%BC%EA%B0%84%EB%8B%B4%ED%9A%8C%20%EC%9E%90%EB%A3%8C_%EA%B3%B5%EC%8B%9C%EC%
  - detected: https://kind.krx.co.kr/external/dst/irReference/17081/250730_%EC%97%98%ED%8B%B0%EC%94%A8%20%EC%A3%BC%EC%A3%BC%EA%B0%84%EB%8B%B4%ED%9A%8C%20%EC%9E%90%EB%A3%8C_%EA%B3%B5%EC%8B%9C%EC%9A%A9_v7.pdf
  - detected: https://file.alphasquare.co.kr/media/pdfs/company-report/250721_%EC%97%98%ED%8B%B0%EC%94%A8.pdf
  - detected: http://www.ltcco.co.kr
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
- **IR_HOMEPAGE**
  - detected: https://dart.fss.or.kr/dsab001/main.do?autoSearch=true&textCrpNm=170920
  - detected: https://finance.naver.com/item/main.naver?code=170920
  - detected: https://kind.krx.co.kr/external/dst/irReference/17081/250730_%EC%97%98%ED%8B%B0%EC%94%A8%20%EC%A3%BC%EC%A3%BC%EA%B0%84%EB%8B%B4%ED%9A%8C%20%EC%9E%90%EB%A3%8C_%EA%B3%B5%EC%8B%9C%EC%
  - detected: https://kind.krx.co.kr/external/dst/irReference/17081/250730_%EC%97%98%ED%8B%B0%EC%94%A8%20%EC%A3%BC%EC%A3%BC%EA%B0%84%EB%8B%B4%ED%9A%8C%20%EC%9E%90%EB%A3%8C_%EA%B3%B5%EC%8B%9C%EC%9A%A9_v7.pdf
  - detected: https://file.alphasquare.co.kr/media/pdfs/company-report/250721_%EC%97%98%ED%8B%B0%EC%94%A8.pdf
  - detected: http://www.ltcco.co.kr\
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+IR
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88
- **DART**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://dart.fss.or.kr/dsab007/main.do?option=corp
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+DART+%EC%82%AC%EC%97%85%EB%B3%B4%EA%B3%A0%EC%84%9C
- **VALUATION**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
  - fallback: https://www.google.com/search?q=%EC%97%98%ED%8B%B0%EC%94%A8+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF
- **FINANCE**
  - detected: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#sessionnotcreatedexception
  - fallback: https://dart.fss.or.kr/
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->

<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->
# Technology Lifecycle Features

- company: 엘티씨
- status: OK
- overall_lifecycle_stage: STABLE_MATURITY
- overall_lifecycle_score: 54.12
- source_patent_csv: `data\반도체\엘티씨\tech\ltc_kipris_bibliographic_normalized.csv`

## Summary
power_thermal_efficiency, semiconductor_test, semiconductor_materials 관련 출원이 장기간 누적되고 최근에도 유지되어 기술 수명주기는 성숙기 또는 안정화 단계로 해석됩니다. 차별화 강도는 제품 성능·고객 채택 근거와 함께 확인해야 합니다.

## Keyword Trends
| keyword | stage | score | total | recent | baseline | trend_ratio | reason |
|---|---:|---:|---:|---:|---:|---:|---|
| advanced_packaging | INTRODUCTION_OR_SPARSE | 35.0 | 2 | 1 | 0 | None | 출원 수가 적어 도입기 또는 확인 제한으로 분류합니다. |
| hbm_ai_memory | NO_DATA | 0.0 | 0 | 0 | 0 | None | 특허 출원 추세 데이터가 없습니다. |
| fan_out_wlp | NO_DATA | 0.0 | 0 | 0 | 0 | None | 특허 출원 추세 데이터가 없습니다. |
| bump_rdl_interposer | DECLINE_OR_SHIFT | 30.0 | 27 | 2 | 8 | 0.417 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| semiconductor_test | GROWTH | 90.0 | 32 | 19 | 2 | 15.833 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |
| semiconductor_materials | MATURITY | 55.0 | 67 | 14 | 24 | 0.972 | 장기간 출원이 누적되고 최근 출원도 유지되어 성숙기 신호로 분류합니다. |
| process_yield_quality | MATURITY | 55.0 | 66 | 10 | 14 | 1.19 | 장기간 출원이 누적되고 최근 출원도 유지되어 성숙기 신호로 분류합니다. |
| power_thermal_efficiency | STABLE_MATURITY | 50.0 | 140 | 20 | 50 | 0.667 | 최근과 과거 출원 밀도가 유사해 안정적 성숙기 신호로 분류합니다. |

## External Signals
- status: NOT_PROVIDED
- summary: 논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.
<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->

<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->
# Certification & Standards Features

- company: 엘티씨
- status: OK
- certification_signal: CERTIFICATION_STRONG
- certification_score: 28.24
- quality_gate_stage: 5 / SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED
- evidence_count: 3

## Summary
FDA, SEMICONDUCTOR_QUALIFICATION 관련 근거가 확인되어 고객 품질·상용화 게이트 통과 가능성을 강하게 보강합니다. 단계: SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED.

## Confirmed Keys
FDA, SEMICONDUCTOR_QUALIFICATION

## Evidence
| certification | status | confidence | source | evidence |
|---|---:|---:|---|---|
| FDA | MENTIONED | LOW | kipris_ltc_patents.csv | 내지 1:1인, 표시 장치의 제조 방법이 제공된다. / http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=ed43a0609e94d6e22d01c5c32ba711cf6d1815af8c7dab2071fb4f02ad9d08234b29202b7a71df3fda2dada8f3f0ee6672f |
| SEMICONDUCTOR_QUALIFICATION | MENTIONED | LOW | ltc_tech_excel_frame_evidence.json | (개월), 검증 단계 수, 고객 테스트 횟수", "item_name": "추가 검증 필요 여부", "content": "기존 박리액/세정액/식각계 제품은 상용화 수준으로 보이지만, Glass Carrier, 저유전 절연막, CMP Slurry 등 신규 과제는 고객 Qualification과 추가 검증 필요", "conte |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | ltc_tech_excel_frame_evidence.md | : 필요 인증 수, 예상 개발 기간(개월), 검증 단계 수, 고객 테스트 횟수 - 수치 신호 수: 0 / 키워드 신호 수: 7 - 내용: 기존 박리액/세정액/식각계 제품은 상용화 수준으로 보이지만, Glass Carrier, 저유전 절연막, CMP Slurry 등 신규 과제는 고객 Qualification과 추가 검증 필 |
<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->
