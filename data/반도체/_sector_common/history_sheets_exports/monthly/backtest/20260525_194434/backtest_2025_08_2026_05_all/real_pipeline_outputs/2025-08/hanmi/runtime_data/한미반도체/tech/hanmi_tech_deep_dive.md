# 한미반도체 Tech Deep-Dive Appendix

이 파일은 Chair 최종 보고서에 길게 삽입하지 않고, Tech Agent 상세 산출물로 별도 보관합니다.

## 1. Chair Compact Summary
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


## 2. 원천 상세 파일 위치
| 구분 | 경로 |
|---|---|
| report_md | `data/반도체/한미반도체/tech/hanmi_tech_high_quality_report.md` |
| packet_json | `data/반도체/한미반도체/tech/hanmi_tech_agent_packet.json` |
| chair_packet_json | `data/반도체/한미반도체/tech/tech.json` |
| tech_to_value_json | `data/반도체/한미반도체/tech/hanmi_tech_to_value_inputs.json` |
| formula_catalog_json | `data/반도체/한미반도체/tech/hanmi_tech_formula_rules.json` |
| formula_catalog_md | `data/반도체/한미반도체/tech/hanmi_tech_formula_rules.md` |
| evidence_harvest_json | `data/반도체/한미반도체/tech/hanmi_tech_evidence_harvest.json` |
| evidence_harvest_md | `data/반도체/한미반도체/tech/hanmi_tech_evidence_harvest.md` |
| patent_json | `data/반도체/한미반도체/tech/hanmi_tech_patent_evidence.json` |
| patent_md | `data/반도체/한미반도체/tech/hanmi_tech_patent_evidence.md` |
| patent_csv | `data/반도체/한미반도체/tech/hanmi_tech_patent_normalized.csv` |

## 3. 운영 원칙
- Tech의 상세 Excel-frame, KIPRIS/IP, Peer ML, NMF, Differentiation, Momentum, Evidence Confidence는 Tech Agent 쪽에서 산출합니다.
- First Auditor는 Tech Agent가 Chair에 넘긴 claim/evidence를 검증합니다.
- Chair는 상세 부록을 반복 삽입하지 않고, 요약·충돌·최종 판단만 수행합니다.
- IP Evidence Composite Score는 특허 수량이 아니라 법적 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합한 보조 신호입니다.
