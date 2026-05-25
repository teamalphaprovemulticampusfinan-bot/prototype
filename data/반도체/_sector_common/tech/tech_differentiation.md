# Technology Differentiation Score

- 생성 시각: 2026-05-07T22:10:03
- 방법론: Technology Differentiation Score = TF-IDF peer distance + NMF topic distinctiveness + IPC specialization + unique-term signal
- 해석 원칙: 미래 수익률 예측이 아니라 특허/IP 포트폴리오의 peer-relative 차별성을 설명하는 비지도 ML 신호입니다.

## 1. 회사별 Technology Differentiation Score

| 기업 | Differentiation Score | Percentile | Grade | Nearest peer | Similarity | Dominant topic |
|---|---:|---:|---|---|---:|---|
| 한미반도체 | 75.39 | 90.0 | DISTINCTIVE_TECH_LEADER | 엘티씨 | 0.4012 | 패키지 / 자재 / 패키지를 / 패키지의 |
| 덕산테코피아 | 61.4 | 70.0 | DIFFERENTIATED_TECH_POSITION | 한솔케미칼 | 0.1827 | 조성물 / 솔더 / 도전성 / 박리액 |
| 네패스 | 57.59 | 50.0 | MODERATE_DIFFERENTIATION | 엘티씨 | 0.4264 | 패키지 / 재배선 / 전기적으로 / 도전성 |
| 엘티씨 | 56.62 | 30.0 | MODERATE_DIFFERENTIATION | 한솔케미칼 | 0.4988 | 윤활유 / dc / 전력을 / 보호창 |
| 한솔케미칼 | 56.16 | 10.0 | MODERATE_DIFFERENTIATION | 엘티씨 | 0.4988 | 있게 / 자동차용 / 조성물 / 양자점 |

## 2. Component Scores

| 기업 | Peer uniqueness | Topic distinctiveness | IPC specialization | Keyword uniqueness |
|---|---:|---:|---:|---:|
| 한미반도체 | 70.0 | 96.37 | 44.0 | 90.0 |
| 덕산테코피아 | 90.0 | 98.39 | 16.5 | 10.0 |
| 네패스 | 50.0 | 93.15 | 54.0 | 30.0 |
| 엘티씨 | 20.0 | 94.49 | 80.0 | 50.0 |
| 한솔케미칼 | 20.0 | 96.25 | 55.5 | 70.0 |

## 3. 해석상 주의

- Technology Differentiation Score는 '좋은 기업' 점수가 아니라, peer 대비 기술/IP 포트폴리오가 얼마나 구별되는지 보는 점수입니다.
- 점수가 높더라도 양산, 고객 채택, 매출 전환, FCF 개선 근거가 약하면 Chair는 보수적으로 반영해야 합니다.
- 5개 기업 기준 결과는 데모/파일럿이며, 30개 reference universe로 확장할수록 percentile 해석력이 좋아집니다.
