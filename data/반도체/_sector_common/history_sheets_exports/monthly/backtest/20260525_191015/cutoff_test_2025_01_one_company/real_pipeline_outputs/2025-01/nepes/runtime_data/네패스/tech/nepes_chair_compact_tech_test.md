# 네패스 종합 투자 보고서

## 4. 하위 에이전트 의견 요약

### 재무 분석
- **의견:** 보유
- 테스트용 재무 분석 본문입니다.

### 시장 분석
- **의견:** 보유
- 테스트용 시장 분석 본문입니다.

### 기술 분석
- **의견:** 매수
- **요약 방식:** 상세 Excel-frame·KIPRIS/IP·Tech ML 표는 Tech Agent 산출물에 보관하고, Chair에는 검증 후 핵심 신호만 요약합니다.

#### 1) Tech-to-Value Bridge 판정
| 항목 | 값 | 해석 |
|---|---:|---|
| Tech Agent 원점수 | 100.00/100 | Tech Agent 내부 원점수입니다. |
| Auditor 보수 반영 점수 | 73.00/100 | claim/evidence 검증 후 보수적으로 반영한 점수입니다. |
| Base Bridge Score | 73.00/100 | 기본 Tech-to-Value Bridge 판정입니다. |
| Peer-adjusted Bridge Score | 80.53/100 | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 신호입니다. |
| 최종 Tech-to-Value 판정 | 사업화 추적형(COMMERCIALIZATION_WATCH) | Chair는 기술성보다 사업화·재무 전환 근거를 우선합니다. |

- **COMMERCIALIZATION_WATCH:** 사업화 추적형. 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 이어지는 연결고리를 계속 추적해야 하는 상태입니다.
- **TECH_FINANCE_GAP:** 기술-재무 괴리형. 기술/IP 포트폴리오는 존재하지만 수익성·현금흐름·재무안정성으로 전환되는 직접 근거가 약한 상태입니다.

#### 2) Excel-frame 기반 기술 포지션 요약
| 대분류 | 항목 | 정량화 | 핵심 근거 | 등급 | 비고 |
|---|---|---|---|---|---|
| 대표 기술 | 대표 기술 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 핵심 제품/서비스 | 핵심 제품/서비스 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 고객 구매 이유 | 고객 구매 이유 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 경쟁 우위/대체가능성 | 경쟁 우위/대체가능성 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 활용 및 확장 산업 | 활용 및 확장 산업 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| 진입 부담/장벽 | 진입 부담/장벽 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |
| R&D 강도 | R&D 강도 | 5 | 확인 제한 | 강 | 필요 시 원천 근거 확인 |

#### 3) KIPRIS/특허 기반 IP 정량 신호
| 원천 신호 | 값 |
|---|---:|
| 정규화 특허 텍스트 레코드 | 2,378건 |
| 회사 출원인/권리자 매칭 | 828건 |
| 등록 특허 | 477건 |
| 존속 가능 특허 | 517건 |
| 최근 5년 특허 | 122건 |
| IPC/CPC 다양성 | 102개 |
| H01L 등 핵심 IPC 특허 | 12건 |

#### 4) 사업화 연결 체크
| 연결 항목 | 상태 | 점수 | 직접/간접/확인 제한 |
|---|---|---:|---|
| 고객 채택 | 직접 근거 | 88.00/100 | 직접 7건 / 간접 19건 / 확인 제한 0건 |
| 양산 | 직접 근거 | 88.00/100 | 직접 16건 / 간접 63건 / 확인 제한 0건 |
| 매출 전환 | 직접 근거 | 88.00/100 | 직접 7건 / 간접 21건 / 확인 제한 0건 |
| FCF/현금흐름 | 간접 근거 | 42.00/100 | 직접 0건 / 간접 1건 / 확인 제한 0건 |

#### 5) 선택 ML 신호 요약
| ML 신호 | 값 | Chair 반영 의미 |
|---|---:|---|
| Technology Differentiation Score | 57.59/100 / 50.00% | peer 대비 특허/IP 포트폴리오의 구별성입니다. |
| Tech-to-Value Evidence Confidence | 78.80/100 | 고객 채택·양산·매출·FCF 근거의 직접성을 보수적으로 평가합니다. |
| Patent Momentum Score | 52.64/100 | 최근 특허 활동과 기술 지속성 신호입니다. |
| Tech/IP Strength Index + NMF Topic Modeling | 52.00/100 / topic=패키지 / 재배선 / 전기적으로 / 도전성 | 특허/IP 포트폴리오 강도와 기술 주제 집중도를 설명합니다. |

#### 6) Tech Peer ML 통합 보정
- **Peer ML 구성:** Reference Universe 기반 KMeans peer group, 5개 focal 기업 Cosine Similarity, UMAP 2D Peer Map, Peer Percentile 기반 Tech-to-Value Bridge 보정.
- **Peer-adjusted Bridge:** 80.53/100, percentile=72.05%, cluster=반도체 후공정/패키징 cluster.
- **해석:** 이 ML 신호는 미래 수익률 예측이 아니라 기술/IP 포트폴리오의 상대 위치와 차별성을 설명하기 위한 return-free 보조 지표입니다.

#### 7) Chair 반영 원칙
- Chair 최종 보고서에는 Tech 상세 표 전체를 붙이지 않고 compact summary만 반영합니다.
- 상세 Excel-frame/ML 표는 Tech Agent 산출물과 부록 파일에서 확인합니다.
- 기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다.
- **상세 부록:** `workspace/outputs/nepes_tech_full_appendix.md`

### 이슈 분석
- **의견:** 보유
- 테스트용 이슈 분석 본문입니다.

### 거시경제
- **의견:** 매도
- 테스트용 거시경제 본문입니다.

## 5. 충돌 지점 및 해석
- 테스트입니다.
