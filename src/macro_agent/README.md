# 📊 Macro Agent

매크로 데이터를 기반으로 투자 판단(BUY / SELL / HOLD)을 생성하는 분석 시스템입니다.

금리, 환율, 원자재, 뉴스, 규제 데이터를 종합 분석하여 시장 환경을 점수화하고, 이를 기반으로 투자 의사결정을 지원합니다.

---

## 🚀 주요 기능

* 매크로 데이터 자동 분석
* 금리 / 환율 / 원자재 / 뉴스 / 규제 반영
* 매크로 환경 점수 계산
* 투자 신호 생성 (BUY / SELL / HOLD)
* JSON / CSV / Markdown 리포트 자동 생성

---

## 📂 프로젝트 구조

```
TEAM-A/
├─ src/
│   ├─ data/
│   │   └─ macro_data/        # 원본 매크로 데이터 (CSV)
│   │
│   ├─ macro_agent/           # 분석 로직
│   │   ├─ loader.py
│   │   ├─ preprocessor.py
│   │   ├─ feature_builder.py
│   │   ├─ scorer.py
│   │   ├─ decision.py
│   │   ├─ reporter.py
│   │   ├─ runner.py
│   │   └─ cli.py
│
├─ output/ (선택)
```

---

## ⚙️ 실행 방법

프로젝트 루트에서 실행:

```bash
python -m src.macro_agent.runner
```

---

## 📁 입력 데이터

위치:

```
src/data/macro_data/
```

예시 파일:

* ecos_일별_YYYYMMDD.csv
* ext_일별_YYYYMMDD.csv
* 뉴스_YYYYMMDD.csv
* 규제_YYYYMMDD.csv

---

## 📊 출력 결과

저장 위치:

```
src/data/macro_data/
```

생성 파일:

* macro_signal_YYYYMMDD.json
* macro_signal_YYYYMMDD.csv
* macro_report_YYYYMMDD.md

---

## 🧠 분석 흐름

```
데이터 로드
→ 전처리
→ Feature 생성
→ 점수 계산
→ 매수/매도 판단
→ 리포트 생성
```

---

## 📘 지표 설명

### 🔢 점수 (Score)

매크로 환경을 종합한 수치입니다.

* 양수 → 위험자산에 우호적
* 음수 → 위험자산에 비우호적

| 점수 구간   | 의미       |
| ------- | -------- |
| +4 이상   | 강한 매수 환경 |
| +2 ~ +3 | 매수 우위    |
| -1 ~ +1 | 중립       |
| -2 ~ -3 | 매도 우위    |
| -4 이하   | 강한 매도 환경 |

---

### ⚠️ 위험도 (Risk Level)

시장 리스크 수준을 나타냅니다.

| 위험도         | 의미           |
| ----------- | ------------ |
| LOW         | 매우 안정        |
| MEDIUM_LOW  | 비교적 안정       |
| NEUTRAL     | 중립 / 방향성 불확실 |
| MEDIUM_HIGH | 리스크 증가       |
| HIGH        | 매우 위험        |

---

### 🎯 신뢰도 (Confidence)

판단의 확실성 (0 ~ 1)

* 점수 절댓값이 클수록 신뢰도 증가

| 값         | 의미    |
| --------- | ----- |
| 0.7 이상    | 높은 신뢰 |
| 0.4 ~ 0.7 | 중간    |
| 0.4 이하    | 낮음    |

---

## 📌 출력 예시

```json
{
  "signal": "HOLD",
  "score": -2,
  "risk_level": "NEUTRAL",
  "confidence": 0.33
}
```

---

## ⚠️ 주의사항

* 본 시스템은 투자 참고용입니다.
* 실제 투자 결과를 보장하지 않습니다.
* 반드시 백테스트 및 검증 후 사용하세요.

---

## 🚀 향후 개선 방향

* 백테스트 기능 추가
* 점수 기준 자동 최적화
* 뉴스 감성 분석 고도화 (AI 활용)
* 자동 실행 (스케줄링)
* 시각화 대시보드 구축

---
