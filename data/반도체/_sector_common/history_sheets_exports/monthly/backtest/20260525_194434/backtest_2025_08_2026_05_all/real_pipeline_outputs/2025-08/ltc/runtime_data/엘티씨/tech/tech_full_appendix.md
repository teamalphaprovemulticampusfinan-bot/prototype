# 엘티씨 Tech Agent Full Appendix

- **생성 시각:** 2026-05-11T17:47:21
- **목적:** Chair 보고서에는 compact summary만 전달하고, Excel-frame·KIPRIS/IP·Tech ML 상세 산출물은 Tech Agent가 소유하는 풀버전 부록입니다.
- **검증 원칙:** 이 부록은 미래수익률 예측이 아니라 특허/IP·사업화 근거·peer 상대위치 기반 return-free 기술 설명 지표를 정리합니다.

## Step 1. Excel-frame based technology position
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/ltc_tech_high_quality_report.md`
- **의미:** 기존 Excel 틀(high_quality_report.py)의 대분류를 Tech Agent 소유 풀버전 부록으로 옮긴 영역입니다.

| 대분류 | 항목 | 정량화 | 핵심 근거 | 등급 | 비고 |
|---|---|---:|---|---|---|
| 대표 기술 | 핵심 기술 키워드 | 5 / 5 (기술성) | 종속회사 엘티씨에이엠을 통해 반도체 제조 과정의 세정액, 식각액 등 화학재료와 시스템을 국내외에 공급하며, 엘에스이를 통해 웨이퍼세정장비를 직접 공급함.; 직접근... | 강 | https://finance.naver.com/item/main.naver?code=170920 |
| 핵심 제품/서비스 | 제품명/서비스명 | 5 / 5 (수익성 기여) | 종속회사 엘티씨에이엠을 통해 반도체 제조 과정의 세정액, 식각액 등 화학재료와 시스템을 국내외에 공급하며, 엘에스이를 통해 웨이퍼세정장비를 직접 공급함.; 직접근... | 강 | https://finance.naver.com/item/main.naver?code=170920 |
| 고객 구매 이유 | 고객 효익 | 5 / 5 (고객 채택도) | 종속회사 엘티씨에이엠을 통해 반도체 제조 과정의 세정액, 식각액 등 화학재료와 시스템을 국내외에 공급하며, 엘에스이를 통해 웨이퍼세정장비를 직접 공급함.; 직접근... | 강 | https://finance.naver.com/item/main.naver?code=170920 |
| 경쟁 우위/대체가능성 | 등록 특허 | 5 / 5 (진입장벽) | 종속회사 엘티씨에이엠을 통해 반도체 제조 과정의 세정액, 식각액 등 화학재료와 시스템을 국내외에 공급하며, 엘에스이를 통해 웨이퍼세정장비를 직접 공급함.; 직접근... | 강 | https://finance.naver.com/item/main.naver?code=170920 |
| 활용 및 확장 산업 | 활용 산업 | 5 / 5 (확장성) | 종속회사 엘티씨에이엠을 통해 반도체 제조 과정의 세정액, 식각액 등 화학재료와 시스템을 국내외에 공급하며, 엘에스이를 통해 웨이퍼세정장비를 직접 공급함.; 직접근... | 강 | https://finance.naver.com/item/main.naver?code=170920 |
| 진입 부담/장벽 | 인증/승인 | 5 / 5 (양산성) | 29; 직접근거 9건, 공식/DART/IR/특허 근거 9건, 정량화 지표 6건 | 강 | 등록 |
| R&D 강도 | 연구개발비 | 5 / 5 (투자 지속성) | (4) 당기와 전기 경상연구개발비 발생액은 각각 3,123백만원과 2,666백만원 입니다.; 직접근거 9건, 공식/DART/IR/특허 근거 9건, 정량화 지표 6... | 강 | data\반도체\엘티씨\tech\source\dart_latest_business_report.txt |
## Step 2. Tech-to-Value Bridge
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/ltc_tech_to_value_inputs.json`
| 항목 | 값 | 해석 |
|---|---:|---|
| Tech Agent 원점수 | 원문 확인 필요 | Tech Agent 내부 원점수 또는 기술 평가 총점입니다. |
| Auditor 보수 반영 점수 | 별도 Auditor 보수 점수 미생성 | claim/evidence 검증 후 Chair 반영에 사용하는 보수 점수입니다. |
| Base Bridge Score | 원문 확인 필요 | 사업화 연결 전 기본 Tech-to-Value 점수입니다. |
| Peer-adjusted Bridge Score | 84.00/100 | Step 8의 peer percentile 보정 후 점수입니다. |
| Bridge Grade | VALUE_BRIDGE_READY(점수 기반 보조 판정) | 최종 기술-가치 연결 판정입니다. |

- **COMMERCIALIZATION_WATCH:** 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 추적해야 하는 사업화 추적형입니다.
- **TECH_FINANCE_GAP:** 기술/IP 포트폴리오는 있으나 수익성·현금흐름·재무안정성 전환 근거가 약한 기술-재무 괴리형입니다.
## Step 3. KIPRIS/IP quantitative signals
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/ltc_tech_patent_evidence.json`
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 2,041건 |
| 회사 출원인/권리자 매칭 | 812건 |
| 등록 특허 | 381건 |
| 존속 가능 특허 | 480건 |
| 최근 5년 특허 | 150건 |
| IPC/CPC 다양성 | 248개 |
| H01L 등 핵심 IPC 특허 | 4건 |
| 핵심기술 키워드 매칭 | 581회 |

| 대표 특허 예시 | 상태/연도 |
|---|---|
| 통합 공정 씬너 조성물 | 등록 |
| 디스플레이 제조용 포토레지스트 박리액 조성물 | 등록 |
| 과산화수소를 이용한 질화티탄막 식각용 고선택비 식각액 조성물 | 등록 |
| CMP 후 세정액 조성물 | 등록 |
| LCD 제조용 포토레지스트 박리액 조성물 | 등록 |
## Step 4. Patent KMeans clustering
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_ml_signal.json`
| 항목 | 값 |
|---|---:|
| 모델 | tfidf_kmeans |
| 정규화 특허 텍스트 레코드 | 506건 |
| 특허 클러스터 수 | 8개 |

| Cluster | 특허 수 | 대표 키워드 | 해석 |
|---:|---:|---|---|
| 0 | 224건 | 주식회사, 있도록 | 기술 텍스트 유사도 기반 클러스터 |
| 1 | 134건 | 형성된, 하는, 주식회사 | 기술 텍스트 유사도 기반 클러스터 |
| 7 | 48건 | 내지, 조성물, 화합물 | 기술 텍스트 유사도 기반 클러스터 |
| 4 | 46건 | 전력을, 태양광, 에너지, dc/dc, 배터리 | 기술 텍스트 유사도 기반 클러스터 |
| 6 | 18건 | 디지털, 치료, 데이터를, 방법 이러한, 디지털 치료, 이러한 방법을, 판독 | 기술 텍스트 유사도 기반 클러스터 |
| 5 | 17건 | 윤활유, 윤활유가, 윤활유를, 내부에, 케이엘티, 주식회사 케이엘티 | 기술 텍스트 유사도 기반 클러스터 |
| 3 | 12건 | 레이저, 보호창, 수용, 부재, 배치되며, 비전 검사 | 기술 텍스트 유사도 기반 클러스터 |
| 2 | 7건 | 선로, 접근시, 안전사고, 발생 가능성을, 가능성을, 작업자의 | 기술 텍스트 유사도 기반 클러스터 |
## Step 5. Focal-company cosine similarity
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_peer_similarity.json`
- **분석 방법:** TF-IDF + Cosine Similarity

| 비교 기업 | Cosine Similarity | 해석 |
|---|---:|---|
| 한솔케미칼 | 0.2553 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |
| 네패스 | 0.1622 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |
| 한미반도체 | 0.1464 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |
| 덕산테코피아 | 0.0651 | 특허 텍스트 포트폴리오의 기술 유사도입니다. |

- Cosine Similarity는 기술 텍스트 유사도 신호이며, 재무 건전성이나 주가 방향을 직접 의미하지 않습니다.
## Step 6. Reference-universe company-level KMeans peer group
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_peer_cluster.json`
| 항목 | 값 |
|---|---|
| 현재 기업 cluster | 6 |
| Peer group | 소재 |
| Reference universe | valuation/credit ML overlay 기반 딥테크 후보군 |

- Company-level KMeans는 기업 단위 특허/IP 특징량을 기준으로 기술 peer group을 배정합니다.
## Step 7. UMAP 2D tech peer map
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_peer_map.json`
| 항목 | 값 |
|---|---:|
| UMAP x | 19.12 |
| UMAP y | 13.13 |
| Cluster | 6 |
| Map PNG | `data/반도체/_sector_common/ml_universe/tech_peer_map.png` |

- UMAP 2D Peer Map은 고차원 특허/IP 특징량을 2차원으로 압축해 peer 위치를 설명하는 시각화 보조지표입니다.
- 한글 폰트는 시스템에 설치된 Malgun Gothic/Noto Sans CJK/AppleGothic을 우선 사용하도록 처리합니다.
## Step 8. Peer-percentile adjusted Tech-to-Value Bridge
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_peer_percentile_bridge.json`
| 항목 | 값 | 해석 |
|---|---:|---|
| Base Bridge Score | 89.39/100 | Tech-to-Value 기본 점수입니다. |
| Peer-adjusted Bridge Score | 84.00/100 | reference universe 내 상대 위치를 반영한 보정 점수입니다. |
| Peer Percentile | 95.00% | 같은 기술군 내 상대 순위입니다. |
| Final Bridge Grade | VALUE_BRIDGE_READY(점수 기반 보조 판정) | Chair 반영 시 보수 판단 기준입니다. |

- 이 보정은 기술/IP 상대 위치를 설명하기 위한 return-free 보조 지표이며, 미래 수익률 예측이 아닙니다.
## Step 9. Tech/IP Strength Index + NMF Topic Modeling
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_ip_ml.json`
### 9-1. Tech/IP Strength Index
| 항목 | 값 | 해석 |
|---|---:|---|
| Tech/IP Strength Index | 58.35/100 | 특허 등록률·존속성·최근성·IPC/CPC 다양성·핵심기술 키워드 밀도 점수를 통합한 IP 강도 지표입니다. |
| Reference Universe Percentile | 50.00% | reference universe 안에서의 상대적 기술/IP 위치입니다. |
| Patent Momentum Score | 38.85/100 | 최근 특허 활동과 기술 포트폴리오 지속성을 반영합니다. |

### 9-2. 특허/IP 원천 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 2,041건 |
| 회사 출원인/권리자 매칭 | 812건 |
| 등록 특허 | 381건 |
| 존속 가능 특허 | 480건 |
| 최근 5년 특허 | 150건 |
| IPC/CPC 다양성 | 248개 |
| H01L 등 핵심 IPC 특허 | 4건 |
| 핵심기술 키워드 매칭 | 581회 |
| 핵심기술 키워드 밀도 점수 | 71.55/100 |

### 9-3. NMF Topic Modeling
| Topic | 비중/점수 | 대표 키워드 |
|---|---:|---|
| Topic | 산출물 원문 참조 | `dominant_topics`/`topics` 구조 확인 필요 |

### 9-4. 해석
- 엘티씨의 Tech/IP Strength Index는 58.35/100, percentile 50.0로 산출되어 중간 수준 IP 포지션으로 해석됩니다. NMF 기준 주된 기술 주제는 '주요 topic 확인 제한'입니다. 단, 이 지표는 기술/IP 포트폴리오 상대 강도 신호이며 고객 채택·양산·매출 전환·FCF 개선 근거를 대체하지 않습니다.
## Step 10. Technology Differentiation Score
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_differentiation.json`
### 10-1. Technology Differentiation Score 요약
| 항목 | 값 | 해석 |
|---|---:|---|
| Technology Differentiation Score | 56.62/100 | peer 대비 특허/IP 포트폴리오가 얼마나 구별되는지 보는 비지도 ML 기반 차별화 점수입니다. |
| Reference Percentile | 30.00% | 분석 universe 안에서의 상대적 차별화 위치입니다. |
| Grade | 보통 차별화형 | 원문 grade: `MODERATE_DIFFERENTIATION` |
| Nearest Tech Peer | 한솔케미칼 | cosine similarity=0.4988, technology distance=0.5012 |
| Dominant NMF Topic | 윤활유 / dc / 전력을 / 보호창 | topic weight=0.9421, topic rarity=100 |

### 10-2. 구성 점수
| 구성 요소 | 값 | 의미 |
|---|---:|---|
| Peer uniqueness | 20.00/100 | 가장 가까운 peer와의 기술 텍스트 거리입니다. |
| Topic distinctiveness | 94.49/100 | NMF dominant topic 집중도와 희소성을 반영합니다. |
| IPC specialization | 80.00/100 | IPC/CPC 다양성과 핵심 IPC 집중도를 반영합니다. |
| Keyword uniqueness | 50.00/100 | TF-IDF 상위 용어 중 고유 기술어 비중입니다. |

### 10-3. 차별화 근거 신호
| 원천 신호 | 값 |
|---|---:|
| 차별화 분석용 특허 텍스트 레코드 | 2,041건 |
| 회사 출원인/권리자 매칭 | 812건 |
| 등록 특허 | 381건 |
| 존속 가능 특허 | 480건 |
| 최근 5년 특허 | 150건 |
| IPC/CPC 다양성 | 248개 |
| H01L 등 핵심 IPC 특허 | 4건 |

### 10-4. 고유 기술어 / 차별화 키워드
- 윤활유, 보호창, 수용, dc dc, 레이저 비전, 컨버터, 용접, 치료, 보호창 부재, 질병, 볼트, 분산형

### 10-5. 해석
- 엘티씨의 Technology Differentiation Score는 56.62/100, percentile 30.0로 산출되어 보통 차별화형으로 해석됩니다. 가장 유사한 peer는 한솔케미칼(cosine similarity=0.4988)이며, 주된 NMF 기술 주제는 '윤활유 / dc / 전력을 / 보호창'입니다. 이 점수는 특허/IP 포트폴리오의 차별성 신호이며 고객 채택·양산·매출 전환·FCF 개선 근거를 대체하지 않습니다.
- 현재는 5개 focal 기업 중심 검증 단계이며, 30개 reference universe 전체에 동일한 산출 방식을 확장 적용하면 percentile 해석의 안정성과 비교 설명력이 강화됩니다.
## Step 11. Patent Momentum Score + Tech-to-Value Evidence Confidence
- **산출물 상태:** 확인됨: `data/반도체/엘티씨/tech/tech_momentum_confidence.json`
### 11-1. Patent Momentum Score
| 항목 | 값 | 해석 |
|---|---:|---|
| Patent Momentum Score | 61.93/100 | 최근 특허 활동과 기술 포트폴리오 지속성 신호입니다. |
| Momentum Grade | 최근 특허 모멘텀 보통 | 최근성·지속성 기준 보조 등급입니다. |

### 11-2. Tech-to-Value Evidence Confidence
| 항목 | 값 | 해석 |
|---|---:|---|
| Evidence Confidence | 78.80/100 | 고객 채택·양산·매출·FCF 근거의 직접성을 보수적으로 평가합니다. |
| Confidence Grade | 기술-가치 연결 직접 근거 강함 | 2차 산출물보다 직접 원천 근거를 우선하는 보수 기준입니다. |
| Direct Dimension Count | 3/4 | 직접 근거가 확인된 사업화 연결 항목 수입니다. |

### 11-3. 고객 채택·양산·매출·FCF별 직접성
| 항목 | 상태 | 직접 근거 | 간접 근거 | 원문 확인 필요 |
|---|---|---:|---:|---:|
| 고객 채택 | 직접 근거 | 6 | 36 | 0 |
| 양산 | 직접 근거 | 5 | 42 | 0 |
| 매출 전환 | 직접 근거 | 8 | 32 | 0 |
| FCF/현금흐름 | 간접 근거 | 0 | 1 | 0 |

- Evidence Confidence는 `agent_output`, `generated_report` 등 2차 산출물보다 DART/IR/공시/CSV 직접 수치 근거를 더 강하게 인정합니다.
- 대표 스니펫이 문서 첫머리·목차·생성 보고서 헤더에 가까우면 강한 근거로 사용하지 않습니다.
## Artifact inventory
| 구분 | 경로 | 상태 |
|---|---|---|
| chair_summary | `data/반도체/엘티씨/tech/tech_chair_summary.json` | 확인됨 |
| tech_packet | `data/반도체/엘티씨/tech/tech.json` | 확인됨 |
| high_quality_md | `data/반도체/엘티씨/tech/ltc_tech_high_quality_report.md` | 확인됨 |
| tech_to_value | `data/반도체/엘티씨/tech/ltc_tech_to_value_inputs.json` | 확인됨 |
| patent_json | `data/반도체/엘티씨/tech/ltc_tech_patent_evidence.json` | 확인됨 |
| ml_signal | `data/반도체/엘티씨/tech/tech_ml_signal.json` | 확인됨 |
| peer_similarity | `data/반도체/엘티씨/tech/tech_peer_similarity.json` | 확인됨 |
| peer_cluster | `data/반도체/엘티씨/tech/tech_peer_cluster.json` | 확인됨 |
| peer_map | `data/반도체/엘티씨/tech/tech_peer_map.json` | 확인됨 |
| peer_percentile | `data/반도체/엘티씨/tech/tech_peer_percentile_bridge.json` | 확인됨 |
| tech_ip_ml | `data/반도체/엘티씨/tech/tech_ip_ml.json` | 확인됨 |
| tech_differentiation | `data/반도체/엘티씨/tech/tech_differentiation.json` | 확인됨 |
| tech_momentum_confidence | `data/반도체/엘티씨/tech/tech_momentum_confidence.json` | 확인됨 |

---

## KIPRIS Tech ML Feature 반영 요약

- kipris_tech_ml_score: 38.64
- legal_stability_score_estimated: 40.24
- portfolio_momentum_score: 75.15
- ip_technology_fit_score: 0.0
- bridge_adjustment_points: -2.0
- bridge_signal: IP_QUALITY_WEAK

### 핵심 KIPRIS 정량 신호

- total_patents: 500
- registered_patents_estimated: 336
- alive_patents_estimated: 0
- recent_5y_application_patents: 145
- semiconductor_related_ipc_patents: 0
- registration_rate_estimated: 0.672
- alive_rate_among_registered_estimated: 0.0

주의: 이 값은 기술/IP 포트폴리오 품질 보조 신호이며, 고객 채택·양산·매출 전환·FCF 개선의 직접 근거로 보지는 않는다.

