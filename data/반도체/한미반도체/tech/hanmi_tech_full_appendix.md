# 한미반도체 Tech Agent Full Appendix

- **생성 시각:** 2026-05-20T19:58:24
- **목적:** Chair 보고서에는 compact summary만 전달하고, Excel-frame·KIPRIS/IP·Tech ML 상세 산출물은 Tech Agent가 소유하는 풀버전 부록입니다.
- **검증 원칙:** 이 부록은 미래수익률 예측이 아니라 특허/IP·사업화 근거·peer 상대위치 기반 return-free 기술 설명 지표를 정리합니다.

## Shared Tech Rubric Alignment

- **원천 파일:** `src/tech_agent/prompts.py`
- **최종 점수 정책:** 개인투자자용 최종 Tech 점수는 기술-사업화 연결 가능성, IP 품질, Excel/DART 정량 근거, 근거 신뢰도, 딥테크 성장투자 지속성을 하나로 합성한다.
- **가중치:** {'tech_to_value_bridge': 0.4, 'ip_evidence_composite': 0.2, 'excel_quantified_evidence': 0.15, 'evidence_confidence': 0.15, 'commercialization_and_funding_signal': 0.1}
- **판정 임계값:** {'INVESTOR_TECH_CONVICTION': 82, 'TECH_TO_VALUE_READY': 68, 'COMMERCIALIZATION_WATCH': 52, 'EVIDENCE_WEAK_OR_EARLY': 0}
- **Tech-to-Value 원칙:** Tech-to-Value Bridge는 기술이 실제 기업가치로 연결될 가능성을 평가한다. 판단 순서는 다음과 같다. 1. 기술/IP 근거가 실제 제품·공정·고객 채택과 연결되는가? 2. 양산성과 확장성이 확인되는가? 3. 고객 채택 또는 매출 전환 가능성을 설명할 수 있는가? 4. 특허/IP가 방어력, 협상력, 라이선스 가능성, 공급망 지위로 작동할 수 있는가? 5. R&D와 특허가 단순 투입/산출에 머무르지 않고 상업화 결과...
- **논문/IB/사업타당성 반영:** 논문·IB·사업타당성 자료 반영 원칙: - Financing Deep Tech / Deep Tech Revolution / Missing Middle 계열 자료의 핵심은 딥테크의 자금공백, 긴 개발주기, 높은 CAPEX, 정보비대칭이다. 따라서 기술이 “투자 가능한 기업가치”로 전환되려면 기술성뿐 아니라 양산·고객·자금조달·시장 수요가 함께 확인되어야 한다. - R&D와 특허 관련 연구의 핵심은 R&D는 effort, 특허는 ...
- **데이터 품질 원칙:** 데이터 품질 판정 기준: - OK: 원천 파일/공식 출처가 있고 수치·기간·단위·회사명이 확인됨 - FALLBACK_LOCAL_PROXY: API는 없지만 기업별 CSV/Excel/DART 등 로컬 원천으로 대체 산출됨 - PARTIAL: 일부 항목은 확인되지만 claim/citation/family/customer/adoption 등 핵심 보강 필요 - MISSING: 필수 원천 파일 또는 필수 수치가 없음 - API_PER...
- **자금조달·희석 리스크 원칙:** 딥테크 자금조달·희석 리스크 해석 원칙: - CB/BW, 유상증자, 정부과제, 기술이전은 Tech Agent의 핵심 기술점수에 직접 과대 반영하지 않고 투자 지속성·사업화 가능성의 보조 신호로 사용한다. - CB/BW 발행잔액/시가총액, 전환가액/현재주가, 최근 1년 메자닌 발행, 최근 2년 유상증자 횟수, 증자규모/기존주식수, 3자배정/주주배정 여부는 희석·오버행 watch point로 분리한다. - 희석성 자금조달이라도 시...

| 근거 우선순위 | 설명 |
|---:|---|
| 1 | 기업별 공시/DART 사업보고서 원문 |
| 2 | KIPRIS 원천 CSV·정규화 JSON·IP Evidence Composite |
| 3 | 기업별 Excel 정량 근거 및 quantified_metrics |
| 4 | IR 자료·공식 홈페이지·보도자료 |
| 5 | 정부과제/기술이전/인증/수상/고객 채택 공식 근거 |
| 6 | peer similarity·cluster·reference universe 등 Tech ML 산출물 |
| 7 | 뉴스/RSS/외부 요약 자료 |
| 8 | LLM 해석 또는 agent-generated 요약 |
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
- 투자자가 확인할 핵심 근거는 6개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다.

### 3) 개인투자자가 확인할 근거
| ID | 출처 | 근거 | 값 | 강도 |
|---|---|---|---:|---|
| tech.inv.ev.001 | tech_to_value | **최종 Tech-to-Value Bridge**: 한미반도체의 최종 기술-사업화 연결 점수는 80.85이며, Chair에는 기술성보다 고객 채택·양산·매출 전환 가능성을 우선 반영합니다. | 80.85점 | 상 |
| tech.inv.ev.002 | kipris_ip_evidence | **IP Evidence Composite**: 법적 안정성·청구항 방어력·인용 영향력·해외 패밀리 확장성을 합성한 IP Evidence Composite Score는 48.12입니다. | 48.12점 | 상 |
| tech.inv.ev.003 | kipris_legal | **권리 안정성**: 등록률 0.5727, 존속률 0.6202, 권리 안정성 점수 56.38를 확인했습니다. | 56.38점 | 중 |
| tech.inv.ev.004 | kipris_claim | **청구항 방어력**: 청구항 수 10915, 독립항 추정 1882, claim defense score 55.58입니다. | 55.58점 | 중 |
| tech.inv.ev.005 | kipris_citation | **인용 영향력**: 전방/후방 인용 및 기술 영향력 점수 기준 IP_CITATION_FALLBACK_ESTIMATED입니다. | - | 중 |
| tech.inv.ev.006 | kipris_family | **글로벌 패밀리 확장성**: 해외 패밀리 비중 0.3074, 감지 지역 ['CN', 'EP', 'JP', 'US', 'WO'], global extension score 45.17입니다. | 45.17점 | 중 |

### 4) 한계와 보완 필요사항
- 이 점수는 투자수익률 예측값이 아니라 기술-사업화 근거의 설명 가능성 점수입니다.
- KIPRIS Plus 유료 endpoint 접근 권한 또는 호출 제한으로 일부 청구항·패밀리·인용 데이터가 부족하면 보수적으로 반영합니다.
- Excel 템플릿 값은 복사 근거가 아니라 정량화 프레임이며, 실제 기업별 자료가 채워진 항목만 점수화합니다.
- CB/BW·유상증자·정부과제·기술이전 신호는 성장자금과 희석/오버행 리스크를 분리해 보조 레이어로만 해석합니다.
- R&D 비용은 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진은 commercial outcome으로 구분합니다.
<!-- TECH_INVESTOR_SCORECARD_END -->
## Step 1. Excel-frame based technology position
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/hanmi_tech_high_quality_report.md`
- **의미:** 기존 Excel 틀(high_quality_report.py)의 대분류를 Tech Agent 소유 풀버전 부록으로 옮긴 영역입니다.

| 대분류 | 항목 | 정량화 | 핵심 근거 | 등급 | 비고 |
|---|---|---:|---|---|---|
| 대표 기술 | 핵심 기술 키워드 | 5 / 5 (기술성) | 우리의 의견으로는 별첨된 연결회사의 연결재무제표는 연결회사의 2025년 12월 31일 현재의 연결재무상태와 동일로 종료되는 보고기간의 연결재무성과 및 연결현금흐름... | 강 | data\반도체\한미반도체\tech\source\dart_latest_business_report.txt |
| 핵심 제품/서비스 | 제품명/서비스명 | 5 / 5 (수익성 기여) | 지배기업의 개요한미반도체 주식회사(이하 '지배기업')는 반도체 장비 제조판매를 목적으로, 1980년 12월 24일에 설립되었으며, 인천광역시 서구 가좌로 30번길... | 강 | data\반도체\한미반도체\tech\source\dart_latest_business_report.txt |
| 고객 구매 이유 | 고객 효익 | 5 / 5 (고객 채택도) | 우리의 의견으로는 별첨된 연결회사의 연결재무제표는 연결회사의 2025년 12월 31일 현재의 연결재무상태와 동일로 종료되는 보고기간의 연결재무성과 및 연결현금흐름... | 강 | data\반도체\한미반도체\tech\source\dart_latest_business_report.txt |
| 경쟁 우위/대체가능성 | 등록 특허 | 5 / 5 (진입장벽) | 우리의 의견으로는 별첨된 연결회사의 연결재무제표는 연결회사의 2025년 12월 31일 현재의 연결재무상태와 동일로 종료되는 보고기간의 연결재무성과 및 연결현금흐름... | 강 | data\반도체\한미반도체\tech\source\dart_latest_business_report.txt |
| 활용 및 확장 산업 | 활용 산업 | 5 / 5 (확장성) | 지배기업의 개요한미반도체 주식회사(이하 '지배기업')는 반도체 장비 제조판매를 목적으로, 1980년 12월 24일에 설립되었으며, 인천광역시 서구 가좌로 30번길... | 강 | data\반도체\한미반도체\tech\source\dart_latest_business_report.txt |
| 진입 부담/장벽 | 인증/승인 | 5 / 5 (양산성) | 우리의 의견으로는 별첨된 연결회사의 연결재무제표는 연결회사의 2025년 12월 31일 현재의 연결재무상태와 동일로 종료되는 보고기간의 연결재무성과 및 연결현금흐름... | 강 | data\반도체\한미반도체\tech\source\dart_latest_business_report.txt |
| R&D 강도 | 연구개발비 | 5 / 5 (투자 지속성) | (*) 연결포괄손익계산서의 매출원가, 판매비와관리비 및 연구개발비를 합산한 금액입니다.; 직접근거 9건, 공식/DART/IR/특허 근거 9건, 정량화 지표 6건 | 강 | data\반도체\한미반도체\tech\source\dart_latest_business_report.txt |
## Step 2. Tech-to-Value Bridge
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/hanmi_tech_to_value_inputs.json`
| 항목 | 값 | 해석 |
|---|---:|---|
| Tech Agent 원점수 | 원문 확인 필요 | Tech Agent 내부 원점수 또는 기술 평가 총점입니다. |
| Auditor 보수 반영 점수 | 별도 Auditor 보수 점수 미생성 | claim/evidence 검증 후 Chair 반영에 사용하는 보수 점수입니다. |
| Base Bridge Score | 원문 확인 필요 | 사업화 연결 전 기본 Tech-to-Value 점수입니다. |
| Peer-adjusted Bridge Score | 80.85/100 | Step 8의 peer percentile 보정 후 점수입니다. |
| Bridge Grade | COMMERCIALIZATION_WATCH(점수 기반 보조 판정) | 최종 기술-가치 연결 판정입니다. |
| Shared Rubric | prompts.py | Tech-to-Value Bridge는 기술이 실제 기업가치로 연결될 가능성을 평가한다. 판단 순서는 다음과 같다. 1. 기술/IP 근거가 실제 제품·공정·고객 채택과 연결되는가? 2. 양산성과 확장성이 확인되는가? 3. 고객 채택 또는 매출 전환 가... |

- **COMMERCIALIZATION_WATCH:** 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 추적해야 하는 사업화 추적형입니다.
- **TECH_FINANCE_GAP:** 기술/IP 포트폴리오는 있으나 수익성·현금흐름·재무안정성 전환 근거가 약한 기술-재무 괴리형입니다.
## Step 3. KIPRIS/IP quantitative signals
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/hanmi_tech_patent_evidence.json`
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 23,664건 |
| 회사 출원인/권리자 매칭 | 16,218건 |
| 등록 특허 | 5,373건 |
| 존속 가능 특허 | 7,942건 |
| 최근 5년 특허 | 341건 |
| IPC/CPC 다양성 | 237개 |
| H01L 등 핵심 IPC 특허 | 6건 |
| 핵심기술 키워드 매칭 | 26,999회 |

| 대표 특허 예시 | 상태/연도 |
|---|---|
| 마스킹 테이프 박리장치 | 등록 |
| 열압착 본딩장치 | 등록 |
| 열압착 본딩장치 | 등록 |
| 반도체 제조장치의 처리방법 | 등록 |
| 스퍼터링 전처리 방법 | 등록 |
## Step 4. Patent KMeans clustering
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_ml_signal.json`
| 항목 | 값 |
|---|---:|
| 모델 | tfidf_kmeans |
| 정규화 특허 텍스트 레코드 | 896건 |
| 특허 클러스터 수 | 8개 |

| Cluster | 특허 수 | 대표 키워드 | 해석 |
|---:|---:|---|---|
| 2 | 205건 | 것을, 의해 | 기술 텍스트 유사도 기반 클러스터 |
| 6 | 180건 | 반도체, 한미반도체 주식회사, 한미반도체 | 기술 텍스트 유사도 기반 클러스터 |
| 3 | 161건 | 반도체, 패키지, 반도체 패키지, 패키지를, 반도체 패키지를, 패키지의 | 기술 텍스트 유사도 기반 클러스터 |
| 5 | 113건 | 한미약품, 한미약품 주식회사, 조성물 | 기술 텍스트 유사도 기반 클러스터 |
| 1 | 97건 | 화합물, 유도체, 1의 | 기술 텍스트 유사도 기반 클러스터 |
| 0 | 72건 | 반도체, 자재, 반도체 자재, 웨이퍼, 자재의, 반도체 자재의, 절단 | 기술 텍스트 유사도 기반 클러스터 |
| 4 | 43건 | 면역글로불린, 단백질, 결합체, fc, 지속형, 생리활성 | 기술 텍스트 유사도 기반 클러스터 |
| 7 | 25건 | 모두에 활성을, 수용체 모두에, 모두에, glp-1 gip, glp-1, gip, 갖는 삼중, 삼중 | 기술 텍스트 유사도 기반 클러스터 |
## Step 5. Focal-company cosine similarity
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_peer_similarity.json`
- **분석 방법:** TF-IDF + Cosine Similarity

| 비교 기업 | Cosine Similarity | 해석 |
|---|---:|---|
| 네패스 | 0.2553 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |
| LTC | 0.1464 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |
| 한솔케미칼 | 0.0877 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |
| 덕산테코피아 | 0.0198 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |

- Cosine Similarity는 기술 텍스트 유사도 신호이며, 재무 건전성이나 주가 방향을 직접 의미하지 않습니다.
## Step 6. Reference-universe company-level KMeans peer group
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_peer_cluster.json`
| 항목 | 값 |
|---|---|
| 현재 기업 cluster | 6 |
| Peer group | 후공정/패키징/테스트 |
| Reference universe | valuation/credit ML overlay 기반 딥테크 후보군 |

- Company-level KMeans는 기업 단위 특허/IP 특징량을 기준으로 기술 peer group을 배정합니다.
## Step 7. UMAP 2D tech peer map
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_peer_map.json`
| 항목 | 값 |
|---|---:|
| UMAP x | 18.71 |
| UMAP y | 13.01 |
| Cluster | 6 |
| Map PNG | `data/반도체/_sector_common/ml_universe/tech_peer_map.png` |

- UMAP 2D Peer Map은 고차원 특허/IP 특징량을 2차원으로 압축해 peer 위치를 설명하는 시각화 보조지표입니다.
- 한글 폰트는 시스템에 설치된 Malgun Gothic/Noto Sans CJK/AppleGothic을 우선 사용하도록 처리합니다.
## Step 8. Peer-percentile adjusted Tech-to-Value Bridge
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_peer_percentile_bridge.json`
| 항목 | 값 | 해석 |
|---|---:|---|
| Base Bridge Score | 77.52/100 | Tech-to-Value 기본 점수입니다. |
| Peer-adjusted Bridge Score | 80.85/100 | reference universe 내 상대 위치를 반영한 보정 점수입니다. |
| Peer Percentile | 88.33% | 같은 기술군 내 상대 순위입니다. |
| Final Bridge Grade | COMMERCIALIZATION_WATCH(점수 기반 보조 판정) | Chair 반영 시 보수 판단 기준입니다. |

- 이 보정은 기술/IP 상대 위치를 설명하기 위한 return-free 보조 지표이며, 미래 수익률 예측이 아닙니다.
## Step 9. Tech/IP Strength Index + NMF Topic Modeling
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_ip_ml.json`
### 9-1. Tech/IP Strength Index
| 항목 | 값 | 해석 |
|---|---:|---|
| Tech/IP Strength Index | 54.98/100 | 특허 등록률·존속성·최근성·IPC/CPC 다양성·핵심기술 키워드 밀도 점수를 통합한 IP 강도 지표입니다. |
| Reference Universe Percentile | 50.00% | reference universe 안에서의 상대적 기술/IP 위치입니다. |
| Patent Momentum Score | 26.58/100 | 최근 특허 활동과 기술 포트폴리오 지속성을 반영합니다. |

### 9-2. 특허/IP 원천 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 23,664건 |
| 회사 출원인/권리자 매칭 | 16,218건 |
| 등록 특허 | 5,373건 |
| 존속 가능 특허 | 7,942건 |
| 최근 5년 특허 | 341건 |
| IPC/CPC 다양성 | 237개 |
| H01L 등 핵심 IPC 특허 | 6건 |
| 핵심기술 키워드 매칭 | 26,999회 |
| 핵심기술 키워드 밀도 점수 | 100.00/100 |

### 9-3. NMF Topic Modeling
| Topic | 비중/점수 | 대표 키워드 |
|---|---:|---|
| Topic | 산출물 원문 참조 | `dominant_topics`/`topics` 구조 확인 필요 |

### 9-4. 해석
- 한미반도체의 Tech/IP Strength Index는 54.98/100, percentile 50.0로 산출되어 중간 수준 IP 포지션으로 해석됩니다. NMF 기준 주된 기술 주제는 '주요 topic 확인 제한'입니다. 단, 이 지표는 기술/IP 포트폴리오 상대 강도 신호이며 고객 채택·양산·매출 전환·FCF 개선 근거를 대체하지 않습니다.
## Step 10. Technology Differentiation Score
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_differentiation.json`
### 10-1. Technology Differentiation Score 요약
| 항목 | 값 | 해석 |
|---|---:|---|
| Technology Differentiation Score | 75.39/100 | peer 대비 특허/IP 포트폴리오가 얼마나 구별되는지 보는 비지도 ML 기반 차별화 점수입니다. |
| Reference Percentile | 90.00% | 분석 universe 안에서의 상대적 차별화 위치입니다. |
| Grade | 차별화 리더형 | 원문 grade: `DISTINCTIVE_TECH_LEADER` |
| Nearest Tech Peer | 엘티씨 | cosine similarity=0.4012, technology distance=0.5988 |
| Dominant NMF Topic | 패키지 / 자재 / 패키지를 / 패키지의 | topic weight=0.9660, topic rarity=100 |

### 10-2. 구성 점수
| 구성 요소 | 값 | 의미 |
|---|---:|---|
| Peer uniqueness | 70.00/100 | 가장 가까운 peer와의 기술 텍스트 거리입니다. |
| Topic distinctiveness | 96.37/100 | NMF dominant topic 집중도와 희소성을 반영합니다. |
| IPC specialization | 44.00/100 | IPC/CPC 다양성과 핵심 IPC 집중도를 반영합니다. |
| Keyword uniqueness | 90.00/100 | TF-IDF 상위 용어 중 고유 기술어 비중입니다. |

### 10-3. 차별화 근거 신호
| 원천 신호 | 값 |
|---|---:|
| 차별화 분석용 특허 텍스트 레코드 | 23,664건 |
| 회사 출원인/권리자 매칭 | 16,218건 |
| 등록 특허 | 5,373건 |
| 존속 가능 특허 | 7,942건 |
| 최근 5년 특허 | 341건 |
| IPC/CPC 다양성 | 237개 |
| H01L 등 핵심 IPC 특허 | 6건 |

### 10-4. 고유 기술어 / 차별화 키워드
- 자재, 픽커, 척테이블, 반송하, 싱귤레이션, 본딩장치, 패키지들, 리드프레임, 반송된, 스트립, 메모리카드, 발명 패키지

### 10-5. 해석
- 한미반도체의 Technology Differentiation Score는 75.39/100, percentile 90.0로 산출되어 차별화 우위형으로 해석됩니다. 가장 유사한 peer는 엘티씨(cosine similarity=0.4012)이며, 주된 NMF 기술 주제는 '패키지 / 자재 / 패키지를 / 패키지의'입니다. 이 점수는 특허/IP 포트폴리오의 차별성 신호이며 고객 채택·양산·매출 전환·FCF 개선 근거를 대체하지 않습니다.
- 현재는 5개 focal 기업 중심 검증 단계이며, 30개 reference universe 전체에 동일한 산출 방식을 확장 적용하면 percentile 해석의 안정성과 비교 설명력이 강화됩니다.
## Step 11. Patent Momentum Score + Tech-to-Value Evidence Confidence
- **산출물 상태:** 확인됨: `data/반도체/한미반도체/tech/tech_momentum_confidence.json`
### 11-1. Patent Momentum Score
| 항목 | 값 | 해석 |
|---|---:|---|
| Patent Momentum Score | 45.50/100 | 최근 특허 활동과 기술 포트폴리오 지속성 신호입니다. |
| Momentum Grade | 최근 특허 모멘텀 추적 필요 | 최근성·지속성 기준 보조 등급입니다. |

### 11-2. Tech-to-Value Evidence Confidence
| 항목 | 값 | 해석 |
|---|---:|---|
| Evidence Confidence | 88.00/100 | 고객 채택·양산·매출·FCF 근거의 직접성을 보수적으로 평가합니다. |
| Confidence Grade | 기술-가치 연결 직접 근거 강함 | 2차 산출물보다 직접 원천 근거를 우선하는 보수 기준입니다. |
| Direct Dimension Count | 4/4 | 직접 근거가 확인된 사업화 연결 항목 수입니다. |

### 11-3. 고객 채택·양산·매출·FCF별 직접성
| 항목 | 상태 | 직접 근거 | 간접 근거 | 원문 확인 필요 |
|---|---|---:|---:|---:|
| 고객 채택 | 직접 근거 | 13 | 45 | 0 |
| 양산 | 직접 근거 | 11 | 67 | 0 |
| 매출 전환 | 직접 근거 | 16 | 57 | 0 |
| FCF/현금흐름 | 직접 근거 | 3 | 2 | 0 |

- Evidence Confidence는 `agent_output`, `generated_report` 등 2차 산출물보다 DART/IR/공시/CSV 직접 수치 근거를 더 강하게 인정합니다.
- 대표 스니펫이 문서 첫머리·목차·생성 보고서 헤더에 가까우면 강한 근거로 사용하지 않습니다.
## Artifact inventory
| 구분 | 경로 | 상태 |
|---|---|---|
| chair_summary | `data/반도체/한미반도체/tech/tech_chair_summary.json` | 확인됨 |
| tech_packet | `data/반도체/한미반도체/tech/tech.json` | 확인됨 |
| high_quality_md | `data/반도체/한미반도체/tech/hanmi_tech_high_quality_report.md` | 확인됨 |
| tech_to_value | `data/반도체/한미반도체/tech/hanmi_tech_to_value_inputs.json` | 확인됨 |
| patent_json | `data/반도체/한미반도체/tech/hanmi_tech_patent_evidence.json` | 확인됨 |
| ml_signal | `data/반도체/한미반도체/tech/tech_ml_signal.json` | 확인됨 |
| peer_similarity | `data/반도체/한미반도체/tech/tech_peer_similarity.json` | 확인됨 |
| peer_cluster | `data/반도체/한미반도체/tech/tech_peer_cluster.json` | 확인됨 |
| peer_map | `data/반도체/한미반도체/tech/tech_peer_map.json` | 확인됨 |
| peer_percentile | `data/반도체/한미반도체/tech/tech_peer_percentile_bridge.json` | 확인됨 |
| tech_ip_ml | `data/반도체/한미반도체/tech/tech_ip_ml.json` | 확인됨 |
| tech_differentiation | `data/반도체/한미반도체/tech/tech_differentiation.json` | 확인됨 |
| tech_momentum_confidence | `data/반도체/한미반도체/tech/tech_momentum_confidence.json` | 확인됨 |

---

## KIPRIS Tech ML Feature 반영 요약

- kipris_tech_ml_score: 58.24
- legal_stability_score_estimated: 58.5
- portfolio_momentum_score: 72.22
- ip_technology_fit_score: 43.9
- bridge_adjustment_points: 1.0
- bridge_signal: IP_QUALITY_MODERATE

### 핵심 KIPRIS 정량 신호

- total_patents: 901
- registered_patents_estimated: 516
- alive_patents_estimated: 320
- recent_5y_application_patents: 186
- semiconductor_related_ipc_patents: 226
- registration_rate_estimated: 0.5727
- alive_rate_among_registered_estimated: 0.6202

주의: 이 값은 기술/IP 포트폴리오 품질 보조 신호이며, 고객 채택·양산·매출 전환·FCF 개선의 직접 근거로 보지는 않는다.

