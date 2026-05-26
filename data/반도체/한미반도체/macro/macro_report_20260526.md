# 📊 매크로 분석 리포트 (반도체 딥테크 섹터)

## 📘 지표 설명

### 🔢 점수 Score
- 매크로 환경을 종합한 점수입니다.
- 양수는 위험자산에 우호적, 음수는 위험자산에 비우호적입니다.

| 점수 구간 | 의미 |
|---|---|
| +4 이상 | 강한 매수 환경 |
| +2 ~ +3 | 매수 우위 |
| -1 ~ +1 | 중립 |
| -2 ~ -3 | 매도 우위 |
| -4 이하 | 강한 매도 환경 |

### ⚠️ 위험도 Risk Level

| 위험도 | 의미 |
|---|---|
| LOW | 매우 안정 |
| MEDIUM_LOW | 비교적 안정 |
| NEUTRAL | 중립 / 방향성 불확실 |
| MEDIUM_HIGH | 리스크 증가 |
| HIGH | 매우 위험 |

### 🎯 신뢰도 Confidence
- 0에 가까울수록 불확실, 1에 가까울수록 확신이 강합니다.
- 데이터 커버리지가 낮으면 penalty가 적용됩니다.

| 신뢰도 | 의미 |
|---|---|
| 0.7 이상 | 높은 신뢰 |
| 0.4 ~ 0.7 | 중간 신뢰 |
| 0.4 이하 | 낮은 신뢰 |

---

## 🧾 요약

- 생성 시각: 2026-05-26 12:13:37
- 신호: **BUY**
- 점수: 3
- 위험도: MEDIUM_LOW
- 신뢰도: 0.5
- 커버리지: 100% (penalty: 0.0)

---

## 📌 한 줄 요약

매크로 환경 점수는 3점으로, 위험자산에 우호적인 환경입니다. 위험도는 MEDIUM_LOW입니다.

---

## 📡 데이터 커버리지

- 사용 가능: ecos_일별, ext_일별, 시장벤치마크, ecos_월별, ecos_분기별, ext_월별, 뉴스, 규제
- 누락: 없음
- 커버리지 비율: 100%

---

## 🔍 판단 근거

- 국고채_10년 상승 → 금리 부담 증가
- 국고채_3년 하락 → 유동성 환경 개선
- 콜금리 상승 → 금리 부담 증가
- cd금리_91일 하락 → 유동성 환경 개선
- 국내 장단기 금리차 확대 → 경기 정상화 신호
- 원달러 고수준 구간 하락 → 환율 부담 완화
- 신용스프레드_bbb- 확대 → 신용 리스크 증가
- 신용스프레드_aa- 확대 → 신용 리스크 증가
- 10년-2년 스프레드 확대 → 경기 정상화/수요 개선 신호
- 미국_국채_10년 상승 → 글로벌 금리 부담
- 미국_국채_13주 하락 → 글로벌 유동성 부담 완화
- 달러인덱스 상승 → 달러 강세/위험자산 부담
- 평균 유가 상승 → 원가 부담·인플레이션 압력
- 유가_wti 상승 → 유가 상승은 경기 회복과 비용 부담을 동시에 반영
- 유가_brent 상승 → 유가 상승은 경기 회복과 비용 부담을 동시에 반영
- 브렌트-위티 스프레드 축소 → 수요 회복이 더 강한 신호
- 구리 가격 하락 → 경기 둔화 우려
- 미국 하이일드 스프레드 확대 → 글로벌 신용 리스크 증가
- 전체 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 한국 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 미국 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 반도체 섹터 20일 수익률 양수 → 시장/섹터 방향성 우호
- 전체 시장 20/60일 모멘텀 음수 → 추세 약화
- 반도체 섹터 20/60일 모멘텀 음수 → 추세 약화
- 시장 risk-off 비율 25% 이하 → 벤치마크 약세 비중 낮음
- CPI 전년비 117.4% — 고물가 구간 → 금리 인하 기대 약화
- BSI 전망 67.0 — 기업 경기 비관 우위
- 실업률 2.5% — 고용 양호
- GDP 전년비 1.6% — 완만한 성장 → 중립적
- GDP 전기비 -0.2% — 전분기 대비 역성장 → 모멘텀 약화
- 미국 기준금리 인하 → 글로벌 유동성 완화
- oecd_cli_한국 100.77 상승 → 경기 개선 신호
- oecd_cli_미국 100.06 상승 → 경기 개선 신호
- g20_cli 100.14 상승 → 경기 개선 신호
- 뉴스 긍정/부정 신호 중립
- 규제 리스크 신호 약함
- ecos_일별/미국_연방기금금리_dff: 1기간 변화율 급락 극단 구간, rolling z-score 하단 3σ 이상 (변화율 -0.26%, z=-4.75)
- ecos_일별/미국_콜금리_effr: 1기간 변화율 급락 극단 구간, rolling z-score 하단 3σ 이상 (변화율 -0.26%, z=-4.75)
- ecos_일별/미국_sofr: 1기간 변화율 급등 극단 구간 (변화율 4.46%, z=-1.23)
- ecos_일별/신용스프레드_bbb-: rolling z-score 하단 3σ 이상 (변화율 0.05%, z=-3.19)
- ext_일별/미국_연방기금금리_dff: 1기간 변화율 급락 극단 구간, rolling z-score 하단 3σ 이상 (변화율 -0.26%, z=-4.75)
- ext_일별/미국_콜금리_effr: 1기간 변화율 급락 극단 구간, rolling z-score 하단 3σ 이상 (변화율 -0.26%, z=-4.75)
- ext_일별/미국_sofr: 1기간 변화율 급등 극단 구간 (변화율 4.46%, z=-1.23)
- ext_일별/신용스프레드_bbb-: rolling z-score 하단 3σ 이상 (변화율 0.05%, z=-3.19)
- 후공정/HBM·메모리 연계 기업 + 메모리/반도체 수요 proxy 개선 → 수요 민감도 우호
- 딥테크/장기 성장 기업 + 금리 상승 압력 → 할인율·자금조달 민감도 부담

---

## 📊 항목별 핵심 수치 (Score Breakdown)

### ecos_일별
- 국고채_10년_level: 3.061
- 국고채_10년_diff: 0.011
- 국고채_10년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.362, 'low': 1.731, 'high_q': 0.8, 'low_q': 0.2}
- 국고채_3년_level: 2.716
- 국고채_3년_diff: -0.016
- 국고채_3년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.29, 'low': 1.308, 'high_q': 0.8, 'low_q': 0.2}
- 콜금리_level: 2.511
- 콜금리_diff: 0.004
- 콜금리_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.429, 'low': 0.76, 'high_q': 0.8, 'low_q': 0.2}
- cd금리_91일_level: 2.55
- cd금리_91일_diff: -0.01
- cd금리_91일_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.56, 'low': 1.1, 'high_q': 0.8, 'low_q': 0.2}
- 국고채_10년_3년_스프레드: 0.345
- 국고채_10년_3년_스프레드_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 0.5, 'low': 0.0919999999999996, 'high_q': 0.8, 'low_q': 0.2}
- 원달러_level: 1423.2
- 원달러_diff: -9.8
- 원달러_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 1357.6, 'low': 1129.0, 'high_q': 0.8, 'low_q': 0.2}
- 신용스프레드_bbb-_level: 6.256
- 신용스프레드_bbb-_diff: 0.003
- 신용스프레드_aa-_level: 0.406
- 신용스프레드_aa-_diff: 0.003
- 국고채_10년_zone: `neutral`
- 국고채_3년_zone: `neutral`
- 콜금리_zone: `neutral`
- cd금리_91일_zone: `neutral`
- 원달러_zone: `high`
- 신용스프레드_bbb-_zone: `low`
- 신용스프레드_aa-_zone: `low`

### ext_일별
- 미국_국채_10년_2년_스프레드: 0.501
- 미국_국채_10년_2년_스프레드_diff: 0.018
- 미국_국채_10년_2년_스프레드_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 0.5780000686645508, 'low': -0.3449999237060543, 'high_q': 0.8, 'low_q': 0.2}
- 미국_국채_10년_level: 4.101
- 미국_국채_10년_diff: 0.008
- 미국_국채_10년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 4.186999797821045, 'low': 1.5390000343322754, 'high_q': 0.8, 'low_q': 0.2}
- 미국_국채_13주_level: 3.718
- 미국_국채_13주_diff: -0.039
- 미국_국채_13주_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 4.5929999351501465, 'low': 0.1030000001192092, 'high_q': 0.8, 'low_q': 0.2}
- 달러인덱스_dxy_level: 99.8
- 달러인덱스_dxy_diff: 0.27
- 달러인덱스_dxy_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 104.16000366210938, 'low': 93.83999633789062, 'high_q': 0.8, 'low_q': 0.2}
- 유가_평균_diff: 0.24
- 유가_wti_diff: 0.41
- 유가_brent_diff: 0.07
- 구리_diff: -0.0125
- 미국_하이일드_스프레드_level: 2.94
- 미국_하이일드_스프레드_diff: 0.09
- 미국_국채_10년_zone: `neutral`
- 미국_국채_13주_zone: `neutral`
- 달러인덱스_dxy_zone: `neutral`

### ecos_월별
- 한국_기준금리_level: 2.5
- 한국_기준금리_diff: 0.0
- 한국_기준금리_criteria: {'method': 'empirical_percentile', 'lookback_observations': 94, 'high': 3.5, 'low': 0.75, 'high_q': 0.8, 'low_q': 0.2}
- cpi_전년비_level: 117.42
- bsi_전산업_전망_level: 67.0
- 실업률_level: 2.45
- 한국_기준금리_zone: `neutral`
- cpi_전년비_zone: `high`
- bsi_전산업_전망_zone: `low`

### ecos_분기별
- gdp성장률_전년비_level: 1.6
- gdp성장률_전기비_level: -0.2

### ext_월별
- 미국_기준금리_ffr_level: 4.09
- 미국_기준금리_ffr_diff: -0.13
- 미국_기준금리_ffr_criteria: {'method': 'empirical_percentile', 'lookback_observations': 94, 'high': 4.722000000000001, 'low': 0.09, 'high_q': 0.8, 'low_q': 0.2}
- 미국_실업률_level: 4.4
- oecd_cli_한국_level: 100.7692
- oecd_cli_한국_diff: 0.2511
- oecd_cli_미국_level: 100.0611
- oecd_cli_미국_diff: 0.1144
- g20_cli_level: 100.1448
- g20_cli_diff: 0.0659
- 미국_기준금리_ffr_zone: `neutral`
- 미국_실업률_zone: `neutral`
- oecd_cli_한국_zone: `neutral`
- oecd_cli_미국_zone: `neutral`
- g20_cli_zone: `neutral`

### 뉴스
- positive_keyword_count: 0
- negative_keyword_count: 0

### 규제
- regulation_risk_keyword_count: 0

---

## 🤖 LLM 보조 분석 (반도체 딥테크 섹터 관점)

### 요약
현재 매크로 환경은 총점 3점, 리스크 레벨 'medium'으로 평가되며, 전반적으로 중립 우호적인 흐름을 보입니다. 이는 유동성, 신용, 환율, 인플레이션, 투자심리, 규제 등 다양한 거시경제 지표들이 안정적인 수준을 유지하거나 개선되는 추세를 반영합니다. 이러한 환경은 국내 반도체 딥테크 상장기업에 긍정적인 영향을 미칠 수 있으나, 개별 기업의 사업 리스크 및 글로벌 경기 변동성을 고려한 신중한 접근이 필요합니다.

### 매크로 해석
유동성 측면에서 국고채 10년물(3.061%), 3년물(2.716%), 콜금리(2.511%), CD금리 91일물(2.55%) 등 주요 금리 지표들이 과거 2861일 평균 대비 중간 수준에 위치하며 안정적인 흐름을 보이고 있습니다. 이는 반도체 섹터의 자금 조달 환경에 큰 부담을 주지 않는 수준입니다. 신용 리스크는 국고채 대비 신용 스프레드(BBB- 6.256%, AA- 0.406%)가 안정적인 수준을 유지하고 있어 현재로서는 낮은 편입니다. 이는 반도체 기업들의 신용 위험이 크지 않음을 시사합니다. 환율 측면에서 원달러 환율(1423.2원)은 과거 평균 대비 하락하는 추세(diff -9.8)를 보이고 있으며, 달러 인덱스(99.8) 역시 소폭 하락했습니다. 이는 수출 비중이 높은 반도체 기업들에게 단기적으로는 부정적일 수 있으나, 과도한 원화 강세 우려를 완화하는 측면도 있습니다. 인플레이션은 CPI 전년비 레벨(117.42)이 월별 데이터로 제공되며, 구체적인 추세 판단은 제한적이나 전반적인 물가 안정 기조를 예상해 볼 수 있습니다. 이는 반도체 제조 원가에 간접적인 영향을 미칠 수 있습니다. 투자심리 측면에서는 뉴스 키워드 분석 결과 긍정적/부정적 키워드 수가 모두 0으로 나타나, 현재 시장의 투자심리가 특정 이슈에 크게 좌우되지 않고 중립적인 상태임을 보여줍니다. 이는 반도체 섹터의 투자 심리에도 큰 변동성을 야기하지 않을 것으로 예상됩니다. 규제 리스크는 관련 키워드 수가 0으로 나타나, 현재로서는 특별한 규제 관련 이슈가 부각되지 않고 있음을 의미합니다. 이는 반도체 섹터의 사업 환경에 직접적인 부정적 영향을 미치지 않습니다.

### 🔬 반도체 섹터 종합 영향
현재의 중립 우호적인 매크로 환경은 국내 반도체 딥테크 기업들에게 긍정적인 신호로 작용할 수 있습니다. 안정적인 금리 수준과 낮은 신용 리스크는 투자 및 운영 자금 조달에 유리한 환경을 조성합니다. 다만, 원달러 환율의 하락 추세는 수출 기업의 수익성에 일부 부담으로 작용할 수 있으며, 글로벌 AI Capex 사이클 및 미중 반도체 수출 규제와 같은 섹터 고유의 리스크 요인들을 지속적으로 모니터링할 필요가 있습니다.

### 주요 리스크
- 원달러 환율 하락 추세 (1423.2원, diff -9.8)
- 미국 국채 10년물 금리 레벨 (4.101%)
- 글로벌 AI Capex 사이클 변동성

### 📌 확인 포인트 (Watch Points)

| 지표 | 현재 상태 | 주의 기준 | 반도체 관련성 |
|---|---|---|---|
| 원달러 환율 | 1423.2원으로 하락 추세 (diff -9.8) | 지속적인 하락은 수출 기업 수익성 악화 우려 | 수출 비중이 높은 반도체 기업의 수익성에 직접적인 영향 |
| 미국 국채 10년물 금리 | 4.101% 수준으로 과거 평균 대비 높은 레벨 | 금리 상승은 성장주 밸류에이션 할인 요인으로 작용 가능 | 반도체 딥테크 기업의 성장주 특성상 밸류에이션에 부담으로 작용 가능 |
| 미국 국채 10년물 - 2년물 스프레드 | 0.501%로 플랫 구간 유지 | 경기 침체 신호인 역전 또는 급격한 평탄화 여부 주시 | 경기 침체 우려는 반도체 수요 둔화로 이어질 수 있음 |

### 🔗 근거 연결 (Evidence Links)

- **[macro_ev_1]** 원달러 환율이 하락 추세를 보이고 있어 수출 기업에 부담이 될 수 있습니다. _(출처: ecos_일별)_
- **[macro_ev_2]** 미국 국채 10년물 금리가 4.101% 수준으로 과거 평균 대비 높은 레벨을 유지하고 있습니다. _(출처: ext_일별)_
- **[macro_ev_3]** 미국 국채 10년물과 2년물 금리 스프레드가 0.501%로 플랫 구간을 유지하고 있습니다. _(출처: ext_일별)_
- **[macro_ev_4]** 주요 단기 금리 지표들이 안정적인 수준을 유지하고 있습니다. _(출처: ecos_일별)_
- **[macro_ev_5]** 현재 시장에 부각되는 규제 리스크나 부정적인 뉴스가 관찰되지 않고 있습니다. _(출처: 뉴스)_

---

## 📂 상세 데이터

### 시장벤치마크
- market_benchmark_available: True
- kospi_지수: 4107.5
- kosdaq_지수: 900.42
- krx_반도체_지수: 6131.68
- 코스피200: 579.46
- 나스닥: 23724.96
- sox_반도체_지수: 7228.6602
- s&p500: 6840.2
- 시장수익률_20일: 2.9992
- 시장수익률_60일: 14.2207
- 시장변동성_20일: 18.9275
- 시장변동성_z_252일: 0.0015
- 시장모멘텀_20_60: -5.831
- 시장_risk_off_비율: 0.2143
- 한국시장수익률_20일: 12.0045
- 미국시장수익률_20일: 2.9992
- 반도체섹터수익률_20일: 9.7956
- 반도체섹터변동성_20일: 36.3683
- 반도체섹터모멘텀_20_60: -17.5139
- available_market_benchmark_columns: ['kospi_지수', 'kosdaq_지수', 'krx_반도체_지수', '코스피200', '나스닥', 'sox_반도체_지수', 's&p500', '시장수익률_20일', '시장수익률_60일', '시장변동성_20일', '시장변동성_z_252일', '시장모멘텀_20_60', '시장_risk_off_비율', '한국시장수익률_20일', '미국시장수익률_20일', '반도체섹터수익률_20일', '반도체섹터변동성_20일', '반도체섹터모멘텀_20_60']

### 변화율_rolling_기준
- score_raw: 8
- score_capped: 4
- details: {'ecos_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': 10, 'dataset_score_capped': 2, 'triggered_count': 31, 'triggered_items': [{'indicator': '미국_연방기금금리_dff', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': -2, 'latest_1_period_change_pct': -0.2584, 'latest_zscore': -4.7522, 'score_impact': 2}, {'indicator': '미국_콜금리_effr', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': -2, 'latest_1_period_change_pct': -0.2584, 'latest_zscore': -4.7522, 'score_impact': 2}, {'indicator': '미국_sofr', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 4.4554, 'latest_zscore': -1.2267, 'score_impact': -2}, {'indicator': '신용스프레드_bbb-', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.048, 'latest_zscore': -3.1941, 'score_impact': 2}, {'indicator': '미국_정책금리_상단', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': -4.6812, 'score_impact': 2}, {'indicator': '미국_정책금리_하단', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': -4.6812, 'score_impact': 2}, {'indicator': 'krx_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.2785, 'latest_zscore': 3.0055, 'score_impact': 2}, {'indicator': '미국_국채_13주', 'direction_rule': 'risk_up', 'z_alert': -1, 'shock_flag': -1, 'latest_1_period_change_pct': -1.0381, 'latest_zscore': -2.6329, 'score_impact': 1}, {'indicator': '미국_단기금리_3m', 'direction_rule': 'risk_up', 'z_alert': -1, 'shock_flag': -1, 'latest_1_period_change_pct': -0.7979, 'latest_zscore': -2.6124, 'score_impact': 1}, {'indicator': '국고채_10년_3년_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 8.4906, 'latest_zscore': 0.1177, 'score_impact': -1}, {'indicator': '미국_회사채_bbb', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 1.006, 'latest_zscore': -1.0846, 'score_impact': -1}, {'indicator': '미국_ig_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 3.8961, 'latest_zscore': -0.653, 'score_impact': -1}]}, 'ext_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': 10, 'dataset_score_capped': 2, 'triggered_count': 31, 'triggered_items': [{'indicator': '미국_연방기금금리_dff', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': -2, 'latest_1_period_change_pct': -0.2584, 'latest_zscore': -4.7522, 'score_impact': 2}, {'indicator': '미국_콜금리_effr', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': -2, 'latest_1_period_change_pct': -0.2584, 'latest_zscore': -4.7522, 'score_impact': 2}, {'indicator': '미국_sofr', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 4.4554, 'latest_zscore': -1.2267, 'score_impact': -2}, {'indicator': '신용스프레드_bbb-', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.048, 'latest_zscore': -3.1941, 'score_impact': 2}, {'indicator': '미국_정책금리_상단', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': -4.6812, 'score_impact': 2}, {'indicator': '미국_정책금리_하단', 'direction_rule': 'risk_up', 'z_alert': -2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': -4.6812, 'score_impact': 2}, {'indicator': 'krx_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.2785, 'latest_zscore': 3.0055, 'score_impact': 2}, {'indicator': '미국_국채_13주', 'direction_rule': 'risk_up', 'z_alert': -1, 'shock_flag': -1, 'latest_1_period_change_pct': -1.0381, 'latest_zscore': -2.6329, 'score_impact': 1}, {'indicator': '미국_단기금리_3m', 'direction_rule': 'risk_up', 'z_alert': -1, 'shock_flag': -1, 'latest_1_period_change_pct': -0.7979, 'latest_zscore': -2.6124, 'score_impact': 1}, {'indicator': '국고채_10년_3년_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 8.4906, 'latest_zscore': 0.1177, 'score_impact': -1}, {'indicator': '미국_회사채_bbb', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 1.006, 'latest_zscore': -1.0846, 'score_impact': -1}, {'indicator': '미국_ig_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 3.8961, 'latest_zscore': -0.653, 'score_impact': -1}]}, 'ecos_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': 16, 'dataset_score_capped': 2, 'triggered_count': 29, 'triggered_items': [{'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 2, 'latest_1_period_change_pct': 19.941, 'latest_zscore': 4.7541, 'score_impact': 2}, {'indicator': 'krx_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 2, 'latest_1_period_change_pct': 27.9547, 'latest_zscore': 4.899, 'score_impact': 2}, {'indicator': 'krx_반도체_지수_모멘텀_20_60', 'direction_rule': 'market_up', 'z_alert': -2, 'shock_flag': -2, 'latest_1_period_change_pct': -4481.0407, 'latest_zscore': -3.2368, 'score_impact': -2}, {'indicator': '나스닥_수익률_5일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 484.6296, 'latest_zscore': 0.7946, 'score_impact': 2}, {'indicator': 'sox_반도체_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 147.9868, 'latest_zscore': 0.6031, 'score_impact': 2}, {'indicator': '시장수익률_1일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -6865.3243, 'latest_zscore': 0.8056, 'score_impact': -2}, {'indicator': 'sox_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 13.483, 'latest_zscore': 3.3761, 'score_impact': 2}, {'indicator': 'krx_반도체_지수_수익률_60일', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 136.2642, 'latest_zscore': 3.8145, 'score_impact': 2}, {'indicator': '미국_정책금리_상단', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -5.8824, 'latest_zscore': 0.3463, 'score_impact': 1}, {'indicator': '나스닥_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 138.6872, 'latest_zscore': -0.0299, 'score_impact': 1}, {'indicator': 'sox_반도체_지수_모멘텀_20_60', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -2531.3016, 'latest_zscore': -1.1926, 'score_impact': -1}, {'indicator': 's&p500_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 123.3447, 'latest_zscore': -0.1235, 'score_impact': 1}]}, 'ext_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': 16, 'dataset_score_capped': 2, 'triggered_count': 29, 'triggered_items': [{'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 2, 'latest_1_period_change_pct': 19.941, 'latest_zscore': 4.7541, 'score_impact': 2}, {'indicator': 'krx_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 2, 'latest_1_period_change_pct': 27.9547, 'latest_zscore': 4.899, 'score_impact': 2}, {'indicator': 'krx_반도체_지수_모멘텀_20_60', 'direction_rule': 'market_up', 'z_alert': -2, 'shock_flag': -2, 'latest_1_period_change_pct': -4481.0407, 'latest_zscore': -3.2368, 'score_impact': -2}, {'indicator': '나스닥_수익률_5일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 484.6296, 'latest_zscore': 0.7946, 'score_impact': 2}, {'indicator': 'sox_반도체_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 147.9868, 'latest_zscore': 0.6031, 'score_impact': 2}, {'indicator': '시장수익률_1일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -6865.3243, 'latest_zscore': 0.8056, 'score_impact': -2}, {'indicator': 'sox_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 13.483, 'latest_zscore': 3.3761, 'score_impact': 2}, {'indicator': 'krx_반도체_지수_수익률_60일', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 136.2642, 'latest_zscore': 3.8145, 'score_impact': 2}, {'indicator': '미국_정책금리_상단', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -5.8824, 'latest_zscore': 0.3463, 'score_impact': 1}, {'indicator': '나스닥_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 138.6872, 'latest_zscore': -0.0299, 'score_impact': 1}, {'indicator': 'sox_반도체_지수_모멘텀_20_60', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -2531.3016, 'latest_zscore': -1.1926, 'score_impact': -1}, {'indicator': 's&p500_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 123.3447, 'latest_zscore': -0.1235, 'score_impact': 1}]}}

### 기업별_macro_민감도
- score: -1
- reasons: ['후공정/HBM·메모리 연계 기업 + 메모리/반도체 수요 proxy 개선 → 수요 민감도 우호', '딥테크/장기 성장 기업 + 금리 상승 압력 → 할인율·자금조달 민감도 부담']
- details: {'company': '한미반도체', 'company_dir': 'hanmi', 'field': '반도체', 'method': 'company_exposure_from_local_disclosures_and_yaml + macro_shock_from_official_timeseries_rolling_criteria', 'score_raw': -1, 'score_capped': -1, 'basis': {'macro_level': '한국은행 ECOS/FRED 등 공식 시계열의 과거분포 20/80 분위 기준', 'macro_rolling': 'rolling z-score ±2σ watch, ±3σ extreme 및 과거분포 5/95·1/99 분위 급등/급락 cutoff', 'export_fx': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용', 'raw_material': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용', 'equipment_regulation': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭', 'memory_hbm_demand': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용', 'rate_sensitivity': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시', 'credit_spread': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}, 'context': {'slug': 'hanmi', 'company_name': '한미반도체', 'field': '반도체', 'config_path': 'C:\\Agent_6.9\\data\\반도체\\한미반도체\\_company_common\\company.yaml', 'finance_csv_path': 'C:\\Agent_6.9\\data\\반도체\\한미반도체\\finance\\한미반도체_재무.csv', 'external_sensitivity_path': 'C:\\Agent_6.9\\data\\반도체\\_sector_common\\macro_company_sensitivity\\company_sensitivity_external.csv', 'role_flags': {'material_company': False, 'equipment_company': True, 'backend_packaging_company': True, 'hbm_memory_linked': True, 'deeptech_company': True, 'export_keyword_hint': False}, 'role_evidence': {'material_company': [], 'equipment_company': ['장비', '본더', 'bonder', 'tc bonder', '비전', '자동화'], 'backend_packaging_company': ['후공정'], 'hbm_memory_linked': ['tc bonder', '본더', '후공정'], 'deeptech_company': ['장비'], 'export_keyword_hint': []}, 'metrics': {'sales': 558917191547.0, 'operating_income': 255391604854.0, 'net_income': 152614498001.0, 'fcf': 87576840890.0, 'debt_ratio_pct': 31.426939814094, 'current_ratio_pct': 254.8048277734913, 'loss_making': False, 'fcf_negative': False}, 'metric_percentiles': {'debt_ratio_pct': {'available': True, 'observations': 50, 'current': 31.426939814094, 'pctl_rank': 0.52, 'q20': 20.01956806717066, 'q50': 30.79001553161623, 'q80': 85.6362461752803, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'fcf': {'available': True, 'observations': 50, 'current': 87576840890.0, 'pctl_rank': 0.86, 'q20': -5390844101.999999, 'q50': 26599404995.0, 'q80': 51547862446.4, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}}}, 'axes': {'export_fx_sensitivity': {'score': 0, 'exposure_level': 'unknown', 'exposure_metric': None, 'role_keyword_hint': False, 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': '원달러', 'latest': 1423.2, 'diff': 21.0, 'chg1_pct': 1.4976465554129126, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.2452987353363565, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '원달러', 'latest': 1423.2, 'diff': 21.0, 'chg1_pct': 1.4976465554129126, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.2452987353363565, 'pressure_component': 1}, {'dataset': 'ecos_분기별', 'indicator': '원달러', 'latest': 1423.2, 'diff': 40.299999999999955, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': 1}, {'dataset': 'ecos_일별', 'indicator': '원달러', 'latest': 1423.2, 'diff': -9.799999999999955, 'chg1_pct': -0.6838799720865318, 'chg20_pct': 1.5193665739353657, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.5362905060178226, 'pressure_component': -1}, {'dataset': 'ext_일별', 'indicator': '원달러', 'latest': 1423.2, 'diff': -9.799999999999955, 'chg1_pct': -0.6838799720865318, 'chg20_pct': 1.5193665739353657, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.5362905060178226, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.8000030517578, 'diff': 2.030006408691392, 'chg1_pct': 2.076308150139794, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.16414529279109139, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.8000030517578, 'diff': 2.030006408691392, 'chg1_pct': 2.076308150139794, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.16414529279109139, 'pressure_component': 1}, {'dataset': 'ecos_분기별', 'indicator': '달러인덱스_dxy', 'latest': 99.8000030517578, 'diff': -0.2299957275390767, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}]}, 'basis': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용'}, 'raw_material_sensitivity': {'score': 0, 'material_role': False, 'role_evidence': [], 'raw_material_ratio_pct': None, 'raw_material_ratio_level': 'unknown', 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': '구리', 'latest': 5.065499782562256, 'diff': 0.2604999542236328, 'chg1_pct': 5.421435245164274, 'chg20_pct': None, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.2272010695851945, 'pressure_component': 2}, {'dataset': 'ext_월별', 'indicator': '구리', 'latest': 5.065499782562256, 'diff': 0.2604999542236328, 'chg1_pct': 5.421435245164274, 'chg20_pct': None, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.2272010695851945, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': '유가_wti', 'latest': 60.97999954223633, 'diff': -1.3899993896484375, 'chg1_pct': -2.2286346215373176, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.002036605237293, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '유가_brent', 'latest': 65.06999969482422, 'diff': -1.9499969482421875, 'chg1_pct': -2.909574822313765, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9577266854154738, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '유가_평균', 'latest': 63.02499961853027, 'diff': -1.6699981689453125, 'chg1_pct': -2.5813404838984533, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9803108565570107, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 4.090000152587891, 'diff': -0.55999755859375, 'chg1_pct': -12.042964177103766, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.2661678404264171, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '유가_wti', 'latest': 60.97999954223633, 'diff': -1.3899993896484375, 'chg1_pct': -2.2286346215373176, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.002036605237293, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '유가_brent', 'latest': 65.06999969482422, 'diff': -1.9499969482421875, 'chg1_pct': -2.909574822313765, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9577266854154738, 'pressure_component': -1}]}, 'basis': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용'}, 'equipment_regulation_sensitivity': {'score': 0, 'equipment_role': True, 'role_evidence': ['장비', '본더', 'bonder', 'tc bonder', '비전', '자동화'], 'macro_pressure': {'available': True, 'pressure': 0, 'keyword_count': 0, 'method': 'recent_regulation_keyword_count_tail30'}, 'basis': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭'}, 'backend_hbm_memory_demand_sensitivity': {'score': 1, 'backend_role': True, 'hbm_memory_linked': True, 'role_evidence': ['tc bonder', '본더', '후공정'], 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': 'krx_반도체_지수', 'latest': 6131.68, 'diff': 1339.6100000000006, 'chg1_pct': 27.954725202261255, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 2, 'zscore': 4.8989818250901225, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수', 'latest': 7228.66015625, 'diff': 858.84033203125, 'chg1_pct': 13.482961146967543, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 3.376062231711732, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': 'krx_반도체_지수_수익률_60일', 'latest': 58.60732808236011, 'diff': 33.801487921094164, 'chg1_pct': 136.26423334725354, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 3.8144534929175826, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': 'krx_반도체_지수_모멘텀_20_60', 'latest': -40.35405191242747, 'diff': -41.27515843080649, 'chg1_pct': -4481.040749059433, 'chg20_pct': None, 'z_alert': -2, 'shock_flag': -2, 'zscore': -3.2368263096347176, 'pressure_component': -2}, {'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수_변동성_20일', 'latest': 41.52209823900188, 'diff': 24.77842348507864, 'chg1_pct': 147.98677022361994, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 2, 'zscore': 0.6031066584640467, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수_모멘텀_20_60', 'latest': -17.51387565081637, 'diff': -18.234225440223128, 'chg1_pct': -2531.3015577112674, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -1, 'zscore': -1.192552244478625, 'pressure_component': -2}, {'dataset': 'ecos_월별', 'indicator': '반도체섹터변동성_20일', 'latest': 36.36829945504229, 'diff': 14.256320555299798, 'chg1_pct': 64.47329124154429, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 1, 'zscore': 0.5395521158659877, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': '반도체섹터모멘텀_20_60', 'latest': -17.51387565081637, 'diff': -18.33460380470926, 'chg1_pct': -2233.943568006569, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -1, 'zscore': -1.3295071521948711, 'pressure_component': -2}]}, 'basis': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용'}, 'deeptech_loss_rate_sensitivity': {'score': -2, 'deeptech_role': True, 'loss_making': False, 'fcf_negative': False, 'operating_margin_pct': None, 'net_margin_pct': None, 'fcf': 87576840890.0, 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_일별', 'indicator': '국고채_10년', 'latest': 3.061, 'diff': 0.01100000000000012, 'chg1_pct': 0.360655737704918, 'chg20_pct': 3.272604588394068, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.7419010656950316, 'pressure_component': 2}, {'dataset': 'ecos_일별', 'indicator': '국고채_10년_3년_스프레드', 'latest': 0.3449999999999997, 'diff': 0.02700000000000008, 'chg1_pct': 8.490566037735881, 'chg20_pct': -7.50670241286866, 'z_alert': 0, 'shock_flag': 1, 'zscore': 0.11767392275213526, 'pressure_component': 2}, {'dataset': 'ecos_일별', 'indicator': '미국_콜금리_effr', 'latest': 3.86, 'diff': -0.010000000000000231, 'chg1_pct': -0.25839793281654533, 'chg20_pct': -5.85365853658536, 'z_alert': -2, 'shock_flag': -2, 'zscore': -4.752192001647556, 'pressure_component': -2}, {'dataset': 'ext_일별', 'indicator': '국고채_10년', 'latest': 3.061, 'diff': 0.01100000000000012, 'chg1_pct': 0.360655737704918, 'chg20_pct': 3.272604588394068, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.7419010656950316, 'pressure_component': 2}, {'dataset': 'ext_일별', 'indicator': '국고채_10년_3년_스프레드', 'latest': 0.3449999999999997, 'diff': 0.02700000000000008, 'chg1_pct': 8.490566037735881, 'chg20_pct': -7.50670241286866, 'z_alert': 0, 'shock_flag': 1, 'zscore': 0.11767392275213526, 'pressure_component': 2}, {'dataset': 'ext_일별', 'indicator': '미국_콜금리_effr', 'latest': 3.86, 'diff': -0.010000000000000231, 'chg1_pct': -0.25839793281654533, 'chg20_pct': -5.85365853658536, 'z_alert': -2, 'shock_flag': -2, 'zscore': -4.752192001647556, 'pressure_component': -2}, {'dataset': 'ecos_일별', 'indicator': '미국_국채_13주', 'latest': 3.7179999351501465, 'diff': -0.03900003433227539, 'chg1_pct': -1.0380632059906025, 'chg20_pct': -3.503763121453074, 'z_alert': -1, 'shock_flag': -1, 'zscore': -2.6328620728409136, 'pressure_component': -2}, {'dataset': 'ecos_일별', 'indicator': '미국_국채_10년_13주_스프레드', 'latest': 0.3829998970031738, 'diff': 0.04699993133544916, 'chg1_pct': 13.988076231510128, 'chg20_pct': 93.43410321587817, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.5734766125571635, 'pressure_component': 2}]}, 'basis': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시'}, 'high_debt_credit_spread_sensitivity': {'score': 0, 'debt_ratio_pct': 31.426939814094, 'debt_ratio_percentile': {'available': True, 'observations': 50, 'current': 31.426939814094, 'pctl_rank': 0.52, 'q20': 20.01956806717066, 'q50': 30.79001553161623, 'q80': 85.6362461752803, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'high_debt_by_same_field_p80': False, 'macro_pressure': {'available': True, 'pressure': -2, 'events': [{'dataset': 'ecos_월별', 'indicator': '회사채_aa-', 'latest': 3.122, 'diff': 0.10000000000000009, 'chg1_pct': 3.3090668431502435, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.3143735477483405, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '회사채_bbb-', 'latest': 8.972, 'diff': 0.1039999999999992, 'chg1_pct': 1.1727559765448703, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.5487791039756377, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_aa-', 'latest': 0.4059999999999997, 'diff': -0.0340000000000002, 'chg1_pct': -7.727272727272771, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.2112197163302256, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_bbb-', 'latest': 6.255999999999999, 'diff': -0.030000000000001137, 'chg1_pct': -0.477251034043924, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.4155097896077613, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '회사채_aa-', 'latest': 3.122, 'diff': 0.10000000000000009, 'chg1_pct': 3.3090668431502435, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.3143735477483405, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '회사채_bbb-', 'latest': 8.972, 'diff': 0.1039999999999992, 'chg1_pct': 1.1727559765448703, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.5487791039756377, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '신용스프레드_aa-', 'latest': 0.4059999999999997, 'diff': -0.0340000000000002, 'chg1_pct': -7.727272727272771, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.2112197163302256, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '신용스프레드_bbb-', 'latest': 6.255999999999999, 'diff': -0.030000000000001137, 'chg1_pct': -0.477251034043924, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.4155097896077613, 'pressure_component': -1}]}, 'basis': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}}, 'note': '숫자 노출도가 없으면 임의 수치를 만들지 않고 company.yaml 명시 키워드와 로컬 산출물만 사용합니다.'}

### macro_numeric_criteria
- ecos_일별: {'국고채_10년': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.362, 'low': 1.731, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.061, 'zone': 'neutral'}, '국고채_3년': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.29, 'low': 1.308, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.716, 'zone': 'neutral'}, '콜금리': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.429, 'low': 0.76, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.511, 'zone': 'neutral'}, 'cd금리_91일': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.56, 'low': 1.1, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.55, 'zone': 'neutral'}, '국고채_10년_3년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 0.5, 'low': 0.0919999999999996, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.3449999999999997, 'zone': 'neutral'}, '회사채_aa-': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 4.022, 'low': 2.124, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.122, 'zone': 'neutral'}, '회사채_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 10.234, 'low': 8.308, 'high_q': 0.8, 'low_q': 0.2, 'latest': 8.972, 'zone': 'neutral'}, '신용스프레드_aa-': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 0.916, 'low': 0.4880000000000002, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.4059999999999997, 'zone': 'low'}, '신용스프레드_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 7.196, 'low': 6.478999999999999, 'high_q': 0.8, 'low_q': 0.2, 'latest': 6.255999999999999, 'zone': 'low'}, '원달러': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 1357.6, 'low': 1129.0, 'high_q': 0.8, 'low_q': 0.2, 'latest': 1423.2, 'zone': 'high'}}
- ext_일별: {'달러인덱스_dxy': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 104.16000366210938, 'low': 93.83999633789062, 'high_q': 0.8, 'low_q': 0.2, 'latest': 99.8000030517578, 'zone': 'neutral'}, '미국_국채_10년': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 4.186999797821045, 'low': 1.5390000343322754, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.10099983215332, 'zone': 'neutral'}, '미국_국채_13주': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 4.5929999351501465, 'low': 0.1030000001192092, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.7179999351501465, 'zone': 'neutral'}, '미국_국채_10년_13주_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 1.1859999895095823, 'low': -0.7060003280639648, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.3829998970031738, 'zone': 'neutral'}, '미국_국채_10년_2년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 0.5780000686645508, 'low': -0.3449999237060543, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.5009998321533202, 'zone': 'neutral'}, '유가_wti': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 79.83000183105469, 'low': 56.06999969482422, 'high_q': 0.8, 'low_q': 0.2, 'latest': 60.97999954223633, 'zone': 'neutral'}, '유가_brent': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 84.30999755859375, 'low': 62.09999847412109, 'high_q': 0.8, 'low_q': 0.2, 'latest': 65.06999969482422, 'zone': 'neutral'}, '유가_평균': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 82.02000045776367, 'low': 59.045000076293945, 'high_q': 0.8, 'low_q': 0.2, 'latest': 63.02499961853027, 'zone': 'neutral'}, '천연가스': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 3.940999984741211, 'low': 2.302999973297119, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.124000072479248, 'zone': 'high'}, '구리': {'method': 'empirical_percentile', 'lookback_observations': 2861, 'high': 4.403500080108643, 'low': 2.7890000343322754, 'high_q': 0.8, 'low_q': 0.2, 'latest': 5.065499782562256, 'zone': 'high'}}

