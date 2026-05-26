# 한미반도체 Tech Chair Compact Summary

## 1. Chair 반영용 핵심 판단
- **의견:** 매수
- **Tech-to-Value:** base 79.00/100 / 가치 전환 확인형(VALUE_CONVERSION_CONFIRMED)
- **Peer-adjusted:** 80.85/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **IP Evidence Composite:** 48.12/100 / IP 근거 중립형(IP_EVIDENCE_NEUTRAL)
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
| Technology Differentiation Score | 75.39/100 / 90.00%ile | peer 대비 기술/IP 포트폴리오 차별성 |
| Evidence Confidence | 88.00/100 | 고객 채택·양산·매출·FCF 근거의 직접성 |
| Patent Momentum | 45.50/100 | 최근 특허 활동의 현재성·지속성 |
| IP Legal Stability | 56.38/100 | 등록률·존속률·소멸/거절/취하 비중 기반 권리 안정성 |
| IP Claim Defense | 55.58/100 | 청구항 수·독립항 수·수집 커버리지 기반 특허 방어력 |
| IP Citation Impact | 확인 제한 | 피인용·외부인용 기반 기술 영향력/시장 참조 가치 |
| IP Global Extension | 45.17/100 | 해외 패밀리·PCT/WO·미국/일본/유럽/중국 확장성 |
| IP Evidence Composite | 48.12/100 | 법적 안정성·청구항·인용·패밀리 특허를 통합한 종합 IP 근거 점수 |
| IP Evidence Bridge Signal | IP_EVIDENCE_NEUTRAL / 0.00점 | Tech-to-Value Bridge 보수적 보정 신호 |
| Peer-adjusted Bridge | 80.85/100 | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 |

## 4. KIPRIS/IP 정량 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 24,323건 |
| 회사 출원인/권리자 매칭 | 17,778건 |
| 등록 특허 | 5,373건 |
| 존속 가능 특허 | 9,502건 |
| 최근 5년 특허 | 1,901건 |
| IPC/CPC 다양성 | 237개 |
| H01L 등 핵심 IPC 특허 | 6건 |
| KIPRIS 등록률(추정) | 57.27% |
| 등록특허 중 존속률(추정) | 62.02% |
| 소멸·거절·취하 등 부정 처분 비중(추정) | 51.83% |
| 권리자 정보 반영률 | 100.00% |
| 초록/도면 반영률 | 100.00% / 91.56% |
| 청구항 수집 커버리지 | 99.22% |
| 수집 청구항 / 독립항(추정) | 10,915항 / 1,882항 |
| 특허당 평균 청구항 / 독립항 비중 | 12.21항 / 17.24% |
| 피인용 총합 / 외부 피인용 | 확인 제한 / 확인 제한 |
| 외부 피인용률 | 확인 제한 |
| 해외 패밀리 보유율 | 30.74% |
| PCT/WO / US / JP / EP / CN | 236건 / 157건 / 163건 / 163건 / 199건 |

## 5. IP Evidence Composite 세부 구성
| 구성 요소 | Weight | Score | Contribution | Status |
|---|---:|---:|---:|---|
| 등록·존속 안정성 | 0.25 | 56.38/100 | 14.10점 | OK |
| 청구항 방어 범위 | 0.3 | 55.58/100 | 16.67점 | OK |
| 인용 기반 기술 영향력 | 0.25 | 33.26/100 | 8.31점 | OK |
| 해외 패밀리 기반 글로벌 확장성 | 0.2 | 45.17/100 | 9.03점 | OK |

## 6. 사업화 연결 체크
| 연결 항목 | 상태 | 점수 | 직접 | 간접 | 확인 제한 |
|---|---|---:|---:|---:|---:|
| 고객 채택 | 직접 근거 | 88.00/100 | 13건 | 45건 | 0건 |
| 양산 | 직접 근거 | 88.00/100 | 11건 | 67건 | 0건 |
| 매출 전환 | 직접 근거 | 88.00/100 | 16건 | 57건 | 0건 |
| FCF/현금흐름 | 직접 근거 | 88.00/100 | 3건 | 2건 | 0건 |

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

- IP Evidence Composite Score: **48.12 / 100**
- Data Coverage Rate: **1.0**
- Bridge Signal: **IP_EVIDENCE_NEUTRAL**
- Bridge Adjustment Points: **0.0**

| Component | 의미 | Weight | Score | Contribution | Status |
|---|---|---:|---:|---:|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 56.38 | 14.1 | OK |
| claim_defense | 청구항 방어 범위 | 0.3 | 55.58 | 16.67 | OK |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 33.26 | 8.31 | OK |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 45.17 | 9.03 | OK |

해석:
- 법적 안정성과 청구항 방어력은 IP 포트폴리오의 방어력을 보여줍니다.
- 인용 영향력과 글로벌 패밀리 확장성은 시장 내 참조 가치와 해외 권리 확장성을 보여줍니다.
- 본 지표는 직접적인 매출·수주 증거가 아니므로, 사업화·고객 채택·양산·FCF 개선 근거와 함께 해석해야 합니다.

<!-- IP_EVIDENCE_COMPOSITE_END -->

<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->
## IP Evidence Composite → Tech-to-Value Bridge 반영

- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.
- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points

- IP Evidence Composite Score: 48.12
- IP Evidence Bridge Signal: IP_EVIDENCE_NEUTRAL
- IP Evidence Adjustment Points: 0.0
- Peer-adjusted Score Before IP Evidence: 80.85
- Final Bridge Score After IP Evidence: 80.85
- Source: `C:/Agent_6.9/data/반도체/한미반도체/tech/tech_ip_evidence_composite.json`

해석:
- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.
- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.
<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->

<!-- TECH_INVESTOR_SCORECARD_START -->
## 개인투자자용 Tech 최종 점수판

- **대상 기업:** 한미반도체
- **최종 Tech 점수:** 74.46/100
- **최종 판정:** 기술의 가치전환 준비도는 높지만 일부 고객·매출·마진 근거는 추가 확인 필요 `TECH_TO_VALUE_READY`
- **해석 원칙:** 특허 수, 기술 키워드 수, 뉴스 수를 각각 따로 과장하지 않고, 사업화 연결 가능성과 근거 직접성을 하나의 최종 점수로 통합했습니다.

### 1) 최종 점수 구성
| 구성요소 | 점수 | 가중치 | 가중 반영 | 의미 |
|---|---:|---:|---:|---|
| Tech-to-Value Bridge | 80.85 | 0.40 | 32.34 | 기술이 고객 채택·양산·매출 전환으로 이어질 가능성 |
| IP Evidence Composite | 48.12 | 0.20 | 9.62 | 권리 안정성·청구항·인용·패밀리 기반 특허 품질 |
| Excel 기반 정량 근거 | 85.00 | 0.15 | 12.75 | 템플릿/수식 기준에 맞춰 실제 기업별 근거가 얼마나 채워졌는지 |
| 근거 직접성·충분성 | 82.00 | 0.15 | 12.30 | Chair가 개인투자자에게 설명할 수 있는 근거의 직접성 |
| 사업화·성장자금 지속성 | 74.50 | 0.10 | 7.45 | R&D·특허·정부과제·기술이전·CAPEX/희석성 자금조달이 사업화와 연결되는 정도 |

### 2) 핵심 해석
- 한미반도체의 개인투자자용 Tech 최종 점수는 74.46/100이며, 판정은 기술의 가치전환 준비도는 높지만 일부 고객·매출·마진 근거는 추가 확인 필요입니다.
- 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(80.85)와 IP Evidence(48.12) 및 Excel 기반 정량 근거(85.0)를 함께 반영했습니다.
- 투자자가 확인할 핵심 근거는 9개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다.

### 3) 개인투자자가 확인할 근거
| ID | 출처 | 근거 | 값 | 강도 |
|---|---|---|---:|---|
| tech.inv.ev.001 | tech_to_value | **최종 Tech-to-Value Bridge**: 한미반도체의 최종 기술-사업화 연결 점수는 80.85이며, Chair에는 기술성보다 고객 채택·양산·매출 전환 가능성을 우선 반영합니다. | 80.85점 | 상 |
| tech.inv.ev.002 | kipris_ip_evidence | **IP Evidence Composite**: 법적 안정성·청구항 방어력·인용 영향력·해외 패밀리 확장성을 합성한 IP Evidence Composite Score는 48.12입니다. | 48.12점 | 상 |
| tech.inv.ev.003 | kipris_legal | **권리 안정성**: 등록률 0.5727, 존속률 0.6202, 권리 안정성 점수 56.38를 확인했습니다. | 56.38점 | 중 |
| tech.inv.ev.004 | kipris_claim | **청구항 방어력**: 청구항 수 10915, 독립항 추정 1882, claim defense score 55.58입니다. | 55.58점 | 중 |
| tech.inv.ev.005 | kipris_citation | **인용 영향력**: 전방/후방 인용 및 기술 영향력 점수 기준 IP_CITATION_FALLBACK_ESTIMATED입니다. | - | 중 |
| tech.inv.ev.006 | kipris_family | **글로벌 패밀리 확장성**: 해외 패밀리 비중 0.3074, 감지 지역 ['CN', 'EP', 'JP', 'US', 'WO'], global extension score 45.17입니다. | 45.17점 | 중 |
| tech.inv.ev.007 | tech_summary | **Tech Agent 핵심 해석**: 한미반도체의 개인투자자용 Tech 최종 점수는 74.46/100이며, 판정은 기술의 가치전환 준비도는 높지만 일부 고객·매출·마진 근거는 추가 확인 필요입니다. | - | 중 |
| tech.inv.ev.008 | tech_summary | **Tech Agent 핵심 해석**: 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(80.85)와 IP Evidence(48.12) 및 Excel 기반 정량 근거(85.0)를 함께 반영했습니다. | - | 중 |
| tech.inv.ev.009 | tech_summary | **Tech Agent 핵심 해석**: 투자자가 확인할 핵심 근거는 6개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다. | - | 중 |

### 4) 한계와 보완 필요사항
- 이 점수는 투자수익률 예측값이 아니라 기술-사업화 근거의 설명 가능성 점수입니다.
- KIPRIS Plus 유료 endpoint 접근 권한 또는 호출 제한으로 일부 청구항·패밀리·인용 데이터가 부족하면 보수적으로 반영합니다.
- Excel 템플릿 값은 복사 근거가 아니라 정량화 프레임이며, 실제 기업별 자료가 채워진 항목만 점수화합니다.
- CB/BW·유상증자·정부과제·기술이전 신호는 성장자금과 희석/오버행 리스크를 분리해 보조 레이어로만 해석합니다.
- R&D 비용은 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진은 commercial outcome으로 구분합니다.
<!-- TECH_INVESTOR_SCORECARD_END -->

<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->
# 한미반도체 Tech Intake Value Evidence Bridge

## 1. 요약
- 생성 시각: 2026-05-26T16:13:24
- 종합 점수: 79.47/100
- 종합 라벨: VALUE_EVIDENCE_STRONG
- 원천 문서 수: 170개

## 2. 기술 → 사업화 → 재무 연결 근거
| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |
|---|---|---:|---:|---:|---:|---|
| 고객 채택 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 고객 채택 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 양산 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 양산 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 매출 전환 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 매출 전환 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| IP 품질 | 직접 근거 확인 | 48.12 | 3 | 0 | 1 | KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. 특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다. |
| 마진·원가·현금흐름 연결 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 마진·원가·현금흐름 연결 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |

## 3. 대표 근거

### 고객 채택
- [DIRECT_EVIDENCE] 우리의 의견으로는 별첨된 연결회사의 연결재무제표는 연결회사의 2025년 12월 31일 현재의 연결재무상태와 동일로 종료되는 보고기간의 연결재무성과 및 연결현금흐름을 한국채택국제회계기준에 따라, 중요성의 관점에서 공정하게 표시하고 있습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 경영진은 한국채택국제회계기준에 따라 이 연결재무제표를 작성하고 공정하게 표시할 책임이 있으며, 부정이나 오류로 인한 중요한 왜곡표시가 없는 연결재무제표를 작성하는데 필요하다고 결정한 내부통제에 대해서도 책임이 있습니다.경영진은 연결재무제표를 작성할 때, 연결회사의 계속기업으로서의 존속능력을 평가하고 해당되는 경우, 계속기업 관련 사항을 공시할 책임이 있습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 당기 중 메모리 반도체 성장에 따라 글로벌 고객사 현지 대응을 위해 설립하였습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=고객사, 고객, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 2.1 연결재무제표 작성기준연결실체는 주식회사 등의 외부감사에 관한 법률에서 규정하고 있는 국제회계기준위원회의 국제회계기준을 채택하여 정한 회계처리기준인 한국채택국제회계기준에 따라 연결재무제표를 작성하였습니다.(1) 측정기준 (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 2.1.1 연결실체가 채택한 제ㆍ개정 기준서 및 해석서 (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### 양산
- [DIRECT_EVIDENCE] - **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. (source=data/반도체/한미반도체/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다. (source=data/반도체/한미반도체/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 | (source=data/반도체/한미반도체/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | 양산 | 직접 근거 | 88.00/100 | 17건 | 63건 | 0건 | (source=data/반도체/한미반도체/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/한미반도체/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 매출 전환
- [DIRECT_EVIDENCE] 연결회사의 수익 대부분은 장비 판매로부터 창출되며, 2025년 중 발생한 장비제조판매 수익은 565,059백만원으로 총매출의 약 98%를 차지하고 있습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=매출, 판매, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 수익은 연결회사의 경영진이 관심을 두는 주요 성과지표 중에 하나이며, 연결재무제표 이용자 관점에서도 매출액이 연결회사의 영업성과 또는 미래에 예상되는 영업을 대표합니다.이에 따라 매출액은 목표 또는 기대치를 달성하기 위해 조정될 수 있는 등 수익인식 왜곡에 대한 유인이 존재하며, 고객 및 계약 조건에 따라 수익인식의 시기가 달라지기 때문에 수익인식의 기간귀속 왜곡에 대한 고유위험이 있습니다.따라서 우리는 장비 제조판매로 인한 수익인식의 기간귀속에 유의적인 위험이 있는 것으로 판단하고 핵심감사항목으로 결정하였습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=매출, 매출액, 판매, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] - 수익인식 프로세스와 연결회사의 회계정책에 대한 이해, 그리고 관련 통제 이해, 평가 및 운영테스트- 회사의 주요 매출 유형별 계약서를 열람하여 수익인식 여부에 영향을 미치는 거래조건을 검토- 보고기간말 전후에 발생한 장비제조판매 수익인식시점의 적정성 확인을 위하여 표본으로 추출된 개별 거래 단위에 대한 관련 거래약정과 선적서류 및 인수증을 비롯한재고자산의 통제이전과 관련된 증빙의 확인 (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=매출, 판매, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 매출채권의 감소(증가) (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 재고자산의 판매에 따른 수익을 인식하는 기간에 재고자산의 장부금액을 매출원가로 인식하고 있습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=매출, 판매, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### 마진·원가·현금흐름 연결
- [DIRECT_EVIDENCE] 연결현금흐름표·························· (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 해당 연결재무제표는 2025년 12월 31일 현재의 연결재무상태표, 동일로 종료되는 보고기간의 연결포괄손익계산서, 연결자본변동표, 연결현금흐름표 그리고 중요한 회계정책 정보를 포함한 연결재무제표의 주석으로 구성되어 있습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 우리의 의견으로는 별첨된 연결회사의 연결재무제표는 연결회사의 2025년 12월 31일 현재의 연결재무상태와 동일로 종료되는 보고기간의 연결재무성과 및 연결현금흐름을 한국채택국제회계기준에 따라, 중요성의 관점에서 공정하게 표시하고 있습니다. (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 영업활동현금흐름 (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 투자활동현금흐름 (source=data/반도체/한미반도체/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### IP 품질
- [DIRECT_EVIDENCE] legal_status: status=COLLECTED, count=None, score=0.5727, signal=None (source=data/반도체/한미반도체/tech/hanmi_tech_ip_legal_features.json, keywords=legal_status, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] claims: status=COLLECTED, count=10915.0, score=None, signal=None (source=data/반도체/한미반도체/tech/hanmi_tech_ip_claim_features.json, keywords=claims, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [PARTIAL_EVIDENCE] citations: status=NO_CITATION_COLLECTED, count=0, score=None, signal=None (source=data/반도체/한미반도체/tech/hanmi_tech_ip_citation_features.json, keywords=citations, NO_CITATION_COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] family: status=COLLECTED, count=236.0, score=None, signal=None (source=data/반도체/한미반도체/tech/hanmi_tech_ip_family_features.json, keywords=family, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] composite: status=COLLECTED, count=None, score=48.12, signal=IP_EVIDENCE_NEUTRAL (source=data/반도체/한미반도체/tech/hanmi_tech_ip_evidence_composite.json, keywords=composite, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)

## 4. 다음 확인 포인트
- 고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인
- 양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인
- 매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인
- IP 품질: citations 데이터 보강 후 청구항·인용·패밀리·존속 상태를 재점수화
- 마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인

## 5. URL 인식 결과 및 대체 조회 URL
- **KIPRIS**
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93d0a6a92317127eda477cb73a30800be48c1cbdca13a6c3844adaf412eab4dca7fe9cb239fa568c206d00eea4bf63ef89bb90acd71d1a15db
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c9385f595290fd0a5ae9795b1d907314b6261124e330c35d8bca45306e02d6a92b45b3699bf90a05d6c2e6f261b216da4e7ef930fc6bc659b7d
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e0044a5c669ddd812feaf8c57a51f2b5513e7f704bd22f17e697708bf9ce61926a26a270cfa4df94dcf1e2f04632bffe52d86608da4f87d59bf
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e0087ec9c7dcef9df01b2b47920830d0b16d77a7df23de1c261390f0b98dc36b7ec74ca3cae646f54ed88dd2fdf1c5f3c5f478641c143488190
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93248f2995ab0a14eab6c2fc1392960175391aee28d3ccec8a3aefbc806e530efc582a403ae9e9e4e250ef3c039bc5abc77c3cbe87d5aaf32b
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e00e8d49067bfb0ab9645b3d0b5494e334e3e38e20ee7f7660d6d165920e7d919d11a549a6c9fd85efc9e31803926c7df5c18d9100513a369da
  - fallback: https://www.kipris.or.kr/khome/main.jsp
  - fallback: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+KIPRIS+%ED%8A%B9%ED%97%88
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC
- **TECH_OUTPUT**
  - detected: https://www.hanmisemi.com
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=2&sNo=6
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=10
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=3
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=4
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=5
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
- **IR_HOMEPAGE**
  - detected: https://www.hanmisemi.com
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=2&sNo=6
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=10
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=3
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=4
  - detected: https://www.hanmisemi.com?module=Html&action=SiteProduct&sSubNo=5
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+IR
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88
- **DART**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://dart.fss.or.kr/dsab007/main.do?option=corp
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+DART+%EC%82%AC%EC%97%85%EB%B3%B4%EA%B3%A0%EC%84%9C
- **VALUATION**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
  - fallback: https://www.google.com/search?q=%ED%95%9C%EB%AF%B8%EB%B0%98%EB%8F%84%EC%B2%B4+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF
- **FINANCE**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->

<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->
# Technology Lifecycle Features

- company: 한미반도체
- status: OK
- overall_lifecycle_stage: DECLINE_OR_SHIFT
- overall_lifecycle_score: 48.55
- source_patent_csv: `data\반도체\한미반도체\tech\hanmi_kipris_bibliographic_normalized.csv`

## Summary
power_thermal_efficiency, bump_rdl_interposer, semiconductor_test 관련 최근 출원 밀도가 약해져 쇠퇴 또는 차세대 기술 전환 가능성을 점검해야 합니다.

## Keyword Trends
| keyword | stage | score | total | recent | baseline | trend_ratio | reason |
|---|---:|---:|---:|---:|---:|---:|---|
| advanced_packaging | DECLINE_OR_SHIFT | 30.0 | 246 | 2 | 17 | 0.196 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| hbm_ai_memory | UNCERTAIN | 40.0 | 18 | 0 | 0 | None | 출원 추세만으로 수명주기 단계를 단정하기 어렵습니다. |
| fan_out_wlp | INTRODUCTION_OR_SPARSE | 35.0 | 1 | 0 | 0 | None | 출원 수가 적어 도입기 또는 확인 제한으로 분류합니다. |
| bump_rdl_interposer | GROWTH | 90.0 | 72 | 18 | 9 | 3.333 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |
| semiconductor_test | GROWTH | 73.33 | 106 | 12 | 12 | 1.667 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |
| semiconductor_materials | UNCERTAIN | 40.0 | 5 | 0 | 1 | 0.0 | 출원 추세만으로 수명주기 단계를 단정하기 어렵습니다. |
| process_yield_quality | DECLINE_OR_SHIFT | 30.0 | 242 | 8 | 32 | 0.417 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| power_thermal_efficiency | GROWTH | 67.59 | 192 | 24 | 29 | 1.379 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |

## External Signals
- status: NOT_PROVIDED
- summary: 논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.
<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->

<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->
# Certification & Standards Features

- company: 한미반도체
- status: OK
- certification_signal: CERTIFICATION_STRONG
- certification_score: 42.97
- quality_gate_stage: 5 / SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED
- evidence_count: 9

## Summary
CE, FDA, ISO_45001, RoHS, SEMICONDUCTOR_QUALIFICATION 관련 근거가 확인되어 고객 품질·상용화 게이트 통과 가능성을 강하게 보강합니다. 단계: SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED.

## Confirmed Keys
CE, FDA, ISO_45001, RoHS, SEMICONDUCTOR_QUALIFICATION

## Evidence
| certification | status | confidence | source | evidence |
|---|---:|---:|---|---|
| ISO_45001 | CONFIRMED | HIGH | hanmi_tech_excel_frame_evidence.json | 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지연·검증 이슈 기사", "quantifiable": "필요 인증 수, 예상 개발 기간(개월), 검증 단계 수, 고객 테스트 횟수", "item_name": "인증 종류", "content": "ISO 45001, RoHS", "content_present": t |
| RoHS | CONFIRMED | HIGH | hanmi_tech_excel_frame_evidence.json | 승인 기사 / 테스트베드 기사 / 개발 지연·검증 이슈 기사", "quantifiable": "필요 인증 수, 예상 개발 기간(개월), 검증 단계 수, 고객 테스트 횟수", "item_name": "인증 종류", "content": "ISO 45001, RoHS", "content_present": true, "conte |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | hanmi_tech_excel_frame_evidence.json | , "middle_source": "사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인\n규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건\n기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지 |
| ISO_45001 | CONFIRMED | HIGH | hanmi_tech_excel_frame_evidence.md | / 안전기준 / 공급 승인 조건 기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지연·검증 이슈 기사 - 정량화 가능 부분: 필요 인증 수, 예상 개발 기간(개월), 검증 단계 수, 고객 테스트 횟수 - 수치 신호 수: 2 / 키워드 신호 수: 0 - 내용: ISO 45001, RoHS - 추출 수 |
| RoHS | CONFIRMED | HIGH | hanmi_tech_excel_frame_evidence.md | 승인 조건 기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지연·검증 이슈 기사 - 정량화 가능 부분: 필요 인증 수, 예상 개발 기간(개월), 검증 단계 수, 고객 테스트 횟수 - 수치 신호 수: 2 / 키워드 신호 수: 0 - 내용: ISO 45001, RoHS - 추출 수치: - 450: IS |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | hanmi_tech_excel_frame_evidence.md | 수 / 출처: 사업보고서 / 규제자료 / 기사 > 사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인 규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건 기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사  |
| CE | MENTIONED | LOW | kipris_hanmi_patents.csv | 픽커의 흡착패드에 관한 것으로, 상기 흡착패드의 센터를 정확하게 구할 수 있도록 상기 흡착패드의 하면에 기준마크가 형성되어, 고배율의 비젼카메라를 사용하여 FOV(Field Of View)를 작게 하더라도, 흡착패드의 센터를 확실하게 계산할 수 있기 때문에 이러한 기준마크(Reference Mark)를 구비한 흡착패드를  |
| FDA | MENTIONED | LOW | kipris_hanmi_patents.csv | 체, 패키지, 픽앤플레이스 / http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=ed43a0609e94d6e2d625a3dcb0746fe407489d23bbfec2437e1712f4d2efc17534b8fe896680c1260ef7a080023affda / http://plus.ki |
| SEMICONDUCTOR_QUALIFICATION | MENTIONED | LOW | kipris_hanmi_patents.csv | 이물질과 침전 이물질을 모두 분리 배출할 수 있도록 일측에 상부 배수구와 하부 배수구를 구비하며, 상부 배수구와 하부 배수구 측으로 이물질이 배출될 수 있도록 액체를 일측 방향으로 공급해주는 초음파 세척부를 통해 다양한 종류의 반도체 패키지의 이물질이나 얼룩을 제거함으로써, 높은 세척 퀄리티를 보장할 수 있으며, 반도체  |
<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->
