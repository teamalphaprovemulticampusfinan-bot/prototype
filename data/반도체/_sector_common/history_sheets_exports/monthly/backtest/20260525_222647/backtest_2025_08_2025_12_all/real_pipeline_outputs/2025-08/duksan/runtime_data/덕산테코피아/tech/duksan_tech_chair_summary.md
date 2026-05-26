# 덕산테코피아 Tech Chair Compact Summary

## 1. Chair 반영용 핵심 판단
- **의견:** 매수
- **Tech-to-Value:** base 77.00/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **Peer-adjusted:** 50.72/100 / 근거 보강 필요형(TECH_EVIDENCE_WEAK)
- **IP Evidence Composite:** 52.54/100 / IP 근거 중립형(IP_EVIDENCE_NEUTRAL)
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
| Technology Differentiation Score | 61.40/100 / 70.00%ile | peer 대비 기술/IP 포트폴리오 차별성 |
| Evidence Confidence | 88.00/100 | 고객 채택·양산·매출·FCF 근거의 직접성 |
| Patent Momentum | 50.96/100 | 최근 특허 활동의 현재성·지속성 |
| IP Legal Stability | 82.25/100 | 등록률·존속률·소멸/거절/취하 비중 기반 권리 안정성 |
| IP Claim Defense | 60.93/100 | 청구항 수·독립항 수·수집 커버리지 기반 특허 방어력 |
| IP Citation Impact | 확인 제한 | 피인용·외부인용 기반 기술 영향력/시장 참조 가치 |
| IP Global Extension | 30.68/100 | 해외 패밀리·PCT/WO·미국/일본/유럽/중국 확장성 |
| IP Evidence Composite | 52.54/100 | 법적 안정성·청구항·인용·패밀리 특허를 통합한 종합 IP 근거 점수 |
| IP Evidence Bridge Signal | IP_EVIDENCE_NEUTRAL / 0.00점 | Tech-to-Value Bridge 보수적 보정 신호 |
| Peer-adjusted Bridge | 50.72/100 | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 |

## 4. KIPRIS/IP 정량 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 2,339건 |
| 회사 출원인/권리자 매칭 | 2,279건 |
| 등록 특허 | 539건 |
| 존속 가능 특허 | 2,142건 |
| 최근 5년 특허 | 1,589건 |
| IPC/CPC 다양성 | 34개 |
| H01L 등 핵심 IPC 특허 | 확인 제한 |
| KIPRIS 등록률(추정) | 78.95% |
| 등록특허 중 존속률(추정) | 96.67% |
| 소멸·거절·취하 등 부정 처분 비중(추정) | 21.05% |
| 권리자 정보 반영률 | 100.00% |
| 초록/도면 반영률 | 100.00% / 84.21% |
| 청구항 수집 커버리지 | 100.00% |
| 수집 청구항 / 독립항(추정) | 365항 / 75항 |
| 특허당 평균 청구항 / 독립항 비중 | 9.61항 / 20.55% |
| 피인용 총합 / 외부 피인용 | 확인 제한 / 확인 제한 |
| 외부 피인용률 | 확인 제한 |
| 해외 패밀리 보유율 | 23.68% |
| PCT/WO / US / JP / EP / CN | 8건 / 6건 / 2건 / 0건 / 0건 |

## 5. IP Evidence Composite 세부 구성
| 구성 요소 | Weight | Score | Contribution | Status |
|---|---:|---:|---:|---|
| 등록·존속 안정성 | 0.25 | 82.25/100 | 20.56점 | OK |
| 청구항 방어 범위 | 0.3 | 60.93/100 | 18.28점 | OK |
| 인용 기반 기술 영향력 | 0.25 | 30.26/100 | 7.57점 | OK |
| 해외 패밀리 기반 글로벌 확장성 | 0.2 | 30.68/100 | 6.14점 | OK |

## 6. 사업화 연결 체크
| 연결 항목 | 상태 | 점수 | 직접 | 간접 | 확인 제한 |
|---|---|---:|---:|---:|---:|
| 고객 채택 | 직접 근거 | 88.00/100 | 8건 | 38건 | 0건 |
| 양산 | 직접 근거 | 88.00/100 | 6건 | 58건 | 0건 |
| 매출 전환 | 직접 근거 | 88.00/100 | 13건 | 35건 | 0건 |
| FCF/현금흐름 | 직접 근거 | 88.00/100 | 1건 | 1건 | 0건 |

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

- IP Evidence Composite Score: **52.54 / 100**
- Data Coverage Rate: **1.0**
- Bridge Signal: **IP_EVIDENCE_NEUTRAL**
- Bridge Adjustment Points: **0.0**

| Component | 의미 | Weight | Score | Contribution | Status |
|---|---|---:|---:|---:|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 82.25 | 20.56 | OK |
| claim_defense | 청구항 방어 범위 | 0.3 | 60.93 | 18.28 | OK |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 30.26 | 7.57 | OK |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 30.68 | 6.14 | OK |

해석:
- 법적 안정성과 청구항 방어력은 IP 포트폴리오의 방어력을 보여줍니다.
- 인용 영향력과 글로벌 패밀리 확장성은 시장 내 참조 가치와 해외 권리 확장성을 보여줍니다.
- 본 지표는 직접적인 매출·수주 증거가 아니므로, 사업화·고객 채택·양산·FCF 개선 근거와 함께 해석해야 합니다.

<!-- IP_EVIDENCE_COMPOSITE_END -->

<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->
## IP Evidence Composite → Tech-to-Value Bridge 반영

- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.
- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points

- IP Evidence Composite Score: 52.54
- IP Evidence Bridge Signal: IP_EVIDENCE_NEUTRAL
- IP Evidence Adjustment Points: 0.0
- Peer-adjusted Score Before IP Evidence: 50.72
- Final Bridge Score After IP Evidence: 50.72
- Source: `C:/Agent_6.9/data/반도체/덕산테코피아/tech/tech_ip_evidence_composite.json`

해석:
- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.
- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.
<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->

<!-- TECH_INVESTOR_SCORECARD_START -->
## 개인투자자용 Tech 최종 점수판

- **대상 기업:** 덕산테코피아
- **최종 Tech 점수:** 60.13/100
- **최종 판정:** 기술성은 확인되나 양산·고객 채택·재무성과 전환을 계속 추적해야 함 `COMMERCIALIZATION_WATCH`
- **해석 원칙:** 특허 수, 기술 키워드 수, 뉴스 수를 각각 따로 과장하지 않고, 사업화 연결 가능성과 근거 직접성을 하나의 최종 점수로 통합했습니다.

### 1) 최종 점수 구성
| 구성요소 | 점수 | 가중치 | 가중 반영 | 의미 |
|---|---:|---:|---:|---|
| Tech-to-Value Bridge | 50.72 | 0.40 | 20.29 | 기술이 고객 채택·양산·매출 전환으로 이어질 가능성 |
| IP Evidence Composite | 52.54 | 0.20 | 10.51 | 권리 안정성·청구항·인용·패밀리 기반 특허 품질 |
| Excel 기반 정량 근거 | 82.73 | 0.15 | 12.41 | 템플릿/수식 기준에 맞춰 실제 기업별 근거가 얼마나 채워졌는지 |
| 근거 직접성·충분성 | 63.17 | 0.15 | 9.48 | Chair가 개인투자자에게 설명할 수 있는 근거의 직접성 |
| 사업화·성장자금 지속성 | 74.50 | 0.10 | 7.45 | R&D·특허·정부과제·기술이전·CAPEX/희석성 자금조달이 사업화와 연결되는 정도 |

### 2) 핵심 해석
- 덕산테코피아의 개인투자자용 Tech 최종 점수는 60.13/100이며, 판정은 기술성은 확인되나 양산·고객 채택·재무성과 전환을 계속 추적해야 함입니다.
- 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(50.72)와 IP Evidence(52.54) 및 Excel 기반 정량 근거(82.73)를 함께 반영했습니다.
- 투자자가 확인할 핵심 근거는 9개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다.

### 3) 개인투자자가 확인할 근거
| ID | 출처 | 근거 | 값 | 강도 |
|---|---|---|---:|---|
| tech.inv.ev.001 | tech_to_value | **최종 Tech-to-Value Bridge**: 덕산테코피아의 최종 기술-사업화 연결 점수는 50.72이며, Chair에는 기술성보다 고객 채택·양산·매출 전환 가능성을 우선 반영합니다. | 50.72점 | 상 |
| tech.inv.ev.002 | kipris_ip_evidence | **IP Evidence Composite**: 법적 안정성·청구항 방어력·인용 영향력·해외 패밀리 확장성을 합성한 IP Evidence Composite Score는 52.54입니다. | 52.54점 | 상 |
| tech.inv.ev.003 | kipris_legal | **권리 안정성**: 등록률 0.7895, 존속률 0.9667, 권리 안정성 점수 82.25를 확인했습니다. | 82.25점 | 중 |
| tech.inv.ev.004 | kipris_claim | **청구항 방어력**: 청구항 수 365, 독립항 추정 75, claim defense score 60.93입니다. | 60.93점 | 중 |
| tech.inv.ev.005 | kipris_citation | **인용 영향력**: 전방/후방 인용 및 기술 영향력 점수 기준 IP_CITATION_FALLBACK_ESTIMATED입니다. | - | 중 |
| tech.inv.ev.006 | kipris_family | **글로벌 패밀리 확장성**: 해외 패밀리 비중 0.2368, 감지 지역 ['JP', 'US', 'WO'], global extension score 30.68입니다. | 30.68점 | 중 |
| tech.inv.ev.007 | tech_summary | **Tech Agent 핵심 해석**: 덕산테코피아의 개인투자자용 Tech 최종 점수는 60.13/100이며, 판정은 기술성은 확인되나 양산·고객 채택·재무성과 전환을 계속 추적해야 함입니다. | - | 중 |
| tech.inv.ev.008 | tech_summary | **Tech Agent 핵심 해석**: 최종 판단은 단순 특허 수보다 Tech-to-Value Bridge(50.72)와 IP Evidence(52.54) 및 Excel 기반 정량 근거(82.73)를 함께 반영했습니다. | - | 중 |
| tech.inv.ev.009 | tech_summary | **Tech Agent 핵심 해석**: 투자자가 확인할 핵심 근거는 6개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다. | - | 중 |

### 4) 한계와 보완 필요사항
- 이 점수는 투자수익률 예측값이 아니라 기술-사업화 근거의 설명 가능성 점수입니다.
- KIPRIS Plus 유료 endpoint 접근 권한 또는 호출 제한으로 일부 청구항·패밀리·인용 데이터가 부족하면 보수적으로 반영합니다.
- Excel 템플릿 값은 복사 근거가 아니라 정량화 프레임이며, 실제 기업별 자료가 채워진 항목만 점수화합니다.
- CB/BW·유상증자·정부과제·기술이전 신호는 성장자금과 희석/오버행 리스크를 분리해 보조 레이어로만 해석합니다.
- R&D 비용은 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진은 commercial outcome으로 구분합니다.
<!-- TECH_INVESTOR_SCORECARD_END -->

<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->
# 덕산테코피아 Tech Intake Value Evidence Bridge

## 1. 요약
- 생성 시각: 2026-05-25T22:53:03
- 종합 점수: 80.13/100
- 종합 라벨: VALUE_EVIDENCE_STRONG
- 원천 문서 수: 159개

## 2. 기술 → 사업화 → 재무 연결 근거
| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |
|---|---|---:|---:|---:|---:|---|
| 고객 채택 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 고객 채택 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 양산 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 양산 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 매출 전환 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 매출 전환 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| IP 품질 | 직접 근거 확인 | 52.54 | 4 | 0 | 0 | KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. 특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다. |
| 마진·원가·현금흐름 연결 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 마진·원가·현금흐름 연결 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |

## 3. 대표 근거

### 고객 채택
- [DIRECT_EVIDENCE] 재무제표 작성기준당사는 주식회사 등의 외부감사에 관한 법률 제5조 1항 1호에서 규정하고 있는 국제회계기준위원회의 국제회계기준을 채택하여 정한 회계처리기준인 한국채택국제회계기준에 따라 재무제표를 작성하였습니다.당사의 재무제표는 기업회계기준서 제1027호 '연결재무제표와 별도재무제표'에 따른 별도재무제표로서 지배기업, 관계기업의 투자자 또는 공동지배기업의 참여자가 투자자산을 피투자자의 보고된 성과와 순자산에 근거하지 않고 직접적인 지분 투자에 근거한 회계처리로 표시한 재무제표입니다. (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] (2) 기능통화와 표시통화당사는 재무제표에 포함되는 항목들에 대하여 영업활동이 이루어지는 주된 경제환경의 통화(기능통화)인 원화를 이용하여 측정하고 있으며, 재무제표는 당사의 기능통화인 '원'으로 표시되어있습니다.(3) 추정과 판단한국채택국제회계기준에서는 재무제표를 작성함에 있어서 회계정책의 적용이나, 보고기간말 현재 자산, 부채 및 수익, 비용의 보고금액에 영향을 미치는 사항에 대하여 경영진의 최선의 판단을 기준으로 한 추정치와 가정의 사용을 요구하고 있습니다. (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=채택, 적용, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 3.1 당사가 채택한 제ㆍ개정 기준서 및 해석서(1) 기업회계기준서 제1021호 '환율변동효과'와 기업회계기준서 제1101호 '한국채택국제회계기준의 최초채택' 개정 - 교환가능성 결여통화의 교환가능성을 평가하고 다른 통화와 교환이 가능하지 않다면 현물환율을 추정하며 관련 정보를 공시하도록 하고 있습니다. (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] (2) 한국채택국제회계기준 연차개선 Volume 11 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=채택, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 한국채택국제회계기준 연차개선 Volume 11은 2026년 1월 1일 이후 시작하는 회계연도부터 적용되며, 조기적용이 허용됩니다. (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=채택, 적용, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### 양산
- [DIRECT_EVIDENCE] - **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. (source=data/반도체/덕산테코피아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다. (source=data/반도체/덕산테코피아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 | (source=data/반도체/덕산테코피아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | 양산 | 직접 근거 | 88.00/100 | 17건 | 63건 | 0건 | (source=data/반도체/덕산테코피아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/덕산테코피아/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 매출 전환
- [DIRECT_EVIDENCE] 회사는 재무제표에 대한 주석 37에서 설명하고 있는 바와 같이 매출 등 중요한 영업활동에서 특수관계자에 대한 거래가 높은 비중을 차지하고 있습니다.따라서, 특수관계자와의 거래 및 잔액이 집계되고 공시되는 과정의 복잡성으로 인하여 공시가 완전하고 정확하게 이루어지지 아니할 위험을 고려하여 우리는 특수관계자와의 거래 및 잔액 공시의 적정성을 핵심감사사항으로 식별하였습니다. (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 매출채권 및 기타유동채권 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 매출채권 및 기타비유동채권 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 지분상품은 현금성자산에서 제외되나, 상환일이 정해져 있고 취득일로부터 상환일까지의 기간이 단기인 우선주와 같이 실질적으로 현금성자산인 경우에는 현금성자산에 포함됩니다.(3) 재고자산재고자산의 단위원가는 월총평균법(미착품은 개별법)으로 결정하고 있으며, 취득원가는 매입원가, 전환원가 및 재고자산을 이용가능한 상태로 준비하는데 필요한 기타 원가를 포함하고 있습니다.재고자산의 판매에 따른 수익을 인식하는 기간에 재고자산의 장부금액을 매출원가로인식하고 있습니다. (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=매출, 판매, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 재고자산을 순실현가능가치로 감액함에 따른 평가손실과 모든 감모손실은 감액이나 감모가 발생한 기간에 비용으로 인식되며, 재고자산의 순실현가능가치의 상승으로 인한 재고자산평가손실의 환입은 환입이 발생한 기간의 비용으로 인식된 재고자산의 매출원가에서 차감됩니다.(4) 금융상품1) 인식 및 최초 측정매출채권과 발행 채무증권은 발행되는 시점에 최초로 인식됩니다. (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=매출, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### 마진·원가·현금흐름 연결
- [DIRECT_EVIDENCE] 영업활동으로 인한 현금흐름 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 영업에서 창출된 현금흐름 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 투자활동으로 인한 현금흐름 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] 재무활동으로 인한 현금흐름 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)
- [DIRECT_EVIDENCE] - 계약상 현금흐름의 시기나 금액을 변경시키는 계약조건이 기업에 미치는 영향과 기업이 노출되는 정도를 금융상품의 각 종류별로 공시 (source=data/반도체/덕산테코피아/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://dart.fss.or.kr/dsab007/main.do?option=corp)

### IP 품질
- [DIRECT_EVIDENCE] legal_status: status=COLLECTED, count=None, score=0.7895, signal=None (source=data/반도체/덕산테코피아/tech/duksan_tech_ip_legal_features.json, keywords=legal_status, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] claims: status=COLLECTED, count=365.0, score=None, signal=None (source=data/반도체/덕산테코피아/tech/duksan_tech_ip_claim_features.json, keywords=claims, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] citations: status=COLLECTED, count=38, score=None, signal=None (source=data/반도체/덕산테코피아/tech/duksan_tech_ip_citation_features.json, keywords=citations, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] family: status=COLLECTED, count=8.0, score=None, signal=None (source=data/반도체/덕산테코피아/tech/duksan_tech_ip_family_features.json, keywords=family, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] composite: status=COLLECTED, count=None, score=52.54, signal=IP_EVIDENCE_NEUTRAL (source=data/반도체/덕산테코피아/tech/duksan_tech_ip_evidence_composite.json, keywords=composite, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)

## 4. 다음 확인 포인트
- 고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인
- 양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인
- 매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인
- IP 품질: 청구항·인용·패밀리·존속 상태가 수집된 상태이므로 IP Evidence Composite와 Bridge 조정값의 방향성을 점검
- 마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인

## 5. URL 인식 결과 및 대체 조회 URL
- **KIPRIS**
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c933c9a35f17d2d8d16852776866d9f2a202664ebeecc284d6488b3f8e61c7bed668a8f5f8da2d8e7a9ad0d2ee46bfcf4021e3df2df386b7f39
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=452306798ef1fd03bf8e5ba4e1dbf726afed5844fd08eb6894f2f21b66acb5ee7af171181198b6f28890cf1c778992f5b0d9bb6da89c0d5eb940b8935e001b558a7f5d71b429a831
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e00c539e3af993238babc263eabb29d035b7166f50989895a5c720a29645256076969935af89c6d645b0fd7305bdf13e614f47c3218a0f77523
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93c23d7d32ee4b79378b2d1c7a9b2b7687a21e618d370970a67c95c8084168196e093a10ac061ffa35f9616bab729923c8a996b40e996212cc
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e00e523148fb7ac78f0c3c8683b10aa8ebe0211bf547d64c143dd281cf656de78fde555210cad3bac879027baadf3daad0c5c519db78453a9d4
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=2ba38663aa11ff0f6ca91af6061a2e00a758b10f588f77a53c0af9566a6052624ab1325b654e98cc61bb14e054f2f77ff64386b5c629a389c44a318c2f355cb9fbb6c2d606210ef4
  - fallback: https://www.kipris.or.kr/khome/main.jsp
  - fallback: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+KIPRIS+%ED%8A%B9%ED%97%88
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC
- **TECH_OUTPUT**
  - detected: https://www.dstp.co.kr/en/rnd/area.php
  - detected: https://www.dstp.co.kr/en/rnd/technology.php
  - detected: https://www.dstp.co.kr/en/ir/stock-information.php
  - detected: https://www.dstp.co.kr/business/semiconductor-materials.php
  - detected: https://www.dstp.co.kr/en/business/battery-materials.php
  - detected: https://www.dstp.co.kr
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
- **IR_HOMEPAGE**
  - detected: https://www.dstp.co.kr/en/rnd/area.php
  - detected: https://www.dstp.co.kr/en/rnd/technology.php
  - detected: https://www.dstp.co.kr/en/ir/stock-information.php
  - detected: https://www.dstp.co.kr/business/semiconductor-materials.php
  - detected: https://www.dstp.co.kr/en/business/battery-materials.php
  - detected: https://www.dstp.co.kr
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+IR
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88
- **DART**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://dart.fss.or.kr/dsab007/main.do?option=corp
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+DART+%EC%82%AC%EC%97%85%EB%B3%B4%EA%B3%A0%EC%84%9C
- **VALUATION**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
  - fallback: https://www.google.com/search?q=%EB%8D%95%EC%82%B0%ED%85%8C%EC%BD%94%ED%94%BC%EC%95%84+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF
- **FINANCE**
  - detected: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#sessionnotcreatedexception
  - fallback: https://dart.fss.or.kr/
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->

<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->
# Technology Lifecycle Features

- company: 덕산테코피아
- status: OK
- overall_lifecycle_stage: DECLINE_OR_SHIFT
- overall_lifecycle_score: 31.58
- source_patent_csv: `data\반도체\덕산테코피아\tech\duksan_kipris_bibliographic_normalized.csv`

## Summary
power_thermal_efficiency, process_yield_quality, semiconductor_materials 관련 최근 출원 밀도가 약해져 쇠퇴 또는 차세대 기술 전환 가능성을 점검해야 합니다.

## Keyword Trends
| keyword | stage | score | total | recent | baseline | trend_ratio | reason |
|---|---:|---:|---:|---:|---:|---:|---|
| advanced_packaging | INTRODUCTION_OR_SPARSE | 35.0 | 2 | 0 | 0 | None | 출원 수가 적어 도입기 또는 확인 제한으로 분류합니다. |
| hbm_ai_memory | NO_DATA | 0.0 | 0 | 0 | 0 | None | 특허 출원 추세 데이터가 없습니다. |
| fan_out_wlp | NO_DATA | 0.0 | 0 | 0 | 0 | None | 특허 출원 추세 데이터가 없습니다. |
| bump_rdl_interposer | UNCERTAIN | 40.0 | 5 | 0 | 1 | 0.0 | 출원 추세만으로 수명주기 단계를 단정하기 어렵습니다. |
| semiconductor_test | NO_DATA | 0.0 | 0 | 0 | 0 | None | 특허 출원 추세 데이터가 없습니다. |
| semiconductor_materials | DECLINE_OR_SHIFT | 30.0 | 7 | 0 | 5 | 0.0 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| process_yield_quality | DECLINE_OR_SHIFT | 30.0 | 10 | 0 | 5 | 0.0 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| power_thermal_efficiency | DECLINE_OR_SHIFT | 30.0 | 14 | 0 | 4 | 0.0 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |

## External Signals
- status: NOT_PROVIDED
- summary: 논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.
<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->

<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->
# Certification & Standards Features

- company: 덕산테코피아
- status: OK
- certification_signal: CERTIFICATION_STRONG
- certification_score: 40.24
- quality_gate_stage: 5 / SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED
- evidence_count: 5

## Summary
FDA, GMP, SEMICONDUCTOR_QUALIFICATION 관련 근거가 확인되어 고객 품질·상용화 게이트 통과 가능성을 강하게 보강합니다. 단계: SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED.

## Confirmed Keys
FDA, GMP, SEMICONDUCTOR_QUALIFICATION

## Evidence
| certification | status | confidence | source | evidence |
|---|---:|---:|---|---|
| GMP | CONFIRMED | HIGH | duksan_tech_excel_frame_evidence.json | / 양산 승인 기사 / 테스트베드 기사 / 개발 지연·검증 이슈 기사", "quantifiable": "필요 인증 수, 예상 개발 기간(개월), 검증 단계 수, 고객 테스트 횟수", "item_name": "인증 종류", "content": "ISO, GMP, 자동차 품질규격 등 구체 인증명 리스트는 직접 확인 불가\n  |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | duksan_tech_excel_frame_evidence.json | , "middle_source": "사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인\n규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건\n기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지 |
| GMP | CONFIRMED | HIGH | duksan_tech_excel_frame_evidence.md | 준 / 공급 승인 조건 기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지연·검증 이슈 기사 - 정량화 가능 부분: 필요 인증 수, 예상 개발 기간(개월), 검증 단계 수, 고객 테스트 횟수 - 수치 신호 수: 0 / 키워드 신호 수: 5 - 내용: ISO, GMP, 자동차 품질규격 등 구체 인증명 |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | duksan_tech_excel_frame_evidence.md | 수 / 출처: 사업보고서 / 규제자료 / 기사 > 사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인 규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건 기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사  |
| FDA | MENTIONED | LOW | kipris_duksan_patents.csv | 공된다. / http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=ed43a0609e94d6e22d01c5c32ba711cfa5deddbc755cf187f6d3757ef79ca6fb35b40029cad8a01c83497d4b4b7c359d87a36e3fda61940e3560536772a |
<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->
