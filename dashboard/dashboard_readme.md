# AlphaProve

AI 기반 반도체 기업 투자 분석 및 정량 밸류에이션 대시보드

---

## 📌 프로젝트 소개

**AlphaProve**는 반도체 기업 투자 분석을 위한 Streamlit 기반 AI 리서치 플랫폼입니다.  
기업의 재무, 시장성, 밸류에이션, 리스크, 동종기업 비교 데이터를 통합하여 투자자 관점의 분석 리포트를 제공합니다.

본 프로젝트는 다음 기능을 포함합니다.

- 투자자용 요약 리포트
- Chair Agent 기반 종합 분석 리포트
- 정량 밸류에이션 대시보드
- 동종기업 비교 분석
- DCF 민감도 분석
- ML 기반 품질 점수 및 투자 판단 보조

메인 애플리케이션은 Streamlit 기반으로 구성되어 있으며, 기업별 JSON / CSV / Excel 데이터를 읽어 동적으로 대시보드를 생성합니다.

---

## 🧩 프로젝트 구조

```bash
project/
│
├── app.py                         # 메인 실행 파일
│
├── dashboard/
│   ├── __init__.py
│   ├── chair_report.py            # Chair Agent 리포트 렌더링
│   ├── companies.py               # 섹터 및 기업 목록
│   ├── investor_report.py         # 투자자 리포트
│   ├── peer_comparison.py         # 동종기업 비교
│   ├── quant_dashboard.py         # 정량 대시보드
│   ├── risk_tab.py                # 시각적 리스크 분석 탭
│   ├── sidebar.py                 # 사이드바 UI
│   ├── state.py                   # 세션 상태 관리
│   └── styles.py                  # 전체 CSS 스타일
│
└── data/
    └── [sector]/
        └── [company]/
            ├── chair/
            ├── finance/
            └── valuation/
```

---

## 🚀 실행 방법

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

필수 라이브러리:

- streamlit
- pandas
- numpy
- plotly
- openpyxl

### 2. 애플리케이션 실행

```bash
streamlit run app.py
```

---

## 📊 주요 기능

### 1. 투자자 보고서

투자자 관점의 핵심 정보를 카드 형태로 제공합니다.

주요 제공 항목:

- 현재 주가
- 1개월 수익률
- 연환산 변동성
- MDD
- 핵심 투자 포인트
- 재무 안정성 지표
- Agent별 분석 요약
- 주가 차트

사용 데이터:

- `*_chair.json`
- `*_주식.csv`
- `*_재무.csv`

---

### 2. Chair Agent 보고서

AI Chair Agent가 생성한 Markdown 리포트를 HTML로 렌더링합니다.

주요 기능:

- Markdown → HTML 변환
- 코드 블록 지원
- 리스트 / 헤딩 지원
- 최신 리포트 자동 선택

파일 규칙:

```bash
*_chair_report.md
```

---

### 3. 정량 대시보드

7개 탭 기반의 정량 분석 시스템입니다.

| 탭 | 설명 |
|---|---|
| 요약 | 핵심 투자지표 |
| 시장성 | 주가 / 거래량 / 리스크 |
| 재무 | 재무제표 분석 |
| 밸류에이션 | DCF 및 멀티플 |
| 동종기업 비교 | Peer 분석 |
| 리스크 | 히트맵 / 다운사이드 시나리오 / 노출도 / 모니터링 기반 시각적 리스크 분석 |
| 민감도 | WACC / 성장률 민감도 |

---


## ⚠️ 리스크 탭

리스크 탭은 JSON payload를 기반으로 기업의 주요 하방 요인과 방어 요인을 시각적으로 분석하는 화면입니다.
단순한 리스크 문구 나열이 아니라, 변동성·MDD·Beta·DCF 괴리율·FCF Margin·영업이익률 등 정량 지표를 활용해 투자자가 모니터링해야 할 위험 요인을 구조화합니다.

주요 구성은 다음과 같습니다.

| 섹션 | 설명 |
|---|---|
| 상단 KPI 카드 | 종합 리스크 수준, 하방 압력, 고객 집중 리스크, 업황 민감도, 재무 방어력, 모니터링 우선순위 표시 |
| 리스크 히트맵 | 발생 가능성 × 영향도 기준으로 핵심 리스크를 산점도 형태로 시각화 |
| 핵심 리스크 설명 | 고객사 투자 지연, 업황 둔화, 환율 변동, CAPEX 부담 등 주요 위험 요인 설명 |
| 다운사이드 시나리오 | 경미 / 기준 / 심화 시나리오별 매출·영업이익·적정가 영향 비교 |
| 리스크 노출도 구성 | 고객 집중도, 업황/수요, 수익성/원가, 환율/거시, 생산/실행 리스크 비중을 도넛 차트로 표시 |
| 방어 요인 / 완충 장치 | 높은 영업이익률, 현금 보유, 포트폴리오 확장, 현금창출력 등 방어 요소 제시 |
| 모니터링 체크리스트 | 고객사 CAPEX, 수주/가동률, 환율, 재고, 신제품 양산, 실적 가이던스 추적 |
| 이벤트 캘린더 | 실적 발표, 고객사 투자 계획, 신제품 양산, 환율/금리 체크포인트 등 주요 이벤트 타임라인 표시 |

리스크 판단 로직 예시:

- 연환산 변동성 또는 MDD가 높을수록 종합 리스크 수준을 상향
- DCF 기준 하방 괴리율이 클수록 하방 압력 증가
- Beta가 높을수록 업황 민감도 상승
- FCF Margin과 영업이익률이 높을수록 재무 방어력 개선
- Valuation diagnostics의 주의 항목 수를 기반으로 모니터링 우선순위 계산

시각화는 Plotly 기반으로 구현되며, Streamlit 레이아웃을 활용해 KPI 카드, 히트맵, 도넛 차트, 체크리스트, 이벤트 타임라인을 하나의 리스크 분석 화면으로 제공합니다.

---
## 📈 밸류에이션 기능

지원하는 가치평가 방식:

- DCF
- Reverse DCF
- EPV
- Graham Number
- Football Field
- Peer Multiple
- ML Overlay

주요 계산 항목:

- WACC
- Terminal Growth Rate
- FCF Projection
- Enterprise Value
- Equity Value
- Margin of Safety

---

## 🏭 지원 산업 및 기업

현재 지원 섹터:

- 바이오
- 이차전지
- 반도체

현재 반도체 기업 예시:

- DB하이텍
- GST
- ISC
- LX세미콘
- 리노공업
- 원익IPS
- 한미반도체
- 한솔케미칼

기업 목록은 `dashboard/companies.py`에서 관리합니다.

---

## 🔍 동종기업 비교 시스템

Excel 기반 Valuation Workbook을 읽어 Peer 비교를 수행합니다.

사용 시트:

| 시트명 | 역할 |
|---|---|
| `00_대시보드` | 현재 기업 핵심 지표 |
| `10_피어비교` | 동종기업 재무·멀티플 비교 |
| `18_밸류에이션_유니버스` | 유니버스 스코어링과 산점도 |
| `22_종합가치평가` | 종합 결론 텍스트 |

---

## 🎨 UI/UX 특징

커스텀 CSS 기반 프리미엄 투자 플랫폼 스타일을 적용합니다.

- 반응형 레이아웃
- 투자 플랫폼 스타일 KPI 카드
- Plotly 인터랙티브 차트
- 리스크 히트맵 및 도넛 차트
- 이벤트 캘린더 타임라인
- Sidebar Navigation
- 투자 리포트 스타일 디자인

---

## ⚙️ 상태 관리

Streamlit Session State 기반으로 다음 상태를 관리합니다.

- 선택된 섹터
- 선택된 기업
- 선택된 메뉴
- 차트 기간

쿼리 파라미터 연동 예시:

```bash
?sector=반도체&company=DB하이텍
```

---

## 📂 데이터 구조

기업 데이터는 아래 구조를 따릅니다.

```bash
data/
└── 반도체/
    └── DB하이텍/
        ├── chair/
        │   ├── xxx_chair.json
        │   └── xxx_chair_report.md
        │
        ├── finance/
        │   ├── xxx_주식.csv
        │   └── xxx_재무.csv
        │
        └── valuation/
            ├── xxx_dashboard_payload.json
            └── xxx_valuation_workbook.xlsx
```

---

## 🤖 AI 분석 시스템

본 프로젝트는 다수의 AI Agent 기반 분석 구조를 사용합니다.

| Agent | 역할 |
|---|---|
| Finance | 재무 분석 |
| Market | 시장 분석 |
| Tech | 기술 분석 |
| Valuation | 가치평가 |
| Issue | 이슈 분석 |
| Macro | 거시환경 분석 |

Agent 결과를 종합하여 최종 투자 의견을 생성합니다.

---

## 📌 핵심 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | Streamlit |
| Visualization | Plotly |
| Data Processing | Pandas / NumPy |
| Excel Parsing | openpyxl |
| AI Output | JSON 기반 Agent 시스템 |
| Styling | Custom CSS |

---

## 🧠 향후 개선 방향

- 실시간 데이터 API 연동
- AI 자동 리포트 생성
- 뉴스 기반 이벤트 감지
- 벡터DB 기반 리서치 검색
- 포트폴리오 최적화
- 사용자 인증 시스템
- 다크모드 지원

---

## 👨‍💻 개발 목적

본 프로젝트는 금융 데이터 분석 및 AI 기반 투자 리서치 자동화를 목표로 개발되었습니다.

핵심 목표:

- 기업 분석 자동화
- 정량 기반 투자 판단
- 멀티에이전트 리서치 시스템
- 투자자용 시각화 UX

---

## 📄 라이선스

MIT License

---

## 🙌 Contributors

- Team AlphaProve
- 금융데이터분석 프로젝트
