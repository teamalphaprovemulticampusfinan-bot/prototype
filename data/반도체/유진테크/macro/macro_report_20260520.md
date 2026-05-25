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

- 생성 시각: 2026-05-20 12:27:43
- 신호: **SELL**
- 점수: -4
- 위험도: MEDIUM_HIGH
- 신뢰도: 0.67
- 커버리지: 100% (penalty: 0.0)

---

## 📌 한 줄 요약

매크로 환경 점수는 -4점으로, 위험자산에 비우호적인 환경입니다. 위험도는 MEDIUM_HIGH입니다.

---

## 📡 데이터 커버리지

- 사용 가능: ecos_일별, ext_일별, 시장벤치마크, ecos_월별, ecos_분기별, ext_월별, 뉴스, 규제
- 누락: 없음
- 커버리지 비율: 100%

---

## 🔍 판단 근거

- 국고채_10년 고수준 구간 하락 → 유동성 환경 개선 (고금리 완화)
- 국고채_3년 고수준 구간 하락 → 유동성 환경 개선 (고금리 완화)
- 국내 장단기 금리차 축소 → 경기 기대 약화 신호
- 원달러 고수준 구간 추가 상승 → 환율 리스크 심화
- 신용스프레드_bbb- 확대 → 신용 리스크 증가
- 신용스프레드_aa- 확대 → 신용 리스크 증가
- 미국_국채_10년 고수준 구간 추가 상승 → 글로벌 긴축 압력 심화
- 미국_국채_13주 상승 → 글로벌 금리 부담
- 달러인덱스 상승 → 달러 강세/위험자산 부담
- 평균 유가 하락 → 원가 부담 완화
- 유가_wti 하락 → 유가 하락은 원가 부담 완화와 성장 둔화 신호
- 유가_brent 하락 → 유가 하락은 원가 부담 완화와 성장 둔화 신호
- 브렌트-위티 스프레드 확대 → 글로벌 공급 우려가 상대적으로 커지는 신호
- 구리 가격 하락 → 경기 둔화 우려
- 전체 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 한국 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 미국 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 반도체 섹터 20일 수익률 양수 → 시장/섹터 방향성 우호
- 전체 시장 20/60일 모멘텀 음수 → 추세 약화
- 반도체 섹터 20/60일 모멘텀 음수 → 추세 약화
- 시장 risk-off 비율 25% 이하 → 벤치마크 약세 비중 낮음
- CPI 전년비 119.4% — 고물가 구간 → 금리 인하 기대 약화
- BSI 전망 71.0 — 기업 경기 비관 우위
- GDP 전년비 3.6% — 고성장 구간 → 경기 우호적
- GDP 전기비 1.7% — 전분기 대비 가속 성장
- 부정 뉴스 키워드 우세 → 투자심리 부담
- 규제 리스크 키워드 일부 발견 → 투자심리 부담
- ecos_일별/유가_브렌트_wti_스프레드: 1기간 변화율 급등 극단 구간 (변화율 109.30%, z=0.85)
- ecos_일별/kosdaq_지수_변동성_z_252일: 1기간 변화율 급등 극단 구간 (변화율 405.70%, z=-0.46)
- ecos_일별/미국_국채_10년: rolling z-score 상단 3σ 이상 (변화율 0.61%, z=3.59)
- ecos_일별/미국_국채_2년: rolling z-score 상단 3σ 이상 (변화율 0.00%, z=3.00)
- ext_일별/유가_브렌트_wti_스프레드: 1기간 변화율 급등 극단 구간 (변화율 109.30%, z=0.85)
- ext_일별/kosdaq_지수_변동성_z_252일: 1기간 변화율 급등 극단 구간 (변화율 405.70%, z=-0.46)
- ext_일별/미국_국채_10년: rolling z-score 상단 3σ 이상 (변화율 0.61%, z=3.59)
- ext_일별/미국_국채_2년: rolling z-score 상단 3σ 이상 (변화율 0.00%, z=3.00)

---

## 📊 항목별 핵심 수치 (Score Breakdown)

### ecos_일별
- 국고채_10년_level: 4.21
- 국고채_10년_diff: -0.029
- 국고채_10년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.43, 'low': 1.792, 'high_q': 0.8, 'low_q': 0.2}
- 국고채_3년_level: 3.751
- 국고채_3년_diff: -0.006
- 국고채_3년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.306, 'low': 1.36, 'high_q': 0.8, 'low_q': 0.2}
- 콜금리_level: 2.524
- 콜금리_diff: 0.0
- 콜금리_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.394, 'low': 0.86, 'high_q': 0.8, 'low_q': 0.2}
- cd금리_91일_level: 2.81
- cd금리_91일_diff: 0.0
- cd금리_91일_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.53, 'low': 1.17, 'high_q': 0.8, 'low_q': 0.2}
- 국고채_10년_3년_스프레드: 0.459
- 국고채_10년_3년_스프레드_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 0.4889999999999999, 'low': 0.0979999999999998, 'high_q': 0.8, 'low_q': 0.2}
- 원달러_level: 1503.4
- 원달러_diff: 3.6
- 원달러_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 1380.4, 'low': 1130.9, 'high_q': 0.8, 'low_q': 0.2}
- 신용스프레드_bbb-_level: 6.427
- 신용스프레드_bbb-_diff: 0.002
- 신용스프레드_aa-_level: 0.626
- 신용스프레드_aa-_diff: 0.002
- 국고채_10년_zone: `high`
- 국고채_3년_zone: `high`
- 콜금리_zone: `neutral`
- cd금리_91일_zone: `neutral`
- 원달러_zone: `high`
- 신용스프레드_bbb-_zone: `low`
- 신용스프레드_aa-_zone: `neutral`

### ext_일별
- 미국_국채_10년_2년_스프레드: 0.505
- 미국_국채_10년_2년_스프레드_diff: 0.0
- 미국_국채_10년_2년_스프레드_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 0.6040000176429748, 'low': -0.3149999046325682, 'high_q': 0.8, 'low_q': 0.2}
- 미국_국채_10년_level: 4.651
- 미국_국채_10년_diff: 0.028
- 미국_국채_10년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 4.21999979019165, 'low': 1.5700000524520874, 'high_q': 0.8, 'low_q': 0.2}
- 미국_국채_13주_level: 3.575
- 미국_국채_13주_diff: 0.007
- 미국_국채_13주_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 4.51800012588501, 'low': 0.1199999973177909, 'high_q': 0.8, 'low_q': 0.2}
- 달러인덱스_dxy_level: 99.271
- 달러인덱스_dxy_diff: 0.301
- 달러인덱스_dxy_criteria: {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 104.04000091552734, 'low': 94.11000061035156, 'high_q': 0.8, 'low_q': 0.2}
- 유가_평균_diff: -3.18
- 유가_wti_diff: -5.06
- 유가_brent_diff: -1.3
- 구리_diff: -0.075
- 미국_하이일드_스프레드_level: 2.83
- 미국_하이일드_스프레드_diff: 0.0
- 미국_국채_10년_zone: `high`
- 미국_국채_13주_zone: `neutral`
- 달러인덱스_dxy_zone: `neutral`

### ecos_월별
- 한국_기준금리_level: 2.5
- 한국_기준금리_diff: 0.0
- 한국_기준금리_criteria: {'method': 'empirical_percentile', 'lookback_observations': 101, 'high': 3.5, 'low': 1.0, 'high_q': 0.8, 'low_q': 0.2}
- cpi_전년비_level: 119.37
- bsi_전산업_전망_level: 71.0
- 실업률_level: 2.85
- 한국_기준금리_zone: `neutral`
- cpi_전년비_zone: `high`
- bsi_전산업_전망_zone: `low`

### ecos_분기별
- gdp성장률_전년비_level: 3.6
- gdp성장률_전기비_level: 1.7

### ext_월별
- 미국_기준금리_ffr_level: 3.64
- 미국_기준금리_ffr_diff: 0.0
- 미국_기준금리_ffr_criteria: {'method': 'empirical_percentile', 'lookback_observations': 101, 'high': 4.64, 'low': 0.09, 'high_q': 0.8, 'low_q': 0.2}
- 미국_실업률_level: 4.3
- oecd_cli_한국_level: 102.502
- oecd_cli_한국_diff: 0.0
- oecd_cli_미국_level: 100.8471
- oecd_cli_미국_diff: 0.0
- g20_cli_level: 100.6478
- g20_cli_diff: 0.0
- 미국_기준금리_ffr_zone: `neutral`
- 미국_실업률_zone: `neutral`
- oecd_cli_한국_zone: `high`
- oecd_cli_미국_zone: `neutral`
- g20_cli_zone: `neutral`

### 뉴스
- positive_keyword_count: 0
- negative_keyword_count: 9

### 규제
- regulation_risk_keyword_count: 1

---

## 🤖 LLM 보조 분석 (반도체 딥테크 섹터 관점)

### 요약
현재 매크로 환경은 중립 비우호적이며, 총점 -4점과 높은 리스크 레벨을 나타냅니다. 이는 고금리 지속, 원달러 환율 상승 압력, 부정적 뉴스 및 규제 리스크 증가 등 복합적인 요인에 기인하며, 반도체 딥테크 기업 투자에 있어 신중한 접근이 요구됩니다.

### 매크로 해석
유동성 측면에서 국고채 금리(10년물 4.21%, 3년물 3.751%)와 콜금리(2.524%), CD금리(2.81%)가 상대적으로 높은 수준을 유지하고 있으며, 이는 고금리 환경이 지속되고 있음을 시사합니다. 반도체 섹터는 고금리로 인한 성장주 밸류에이션 할인 압력을 받을 수 있습니다. 신용 리스크는 신용스프레드(BBB- 6.427%)가 소폭 상승했으나, AA- 스프레드(0.626%)는 안정적인 모습을 보입니다. 이는 전반적인 신용 시장의 불안정성이 크지 않음을 나타내지만, 금리 상승 시 신용 경색 가능성을 배제할 수 없습니다. 반도체 섹터는 자금 조달 비용 증가 및 투자 심리 위축으로 이어질 수 있습니다. 환율/달러 측면에서 원달러 환율(1503.4원)이 상승 추세를 보이며, 이는 수출 비중이 높은 반도체 기업의 단기 실적에 긍정적일 수 있으나, 과도한 상승은 글로벌 수요 둔화 우려를 야기할 수 있습니다. 달러 인덱스(99.271)는 소폭 상승했습니다. 인플레이션은 CPI 전년비 레벨(119.37)이 제시되지 않았으나, 유가(WTI -5.06%, Brent -1.3%) 및 구리(-0.075%) 가격 하락은 원자재 가격 안정화 가능성을 시사합니다. 이는 반도체 제조 원가에 긍정적인 영향을 줄 수 있습니다. 투자심리/뉴스 측면에서 긍정적 키워드 없이 부정적 키워드(9건)가 다수 감지되었으며, 이는 시장의 전반적인 투자 심리가 위축되었음을 나타냅니다. 반도체 섹터는 투자 심리 악화 시 밸류에이션 조정 압력을 받을 수 있습니다. 규제 리스크는 규제 관련 키워드(1건)가 감지되어 미중 반도체 수출 규제 등 지정학적 리스크가 여전히 상존함을 보여줍니다. 이는 반도체 기업의 사업 계획 및 공급망에 직접적인 영향을 미칠 수 있습니다.

### 🔬 반도체 섹터 종합 영향
현재 중립 비우호적인 매크로 환경은 반도체 딥테크 기업에 복합적인 영향을 미치고 있습니다. 고금리 지속은 성장주 밸류에이션에 부담을 주며, 원달러 환율 상승은 단기 실적에 긍정적일 수 있으나 글로벌 수요 둔화 우려를 동반합니다. 또한, 부정적인 뉴스 흐름과 규제 리스크는 투자 심리를 위축시키고 사업 불확실성을 증대시키는 요인으로 작용합니다.

### 주요 리스크
- 고금리 장기화로 인한 성장주 밸류에이션 할인 압력
- 원달러 환율의 과도한 상승으로 인한 글로벌 수요 둔화 우려
- 미중 반도체 수출 규제 등 지정학적 리스크의 사업 영향

### 📌 확인 포인트 (Watch Points)

| 지표 | 현재 상태 | 주의 기준 | 반도체 관련성 |
|---|---|---|---|
| 국고채 10년물 금리 | 4.21% 수준으로 높은 편 | 추가 상승 시 성장주 투자 매력도 저하 | 고금리 환경 지속 시 딥테크 기업의 자금 조달 비용 증가 및 밸류에이션 부담 가중 |
| 원달러 환율 | 1503.4원 수준으로 상승 압력 | 1500원대 상회 지속 시 글로벌 수요 둔화 우려 증폭 | 수출 비중 높은 기업의 실적 변동성 확대 및 경쟁력 약화 가능성 |
| 뉴스 키워드 분석 (부정적) | 부정적 키워드 9건 감지 | 부정적 뉴스 지속 시 투자 심리 위축 심화 | 반도체 섹터 전반의 투자 매력도 하락 및 주가 변동성 확대 요인 |

### 🔗 근거 연결 (Evidence Links)

- **[macro_ev_1]** 고금리 환경이 지속되고 있음을 시사합니다. _(출처: ecos_일별)_
- **[macro_ev_2]** 원달러 환율이 상승 추세를 보이며, 이는 수출 비중이 높은 반도체 기업의 단기 실적에 긍정적일 수 있으나, 과도한 상승은 글로벌 수요 둔화 우려를 야기할 수 있습니다. _(출처: ecos_일별)_
- **[macro_ev_3]** 부정적 키워드(9건)가 다수 감지되었으며, 이는 시장의 전반적인 투자 심리가 위축되었음을 나타냅니다. _(출처: 뉴스)_
- **[macro_ev_4]** 규제 관련 키워드(1건)가 감지되어 미중 반도체 수출 규제 등 지정학적 리스크가 여전히 상존함을 보여줍니다. _(출처: 규제)_
- **[macro_ev_5]** 미국 국채 10년물 금리가 높은 수준을 유지하고 있습니다. _(출처: ext_일별)_

---

## 📂 상세 데이터

### 시장벤치마크
- market_benchmark_available: True
- kospi_지수: 7516.04
- kosdaq_지수: 1111.09
- krx_반도체_프록시_kodex반도체: 140375.0
- 코스피200: 1171.3
- 나스닥: 26090.73
- sox_반도체_지수: 11410.2109
- s&p500: 7403.05
- 시장수익률_20일: 6.6179
- 시장수익률_60일: 12.1472
- 시장변동성_20일: 23.8116
- 시장변동성_z_252일: 0.1223
- 시장모멘텀_20_60: -5.5293
- 시장_risk_off_비율: 0.1429
- 한국시장수익률_20일: 13.5332
- 미국시장수익률_20일: 5.5221
- 반도체섹터수익률_20일: 19.8747
- 반도체섹터변동성_20일: 50.4481
- 반도체섹터모멘텀_20_60: -22.007
- available_market_benchmark_columns: ['kospi_지수', 'kosdaq_지수', 'krx_반도체_프록시_kodex반도체', '코스피200', '나스닥', 'sox_반도체_지수', 's&p500', '시장수익률_20일', '시장수익률_60일', '시장변동성_20일', '시장변동성_z_252일', '시장모멘텀_20_60', '시장_risk_off_비율', '한국시장수익률_20일', '미국시장수익률_20일', '반도체섹터수익률_20일', '반도체섹터변동성_20일', '반도체섹터모멘텀_20_60']
- semiconductor_benchmark_note: KRX 반도체 지수 원천값이 없어서 KODEX 반도체 ETF 프록시만 사용 가능

### 변화율_rolling_기준
- score_raw: 0
- score_capped: 0
- details: {'ecos_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -2, 'dataset_score_capped': -2, 'triggered_count': 23, 'triggered_items': [{'indicator': '유가_브렌트_wti_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 109.3028, 'latest_zscore': 0.8504, 'score_impact': -2}, {'indicator': 'kosdaq_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 405.6979, 'latest_zscore': -0.455, 'score_impact': 2}, {'indicator': '미국_국채_10년', 'direction_rule': 'risk_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.6057, 'latest_zscore': 3.5877, 'score_impact': -2}, {'indicator': '미국_국채_2년', 'direction_rule': 'risk_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 3.0005, 'score_impact': -2}, {'indicator': 'sox_반도체_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': -1.0099, 'latest_zscore': 3.4058, 'score_impact': 2}, {'indicator': '유가_wti', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -4.6567, 'latest_zscore': 1.8251, 'score_impact': 1}, {'indicator': 's&p500_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 30.7474, 'latest_zscore': 0.1178, 'score_impact': 1}, {'indicator': '국고채_10년', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -0.6841, 'latest_zscore': 2.2596, 'score_impact': -1}, {'indicator': '국고채_3년', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -0.1597, 'latest_zscore': 2.0229, 'score_impact': -1}, {'indicator': '미국_국채_10년_13주_스프레드', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 1.9905, 'latest_zscore': 2.6182, 'score_impact': -1}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.3181, 'score_impact': 1}, {'indicator': '나스닥', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.7741, 'score_impact': 1}]}, 'ext_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -2, 'dataset_score_capped': -2, 'triggered_count': 23, 'triggered_items': [{'indicator': '유가_브렌트_wti_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 109.3028, 'latest_zscore': 0.8504, 'score_impact': -2}, {'indicator': 'kosdaq_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 405.6979, 'latest_zscore': -0.455, 'score_impact': 2}, {'indicator': '미국_국채_10년', 'direction_rule': 'risk_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.6057, 'latest_zscore': 3.5877, 'score_impact': -2}, {'indicator': '미국_국채_2년', 'direction_rule': 'risk_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 3.0005, 'score_impact': -2}, {'indicator': 'sox_반도체_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': -1.0099, 'latest_zscore': 3.4058, 'score_impact': 2}, {'indicator': '유가_wti', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -4.6567, 'latest_zscore': 1.8251, 'score_impact': 1}, {'indicator': 's&p500_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 30.7474, 'latest_zscore': 0.1178, 'score_impact': 1}, {'indicator': '국고채_10년', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -0.6841, 'latest_zscore': 2.2596, 'score_impact': -1}, {'indicator': '국고채_3년', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -0.1597, 'latest_zscore': 2.0229, 'score_impact': -1}, {'indicator': '미국_국채_10년_13주_스프레드', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 1.9905, 'latest_zscore': 2.6182, 'score_impact': -1}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.3181, 'score_impact': 1}, {'indicator': '나스닥', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.7741, 'score_impact': 1}]}, 'ecos_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': 8, 'dataset_score_capped': 2, 'triggered_count': 25, 'triggered_items': [{'indicator': 'sox_반도체_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 903.4492, 'latest_zscore': 1.42, 'score_impact': 2}, {'indicator': '구리', 'direction_rule': 'risk_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 4.5731, 'latest_zscore': 3.076, 'score_impact': -2}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 13.8989, 'latest_zscore': 5.2041, 'score_impact': 2}, {'indicator': 'sox_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 8.6304, 'latest_zscore': 4.289, 'score_impact': 2}, {'indicator': 'kospi_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 607.9344, 'latest_zscore': 0.3534, 'score_impact': 1}, {'indicator': '유가_wti', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -1.3991, 'latest_zscore': 2.0362, 'score_impact': -1}, {'indicator': '유가_평균', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -2.1362, 'latest_zscore': 2.0046, 'score_impact': -1}, {'indicator': 'kosdaq_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -6.8151, 'latest_zscore': 2.014, 'score_impact': 1}, {'indicator': '나스닥', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 4.8144, 'latest_zscore': 2.5646, 'score_impact': 1}, {'indicator': 's&p500', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 2.6916, 'latest_zscore': 2.322, 'score_impact': 1}, {'indicator': 'kospi_지수_수익률_20일', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -20.0242, 'latest_zscore': 2.6498, 'score_impact': 1}, {'indicator': 'kospi_지수_수익률_60일', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 24.9638, 'latest_zscore': 2.0167, 'score_impact': 1}]}, 'ext_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': 8, 'dataset_score_capped': 2, 'triggered_count': 25, 'triggered_items': [{'indicator': 'sox_반도체_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 2, 'latest_1_period_change_pct': 903.4492, 'latest_zscore': 1.42, 'score_impact': 2}, {'indicator': '구리', 'direction_rule': 'risk_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 4.5731, 'latest_zscore': 3.076, 'score_impact': -2}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 13.8989, 'latest_zscore': 5.2041, 'score_impact': 2}, {'indicator': 'sox_반도체_지수', 'direction_rule': 'market_up', 'z_alert': 2, 'shock_flag': 0, 'latest_1_period_change_pct': 8.6304, 'latest_zscore': 4.289, 'score_impact': 2}, {'indicator': 'kospi_지수_변동성_z_252일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 607.9344, 'latest_zscore': 0.3534, 'score_impact': 1}, {'indicator': '유가_wti', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -1.3991, 'latest_zscore': 2.0362, 'score_impact': -1}, {'indicator': '유가_평균', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -2.1362, 'latest_zscore': 2.0046, 'score_impact': -1}, {'indicator': 'kosdaq_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -6.8151, 'latest_zscore': 2.014, 'score_impact': 1}, {'indicator': '나스닥', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 4.8144, 'latest_zscore': 2.5646, 'score_impact': 1}, {'indicator': 's&p500', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 2.6916, 'latest_zscore': 2.322, 'score_impact': 1}, {'indicator': 'kospi_지수_수익률_20일', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': -20.0242, 'latest_zscore': 2.6498, 'score_impact': 1}, {'indicator': 'kospi_지수_수익률_60일', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 24.9638, 'latest_zscore': 2.0167, 'score_impact': 1}]}}

### 기업별_macro_민감도
- score: 0
- reasons: []
- details: {'company': '유진테크', 'company_dir': 'eugene_tech', 'field': '반도체', 'method': 'company_exposure_from_local_disclosures_and_yaml + macro_shock_from_official_timeseries_rolling_criteria', 'score_raw': 0, 'score_capped': 0, 'basis': {'macro_level': '한국은행 ECOS/FRED 등 공식 시계열의 과거분포 20/80 분위 기준', 'macro_rolling': 'rolling z-score ±2σ watch, ±3σ extreme 및 과거분포 5/95·1/99 분위 급등/급락 cutoff', 'export_fx': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용', 'raw_material': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용', 'equipment_regulation': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭', 'memory_hbm_demand': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용', 'rate_sensitivity': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시', 'credit_spread': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}, 'context': {'slug': 'eugene_tech', 'company_name': '유진테크', 'field': '반도체', 'config_path': 'C:\\Agent_6.8\\data\\반도체\\유진테크\\_company_common\\company.yaml', 'finance_csv_path': 'C:\\Agent_6.8\\data\\반도체\\유진테크\\finance\\유진테크_재무.csv', 'external_sensitivity_path': 'C:\\Agent_6.8\\data\\반도체\\_sector_common\\macro_company_sensitivity\\company_sensitivity_external.csv', 'role_flags': {'material_company': False, 'equipment_company': False, 'backend_packaging_company': False, 'hbm_memory_linked': False, 'deeptech_company': False, 'export_keyword_hint': False}, 'role_evidence': {'material_company': [], 'equipment_company': [], 'backend_packaging_company': [], 'hbm_memory_linked': [], 'deeptech_company': [], 'export_keyword_hint': []}, 'metrics': {'sales': 350324287104.0, 'operating_income': 51671713116.0, 'net_income': 44481997780.0, 'fcf': 45229353664.0, 'debt_ratio_pct': 18.156716579736624, 'operating_margin_pct': 14.749680515487734, 'loss_making': False, 'fcf_negative': False}, 'metric_percentiles': {'debt_ratio_pct': {'available': True, 'observations': 60, 'current': 18.156716579736624, 'pctl_rank': 0.2, 'q20': 19.50589025876336, 'q50': 31.756309575260122, 'q80': 99.5871247418233, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'operating_margin_pct': {'available': True, 'observations': 60, 'current': 14.749680515487734, 'pctl_rank': 0.6333, 'q20': -0.3670062945932294, 'q50': 11.753710328816975, 'q80': 19.453273837564474, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'fcf': {'available': True, 'observations': 60, 'current': 45229353664.0, 'pctl_rank': 0.6667, 'q20': -7134276155.5999975, 'q50': 24854117993.5, 'q80': 100973388492.00003, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}}}, 'axes': {'export_fx_sensitivity': {'score': 0, 'exposure_level': 'unknown', 'exposure_metric': None, 'role_keyword_hint': False, 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': '원달러', 'latest': 1503.4, 'diff': 27.300000000000182, 'chg1_pct': 1.8494681932118562, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.8071187888757043, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '원달러', 'latest': 1503.4, 'diff': 27.300000000000182, 'chg1_pct': 1.8494681932118562, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.8071187888757043, 'pressure_component': 1}, {'dataset': 'ecos_분기별', 'indicator': '원달러', 'latest': 1427.0, 'diff': 3.7999999999999545, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': 1}, {'dataset': 'ecos_일별', 'indicator': '원달러', 'latest': 1503.4, 'diff': 3.6000000000001364, 'chg1_pct': 0.24003200426725435, 'chg20_pct': 2.0430326477974603, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.514326278527562, 'pressure_component': 1}, {'dataset': 'ext_일별', 'indicator': '원달러', 'latest': 1503.4, 'diff': 3.6000000000001364, 'chg1_pct': 0.24003200426725435, 'chg20_pct': 2.0430326477974603, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.514326278527562, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.27100372314452, 'diff': 1.1910018920898438, 'chg1_pct': 1.214316751483513, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.474121347084467, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.27100372314452, 'diff': 1.1910018920898438, 'chg1_pct': 1.214316751483513, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.474121347084467, 'pressure_component': 1}, {'dataset': 'ecos_분기별', 'indicator': '달러인덱스_dxy', 'latest': 96.98999786376952, 'diff': -2.8100051879882812, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}]}, 'basis': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용'}, 'raw_material_sensitivity': {'score': 0, 'material_role': False, 'role_evidence': [], 'raw_material_ratio_pct': None, 'raw_material_ratio_level': 'unknown', 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_일별', 'indicator': '유가_wti', 'latest': 103.5999984741211, 'diff': -5.060005187988281, 'chg1_pct': -4.6567320241612915, 'chg20_pct': -3.0688612121871794, 'z_alert': 0, 'shock_flag': -1, 'zscore': 1.8250516810971424, 'pressure_component': -2}, {'dataset': 'ecos_일별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 7.200004577636719, 'diff': 3.760009765625, 'chg1_pct': 109.30277430930589, 'chg20_pct': -35.42597675053526, 'z_alert': 0, 'shock_flag': 2, 'zscore': 0.8504119344078271, 'pressure_component': 2}, {'dataset': 'ext_일별', 'indicator': '유가_wti', 'latest': 103.5999984741211, 'diff': -5.060005187988281, 'chg1_pct': -4.6567320241612915, 'chg20_pct': -3.0688612121871794, 'z_alert': 0, 'shock_flag': -1, 'zscore': 1.8250516810971424, 'pressure_component': -2}, {'dataset': 'ext_일별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 7.200004577636719, 'diff': 3.760009765625, 'chg1_pct': 109.30277430930589, 'chg20_pct': -35.42597675053526, 'z_alert': 0, 'shock_flag': 2, 'zscore': 0.8504119344078271, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': '구리', 'latest': 6.197000026702881, 'diff': 0.2709999084472656, 'chg1_pct': 4.573066200461651, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 3.0759875517417736, 'pressure_component': 2}, {'dataset': 'ext_월별', 'indicator': '구리', 'latest': 6.197000026702881, 'diff': 0.2709999084472656, 'chg1_pct': 4.573066200461651, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 3.0759875517417736, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': '유가_brent', 'latest': 110.8000030517578, 'diff': -3.2099990844726847, 'chg1_pct': -2.8155416404931355, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.9666962827709986, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 7.200004577636719, 'diff': -1.7399978637695312, 'chg1_pct': -19.46305803800018, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.8736774658357628, 'pressure_component': -1}]}, 'basis': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용'}, 'equipment_regulation_sensitivity': {'score': 0, 'equipment_role': False, 'role_evidence': [], 'macro_pressure': {'available': True, 'pressure': 0, 'keyword_count': 0, 'method': 'recent_regulation_keyword_count_tail30'}, 'basis': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭'}, 'backend_hbm_memory_demand_sensitivity': {'score': 0, 'backend_role': False, 'hbm_memory_linked': False, 'role_evidence': [], 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': 'krx_반도체_프록시_kodex반도체', 'latest': 140375.0, 'diff': 16525.0, 'chg1_pct': 13.342753330641898, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 5.433444658045141, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수', 'latest': 11410.2109375, 'diff': 906.5107421875, 'chg1_pct': 8.630394292785027, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 4.289003192265333, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수_변동성_z_252일', 'latest': 1.701315895012488, 'diff': 1.5317691005573661, 'chg1_pct': 903.449166042957, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 2, 'zscore': 1.419992174260381, 'pressure_component': 2}, {'dataset': 'ext_월별', 'indicator': 'krx_반도체_프록시_kodex반도체', 'latest': 140375.0, 'diff': 16525.0, 'chg1_pct': 13.342753330641898, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 5.433444658045141, 'pressure_component': 2}, {'dataset': 'ext_월별', 'indicator': 'sox_반도체_지수', 'latest': 11410.2109375, 'diff': 906.5107421875, 'chg1_pct': 8.630394292785027, 'chg20_pct': None, 'z_alert': 2, 'shock_flag': 0, 'zscore': 4.289003192265333, 'pressure_component': 2}, {'dataset': 'ext_월별', 'indicator': 'sox_반도체_지수_변동성_z_252일', 'latest': 1.701315895012488, 'diff': 1.5317691005573661, 'chg1_pct': 903.449166042957, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 2, 'zscore': 1.419992174260381, 'pressure_component': 2}, {'dataset': 'ecos_일별', 'indicator': 'sox_반도체_지수', 'latest': 11410.2109375, 'diff': 107.69140625, 'chg1_pct': 0.9528088489672237, 'chg20_pct': 11.088286336386922, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.661985720088329, 'pressure_component': 2}, {'dataset': 'ecos_일별', 'indicator': 'krx_반도체_프록시_kodex반도체_수익률_1일', 'latest': -4.0170940170940135, 'diff': -4.267291090130986, 'chg1_pct': -1705.5719470788479, 'chg20_pct': 585.8299901157029, 'z_alert': 0, 'shock_flag': -1, 'zscore': -1.4078569974141704, 'pressure_component': -2}]}, 'basis': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용'}, 'deeptech_loss_rate_sensitivity': {'score': 0, 'deeptech_role': False, 'loss_making': False, 'fcf_negative': False, 'operating_margin_pct': 14.749680515487734, 'net_margin_pct': None, 'fcf': 45229353664.0, 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_일별', 'indicator': '미국_국채_10년', 'latest': 4.651000022888184, 'diff': 0.0279998779296875, 'chg1_pct': 0.6056646561048096, 'chg20_pct': 5.2738748294967275, 'z_alert': 2, 'shock_flag': 0, 'zscore': 3.5877357950352664, 'pressure_component': 2}, {'dataset': 'ecos_일별', 'indicator': '미국_국채_10년_13주_스프레드', 'latest': 1.0759999752044678, 'diff': 0.020999908447265847, 'chg1_pct': 1.9905125230763376, 'chg20_pct': 29.951639631027227, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.6181562745208913, 'pressure_component': 2}, {'dataset': 'ext_일별', 'indicator': '미국_국채_10년', 'latest': 4.651000022888184, 'diff': 0.0279998779296875, 'chg1_pct': 0.6056646561048096, 'chg20_pct': 5.2738748294967275, 'z_alert': 2, 'shock_flag': 0, 'zscore': 3.5877357950352664, 'pressure_component': 2}, {'dataset': 'ext_일별', 'indicator': '미국_국채_10년_13주_스프레드', 'latest': 1.0759999752044678, 'diff': 0.020999908447265847, 'chg1_pct': 1.9905125230763376, 'chg20_pct': 29.951639631027227, 'z_alert': 1, 'shock_flag': 0, 'zscore': 2.6181562745208913, 'pressure_component': 2}, {'dataset': 'ecos_월별', 'indicator': '국고채_10년', 'latest': 4.21, 'diff': 0.2869999999999999, 'chg1_pct': 7.315829722151412, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.8018764813068833, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '국고채_3년', 'latest': 3.751, 'diff': 0.1559999999999997, 'chg1_pct': 4.339360222531274, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.1292145781708072, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '콜금리', 'latest': 2.524, 'diff': -0.029999999999999805, 'chg1_pct': -1.1746280344557491, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.1753436535598381, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '회사채_aa-', 'latest': 4.377, 'diff': 0.12899999999999956, 'chg1_pct': 3.0367231638418035, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.8548295663718231, 'pressure_component': 1}]}, 'basis': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시'}, 'high_debt_credit_spread_sensitivity': {'score': 0, 'debt_ratio_pct': 18.156716579736624, 'debt_ratio_percentile': {'available': True, 'observations': 60, 'current': 18.156716579736624, 'pctl_rank': 0.2, 'q20': 19.50589025876336, 'q50': 31.756309575260122, 'q80': 99.5871247418233, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'high_debt_by_same_field_p80': False, 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': '회사채_aa-', 'latest': 4.377, 'diff': 0.12899999999999956, 'chg1_pct': 3.0367231638418035, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.8548295663718231, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '회사채_bbb-', 'latest': 10.178, 'diff': 0.14800000000000146, 'chg1_pct': 1.4755732801595256, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.5541032464284461, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_aa-', 'latest': 0.6259999999999999, 'diff': -0.027000000000000135, 'chg1_pct': -4.134762633996958, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.22976159504878957, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_bbb-', 'latest': 6.427000000000001, 'diff': -0.007999999999997343, 'chg1_pct': -0.12432012432008754, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7880529533986601, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '회사채_aa-', 'latest': 4.377, 'diff': 0.12899999999999956, 'chg1_pct': 3.0367231638418035, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.8548295663718231, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '회사채_bbb-', 'latest': 10.178, 'diff': 0.14800000000000146, 'chg1_pct': 1.4755732801595256, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.5541032464284461, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '신용스프레드_aa-', 'latest': 0.6259999999999999, 'diff': -0.027000000000000135, 'chg1_pct': -4.134762633996958, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.22976159504878957, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '신용스프레드_bbb-', 'latest': 6.427000000000001, 'diff': -0.007999999999997343, 'chg1_pct': -0.12432012432008754, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7880529533986601, 'pressure_component': -1}]}, 'basis': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}}, 'note': '숫자 노출도가 없으면 임의 수치를 만들지 않고 company.yaml 명시 키워드와 로컬 산출물만 사용합니다.'}

### macro_numeric_criteria
- ecos_일별: {'국고채_10년': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.43, 'low': 1.792, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.21, 'zone': 'high'}, '국고채_3년': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.306, 'low': 1.36, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.751, 'zone': 'high'}, '콜금리': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.394, 'low': 0.86, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.524, 'zone': 'neutral'}, 'cd금리_91일': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.53, 'low': 1.17, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.81, 'zone': 'neutral'}, '국고채_10년_3년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 0.4889999999999999, 'low': 0.0979999999999998, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.4590000000000001, 'zone': 'neutral'}, '회사채_aa-': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 4.028, 'low': 2.157, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.377, 'zone': 'high'}, '회사채_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 10.169, 'low': 8.33, 'high_q': 0.8, 'low_q': 0.2, 'latest': 10.178, 'zone': 'high'}, '신용스프레드_aa-': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 0.8490000000000002, 'low': 0.4860000000000002, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.6259999999999999, 'zone': 'neutral'}, '신용스프레드_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 7.194, 'low': 6.442, 'high_q': 0.8, 'low_q': 0.2, 'latest': 6.427000000000001, 'zone': 'low'}, '원달러': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 1380.4, 'low': 1130.9, 'high_q': 0.8, 'low_q': 0.2, 'latest': 1503.4, 'zone': 'high'}}
- ext_일별: {'달러인덱스_dxy': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 104.04000091552734, 'low': 94.11000061035156, 'high_q': 0.8, 'low_q': 0.2, 'latest': 99.27100372314452, 'zone': 'neutral'}, '미국_국채_10년': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 4.21999979019165, 'low': 1.5700000524520874, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.651000022888184, 'zone': 'high'}, '미국_국채_13주': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 4.51800012588501, 'low': 0.1199999973177909, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.575000047683716, 'zone': 'neutral'}, '미국_국채_10년_13주_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 1.1390000134706495, 'low': -0.6220002174377441, 'high_q': 0.8, 'low_q': 0.2, 'latest': 1.0759999752044678, 'zone': 'neutral'}, '미국_국채_10년_2년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 0.6040000176429748, 'low': -0.3149999046325682, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.5049997901916505, 'zone': 'neutral'}, '유가_wti': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 80.33000183105469, 'low': 56.65999984741211, 'high_q': 0.8, 'low_q': 0.2, 'latest': 103.5999984741211, 'zone': 'high'}, '유가_brent': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 84.86000061035156, 'low': 62.290000915527344, 'high_q': 0.8, 'low_q': 0.2, 'latest': 110.8000030517578, 'zone': 'high'}, '유가_평균': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 82.75500106811523, 'low': 59.43999862670898, 'high_q': 0.8, 'low_q': 0.2, 'latest': 107.20000076293944, 'zone': 'high'}, '천연가스': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 3.98799991607666, 'low': 2.328000068664551, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.111999988555908, 'zone': 'neutral'}, '구리': {'method': 'empirical_percentile', 'lookback_observations': 3061, 'high': 4.518499851226807, 'low': 2.803999900817871, 'high_q': 0.8, 'low_q': 0.2, 'latest': 6.197000026702881, 'zone': 'high'}}

