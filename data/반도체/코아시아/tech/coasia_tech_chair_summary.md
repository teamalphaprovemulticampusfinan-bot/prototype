# 코아시아 Tech Chair Compact Summary

## 1. Chair 반영용 핵심 판단
- **의견:** 보유
- **Tech-to-Value:** base 39.00/100 / 기술-재무 괴리형(TECH_FINANCE_GAP)
- **Peer-adjusted:** 39.00/100 / 기술-재무 괴리형(TECH_FINANCE_GAP)
- **IP Evidence Composite:** 53.99/100 / IP 근거 중립형(IP_EVIDENCE_NEUTRAL)
- **ML 우선 반영:** Technology Differentiation Score + Tech-to-Value Evidence Confidence + IP Evidence Composite Score
- **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다.
- **루브릭 원천:** `src/tech_agent/prompts.py`
- **최종 Tech 점수 정책:** 개인투자자용 최종 Tech 점수는 기술-사업화 연결 가능성, IP 품질, Excel/DART 정량 근거, 근거 신뢰도, 딥테크 성장투자 지속성을 하나로 합성한다.

## 2. Excel-frame 핵심 요약
| 대분류 | 항목 | 정량화 | 근거 | 등급 | 비고 |
|---|---|---|---|---|---|
| 대표 기술 | 대표 기술 | 3 | 확인 제한 | 보강 필요 | 필요 시 원천 근거 확인 |
| 핵심 제품/서비스 | 핵심 제품/서비스 | 2 | 확인 제한 | 보강 필요 | 필요 시 원천 근거 확인 |
| 고객 구매 이유 | 고객 구매 이유 | 3 | 확인 제한 | 보강 필요 | 필요 시 원천 근거 확인 |
| 경쟁 우위/대체가능성 | 경쟁 우위/대체가능성 | 3 | 확인 제한 | 보강 필요 | 필요 시 원천 근거 확인 |
| 활용 및 확장 산업 | 활용 및 확장 산업 | 3 | 확인 제한 | 보강 필요 | 필요 시 원천 근거 확인 |
| 진입 부담/장벽 | 진입 부담/장벽 | 3 | 확인 제한 | 보강 필요 | 필요 시 원천 근거 확인 |
| R&D 강도 | R&D 강도 | 3 | 확인 제한 | 보강 필요 | 필요 시 원천 근거 확인 |

## 3. 선택 ML/IP 요약
| ML/IP 신호 | 값 | Chair 해석 |
|---|---:|---|
| Technology Differentiation Score | 확인 제한 / 확인 제한 | peer 대비 기술/IP 포트폴리오 차별성 |
| Evidence Confidence | 확인 제한 | 고객 채택·양산·매출·FCF 근거의 직접성 |
| Patent Momentum | 확인 제한 | 최근 특허 활동의 현재성·지속성 |
| IP Legal Stability | 86.50/100 | 등록률·존속률·소멸/거절/취하 비중 기반 권리 안정성 |
| IP Claim Defense | 64.16/100 | 청구항 수·독립항 수·수집 커버리지 기반 특허 방어력 |
| IP Citation Impact | 확인 제한 | 피인용·외부인용 기반 기술 영향력/시장 참조 가치 |
| IP Global Extension | 24.33/100 | 해외 패밀리·PCT/WO·미국/일본/유럽/중국 확장성 |
| IP Evidence Composite | 53.99/100 | 법적 안정성·청구항·인용·패밀리 특허를 통합한 종합 IP 근거 점수 |
| IP Evidence Bridge Signal | IP_EVIDENCE_NEUTRAL / 0.00점 | Tech-to-Value Bridge 보수적 보정 신호 |
| Peer-adjusted Bridge | 확인 제한 | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 |

## 4. KIPRIS/IP 정량 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 546건 |
| 회사 출원인/권리자 매칭 | 325건 |
| 등록 특허 | 229건 |
| 존속 가능 특허 | 260건 |
| 최근 5년 특허 | 6건 |
| IPC/CPC 다양성 | 7개 |
| H01L 등 핵심 IPC 특허 | 확인 제한 |
| KIPRIS 등록률(추정) | 83.33% |
| 등록특허 중 존속률(추정) | 100.00% |
| 소멸·거절·취하 등 부정 처분 비중(추정) | 13.33% |
| 권리자 정보 반영률 | 100.00% |
| 초록/도면 반영률 | 100.00% / 100.00% |
| 청구항 수집 커버리지 | 100.00% |
| 수집 청구항 / 독립항(추정) | 245항 / 50항 |
| 특허당 평균 청구항 / 독립항 비중 | 8.17항 / 20.41% |
| 피인용 총합 / 외부 피인용 | 확인 제한 / 확인 제한 |
| 외부 피인용률 | 확인 제한 |
| 해외 패밀리 보유율 | 16.67% |
| PCT/WO / US / JP / EP / CN | 2건 / 4건 / 0건 / 0건 / 2건 |

## 5. IP Evidence Composite 세부 구성
| 구성 요소 | Weight | Score | Contribution | Status |
|---|---:|---:|---:|---|
| 등록·존속 안정성 | 0.25 | 86.50/100 | 21.62점 | OK |
| 청구항 방어 범위 | 0.3 | 64.16/100 | 19.25점 | OK |
| 인용 기반 기술 영향력 | 0.25 | 33.00/100 | 8.25점 | OK |
| 해외 패밀리 기반 글로벌 확장성 | 0.2 | 24.33/100 | 4.87점 | OK |

## 6. 사업화 연결 체크
| 연결 항목 | 상태 | 점수 | 직접 | 간접 | 확인 제한 |
|---|---|---:|---:|---:|---:|
| 고객 채택 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 |
| 양산 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 |
| 매출 전환 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 |
| FCF/현금흐름 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 | 확인 제한 |

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

- IP Evidence Composite Score: **53.99 / 100**
- Data Coverage Rate: **1.0**
- Bridge Signal: **IP_EVIDENCE_NEUTRAL**
- Bridge Adjustment Points: **0.0**

| Component | 의미 | Weight | Score | Contribution | Status |
|---|---|---:|---:|---:|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 86.5 | 21.62 | OK |
| claim_defense | 청구항 방어 범위 | 0.3 | 64.16 | 19.25 | OK |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 33.0 | 8.25 | OK |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 24.33 | 4.87 | OK |

해석:
- 법적 안정성과 청구항 방어력은 IP 포트폴리오의 방어력을 보여줍니다.
- 인용 영향력과 글로벌 패밀리 확장성은 시장 내 참조 가치와 해외 권리 확장성을 보여줍니다.
- 본 지표는 직접적인 매출·수주 증거가 아니므로, 사업화·고객 채택·양산·FCF 개선 근거와 함께 해석해야 합니다.

<!-- IP_EVIDENCE_COMPOSITE_END -->

<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->
## IP Evidence Composite → Tech-to-Value Bridge 반영

- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.
- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points

- IP Evidence Composite Score: 53.99
- IP Evidence Bridge Signal: IP_EVIDENCE_NEUTRAL
- IP Evidence Adjustment Points: 0.0
- Peer-adjusted Score Before IP Evidence: 39.0
- Final Bridge Score After IP Evidence: 39.0
- Source: `data/반도체/코아시아/tech/tech_ip_evidence_composite.json`

해석:
- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.
- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.
<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->

<!-- TECH_INVESTOR_SCORECARD_START -->
## 개인투자자용 Tech 최종 점수판

- **대상 기업:** 코아시아
- **최종 Tech 점수:** 44.55/100
- **최종 판정:** 기술 또는 IP 근거가 초기/제한적이어서 보수적 해석 필요 `EVIDENCE_WEAK_OR_EARLY`
- **해석 원칙:** 특허 수, 기술 키워드 수, 뉴스 수를 각각 따로 과장하지 않고, 사업화 연결 가능성과 근거 직접성을 하나의 최종 점수로 통합했습니다.

### 1) 최종 점수 구성
| 구성요소 | 점수 | 가중치 | 가중 반영 | 의미 |
|---|---:|---:|---:|---|
| Tech-to-Value Bridge | 39.00 | 0.40 | 15.60 | 기술이 고객 채택·양산·매출 전환으로 이어질 가능성 |
| IP Evidence Composite | 53.99 | 0.20 | 10.80 | 권리 안정성·청구항·인용·패밀리 기반 특허 품질 |
| Excel 기반 정량 근거 | 45.00 | 0.15 | 6.75 | 템플릿/수식 기준에 맞춰 실제 기업별 근거가 얼마나 채워졌는지 |
| 근거 직접성·충분성 | 43.00 | 0.15 | 6.45 | Chair가 개인투자자에게 설명할 수 있는 근거의 직접성 |
| 사업화·성장자금 지속성 | 49.50 | 0.10 | 4.95 | R&D·특허·정부과제·기술이전·CAPEX/희석성 자금조달이 사업화와 연결되는 정도 |

### 2) 핵심 해석
- 코아시아의 개인투자자용 Tech 최종 점수는 44.55/100이며, 판정은 기술 또는 IP 근거가 초기/제한적이어서 보수적 해석 필요입니다.
- 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(39.0)와 IP Evidence(53.99) 및 Excel 기반 정량 근거(45.0)를 함께 반영했습니다.
- 투자자가 확인할 핵심 근거는 9개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다.

### 3) 개인투자자가 확인할 근거
| ID | 출처 | 근거 | 값 | 강도 |
|---|---|---|---:|---|
| tech.inv.ev.001 | tech_to_value | **최종 Tech-to-Value Bridge**: 코아시아의 최종 기술-사업화 연결 점수는 39.0이며, Chair에는 기술성보다 고객 채택·양산·매출 전환 가능성을 우선 반영합니다. | 39.0점 | 상 |
| tech.inv.ev.002 | kipris_ip_evidence | **IP Evidence Composite**: 법적 안정성·청구항 방어력·인용 영향력·해외 패밀리 확장성을 합성한 IP Evidence Composite Score는 53.99입니다. | 53.99점 | 상 |
| tech.inv.ev.003 | kipris_legal | **권리 안정성**: 등록률 0.8333, 존속률 1.0, 권리 안정성 점수 86.5를 확인했습니다. | 86.5점 | 중 |
| tech.inv.ev.004 | kipris_claim | **청구항 방어력**: 청구항 수 245, 독립항 추정 50, claim defense score 64.16입니다. | 64.16점 | 중 |
| tech.inv.ev.005 | kipris_citation | **인용 영향력**: 전방/후방 인용 및 기술 영향력 점수 기준 IP_CITATION_FALLBACK_ESTIMATED입니다. | - | 중 |
| tech.inv.ev.006 | kipris_family | **글로벌 패밀리 확장성**: 해외 패밀리 비중 0.1667, 감지 지역 ['CN', 'US', 'WO'], global extension score 24.33입니다. | 24.33점 | 중 |
| tech.inv.ev.007 | tech_summary | **Tech Agent 핵심 해석**: 코아시아의 개인투자자용 Tech 최종 점수는 44.55/100이며, 판정은 기술 또는 IP 근거가 초기/제한적이어서 보수적 해석 필요입니다. | - | 중 |
| tech.inv.ev.008 | tech_summary | **Tech Agent 핵심 해석**: 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(39.0)와 IP Evidence(53.99) 및 Excel 기반 정량 근거(45.0)를 함께 반영했습니다. | - | 중 |
| tech.inv.ev.009 | tech_summary | **Tech Agent 핵심 해석**: 투자자가 확인할 핵심 근거는 6개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다. | - | 중 |

### 4) 한계와 보완 필요사항
- 이 점수는 투자수익률 예측값이 아니라 기술-사업화 근거의 설명 가능성 점수입니다.
- KIPRIS Plus 유료 endpoint 접근 권한 또는 호출 제한으로 일부 청구항·패밀리·인용 데이터가 부족하면 보수적으로 반영합니다.
- Excel 템플릿 값은 복사 근거가 아니라 정량화 프레임이며, 실제 기업별 자료가 채워진 항목만 점수화합니다.
- CB/BW·유상증자·정부과제·기술이전 신호는 성장자금과 희석/오버행 리스크를 분리해 보조 레이어로만 해석합니다.
- R&D 비용은 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진은 commercial outcome으로 구분합니다.
<!-- TECH_INVESTOR_SCORECARD_END -->

<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->
# 코아시아 Tech Intake Value Evidence Bridge

## 1. 요약
- 생성 시각: 2026-05-20T21:35:42
- 종합 점수: 80.35/100
- 종합 라벨: VALUE_EVIDENCE_STRONG
- 원천 문서 수: 132개

## 2. 기술 → 사업화 → 재무 연결 근거
| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |
|---|---|---:|---:|---:|---:|---|
| 고객 채택 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 고객 채택 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 양산 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 양산 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 매출 전환 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 매출 전환 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| IP 품질 | 직접 근거 확인 | 53.99 | 4 | 0 | 0 | KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. 특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다. |
| 마진·원가·현금흐름 연결 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 마진·원가·현금흐름 연결 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |

## 3. 대표 근거

### 고객 채택
- [DIRECT_EVIDENCE] - **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다. (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 | (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | 고객 채택 | 직접 근거 | 88.00/100 | 8건 | 12건 | 0건 | (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 양산
- [DIRECT_EVIDENCE] - **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다. (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 | (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | 양산 | 직접 근거 | 88.00/100 | 17건 | 63건 | 0건 | (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/코아시아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 매출 전환
- [DIRECT_EVIDENCE] summary: 코아시아는 2023년부터 2025년까지 지속적인 매출 감소와 영업손실을 기록했으나, 2025년에는 영업손실 폭이 크게 줄어들며 개선 가능성을 보였다. (source=data/반도체/코아시아/finance/코아시아_finance.json, keywords=매출, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] key_thesis: 2025년 매출액이 3,751억 원으로 전년(3,578억 원) 대비 4.8% 증가하며 매출 성장세가 재개되었다. (source=data/반도체/코아시아/finance/코아시아_finance.json, keywords=매출, 매출액, 성장, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] missing_prompt_metrics: 매출성장률 (source=data/반도체/코아시아/finance/코아시아_finance_agent_packet.json, keywords=매출, 성장, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] source_contexts: 필수 지표 산출 한계: 매출성장률, 영업이익률, ROE, 부채비율, 변동성지수 (source=data/반도체/코아시아/finance/코아시아_finance_agent_packet.json, keywords=매출, 성장, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] sales: 375129006470.0 (source=data/반도체/코아시아/finance/코아시아_finance_agent_packet.json, keywords=sales, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)

### 마진·원가·현금흐름 연결
- [DIRECT_EVIDENCE] 그러나 여전히 높은 부채비율과 음(-)의 ROE는 재무 건전성 및 수익성 측면에서 부담으로 작용한다. (source=data/반도체/코아시아/finance/코아시아_finance.json, keywords=수익성, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] key_thesis: 2025년 영업이익률이 -0.60%로 개선되며 이전 연도(-6.75%, -11.07%) 대비 손실 폭이 크게 축소되었다. (source=data/반도체/코아시아/finance/코아시아_finance.json, keywords=영업이익률, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] key_thesis: 2025년 영업활동현금흐름(OCF)이 129억 원으로 흑자 전환하며 현금 창출 능력이 회복되는 추세를 보였다. (source=data/반도체/코아시아/finance/코아시아_finance.json, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] key_risks: 2025년 ROE가 -15.77%로 여전히 음수 값을 기록하며 자본 대비 수익성이 부진하다. (source=data/반도체/코아시아/finance/코아시아_finance.json, keywords=수익성, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] report_core_points: FCF: 코아시아 2025 기준 FCF 값은 -6,462,985,878원이며, 투자·운전자본 변동을 반영한 현금창출력을 확인하는 지표입니다. (source=data/반도체/코아시아/finance/코아시아_finance_agent_packet.json, keywords=FCF, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)

### IP 품질
- [DIRECT_EVIDENCE] legal_status: status=COLLECTED, count=None, score=0.8333, signal=None (source=data/반도체/코아시아/tech/coasia_tech_ip_legal_features.json, keywords=legal_status, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] claims: status=COLLECTED, count=245.0, score=None, signal=None (source=data/반도체/코아시아/tech/coasia_tech_ip_claim_features.json, keywords=claims, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] citations: status=COLLECTED, count=30, score=None, signal=None (source=data/반도체/코아시아/tech/coasia_tech_ip_citation_features.json, keywords=citations, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] family: status=COLLECTED, count=2.0, score=None, signal=None (source=data/반도체/코아시아/tech/coasia_tech_ip_family_features.json, keywords=family, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] composite: status=COLLECTED, count=None, score=53.99, signal=IP_EVIDENCE_NEUTRAL (source=data/반도체/코아시아/tech/coasia_tech_ip_evidence_composite.json, keywords=composite, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)

## 4. 다음 확인 포인트
- 고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인
- 양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인
- 매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인
- IP 품질: 청구항·인용·패밀리·존속 상태가 수집된 상태이므로 IP Evidence Composite와 Bridge 조정값의 방향성을 점검
- 마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인

## 5. URL 인식 결과 및 대체 조회 URL
- **KIPRIS**
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93a9b771f368fa655e7f7a1562646a3d34403defa067eeb74aafa9b695564b9de1c0a72bcc6ded89f060a81b1d622495bb14dfcc58a660810b
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93e7ccc07c8be1ba8f41d3d151087321cfaaea617e30d30054b9702f660bc41f3edc469102389d050ed69882a262662107e1c5f9bc946e4d82
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93db78754d5dbd5ab24bd88199c6f35482a04069254144e9213b264a8d1109a9c1a1b85ada54eba73caf0f443a92ea5f553deaa62a652f8c57
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93cddb60135cf54cd31373afd14d1f5fa8c804c3146f3f22243c57908335803b46d447c0620668158d59663bd9a6dbdd5c0043e8e51c02316a
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e00b49fc7e887ad431d391693870500aaa4a0336de5de60fbd0498c526df35c20bf49627da1ff522444557fa3c18beb0f69a461e2eb6f289494
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c9390b4cc17636c7cca404ff08f54bc498c835c4e98d9add92763706cd0e2c25cfaa8ca89ca22fb3eaefcff86e75e811b79e62eaaa1540197e0
  - fallback: https://www.kipris.or.kr/khome/main.jsp
  - fallback: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+KIPRIS+%ED%8A%B9%ED%97%88
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC
- **TECH_OUTPUT**
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93a9b771f368fa655e7f7a1562646a3d34403defa067eeb74aafa9b695564b9de1c0a72bcc6ded89f060a81b1d622495bb14dfcc58a660810b
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93e7ccc07c8be1ba8f41d3d151087321cfaaea617e30d30054b9702f660bc41f3edc469102389d050ed69882a262662107e1c5f9bc946e4d82
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93db78754d5dbd5ab24bd88199c6f35482a04069254144e9213b264a8d1109a9c1a1b85ada54eba73caf0f443a92ea5f553deaa62a652f8c57
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93cddb60135cf54cd31373afd14d1f5fa8c804c3146f3f22243c57908335803b46d447c0620668158d59663bd9a6dbdd5c0043e8e51c02316a
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e00b49fc7e887ad431d391693870500aaa4a0336de5de60fbd0498c526df35c20bf49627da1ff522444557fa3c18beb0f69a461e2eb6f289494
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c9390b4cc17636c7cca404ff08f54bc498c835c4e98d9add92763706cd0e2c25cfaa8ca89ca22fb3eaefcff86e75e811b79e62eaaa1540197e0
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
- **IR_HOMEPAGE**
  - detected: http://www.w3.org/2001/XMLSchema-instance
  - detected: http://www.nepes.co.kr
  - detected: https://dart.fss.or.kr/
  - detected: https://opendart.fss.or.kr/
  - detected: https://www.kipris.or.kr/khome/main.jsp
  - detected: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+IR
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88
- **VALUATION**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
  - fallback: https://www.google.com/search?q=%EC%BD%94%EC%95%84%EC%8B%9C%EC%95%84+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF
- **FINANCE**
  - detected: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#sessionnotcreatedexception
  - fallback: https://dart.fss.or.kr/
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->

<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->
# Technology Lifecycle Features

- company: 코아시아
- status: EMPTY_PATENT_CSV
- overall_lifecycle_stage: UNKNOWN
- overall_lifecycle_score: 0.0
- source_patent_csv: `data\반도체\코아시아\tech\coasia_kipris_bibliographic_normalized.csv`

## Summary
특허 CSV는 존재하지만 행이 없어 기술 수명주기 추세를 계산하지 못했습니다.

## Keyword Trends
| keyword | stage | score | total | recent | baseline | trend_ratio | reason |
|---|---:|---:|---:|---:|---:|---:|---|

## External Signals
- status: NOT_PROVIDED
- summary: 논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.
<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->

<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->
# Certification & Standards Features

- company: 코아시아
- status: NOT_PROVIDED
- certification_signal: NOT_PROVIDED
- certification_score: 0.0
- quality_gate_stage: 0 / NOT_PROVIDED
- evidence_count: 0

## Summary
기술 표준·인증 데이터가 아직 제공되지 않았습니다. 이는 감점이 아니라 확인 제한으로 처리합니다.

## Confirmed Keys
-

## Evidence
| certification | status | confidence | source | evidence |
|---|---:|---:|---|---|
<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->
