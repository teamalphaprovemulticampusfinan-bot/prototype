# Valuation Agent

> **독립 Intake 기반 Explainable Valuation Pipeline + Dashboard/Workbook 생성 엔진**

---

## 📌 개요

**Valuation Agent**는 AlphaProve용 독립 가치평가 파이프라인입니다.

기존 `finance_agent`와 분리된 **sidecar 구조**로 설계되어 있으며, 자체 intake 데이터를 기반으로 다음 기능을 수행합니다.

- DART 기반 재무 정규화
- 주가 / 시가총액 / 유동성 분석
- WACC 계산
- DCF 가치평가
- Peer Multiple 비교
- Explainable ML Overlay
- Advanced Valuation (Football Field, Reverse DCF, Owner Earnings, Graham Number)
- Validation / Audit Trail
- Dashboard Payload 생성
- Excel Workbook 생성

---

## ✨ 핵심 특징

### 독립 파이프라인

Valuation Agent는 `finance_agent` 결과를 직접 읽지 않습니다.  
대신 `valuation/intake/` 아래의 **valuation 전용 intake 데이터**를 기반으로 동작합니다.

### Explainable 구조

모든 계산은 아래 구조로 설계되어 있습니다.

- Source account 유지
- Validation audit trail 저장
- Workbook traceability 제공

---

## 🔄 전체 파이프라인 흐름

```
valuation/intake
        ↓
normalize_financials()
        ↓
compute_wacc()
        ↓
build_dcf()
        ↓
compute_peer_multiples()
        ↓
build_ml_overlay()
        ↓
advanced_valuation()
        ↓
validate_valuation()
        ↓
dashboard_payload
        ↓
excel_workbook
```

---

## 📁 디렉토리 구조

### Intake

```
data/<field>/<company>/valuation/intake/
```

| 파일명 | 설명 |
|---|---|
| `valuation_price_history.csv` | 가격 히스토리 |
| `valuation_peer_input.csv` | 피어 입력 데이터 |
| `valuation_price_summary.json` | 가격 요약 |
| `valuation_source_map.json` | 소스 맵 |

### Output

```
data/<field>/<company>/valuation/
```

| 파일명 | 설명 |
|---|---|
| `<company>_valuation_metrics.json` | 가치평가 지표 |
| `<company>_dashboard_payload.json` | 대시보드 페이로드 |
| `<company>_valuation_workbook.xlsx` | 엑셀 워크북 |
| `<company>_valuation_report.md` | 가치평가 리포트 |
| `validation.json` | 검증 결과 |

---

## 🧩 주요 모듈

### 1. Financial Normalizer — `normalizer.py`

재무제표를 정규화하고 핵심 지표를 생성합니다.

| 생성 지표 | 설명 |
|---|---|
| ROE | 자기자본이익률 |
| ROA | 총자산이익률 |
| OP Margin | 영업이익률 |
| FCF Margin | 잉여현금흐름 마진 |
| Revenue Growth | 매출 성장률 |
| Debt Ratio | 부채 비율 |

---

### 2. WACC Engine — `wacc.py`

$$\text{WACC} = \frac{E}{V} \times K_e + \frac{D}{V} \times K_d \times (1 - T)$$

**사용 변수**

- Risk Free Rate
- Beta
- Market Risk Premium
- Tax Rate
- Cost of Debt

---

### 3. DCF Engine — `dcf.py`

**Terminal Value 계산식**

$$TV = \frac{FCF \times (1+g)}{WACC - g}$$

**산출 지표**

- Enterprise Value
- Equity Value
- Implied Price
- Upside / Downside

---

### 4. Peer Valuation — `peer_comps.py`

**산출 배수**

| 배수 | 설명 |
|---|---|
| P/S | 주가매출비율 |
| PER | 주가수익비율 |
| PBR | 주가순자산비율 |
| EV/Sales | 기업가치/매출 |
| EV/EBIT | 기업가치/영업이익 |
| P/FCF | 주가/잉여현금흐름 |

**기능**

- Peer Median 계산
- Relative Valuation Signal 생성
- Percentile 기반 attractiveness 분석

---

### 5. ML Overlay — `ml_overlay.py`

> ⚠️ 실제 predictive ML 모델이 아닌, **설명 가능한 deterministic scoring layer**입니다.

**평가 요소**

- ROE percentile
- Operating Margin percentile
- FCF Margin percentile
- PSR attractiveness
- Volatility
- Debt Ratio

**출력**

- Composite Score
- Valuation Label
- Confidence

---

### 6. Advanced Valuation — `advanced_valuation.py`

#### Football Field

다중 valuation range를 비교합니다.

| 방법론 | 비고 |
|---|---|
| DCF | 현금흐름 할인법 |
| PER | 주가수익비율 |
| PBR | 주가순자산비율 |
| EV/Sales | 기업가치/매출 |
| EV/EBIT | 기업가치/영업이익 |

#### Reverse DCF

시장 가격 기준으로 **Implied Terminal Growth**를 역산합니다.

#### Owner Earnings

$$\text{Owner Earnings} = CFO - CAPEX$$

#### Graham Number

$$\text{Graham Number} = \sqrt{22.5 \times EPS \times BPS}$$

---

### 7. Validation Layer — `validation.py`

| 검증 항목 | 설명 |
|---|---|
| Missing Financials | 재무 데이터 누락 |
| Negative FCF | 음수 잉여현금흐름 |
| Missing Price History | 가격 히스토리 누락 |
| Short Financial History | 재무 히스토리 부족 |
| Missing Shares Outstanding | 발행주식수 누락 |
| Liquidity Issues | 유동성 이슈 |

**출력 상태**

```
PASS  |  PASS_WITH_WARNINGS  |  FAIL
```

---

### 8. Dashboard Payload — `dashboard_payload.py`

프론트엔드 대시보드 렌더링용 JSON을 생성합니다.

- Summary cards
- Price charts
- Valuation charts
- Peer comparison
- Positioning map

---

### 9. Workbook Generator — `workbook.py` / `presentation_polish.py`

**생성 파일:** `valuation_workbook.xlsx`

| 시트 | 내용 |
|---|---|
| 00_대시보드 | 종합 요약 |
| 07_WACC | WACC 계산 |
| 08_FCF_추정 | FCF 추정 |
| 09_DCF_가치평가 | DCF 결과 |
| 10_피어비교 | Peer 비교 |
| 12_민감도 | 민감도 분석 |
| 22_종합가치평가 | Football Field |
| 24_역산DCF | Reverse DCF |
| 29_시장위치_맵 | 시장 포지셔닝 |

**특징**

- `openpyxl` 기반 자동 생성
- 차트 자동 생성
- 한국어 라벨링
- 투자자용 formatting
- 208개 semiconductor universe positioning

---

## 🔍 주요 데이터 흐름

### 가격 데이터

**입력:** `valuation_price_history.csv`

**생성 지표**

- MDD (최대낙폭)
- Volatility (변동성)
- Moving Average (이동평균)
- Trading Value (거래대금)
- Turnover Ratio (회전율)

### Peer Universe

- 기준: **208개 semiconductor reference universe**
- 사용 목적: relative positioning, percentile scoring, peer clustering

---

## ✅ Validation Philosophy

Valuation Agent는 아래 세 가지 원칙을 우선합니다.

1. **설명 가능성** — 모든 산출 근거 명시
2. **감사 추적성** — 원천 데이터 trace 가능
3. **재현 가능성** — 동일 입력 → 동일 결과

따라서 source account 보존 / deterministic scoring / audit trail 저장 / workbook traceability 구조를 유지합니다.

---

## 🏗️ 설계 원칙

| 원칙 | 설명 |
|---|---|
| **독립성** | `finance_agent` 의존 최소화 |
| **Explainability** | 모든 valuation score는 설명 가능해야 함 |
| **Auditability** | 원천 데이터 trace 가능해야 함 |
| **Investor-facing Output** | 최종 산출물은 투자자 보고용 Excel Workbook 기준으로 설계 |

---

## 📦 최종 산출물

```
<company>_valuation_metrics.json
<company>_dashboard_payload.json
<company>_valuation_workbook.xlsx
<company>_valuation_report.md
```

---

## 🚀 향후 확장 가능 영역

- [ ] Monte Carlo DCF
- [ ] Scenario Engine
- [ ] Factor Exposure
- [ ] Residual Income Model
- [ ] Economic Profit Model
- [ ] Bayesian Valuation Overlay
- [ ] Sector-specific Templates
- [ ] API Serving Layer
- [ ] Frontend Dashboard Integration

---

## 📝 License

Internal use only — AlphaProve Project.