# LX세미콘 Tech Agent Full Appendix

- **생성 시각:** 2026-05-15T03:14:33
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
## Final Investor Tech Scorecard

- 아직 `tech_investor_scorecard.json`이 생성되지 않았습니다. `python main.py tech ...` 또는 tech_intake를 먼저 실행하세요.
## Step 1. Excel-frame based technology position
- **산출물 상태:** 확인됨: `data/반도체/LX세미콘/tech/lxsemicon_tech_high_quality_report.md`
- **의미:** 기존 Excel 틀(high_quality_report.py)의 대분류를 Tech Agent 소유 풀버전 부록으로 옮긴 영역입니다.

| 대분류 | 항목 | 정량화 | 핵심 근거 | 등급 | 비고 |
|---|---|---:|---|---|---|
| 대표 기술 | 핵심 기술 키워드 | 4 / 5 (기술성) | LX세미콘은 Universe CSV에서 '팹리스/설계' peer_group으로 분류되어 있습니다.; 직접근거 3건, 공식/DART/IR/특허 근거 0건, 정량화 ... | 강 | data\반도체\LX세미콘\tech\source\lxsemicon_tech_local_proxy_eviden... |
| 핵심 제품/서비스 | 제품명/서비스명 | 3 / 5 (수익성 기여) | LX세미콘은 Universe CSV에서 '팹리스/설계' peer_group으로 분류되어 있습니다.; 직접근거 3건, 공식/DART/IR/특허 근거 0건, 정량화 ... | 중 | data\반도체\LX세미콘\tech\source\lxsemicon_tech_local_proxy_eviden... |
| 고객 구매 이유 | 고객 효익 | 3 / 5 (고객 채택도) | LX세미콘은 Universe CSV에서 '팹리스/설계' peer_group으로 분류되어 있습니다.; 직접근거 3건, 공식/DART/IR/특허 근거 0건, 정량화 ... | 중 | data\반도체\LX세미콘\tech\source\lxsemicon_tech_local_proxy_eviden... |
| 경쟁 우위/대체가능성 | 등록 특허 | 3 / 5 (진입장벽) | LX세미콘은 Universe CSV에서 '팹리스/설계' peer_group으로 분류되어 있습니다.; 직접근거 4건, 공식/DART/IR/특허 근거 0건, 정량화 ... | 중 | data\반도체\LX세미콘\tech\source\lxsemicon_tech_local_proxy_eviden... |
| 활용 및 확장 산업 | 활용 산업 | 3 / 5 (확장성) | LX세미콘은 Universe CSV에서 '팹리스/설계' peer_group으로 분류되어 있습니다.; 직접근거 3건, 공식/DART/IR/특허 근거 0건, 정량화 ... | 중 | data\반도체\LX세미콘\tech\source\lxsemicon_tech_local_proxy_eviden... |
| 진입 부담/장벽 | 인증/승인 | 3 / 5 (양산성) | LX세미콘은 Universe CSV에서 '팹리스/설계' peer_group으로 분류되어 있습니다.; 직접근거 3건, 공식/DART/IR/특허 근거 0건, 정량화 ... | 중 | data\반도체\LX세미콘\tech\source\lxsemicon_tech_local_proxy_eviden... |
| R&D 강도 | 연구개발비 | 3 / 5 (투자 지속성) | LX세미콘은 Universe CSV에서 '팹리스/설계' peer_group으로 분류되어 있습니다.; 직접근거 3건, 공식/DART/IR/특허 근거 0건, 정량화 ... | 중 | data\반도체\LX세미콘\tech\source\lxsemicon_tech_local_proxy_eviden... |
## Step 2. Tech-to-Value Bridge
- **산출물 상태:** 확인됨: `data/반도체/LX세미콘/tech/lxsemicon_tech_to_value_inputs.json`
| 항목 | 값 | 해석 |
|---|---:|---|
| Tech Agent 원점수 | 원문 확인 필요 | Tech Agent 내부 원점수 또는 기술 평가 총점입니다. |
| Auditor 보수 반영 점수 | 별도 Auditor 보수 점수 미생성 | claim/evidence 검증 후 Chair 반영에 사용하는 보수 점수입니다. |
| Base Bridge Score | 원문 확인 필요 | 사업화 연결 전 기본 Tech-to-Value 점수입니다. |
| Peer-adjusted Bridge Score | 원문 확인 필요 | Step 8의 peer percentile 보정 후 점수입니다. |
| Bridge Grade | 별도 판정 미생성 | 최종 기술-가치 연결 판정입니다. |
| Shared Rubric | prompts.py | Tech-to-Value Bridge는 기술이 실제 기업가치로 연결될 가능성을 평가한다. 판단 순서는 다음과 같다. 1. 기술/IP 근거가 실제 제품·공정·고객 채택과 연결되는가? 2. 양산성과 확장성이 확인되는가? 3. 고객 채택 또는 매출 전환 가... |

- **COMMERCIALIZATION_WATCH:** 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 추적해야 하는 사업화 추적형입니다.
- **TECH_FINANCE_GAP:** 기술/IP 포트폴리오는 있으나 수익성·현금흐름·재무안정성 전환 근거가 약한 기술-재무 괴리형입니다.
## Step 3. KIPRIS/IP quantitative signals
- **산출물 상태:** 확인됨: `data/반도체/LX세미콘/tech/lxsemicon_tech_patent_evidence.json`
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 0건 |
| 회사 출원인/권리자 매칭 | 0건 |
| 등록 특허 | 0건 |
| 존속 가능 특허 | 0건 |
| 최근 5년 특허 | 0건 |
| IPC/CPC 다양성 | 0개 |
| H01L 등 핵심 IPC 특허 | 0건 |
| 핵심기술 키워드 매칭 | 0회 |

| 대표 특허 예시 | 상태/연도 |
|---|---|
| 대표 특허 예시 | patent evidence JSON의 title/status 필드 확인 필요 |
## Step 4. Patent KMeans clustering
- **산출물 상태:** 확인됨: `data/반도체/LX세미콘/tech/tech_ml_signal.json`
| 항목 | 값 |
|---|---:|
| 모델 | keyword_fallback |
| 정규화 특허 텍스트 레코드 | 0건 |
| 특허 클러스터 수 | 1개 |

| Cluster | 특허 수 | 대표 키워드 | 해석 |
|---:|---:|---|---|
| 0 | 0건 | 기술 키워드 미확인 | 기술 텍스트 유사도 기반 클러스터 |
## Step 5. Focal-company cosine similarity
- **산출물 상태:** 원문 확인 필요: 산출물 파일을 찾지 못했습니다.
- **분석 방법:** TF-IDF + Cosine Similarity

| 비교 기업 | Cosine Similarity | 해석 |
|---|---:|---|
| 비교군 | 산출물 원문 참조 | pairwise/matrix/company_pairs 중 회사명 매칭 구조 확인 필요 |

- Cosine Similarity는 기술 텍스트 유사도 신호이며, 재무 건전성이나 주가 방향을 직접 의미하지 않습니다.
## Step 6. Reference-universe company-level KMeans peer group
- **산출물 상태:** 확인됨: `data/반도체/_sector_common/ml_universe/tech_peer_clusters.json`
| 항목 | 값 |
|---|---|
| 현재 기업 cluster | 4 |
| Peer group | 팹리스/설계 |
| Reference universe | valuation/credit ML overlay 기반 딥테크 후보군 |

- Company-level KMeans는 기업 단위 특허/IP 특징량을 기준으로 기술 peer group을 배정합니다.
## Step 7. UMAP 2D tech peer map
- **산출물 상태:** 확인됨: `data/반도체/_sector_common/ml_universe/tech_peer_map.json`
| 항목 | 값 |
|---|---:|
| UMAP x | 원문 확인 필요 |
| UMAP y | 원문 확인 필요 |
| Cluster | 원문 확인 필요 |
| Map PNG | `data/반도체/_sector_common/ml_universe/tech_peer_map.png` |

- UMAP 2D Peer Map은 고차원 특허/IP 특징량을 2차원으로 압축해 peer 위치를 설명하는 시각화 보조지표입니다.
- 한글 폰트는 시스템에 설치된 Malgun Gothic/Noto Sans CJK/AppleGothic을 우선 사용하도록 처리합니다.
## Step 8. Peer-percentile adjusted Tech-to-Value Bridge
- **산출물 상태:** 원문 확인 필요: 산출물 파일을 찾지 못했습니다.
| 항목 | 값 | 해석 |
|---|---:|---|
| Base Bridge Score | 원문 확인 필요 | Tech-to-Value 기본 점수입니다. |
| Peer-adjusted Bridge Score | 원문 확인 필요 | reference universe 내 상대 위치를 반영한 보정 점수입니다. |
| Peer Percentile | 원문 확인 필요 | 같은 기술군 내 상대 순위입니다. |
| Final Bridge Grade | 별도 판정 미생성 | Chair 반영 시 보수 판단 기준입니다. |

- 이 보정은 기술/IP 상대 위치를 설명하기 위한 return-free 보조 지표이며, 미래 수익률 예측이 아닙니다.
## Step 9. Tech/IP Strength Index + NMF Topic Modeling
- **산출물 상태:** 확인됨: `data/반도체/LX세미콘/tech/tech_ip_ml.json`
### 9-1. Tech/IP Strength Index
| 항목 | 값 | 해석 |
|---|---:|---|
| Tech/IP Strength Index | 0.00/100 | 특허 등록률·존속성·최근성·IPC/CPC 다양성·핵심기술 키워드 밀도 점수를 통합한 IP 강도 지표입니다. |
| Reference Universe Percentile | 50.00% | reference universe 안에서의 상대적 기술/IP 위치입니다. |
| Patent Momentum Score | 0.00/100 | 최근 특허 활동과 기술 포트폴리오 지속성을 반영합니다. |

### 9-2. 특허/IP 원천 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 0건 |
| 회사 출원인/권리자 매칭 | 0건 |
| 등록 특허 | 0건 |
| 존속 가능 특허 | 0건 |
| 최근 5년 특허 | 0건 |
| IPC/CPC 다양성 | 0개 |
| H01L 등 핵심 IPC 특허 | 0건 |
| 핵심기술 키워드 매칭 | 0회 |
| 핵심기술 키워드 밀도 점수 | 0.00/100 |

### 9-3. NMF Topic Modeling
| Topic | 비중/점수 | 대표 키워드 |
|---|---:|---|
| Topic | 산출물 원문 참조 | `dominant_topics`/`topics` 구조 확인 필요 |

### 9-4. 해석
- lxsemicon의 Tech/IP Strength Index는 0.0/100, percentile 50.0로 산출되어 근거 보강 필요 IP 포지션으로 해석됩니다. NMF 기준 주된 기술 주제는 '주요 topic 확인 제한'입니다. 단, 이 지표는 기술/IP 포트폴리오 상대 강도 신호이며 고객 채택·양산·매출 전환·FCF 개선 근거를 대체하지 않습니다.
## Step 10. Technology Differentiation Score
- **산출물 상태:** 원문 확인 필요: 산출물 파일을 찾지 못했습니다.
### 10-1. Technology Differentiation Score 요약
| 항목 | 값 | 해석 |
|---|---:|---|
| Technology Differentiation Score | 원문 확인 필요 | peer 대비 특허/IP 포트폴리오가 얼마나 구별되는지 보는 비지도 ML 기반 차별화 점수입니다. |
| Reference Percentile | 원문 확인 필요 | 분석 universe 안에서의 상대적 차별화 위치입니다. |
| Grade | 원문 확인 필요 | 원문 grade: `원문 확인 필요` |
| Nearest Tech Peer | 원문 확인 필요 | cosine similarity=원문 확인 필요, technology distance=원문 확인 필요 |
| Dominant NMF Topic | 원문 확인 필요 | topic weight=원문 확인 필요, topic rarity=원문 확인 필요 |

### 10-2. 구성 점수
| 구성 요소 | 값 | 의미 |
|---|---:|---|
| Peer uniqueness | 원문 확인 필요 | 가장 가까운 peer와의 기술 텍스트 거리입니다. |
| Topic distinctiveness | 원문 확인 필요 | NMF dominant topic 집중도와 희소성을 반영합니다. |
| IPC specialization | 원문 확인 필요 | IPC/CPC 다양성과 핵심 IPC 집중도를 반영합니다. |
| Keyword uniqueness | 원문 확인 필요 | TF-IDF 상위 용어 중 고유 기술어 비중입니다. |

### 10-3. 차별화 근거 신호
| 원천 신호 | 값 |
|---|---:|
| 차별화 분석용 특허 텍스트 레코드 | 0건 |
| 회사 출원인/권리자 매칭 | 0건 |
| 등록 특허 | 0건 |
| 존속 가능 특허 | 0건 |
| 최근 5년 특허 | 0건 |
| IPC/CPC 다양성 | 0개 |
| H01L 등 핵심 IPC 특허 | 0건 |

### 10-4. 고유 기술어 / 차별화 키워드
- 산출물 원문 확인 필요

### 10-5. 해석
- LX세미콘의 Technology Differentiation Score는 peer 대비 기술/IP 포트폴리오 차별성 신호입니다.
- 현재는 5개 focal 기업 중심 검증 단계이며, 30개 reference universe 전체에 동일한 산출 방식을 확장 적용하면 percentile 해석의 안정성과 비교 설명력이 강화됩니다.
## Step 11. Patent Momentum Score + Tech-to-Value Evidence Confidence
- **산출물 상태:** 원문 확인 필요: 산출물 파일을 찾지 못했습니다.
### 11-1. Patent Momentum Score
| 항목 | 값 | 해석 |
|---|---:|---|
| Patent Momentum Score | 원문 확인 필요 | 최근 특허 활동과 기술 포트폴리오 지속성 신호입니다. |
| Momentum Grade | 원문 확인 필요 | 최근성·지속성 기준 보조 등급입니다. |

### 11-2. Tech-to-Value Evidence Confidence
| 항목 | 값 | 해석 |
|---|---:|---|
| Evidence Confidence | 원문 확인 필요 | 고객 채택·양산·매출·FCF 근거의 직접성을 보수적으로 평가합니다. |
| Confidence Grade | 원문 확인 필요 | 2차 산출물보다 직접 원천 근거를 우선하는 보수 기준입니다. |
| Direct Dimension Count | 원문 확인 필요/4 | 직접 근거가 확인된 사업화 연결 항목 수입니다. |

### 11-3. 고객 채택·양산·매출·FCF별 직접성
| 항목 | 상태 | 직접 근거 | 간접 근거 | 원문 확인 필요 |
|---|---|---:|---:|---:|
| 고객 채택 | 원문 확인 필요 | 0 | 0 | 0 |
| 양산 | 원문 확인 필요 | 0 | 0 | 0 |
| 매출 전환 | 원문 확인 필요 | 0 | 0 | 0 |
| FCF/현금흐름 | 원문 확인 필요 | 0 | 0 | 0 |

- Evidence Confidence는 `agent_output`, `generated_report` 등 2차 산출물보다 DART/IR/공시/CSV 직접 수치 근거를 더 강하게 인정합니다.
- 대표 스니펫이 문서 첫머리·목차·생성 보고서 헤더에 가까우면 강한 근거로 사용하지 않습니다.
## Artifact inventory
| 구분 | 경로 | 상태 |
|---|---|---|
| chair_summary | `data/반도체/LX세미콘/tech/tech_chair_summary.json` | 확인됨 |
| tech_packet | `data/반도체/LX세미콘/tech/tech.json` | 확인됨 |
| high_quality_md | `data/반도체/LX세미콘/tech/lxsemicon_tech_high_quality_report.md` | 확인됨 |
| tech_to_value | `data/반도체/LX세미콘/tech/lxsemicon_tech_to_value_inputs.json` | 확인됨 |
| patent_json | `data/반도체/LX세미콘/tech/lxsemicon_tech_patent_evidence.json` | 확인됨 |
| ml_signal | `data/반도체/LX세미콘/tech/tech_ml_signal.json` | 확인됨 |
| peer_similarity | `원문 확인 필요` | 미확인 |
| peer_cluster | `data/반도체/_sector_common/ml_universe/tech_peer_clusters.json` | 확인됨 |
| peer_map | `data/반도체/_sector_common/ml_universe/tech_peer_map.json` | 확인됨 |
| peer_percentile | `원문 확인 필요` | 미확인 |
| tech_ip_ml | `data/반도체/LX세미콘/tech/tech_ip_ml.json` | 확인됨 |
| tech_differentiation | `원문 확인 필요` | 미확인 |
| tech_momentum_confidence | `원문 확인 필요` | 미확인 |

---

## KIPRIS Tech ML Feature 반영 요약

- kipris_tech_ml_score: 4.0
- legal_stability_score_estimated: 10.0
- portfolio_momentum_score: 0.0
- ip_technology_fit_score: 0.0
- bridge_adjustment_points: -2.0
- bridge_signal: IP_QUALITY_WEAK

### 핵심 KIPRIS 정량 신호

- total_patents: 0
- registered_patents_estimated: 0
- alive_patents_estimated: 0
- recent_5y_application_patents: 0
- semiconductor_related_ipc_patents: 0
- registration_rate_estimated: None
- alive_rate_among_registered_estimated: None

주의: 이 값은 기술/IP 포트폴리오 품질 보조 신호이며, 고객 채택·양산·매출 전환·FCF 개선의 직접 근거로 보지는 않는다.

