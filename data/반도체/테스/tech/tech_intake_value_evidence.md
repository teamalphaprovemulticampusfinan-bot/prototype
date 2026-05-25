# 테스 Tech Intake Value Evidence Bridge

## 1. 요약
- 생성 시각: 2026-05-20T22:03:26
- 종합 점수: 80.15/100
- 종합 라벨: VALUE_EVIDENCE_STRONG
- 원천 문서 수: 134개

## 2. 기술 → 사업화 → 재무 연결 근거
| 항목 | 상태 | 점수 | 직접 | 간접 | 부분/교차 | 요약 |
|---|---|---:|---:|---:|---:|---|
| 고객 채택 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 고객 채택 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 양산 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 양산 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| 매출 전환 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 매출 전환 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |
| IP 품질 | 직접 근거 확인 | 52.69 | 4 | 0 | 0 | KIPRIS 기반 법적 상태·청구항·인용·패밀리 산출물을 함께 반영합니다. 특허 수량만이 아니라 권리 안정성, 청구항 방어력, 인용 영향력, 해외 확장성을 분리해 Chair 판단에 전달합니다. |
| 마진·원가·현금흐름 연결 | 직접 근거 확인 | 85.0 | 8 | 0 | 0 | 마진·원가·현금흐름 연결 관련 직접 근거가 8건 확인됩니다. Chair에서는 가치 전환 근거로 반영하되 원천 URL/파일을 함께 확인합니다. |

## 3. 대표 근거

### 고객 채택
- [DIRECT_EVIDENCE] - **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다. (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 | (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | 고객 채택 | 직접 근거 | 88.00/100 | 8건 | 12건 | 0건 | (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=고객 채택, 채택, 고객, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 양산
- [DIRECT_EVIDENCE] - **해석:** prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] 차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다. (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | Evidence Confidence | 79.70/100 | 고객 채택·양산·매출·FCF 근거의 직접성 | (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] | 양산 | 직접 근거 | 88.00/100 | 17건 | 63건 | 0건 | (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)
- [DIRECT_EVIDENCE] - 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다. (source=data/반도체/테스/tech/_nepes_reference_schema/nepes_tech_chair_summary.md, keywords=양산, urls=http://www.w3.org/2001/XMLSchema-instance, http://www.nepes.co.kr)

### 매출 전환
- [DIRECT_EVIDENCE] summary: 테스는 2023년 영업이익 적자에서 2024년 흑자 전환하며 매출과 이익이 크게 성장하는 추세를 보이고 있습니다. (source=data/반도체/테스/finance/테스_finance.json, keywords=매출, 성장, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] key_thesis: 매출액은 2023년 1,469억원에서 2025년 3,511억원으로 2년 만에 2배 이상 성장할 것으로 전망됩니다. (source=data/반도체/테스/finance/테스_finance.json, keywords=매출, 매출액, 성장, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] missing_prompt_metrics: 매출성장률 (source=data/반도체/테스/finance/테스_finance_agent_packet.json, keywords=매출, 성장, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] source_contexts: 필수 지표 산출 한계: 매출성장률, 영업이익률, ROE, 부채비율, 변동성지수 (source=data/반도체/테스/finance/테스_finance_agent_packet.json, keywords=매출, 성장, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] sales: 351115732341.0 (source=data/반도체/테스/finance/테스_finance_agent_packet.json, keywords=sales, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)

### 마진·원가·현금흐름 연결
- [DIRECT_EVIDENCE] 2025년에도 이러한 성장세가 이어질 것으로 전망되나, 2024년 자유현금흐름이 마이너스를 기록한 점은 투자 시 고려해야 할 부분입니다. (source=data/반도체/테스/finance/테스_finance.json, keywords=현금흐름, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] key_thesis: 2023년 영업이익률 -3.99%에서 2024년 16.03%로 급등하며 수익성이 크게 개선되었고, 2025년에는 16.47%로 유지될 것으로 보입니다. (source=data/반도체/테스/finance/테스_finance.json, keywords=영업이익률, 수익성, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] key_risks: 2024년 자유현금흐름(FCF)이 -243억원을 기록하며 마이너스로 전환되었고, 이는 투자 및 운전자본 증가로 인한 현금 유출 가능성을 시사합니다. (source=data/반도체/테스/finance/테스_finance.json, keywords=현금흐름, FCF, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] report_core_points: FCF: 테스 2025 기준 FCF 값은 49,284,217,786원이며, 투자·운전자본 변동을 반영한 현금창출력을 확인하는 지표입니다. (source=data/반도체/테스/finance/테스_finance_agent_packet.json, keywords=FCF, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)
- [DIRECT_EVIDENCE] missing_prompt_metrics: 영업이익률 (source=data/반도체/테스/finance/테스_finance_agent_packet.json, keywords=영업이익률, urls=https://dart.fss.or.kr/, https://opendart.fss.or.kr/)

### IP 품질
- [DIRECT_EVIDENCE] legal_status: status=COLLECTED, count=None, score=0.7513, signal=None (source=data/반도체/테스/tech/tech_ip_legal_features.json, keywords=legal_status, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] claims: status=COLLECTED, count=4498.0, score=None, signal=None (source=data/반도체/테스/tech/tech_ip_claim_features.json, keywords=claims, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] citations: status=COLLECTED, count=382, score=None, signal=None (source=data/반도체/테스/tech/tech_ip_citation_features.json, keywords=citations, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] family: status=COLLECTED, count=142.0, score=None, signal=None (source=data/반도체/테스/tech/tech_ip_family_features.json, keywords=family, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)
- [DIRECT_EVIDENCE] composite: status=COLLECTED, count=None, score=52.69, signal=IP_EVIDENCE_NEUTRAL (source=data/반도체/테스/tech/tech_ip_evidence_composite.json, keywords=composite, COLLECTED, urls=https://www.kipris.or.kr/khome/main.jsp, https://plus.kipris.or.kr/)

## 4. 다음 확인 포인트
- 고객 채택: 확인된 고객사·공급 근거가 실제 반복 매출로 이어지는지 후속 확인
- 양산: 양산 근거가 제품별 매출·가동률·수율 개선으로 이어지는지 확인
- 매출 전환: 기술 적용 제품군의 매출 지속성과 고객 concentration 리스크 확인
- IP 품질: 청구항·인용·패밀리·존속 상태가 수집된 상태이므로 IP Evidence Composite와 Bridge 조정값의 방향성을 점검
- 마진·원가·현금흐름: 확인된 수익성/현금흐름 개선이 일회성이 아닌지 기간별 추세 확인

## 5. URL 인식 결과 및 대체 조회 URL
- **TECH_OUTPUT**
  - detected: https://www.nepes.co.kr/kr/ir/ir_news.php?bgu=view&idx=1124
  - detected: https://www.nepes.co.kr/kr/ir/ir_news.php?bgu=view&idx=1126
  - detected: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - detected: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
  - detected: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+IR
  - detected: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88+%ED%8C%A8%ED%82%A4%EC%A7%95
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EC%96%91%EC%82%B0+%EB%A7%A4%EC%B6%9C+%EC%A0%84%ED%99%98
- **IR_HOMEPAGE**
  - detected: http://www.w3.org/2001/XMLSchema-instance
  - detected: http://www.nepes.co.kr
  - detected: https://dart.fss.or.kr/
  - detected: https://opendart.fss.or.kr/
  - detected: https://www.kipris.or.kr/khome/main.jsp
  - detected: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+IR
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EA%B8%B0%EC%97%85%EC%86%8C%EA%B0%9C+IR+%EC%9E%90%EB%A3%8C
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80+%EA%B8%B0%EC%88%A0+%EC%A0%9C%ED%92%88
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EC%96%91%EC%82%B0+%EA%B3%A0%EA%B0%9D%EC%82%AC+%EB%82%A9%ED%92%88
- **KIPRIS**
  - detected: http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo?accessKey=%2A%2A%2AKEY%2A%2A%2A&applicationNumber=102020060013627&registerNumber=2004234460000&registrationNumber=2004234460000&format=xml
  - detected: http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo?accessKey=%2A%2A%2AKEY%2A%2A%2A&applicationNumber=102020237000046&openNumber=2020240000063&publicationNumber=2020240000063&format=xml
  - detected: http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo?accessKey=%2A%2A%2AKEY%2A%2A%2A&applicationNumber=102020150001595&openNumber=2020160003177&publicationNumber=2020160003177&registerNumber=2004815330000&registrationNumber=2004815330000&format=xml
  - detected: http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo?accessKey=%2A%2A%2AKEY%2A%2A%2A&applicationNumber=102020190003460&openNumber=2020210000492&publicationNumber=2020210000492&format=xml
  - detected: http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentClaimInfo?accessKey=%2A%2A%2AKEY%2A%2A%2A&applicationNumber=102019990009838&openNumber=2020000002171&publicationNumber=2020000002171&format=xml
  - detected: http://plus.kipris.or.kr/kipo-api/kipi/patFamInfoSearchService/getAppNoPatFamInfoSearch
  - fallback: https://www.kipris.or.kr/khome/main.jsp
  - fallback: https://plus.kipris.or.kr/
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+KIPRIS+%ED%8A%B9%ED%97%88
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%ED%8A%B9%ED%97%88+%EC%B2%AD%EA%B5%AC%ED%95%AD+%EC%9D%B8%EC%9A%A9+%ED%8C%A8%EB%B0%80%EB%A6%AC
- **VALUATION**
  - detected: URL 확인 제한
  - fallback: https://dart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
  - fallback: https://www.google.com/search?q=%ED%85%8C%EC%8A%A4+%EC%9E%AC%EB%AC%B4%EC%A0%9C%ED%91%9C+%ED%98%84%EA%B8%88%ED%9D%90%EB%A6%84+FCF
- **FINANCE**
  - detected: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#sessionnotcreatedexception
  - fallback: https://dart.fss.or.kr/
  - fallback: https://opendart.fss.or.kr/
  - fallback: https://finance.naver.com/
  - fallback: https://comp.fnguide.com/
