# 네패스 Tech Chair Compact Summary

## 1. Chair 반영용 핵심 판단
- **의견:** 매수
- **Tech-to-Value:** base 72.00/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **Peer-adjusted:** 80.53/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **IP Evidence Composite:** 46.17/100 / IP 근거 중립형(IP_EVIDENCE_NEUTRAL)
- **ML 우선 반영:** Technology Differentiation Score + Tech-to-Value Evidence Confidence + IP Evidence Composite Score
- **해석:** 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다.

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
| Technology Differentiation Score | 57.59/100 / 50.00%ile | peer 대비 기술/IP 포트폴리오 차별성 |
| Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 |
| Patent Momentum | 52.64/100 | 최근 특허 활동의 현재성·지속성 |
| IP Legal Stability | 70.47/100 | 등록률·존속률·소멸/거절/취하 비중 기반 권리 안정성 |
| IP Claim Defense | 29.09/100 | 청구항 수·독립항 수·수집 커버리지 기반 특허 방어력 |
| IP Citation Impact | 확인 제한 | 피인용·외부인용 기반 기술 영향력/시장 참조 가치 |
| IP Global Extension | 55.00/100 | 해외 패밀리·PCT/WO·미국/일본/유럽/중국 확장성 |
| IP Evidence Composite | 46.17/100 | 법적 안정성·청구항·인용·패밀리 특허를 통합한 종합 IP 근거 점수 |
| IP Evidence Bridge Signal | IP_EVIDENCE_NEUTRAL / 0.00점 | Tech-to-Value Bridge 보수적 보정 신호 |
| Peer-adjusted Bridge | 80.53/100 | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 |

## 4. KIPRIS/IP 정량 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 8,602건 |
| 회사 출원인/권리자 매칭 | 7,733건 |
| 등록 특허 | 4,588건 |
| 존속 가능 특허 | 4,981건 |
| 최근 5년 특허 | 382건 |
| IPC/CPC 다양성 | 126개 |
| H01L 등 핵심 IPC 특허 | 36건 |
| KIPRIS 등록률(추정) | 73.81% |
| 등록특허 중 존속률(추정) | 77.74% |
| 소멸·거절·취하 등 부정 처분 비중(추정) | 37.86% |
| 권리자 정보 반영률 | 100.00% |
| 초록/도면 반영률 | 100.00% / 96.43% |
| 청구항 수집 커버리지 | 0.00% |
| 수집 청구항 / 독립항(추정) | 0항 / 0항 |
| 특허당 평균 청구항 / 독립항 비중 | 확인 제한 / 확인 제한 |
| 피인용 총합 / 외부 피인용 | 확인 제한 / 확인 제한 |
| 외부 피인용률 | 확인 제한 |
| 해외 패밀리 보유율 | 100.00% |
| PCT/WO / US / JP / EP / CN | 확인 제한 / 확인 제한 / 확인 제한 / 확인 제한 / 확인 제한 |

## 5. IP Evidence Composite 세부 구성
| 구성 요소 | Weight | Score | Contribution | Status |
|---|---:|---:|---:|---|
| 등록·존속 안정성 | 0.25 | 70.47/100 | 17.62점 | OK |
| 청구항 방어 범위 | 0.3 | 29.09/100 | 8.73점 | OK |
| 인용 기반 기술 영향력 | 0.25 | 35.29/100 | 8.82점 | OK |
| 해외 패밀리 기반 글로벌 확장성 | 0.2 | 55.00/100 | 11.00점 | OK |

## 6. 사업화 연결 체크
| 연결 항목 | 상태 | 점수 | 직접 | 간접 | 확인 제한 |
|---|---|---:|---:|---:|---:|
| 고객 채택 | 직접 근거 | 88.00/100 | 8건 | 12건 | 0건 |
| 양산 | 직접 근거 | 88.00/100 | 17건 | 63건 | 0건 |
| 매출 전환 | 직접 근거 | 88.00/100 | 9건 | 16건 | 0건 |
| FCF/현금흐름 | 간접 근거 | 46.50/100 | 0건 | 2건 | 0건 |

## 7. Chair 반영 원칙
- Chair 최종 보고서에는 Tech 상세 표 전체를 붙이지 않고 compact summary만 반영합니다.
- 상세 Excel-frame/ML 표는 Tech Agent 산출물과 부록 파일에서 확인합니다.
- 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다.
- IP Evidence Composite Score는 직접 매출 근거가 아니라 특허 포트폴리오의 질적 보조 신호로만 사용합니다.

<!-- IP_EVIDENCE_COMPOSITE_START -->

#### IP Evidence Composite Score

KIPRIS 기반 IP Feature 4종을 통합해 특허 포트폴리오의 질적 근거를 평가했습니다. 이 점수는 특허 수량이 아니라 등록·존속 안정성, 청구항 방어 범위, 인용 기반 기술 영향력, 해외 패밀리 확장성을 종합한 Tech-to-Value Bridge 보조 지표입니다.

- IP Evidence Composite Score: **46.17 / 100**
- Data Coverage Rate: **1.0**
- Bridge Signal: **IP_EVIDENCE_NEUTRAL**
- Bridge Adjustment Points: **0.0**

| Component | 의미 | Weight | Score | Contribution | Status |
|---|---|---:|---:|---:|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 70.47 | 17.62 | OK |
| claim_defense | 청구항 방어 범위 | 0.3 | 29.09 | 8.73 | OK |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 35.29 | 8.82 | OK |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 55.0 | 11.0 | OK |

해석:
- 법적 안정성과 청구항 방어력은 IP 포트폴리오의 방어력을 보여줍니다.
- 인용 영향력과 글로벌 패밀리 확장성은 시장 내 참조 가치와 해외 권리 확장성을 보여줍니다.
- 본 지표는 직접적인 매출·수주 증거가 아니므로, 사업화·고객 채택·양산·FCF 개선 근거와 함께 해석해야 합니다.

<!-- IP_EVIDENCE_COMPOSITE_END -->

<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->
## IP Evidence Composite → Tech-to-Value Bridge 반영

- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.
- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points

- IP Evidence Composite Score: 54.05
- IP Evidence Bridge Signal: IP_EVIDENCE_NEUTRAL
- IP Evidence Adjustment Points: 0.0
- Peer-adjusted Score Before IP Evidence: 80.53
- Final Bridge Score After IP Evidence: 80.53
- Source: `C:/Agent_6.9/data/반도체/네패스/tech/tech_ip_evidence_composite.json`

해석:
- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.
- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.
<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->

<!-- INVESTOR_TECH_SCORE_START -->

## 개인투자자용 최종 Tech Scorecard

- **Final Investor Tech Score:** 75.95/100
- **등급/신호:** B+ / 사업화 근거 우수
- **해석:** 개인투자자 관점에서 기술 근거와 전환 가능성이 비교적 설득력 있습니다.
- **산식:** `0.35*Tech-to-Value + 0.20*Evidence Confidence + 0.15*IP Evidence + 0.15*Differentiation + 0.10*Patent Momentum + 0.05*Excel-frame`

| 구성요소 | 점수 | 비중 | 해석 |
|---|---:|---:|---|
| Tech-to-Value Bridge | 80.53/100 | 35% | 기술이 고객·양산·매출로 이어질 가능성 |
| Evidence Confidence | 100.00/100 | 20% | 근거-주장 연결의 신뢰도 |
| IP Evidence Composite | 46.17/100 | 15% | 법적 안정성·청구항·인용·패밀리 종합 |
| Technology Differentiation | 79.19/100 | 15% | peer 대비 기술 차별성 |
| Patent Momentum | 50.00/100 | 10% | 최근 특허/IP 활동성 |
| Excel-frame Evidence | 79.19/100 | 5% | 템플릿 기반 정량·정성 근거 충실도 |

### 핵심 근거 카드

| 구분 | 제목 | 값 | 근거 | 투자자 관점 의미 |
|---|---|---:|---|---|
| 고객 구매 이유 | IR: Investment Highlights / 제품 경쟁력 / 고객사 채택 배경 / 고객 효익 설명 슬라이드 / 양산 적용 사례 제품 홍보 ... | 1, 2, 3 | 1) IR 2) 제품 홍보 자료 3) 인터뷰 기사 | 엑셀 프레임 기반 기술 포지션을 점수와 별개로 확인할 수 있는 근거입니다. |
| 경쟁 우위 요소/대체가능성 | 사업보고서: 시장 경쟁상황 / 진입장벽 / 기술 경쟁력 / 주요 원재료·공정 우위 / 위험요인 / 신규 경쟁사 언급 특허: 등록특허 수 / 핵심... | 정성 근거 중심 | 사업보고서 / 특허 / 기사 | 엑셀 프레임 기반 기술 포지션을 점수와 별개로 확인할 수 있는 근거입니다. |
| 기술 경쟁력 종합 판단 | 내부 종합 로직: ① 기술 독창성 ② 양산성 ③ 고객 채택도 ④ 수익성 기여 ⑤ 확장성 ⑥ 진입장벽 ⑦ 투자 지속성 점수화 후 총점 산출 | 1, 7, 5 | 내부 종합 | 엑셀 프레임 기반 기술 포지션을 점수와 별개로 확인할 수 있는 근거입니다. |
| 신규 산업 진입 시 추가 인증/개발 부담 | 사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인 규제자료: 산업별 필수 인증 / 시... | 정성 근거 중심 | 사업보고서 / 규제자료 / 기사 | 엑셀 프레임 기반 기술 포지션을 점수와 별개로 확인할 수 있는 근거입니다. |
| 대표 기술 | 사업보고서: 사업의 내용 → 주요 제품 및 서비스 / 연구개발활동 / 생산공정·기술설명 / 원재료 및 전구체 설명 / 신규사업 내용 기업 홈페이... | 정성 근거 중심 | 사업 보고서, 기업 홈페이지, 특허 사이트 | 엑셀 프레임 기반 기술 포지션을 점수와 별개로 확인할 수 있는 근거입니다. |
| 핵심 제품/서비스 | 사업보고서: 사업부문별 매출 / 제품별 매출 / 주요 제품 매출 비중 / 수출 비중 / 사업부별 실적 홈페이지: 제품 포트폴리오 / 제품 카테고... | 정성 근거 중심 | 사업 보고서 - 매출 구성 홈페이지 매출구성 IR 발표자료 | 엑셀 프레임 기반 기술 포지션을 점수와 별개로 확인할 수 있는 근거입니다. |
| 현재 활용 산업 + 확장 산업 | 사업보고서: 사업의 내용 → 주요 수요처 / 전방산업 / 응용처 / 고객 산업 / 신규 적용처 / 중장기 성장전략 / 시장전망 / 신규사업 계획 | 정성 근거 중심 | 사업 보고서 | 엑셀 프레임 기반 기술 포지션을 점수와 별개로 확인할 수 있는 근거입니다. |
| Tech-to-Value | 최종 기술가치 전환 점수 | 80.53/100 | Peer-adjusted Bridge와 IP Evidence Composite 조정을 반영한 최종 전환 점수입니다. 현재 값: 80.53/100. | 기술이 매출·양산·고객 채택으로 이어질 가능성을 보는 핵심 축입니다. |
| IP Evidence | IP Evidence Composite | 46.17/100 | 현재 Composite Score는 46.17/100입니다. | 특허 수 자체보다 방어력·영향력·글로벌 확장성까지 같이 보는 축입니다. |
| Differentiation | 기술 차별화 점수 | 79.19/100 | 현재 기술 차별화 점수는 79.19/100입니다. | 비슷한 반도체 peer 안에서 얼마나 차별적인지 판단하는 축입니다. |

### 데이터 품질 메모

- Excel-frame 행 수: 8개
- 숫자 근거 포함 행 수: 8개
- Fallback/추정 구성요소: technology_differentiation_score, patent_momentum_score, evidence_confidence_score

<!-- INVESTOR_TECH_SCORE_END -->

<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->
# 네패스 Tech Intake Value Evidence Bridge

## 1. 요약
- 생성 시각: 2026-05-25T22:31:44
- 종합 점수: 80.36/100
- 종합 라벨: VALUE_EVIDENCE_STRONG
- 원천 문서 수: 177개

## 2. 기술 → 사업화 → 재무 연결 근거
| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |
|---|---|---:|---:|---:|---:|---|
| 고객 채택 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 고객 채택 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 양산 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 양산 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 매출 전환 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 매출 전환 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| IP 품질 | 직접 근거 확인 | 54.05 | 3 | 0 | 1 | KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. 특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다. |
| 마진·원가·현금흐름 연결 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 마진·원가·현금흐름 연결 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |

## 3. 대표 근거

### 고객 채택
- [DIRECT_EVIDENCE] 매출 및 수주상황</TD> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=수주, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <P>특히 전자재료 사업부문은 높은 국내 시장 점유율과 그간 집약한 기술 노하우를 바탕으로 수입에 의존하던 Chemical을 국산화하였으며 내재화를 통한 신뢰성 검증으로 주요 고객 대상 신규 매출을 기대하고 있습니다.</P> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=주요 고객, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 매출 및 수주상황</TITLE> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=수주, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <TD ALIGN="CENTER" WIDTH="320" HEIGHT="23">당사→고객사</TD> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=고객사, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 수주상황</P> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=수주, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 양산
- [DIRECT_EVIDENCE] 따라서, 우수한 품질의 제품을 개발하기 위하여 1) 우수 연구 인력의 확보, 2) 부품소재 개발을 위한 핵심기술 확보, 3) 제품 양산을 위한 생산기술 그리고 4) 고객에게 첨단제품 소개 및 신속한 기술지원 등이 종합적으로 갖추어져야 합니다.</P> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 이어지는 연결고리를 계속 추적해야 하는 상태입니다. (source=data/반도체/네패스/tech/nepes_chair_compact_tech_test.md, keywords=양산, urls=https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+IR, https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C)
- [DIRECT_EVIDENCE] | 양산 | 직접 근거 | 88.00/100 | 직접 16건 / 간접 63건 / 확인 제한 0건 | (source=data/반도체/네패스/tech/nepes_chair_compact_tech_test.md, keywords=양산, urls=https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+IR, https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C)
- [DIRECT_EVIDENCE] | Tech-to-Value Evidence Confidence | 78.80/100 | 고객 채택·양산·매출·FCF 근거의 직접성을 보수적으로 평가합니다. (source=data/반도체/네패스/tech/nepes_chair_compact_tech_test.md, keywords=양산, urls=https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+IR, https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/네패스/tech/nepes_chair_compact_tech_test.md, keywords=양산, urls=https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+IR, https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C)

### 매출 전환
- [DIRECT_EVIDENCE] 매출 및 수주상황</TD> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=매출, 수주, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 관련 교육사업 참여기업 조건으로 '정보통신업' 등 신규 업종을 요구 하고 있어 입찰 제한 요건을 개선하고 교육사업 매출을 증가 될 것으로 예상됩니다. (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=매출, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <P>4.사업 추진현황(조직 및 인력구성 현황, 연구개발활동 내역, 제품 및 서비스 개발 진척도 및 상용화 여부, 매출 발생여부 등) - 교육사업 입찰 제한 개선을 위한 신규업종 추가로 기존 교육사업과 동일한 사업으로 별도의 사업 추진현황은 없습니다.</P> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=매출, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <P> - 입찰 제한 개선으로 매출 극대화에 기여할 예정입니다.</P> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=매출, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <P>(전자재료 부문) 전자재료는 케미컬 시장의 특수성에 기인하여 변동성이 낮으며, 제품인 기능성 Chemical이 매출에 기여하기 시작하였습니다.</P> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=매출, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 마진·원가·현금흐름 연결
- [DIRECT_EVIDENCE] <P>연결회사는 중장기 경영계획 및 단기 경영전략을 통해 현금흐름을 모니터링하고 있으며, 일반적인 예상 운영비용을 충당할 수 있는 현금을 보유하고 있습니다. (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=현금흐름, 비용, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <TH WIDTH="566" ACOPYCOL="Y" ADELETECOL="Y" AMOVECOL="N" VALIGN="MIDDLE" COLSPAN="5" HEIGHT="23">계약상 현금흐름</TH> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 연결 현금흐름표</TITLE> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <TE ENG="Consolidated Statement Of CashFlows" ALIGN="CENTER" VALIGN="MIDDLE" WIDTH="591" HEIGHT="23" AUPDATECONT="N">연결 현금흐름표</TE> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] <TE ENG="Cash flows from (used in) operating activities" VALIGN="MIDDLE" WIDTH="381" HEIGHT="23" AUPDATECONT="N">영업활동현금흐름</TE> (source=data/반도체/네패스/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### IP 품질
- [DIRECT_EVIDENCE] legal_status: status=COLLECTED, count=None, score=0.7352, signal=None (source=data/반도체/네패스/tech/nepes_tech_ip_legal_features.json, keywords=legal_status, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] claims: status=COLLECTED, count=4823.0, score=None, signal=None (source=data/반도체/네패스/tech/nepes_tech_ip_claim_features.json, keywords=claims, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [PARTIAL_EVIDENCE] citations: status=NO_CITATION_COLLECTED, count=0, score=None, signal=None (source=data/반도체/네패스/tech/nepes_tech_ip_citation_features.json, keywords=citations, NO_CITATION_COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] family: status=COLLECTED, count=40.0, score=None, signal=None (source=data/반도체/네패스/tech/nepes_tech_ip_family_features.json, keywords=family, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] composite: status=COLLECTED, count=None, score=54.05, signal=IP_EVIDENCE_NEUTRAL (source=data/반도체/네패스/tech/nepes_tech_ip_evidence_composite.json, keywords=composite, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)

## 4. 다음 확인 포인트
- 고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인
- 양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인
- 매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인
- IP 품질: citations 데이터 보강 후 청구항·인용·패밀리·존속 상태를 재점수화
- 마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인

## 5. URL 인식 결과 및 대체 조회 URL
- **KIPRIS**
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c9328f5a912c888a1604ff579e87f821b091a0665246f3173a6cae241fd42c7005fb584f7181202ddb2669153aa54387f5f558cf6b7b6d352be
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c9328f5a912c888a1604ff579e87f821b091a0665246f3173a6cae241fd42c7005f99f63731d0311929be11400294078a7500be1e049034125a
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c9322af84f57b08f2914d8d6d578d04e03445d891357f9d9514d3d00ad20d4a18bd19eba5573d7be6aac19dee99cdc16abd632f246c9310f285
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c9322af84f57b08f2914d8d6d578d04e034c00c52ee695737d21b3f879b3a036daacbefcdab0ce327f373387ac5e1436b444e048689ba5bd44d
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93c040d70001b624f5684d1632e77fbbe56bbb3117cbeab3944e9633126c9d0314bacd1aee33943ab15d5a9bc96c0cdb5e4e90695e30d95718
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93f6548c790985d9b42df3b696cb0bd420628364929a7eeeebfe825a6a229a6517dc933a022c3933651a90fed613eac47cfdf019f60b965c6c
  - fallback: https://www.kipris.or.kr/khome/main.jsp
  - fallback: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+KIPRIS+%ED%8A%B9%ED%97%88
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC
- **IR_HOMEPAGE**
  - detected: https://www.nepes.co.kr
  - detected: http://www.nepesrua.co.kr
  - detected: http://www.nepes.co.kr
  - detected: https://www.nepes.co.kr/kr/business/semiconductor/overview.php
  - detected: https://www.nepes.co.kr/kr/business/semiconductor/plp.php
  - detected: https://www.nepes.co.kr/kr/business/it/em.php
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+IR
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88
- **TECH_OUTPUT**
  - detected: https://www.nepes.co.kr/kr/ir/ir_news.php?bgu=view&idx=1124
  - detected: https://www.nepes.co.kr
  - detected: http://www.nepes.co.kr
  - detected: https://www.nepes.co.kr/kr/business/semiconductor/overview.php
  - detected: https://www.nepes.co.kr/kr/business/semiconductor/plp.php
  - detected: https://www.nepes.co.kr/kr/business/it/em.php
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
- **DART**
  - detected: http://www.w3.org/2001/XMLSchema-instance
  - detected: http://www.nepes.co.kr
- **VALUATION**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
  - fallback: https://www.google.com/search?q=%EB%84%A4%ED%8C%A8%EC%8A%A4+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF
- **FINANCE**
  - detected: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#sessionnotcreatedexception
  - fallback: https://dart.fss.or.kr/
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->

<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->
# Technology Lifecycle Features

- company: 네패스
- status: OK
- overall_lifecycle_stage: DECLINE_OR_SHIFT
- overall_lifecycle_score: 30.24
- source_patent_csv: `data\반도체\네패스\tech\nepes_kipris_bibliographic_normalized.csv`

## Summary
advanced_packaging, bump_rdl_interposer, power_thermal_efficiency 관련 최근 출원 밀도가 약해져 쇠퇴 또는 차세대 기술 전환 가능성을 점검해야 합니다.

## Keyword Trends
| keyword | stage | score | total | recent | baseline | trend_ratio | reason |
|---|---:|---:|---:|---:|---:|---:|---|
| advanced_packaging | DECLINE_OR_SHIFT | 30.0 | 204 | 20 | 90 | 0.37 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| hbm_ai_memory | DECLINE_OR_SHIFT | 30.0 | 5 | 1 | 3 | 0.556 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| fan_out_wlp | UNCERTAIN | 40.0 | 14 | 0 | 0 | None | 출원 추세만으로 수명주기 단계를 단정하기 어렵습니다. |
| bump_rdl_interposer | DECLINE_OR_SHIFT | 30.0 | 175 | 18 | 68 | 0.441 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| semiconductor_test | DECLINE_OR_SHIFT | 30.0 | 13 | 1 | 7 | 0.238 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| semiconductor_materials | DECLINE_OR_SHIFT | 30.0 | 23 | 0 | 4 | 0.0 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| process_yield_quality | DECLINE_OR_SHIFT | 30.0 | 72 | 2 | 8 | 0.417 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| power_thermal_efficiency | DECLINE_OR_SHIFT | 30.0 | 78 | 2 | 29 | 0.115 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |

## External Signals
- status: NOT_PROVIDED
- summary: 논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.
<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->

<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->
# Certification & Standards Features

- company: 네패스
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
| FDA | MENTIONED | LOW | kipris_nepes_patents.csv | 명에 따른 감광성 도전 페이스트 조성물은 고해상도, 낮은 접촉저항, 우수한 보관 안정성 및 전기 비저항 등을 나타낼 수 있다. / http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=ed43a0609e94d6e22d01c5c32ba711cf8fc21fda6626cf8b16e9d70a6 |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | nepes_tech_excel_frame_evidence.json | , "middle_source": "사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인\n규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건\n기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지 |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | nepes_tech_excel_frame_evidence.md | 수 / 출처: 사업보고서 / 규제자료 / 기사 > 사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인 규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건 기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사  |
<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->
