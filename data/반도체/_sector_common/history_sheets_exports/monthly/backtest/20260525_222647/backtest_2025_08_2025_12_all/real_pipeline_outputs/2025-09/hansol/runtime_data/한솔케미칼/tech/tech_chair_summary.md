# 한솔케미칼 Tech Chair Compact Summary

## 1. Chair 반영용 핵심 판단
- **의견:** 매수
- **Tech-to-Value:** base 62.00/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **Peer-adjusted:** 84.00/100 / 사업화 추적형(COMMERCIALIZATION_WATCH)
- **IP Evidence Composite:** 39.06/100 / IP 근거 취약형(IP_EVIDENCE_WEAK)
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
| R&D 강도 | R&D 강도 | 4 | 확인 제한 | 중 | 필요 시 원천 근거 확인 |

## 3. 선택 ML/IP 요약
| ML/IP 신호 | 값 | Chair 해석 |
|---|---:|---|
| Technology Differentiation Score | 56.16/100 / 10.00%ile | peer 대비 기술/IP 포트폴리오 차별성 |
| Evidence Confidence | 88.00/100 | 고객 채택·양산·매출·FCF 근거의 직접성 |
| Patent Momentum | 70.35/100 | 최근 특허 활동의 현재성·지속성 |
| IP Legal Stability | 87.23/100 | 등록률·존속률·소멸/거절/취하 비중 기반 권리 안정성 |
| IP Claim Defense | 20.00/100 | 청구항 수·독립항 수·수집 커버리지 기반 특허 방어력 |
| IP Citation Impact | 확인 제한 | 피인용·외부인용 기반 기술 영향력/시장 참조 가치 |
| IP Global Extension | 25.00/100 | 해외 패밀리·PCT/WO·미국/일본/유럽/중국 확장성 |
| IP Evidence Composite | 39.06/100 | 법적 안정성·청구항·인용·패밀리 특허를 통합한 종합 IP 근거 점수 |
| IP Evidence Bridge Signal | IP_EVIDENCE_WEAK / -1.00점 | Tech-to-Value Bridge 보수적 보정 신호 |
| Peer-adjusted Bridge | 84.00/100 | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 |

## 4. KIPRIS/IP 정량 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 2,186건 |
| 회사 출원인/권리자 매칭 | 1,326건 |
| 등록 특허 | 826건 |
| 존속 가능 특허 | 1,133건 |
| 최근 5년 특허 | 357건 |
| IPC/CPC 다양성 | 217개 |
| H01L 등 핵심 IPC 특허 | 확인 제한 |
| KIPRIS 등록률(추정) | 68.20% |
| 등록특허 중 존속률(추정) | 100.00% |
| 소멸·거절·취하 등 부정 처분 비중(추정) | 8.20% |
| 권리자 정보 반영률 | 100.00% |
| 초록/도면 반영률 | 0.00% / 0.00% |
| 청구항 수집 커버리지 | 0.00% |
| 수집 청구항 / 독립항(추정) | 0항 / 0항 |
| 특허당 평균 청구항 / 독립항 비중 | 확인 제한 / 확인 제한 |
| 피인용 총합 / 외부 피인용 | 확인 제한 / 확인 제한 |
| 외부 피인용률 | 확인 제한 |
| 해외 패밀리 보유율 | 0.00% |
| PCT/WO / US / JP / EP / CN | 확인 제한 / 확인 제한 / 확인 제한 / 확인 제한 / 확인 제한 |

## 5. IP Evidence Composite 세부 구성
| 구성 요소 | Weight | Score | Contribution | Status |
|---|---:|---:|---:|---|
| 등록·존속 안정성 | 0.25 | 87.23/100 | 21.81점 | OK |
| 청구항 방어 범위 | 0.3 | 20.00/100 | 6.00점 | OK |
| 인용 기반 기술 영향력 | 0.25 | 25.00/100 | 6.25점 | OK |
| 해외 패밀리 기반 글로벌 확장성 | 0.2 | 25.00/100 | 5.00점 | OK |

## 6. 사업화 연결 체크
| 연결 항목 | 상태 | 점수 | 직접 | 간접 | 확인 제한 |
|---|---|---:|---:|---:|---:|
| 고객 채택 | 직접 근거 | 88.00/100 | 2건 | 22건 | 0건 |
| 양산 | 직접 근거 | 88.00/100 | 5건 | 31건 | 0건 |
| 매출 전환 | 직접 근거 | 88.00/100 | 11건 | 36건 | 0건 |
| FCF/현금흐름 | 직접 근거 | 88.00/100 | 1건 | 2건 | 0건 |

## 7. Chair 반영 원칙
- Chair 최종 보고서에는 Tech 상세 표 전체를 붙이지 않고 compact summary만 반영합니다.
- 상세 Excel-frame/ML 표는 Tech Agent 산출물과 부록 파일에서 확인합니다.
- 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다.
- IP Evidence Composite Score는 직접 매출 근거가 아니라 특허 포트폴리오의 질적 보조 신호로만 사용합니다.

<!-- IP_EVIDENCE_COMPOSITE_START -->

#### IP Evidence Composite Score

KIPRIS 기반 IP Feature 4종을 통합해 특허 포트폴리오의 질적 근거를 평가했습니다. 이 점수는 특허 수량이 아니라 등록·존속 안정성, 청구항 방어 범위, 인용 기반 기술 영향력, 해외 패밀리 확장성을 종합한 Tech-to-Value Bridge 보조 지표입니다.

- IP Evidence Composite Score: **39.06 / 100**
- Data Coverage Rate: **1.0**
- Bridge Signal: **IP_EVIDENCE_WEAK**
- Bridge Adjustment Points: **-1.0**

| Component | 의미 | Weight | Score | Contribution | Status |
|---|---|---:|---:|---:|---|
| legal_stability | 등록·존속 안정성 | 0.25 | 87.23 | 21.81 | OK |
| claim_defense | 청구항 방어 범위 | 0.3 | 20.0 | 6.0 | OK |
| citation_influence | 인용 기반 기술 영향력 | 0.25 | 25.0 | 6.25 | OK |
| global_extension | 해외 패밀리 기반 글로벌 확장성 | 0.2 | 25.0 | 5.0 | OK |

해석:
- 법적 안정성과 청구항 방어력은 IP 포트폴리오의 방어력을 보여줍니다.
- 인용 영향력과 글로벌 패밀리 확장성은 시장 내 참조 가치와 해외 권리 확장성을 보여줍니다.
- 본 지표는 직접적인 매출·수주 증거가 아니므로, 사업화·고객 채택·양산·FCF 개선 근거와 함께 해석해야 합니다.

<!-- IP_EVIDENCE_COMPOSITE_END -->

<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->
## IP Evidence Composite → Tech-to-Value Bridge 반영

- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.
- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points

- IP Evidence Composite Score: 52.94
- IP Evidence Bridge Signal: IP_EVIDENCE_NEUTRAL
- IP Evidence Adjustment Points: 0.0
- Peer-adjusted Score Before IP Evidence: 84.0
- Final Bridge Score After IP Evidence: 84.0
- Source: `C:/Agent_6.9/data/반도체/한솔케미칼/tech/tech_ip_evidence_composite.json`

해석:
- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.
- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.
<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->

<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->
# 한솔케미칼 Tech Intake Value Evidence Bridge

## 1. 요약
- 생성 시각: 2026-05-26T03:37:23
- 종합 점수: 80.19/100
- 종합 라벨: VALUE_EVIDENCE_STRONG
- 원천 문서 수: 171개

## 2. 기술 → 사업화 → 재무 연결 근거
| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |
|---|---|---:|---:|---:|---:|---|
| 고객 채택 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 고객 채택 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 양산 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 양산 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 매출 전환 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 매출 전환 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| IP 품질 | 직접 근거 확인 | 52.94 | 4 | 0 | 0 | KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. 특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다. |
| 마진·원가·현금흐름 연결 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 마진·원가·현금흐름 연결 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |

## 3. 대표 근거

### 고객 채택
- [DIRECT_EVIDENCE] <TD WIDTH="572" HEIGHT="23">삼성전자 (반도체사업부) 1차 Vender 선정</TD> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=삼성전자, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] 매출 및 수주상황</TITLE> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=수주, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] 또한 장기적인 공급안정이 가능한 거래선 개발이 가능하도록 기술 중심적인 영업활동을 전개하고, 고객감동 실천으로 평생고객을 확보하고자 하고 있습니다.- 정밀화학, 제지/환경: 지속적인 품질개선을 통하여 반도체세정용, LCD에천트용, 환경처리용 등 다양한 수요에 대응하고 시장지배력을 강화, 잉여물량은 수출시장을 개척하고, 다양한 GRADE 개발로 수요처의 요구 품질 수준에 적극 부응하여 판매 극대화 및 수익성 확보, 환경에 대한 중요성 홍보를 통한 시장규모 확대 노력- 전자 및 이차전지소재: 다양한 고객사의 Needs를 충족시킬 수 있도록 고객별 커스터마이즈된 제품 공급 및 신규제품 공동개발</P> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=고객사, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <P>- 전자재료 :차별화된 기술우위를 바탕으로 급격한 시장의 변화 및 고객의 요구에 신속히 대응하여 고객사 제품 승인을 지속적으로 추진 중이며, 제품 포트폴리오 다각화 및 성장 가능성이 높은 해외시장 개척을 통해 중,장기 매출 확대의 기반을 구축하고 있습니다.</P> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=고객사, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] 특히 고객사의 반도체라인 증설에 따라, 초고순도 과산화수소의 수요량이 꾸준히 증가하고 있습니다. (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=고객사, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)

### 양산
- [DIRECT_EVIDENCE] <TD WIDTH="257" VALIGN="MIDDLE" HEIGHT="23">퀀텀닷 양산기술 개발</TD> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TD ALIGN="CENTER" WIDTH="229" VALIGN="MIDDLE" HEIGHT="23">양산기술 확보 및 매출증대</TD> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TD WIDTH="257" VALIGN="MIDDLE" HEIGHT="23">2세대 퀀텀닷 양산 기술 개발</TD> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TD ALIGN="CENTER" WIDTH="229" VALIGN="MIDDLE" HEIGHT="23">양산기술 확보 및 신규매출 창출</TD> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TD ALIGN="CENTER" WIDTH="229" VALIGN="MIDDLE" HEIGHT="23">양산기술 개발 및 신규매출 창출</TD> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)

### 매출 전환
- [DIRECT_EVIDENCE] 또한 제지/환경제품으로 제지산업에서 부재료로 사용되는 라텍스외 제지약품, 폐수처리 등에 사용되는 고분자응집제 등을 생산하고 있습니다.2025년 누적 정밀화학 제품의 매출액은 217,726백만원으로, 전년 대비 8.9% 증가하였으며, 제지/환경 제품의 매출액은 110,064백만원으로 전년 대비 1.8% 증가하였습니다.</P> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=매출, 매출액, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <P>당사의 전자 및 이차전지소재 제품으로는 반도체 공정에서 반도체 박막을 형성하는 데에 사용하는 박막소재(Precursor), 디스플레이 제조에 사용되는 Resin 및 QD 등 전자소재 제품을 생산하고 있으며, 이차전지용 소재인 음극바인더, 분리막바인더, 실리콘음극재 등을 개발 및 생산하고 있습니다.2025년 누적 전자 및 이차전지소재 제품의 매출액은 324,714백만원으로, 전년 대비 37.1% 증가하였습니다.</P> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=매출, 매출액, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TH VALIGN="MIDDLE" USERMARK="BC0XDCDCDC" WIDTH="69" ACOPYCOL="Y" ADELETECOL="Y" AMOVECOL="N" HEIGHT="23">매출유형</TH> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=매출, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TH VALIGN="MIDDLE" USERMARK="BC0XDCDCDC" WIDTH="118" ACOPYCOL="Y" ADELETECOL="Y" AMOVECOL="N" HEIGHT="23">매출액(비율)</TH> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=매출, 매출액, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TD ALIGN="CENTER" WIDTH="69" USERMARK="BC0XDCDCDC" VALIGN="MIDDLE" HEIGHT="23">매출유형</TD> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=매출, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)

### 마진·원가·현금흐름 연결
- [DIRECT_EVIDENCE] 또한 장기적인 공급안정이 가능한 거래선 개발이 가능하도록 기술 중심적인 영업활동을 전개하고, 고객감동 실천으로 평생고객을 확보하고자 하고 있습니다.- 정밀화학, 제지/환경: 지속적인 품질개선을 통하여 반도체세정용, LCD에천트용, 환경처리용 등 다양한 수요에 대응하고 시장지배력을 강화, 잉여물량은 수출시장을 개척하고, 다양한 GRADE 개발로 수요처의 요구 품질 수준에 적극 부응하여 판매 극대화 및 수익성 확보, 환경에 대한 중요성 홍보를 통한 시장규모 확대 노력- 전자 및 이차전지소재: 다양한 고객사의 Needs를 충족시킬 수 있도록 고객별 커스터마이즈된 제품 공급 및 신규제품 공동개발</P> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=수익성, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] 연결 현금흐름표</TITLE> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TE ENG="Consolidated Statement Of CashFlows" ALIGN="CENTER" VALIGN="MIDDLE" WIDTH="765" HEIGHT="23" AUPDATECONT="N">연결 현금흐름표</TE> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TE ENG="Cash flows from (used in) operating activities" VALIGN="MIDDLE" WIDTH="343" HEIGHT="23" AUPDATECONT="N">영업활동현금흐름</TE> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)
- [DIRECT_EVIDENCE] <TE ENG="Cash flows from (used in) investing activities" VALIGN="MIDDLE" WIDTH="343" HEIGHT="23" AUPDATECONT="N">투자활동현금흐름</TE> (source=data/반도체/한솔케미칼/tech/source/dart_latest_business_report.txt, keywords=현금흐름, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.hansolchemical.com)

### IP 품질
- [DIRECT_EVIDENCE] legal_status: status=COLLECTED, count=None, score=0.6296, signal=None (source=data/반도체/한솔케미칼/tech/hansol_tech_ip_legal_features.json, keywords=legal_status, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] claims: status=COLLECTED, count=5310.0, score=None, signal=None (source=data/반도체/한솔케미칼/tech/hansol_tech_ip_claim_features.json, keywords=claims, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] citations: status=COLLECTED, count=656, score=None, signal=None (source=data/반도체/한솔케미칼/tech/hansol_tech_ip_citation_features.json, keywords=citations, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] family: status=COLLECTED, count=121.0, score=None, signal=None (source=data/반도체/한솔케미칼/tech/hansol_tech_ip_family_features.json, keywords=family, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] composite: status=COLLECTED, count=None, score=52.94, signal=IP_EVIDENCE_NEUTRAL (source=data/반도체/한솔케미칼/tech/hansol_tech_ip_evidence_composite.json, keywords=composite, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)

## 4. 다음 확인 포인트
- 고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인
- 양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인
- 매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인
- IP 품질: 청구항·인용·패밀리·존속 상태가 수집된 상태이므로 IP Evidence Composite와 Bridge 조정값의 방향성을 점검
- 마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인

## 5. URL 인식 결과 및 대체 조회 URL
- **KIPRIS**
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93ed40ad8e276e0201091b9a35720d37fa99e28a6b0956600d418c3fc95d3a73836d60025f4a0698677751a941d869a22e50ef3e9a75b7b9bb
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c939ef37838d7979f248b24efc013628b24b7b09404a5e389fa3943a6a4f0a33dc70d4a02708f67af3ce2db0c56a0f98ee85439b0efc12ed816
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=348aaf18c46825cf02d6c2de1c78338e7e8384424434c26bada1b947c35cdac4ce97784bd6e022fcaf4de52d58874543c52ee2075f956b6cb313d6330de999c716351798567d879b
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c933104015e29aa5af8ab0b9d910ba8d7804089a08c2ce72e99f4a302dc61f55c6a1d704b9db0fe7beb19f695c4c05ba4470e39822c82ea5b1d
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c937307e90534ec1c84b9f0427b2f78151ee0bd5b922ef6a2316aa7cc02712cdd79773b90a0335b9b8514dbd5a6529985b087499ea7f6d11b4b
  - detected: http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c934a677ec7646dfd8dd04e9e114dd36228087dbb33c236a452dc6729decd4fb05ed69c049055b2d982700bd905853a0cab856f97cc5217a3c7
  - fallback: https://www.kipris.or.kr/khome/main.jsp
  - fallback: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+KIPRIS+%ED%8A%B9%ED%97%88
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC
- **TECH_OUTPUT**
  - detected: https://dart.fss.or.kr/dsab001/main.do?autoSearch=true&textCrpCik=014680
  - detected: https://hansolchemical.com/en/thinf-mat/
  - detected: https://hansolchemical.com/en/business-intro
  - detected: https://hansolchemical.com/disclosure-info/
  - detected: https://www.hansolchemical.com
  - detected: http://www.hansolchemical.com
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
- **IR_HOMEPAGE**
  - detected: https://dart.fss.or.kr/dsab001/main.do?autoSearch=true&textCrpCik=014680
  - detected: https://hansolchemical.com/en/thinf-mat/
  - detected: https://hansolchemical.com/en/business-intro
  - detected: https://hansolchemical.com/disclosure-info/
  - detected: https://www.hansolchemical.com
  - detected: http://www.hansolchemical.com\n작
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+IR
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88
- **DART**
  - detected: http://www.w3.org/2001/XMLSchema-instance
  - detected: http://www.hansolchemical.com
  - detected: http://dart.fss.or.kr
- **VALUATION**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
  - fallback: https://www.google.com/search?q=%ED%95%9C%EC%86%94%EC%BC%80%EB%AF%B8%EC%B9%BC+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF
- **FINANCE**
  - detected: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#sessionnotcreatedexception
  - fallback: https://dart.fss.or.kr/
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->

<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->
# Technology Lifecycle Features

- company: 한솔케미칼
- status: OK
- overall_lifecycle_stage: GROWTH
- overall_lifecycle_score: 69.81
- source_patent_csv: `data\반도체\한솔케미칼\tech\hansol_kipris_bibliographic_normalized.csv`

## Summary
power_thermal_efficiency, semiconductor_materials, process_yield_quality 중심의 최근 특허 출원 밀도가 높아 기술 수명주기는 성장기 신호에 가깝습니다. 다만 논문/산업 리포트/고객 채택 속도 데이터가 없으면 확정이 아니라 특허 기반 추정입니다.

## Keyword Trends
| keyword | stage | score | total | recent | baseline | trend_ratio | reason |
|---|---:|---:|---:|---:|---:|---:|---|
| advanced_packaging | DECLINE_OR_SHIFT | 30.0 | 5 | 1 | 4 | 0.417 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| hbm_ai_memory | MATURITY | 55.0 | 3 | 1 | 1 | 1.667 | 장기간 출원이 누적되고 최근 출원도 유지되어 성숙기 신호로 분류합니다. |
| fan_out_wlp | NO_DATA | 0.0 | 0 | 0 | 0 | None | 특허 출원 추세 데이터가 없습니다. |
| bump_rdl_interposer | DECLINE_OR_SHIFT | 30.0 | 30 | 3 | 10 | 0.5 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| semiconductor_test | MATURITY | 55.0 | 4 | 1 | 2 | 0.833 | 장기간 출원이 누적되고 최근 출원도 유지되어 성숙기 신호로 분류합니다. |
| semiconductor_materials | GROWTH | 67.21 | 103 | 40 | 49 | 1.361 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |
| process_yield_quality | GROWTH | 81.33 | 103 | 31 | 25 | 2.067 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |
| power_thermal_efficiency | GROWTH | 72.8 | 194 | 62 | 63 | 1.64 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |

## External Signals
- status: NOT_PROVIDED
- summary: 논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.
<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->

<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->
# Certification & Standards Features

- company: 한솔케미칼
- status: OK
- certification_signal: CERTIFICATION_STRONG
- certification_score: 38.0
- quality_gate_stage: 5 / SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED
- evidence_count: 3

## Summary
FDA, SEMICONDUCTOR_QUALIFICATION 관련 근거가 확인되어 고객 품질·상용화 게이트 통과 가능성을 강하게 보강합니다. 단계: SEMICONDUCTOR_CUSTOMER_QUALIFICATION_MENTIONED.

## Confirmed Keys
FDA, SEMICONDUCTOR_QUALIFICATION

## Evidence
| certification | status | confidence | source | evidence |
|---|---:|---:|---|---|
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | hansol_tech_excel_frame_evidence.json | , "middle_source": "사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인\n규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건\n기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사 / 개발 지 |
| SEMICONDUCTOR_QUALIFICATION | CONFIRMED | HIGH | hansol_tech_excel_frame_evidence.md | 수 / 출처: 사업보고서 / 규제자료 / 기사 > 사업보고서: 신규시장 진입 계획 / 개발 일정 / 품질 요구 / 고객 승인 절차 / 시험평가 / 리스크 요인 규제자료: 산업별 필수 인증 / 시험규격 / 법적 허가 / 환경규제 / 안전기준 / 공급 승인 조건 기사: 인증 획득 기사 / 양산 승인 기사 / 테스트베드 기사  |
| FDA | CONFIRMED | HIGH | kipris_hansol_patents.csv | 1da412f4dc31e33b545f650988a70b35a / http://plus.kipris.or.kr/openapi/fileToss.jsp?arg=6c650beb4cee9ce4122b704b88878c93b9d11a69450b116343e25733ebb1af1b8df3c3c662fda27c66c6df218525a1 |
<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->
