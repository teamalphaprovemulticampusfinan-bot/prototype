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

- 생성 시각: 2026-05-24 20:41:57
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

- 미국 하이일드 스프레드 확대 → 글로벌 신용 리스크 증가
- 전체 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 한국 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 미국 시장 20일 수익률 양수 → 시장/섹터 방향성 우호
- 반도체 섹터 20일 수익률 양수 → 시장/섹터 방향성 우호
- 전체 시장 20/60일 모멘텀 양수 → 추세 우호
- 반도체 섹터 20/60일 모멘텀 양수 → 추세 우호
- 시장 risk-off 비율 25% 이하 → 벤치마크 약세 비중 낮음
- 한국 기준금리 인하 → 국내 유동성 완화
- CPI 전년비 116.3% — 고물가 구간 → 금리 인하 기대 약화
- BSI 전망 65.0 — 기업 경기 비관 우위
- 실업률 2.8% — 고용 양호
- GDP 전년비 0.6% — 저성장 구간 → 경기 부담
- oecd_cli_한국 99.90 상승 → 경기 개선 신호
- oecd_cli_미국 99.70 하락 → 경기 둔화 신호
- g20_cli 99.95 하락 → 경기 둔화 신호
- 뉴스 텍스트가 비어 있어 뉴스 점수 계산 생략
- 규제 텍스트가 비어 있어 규제 점수 계산 생략
- ecos_일별/미국_회사채_aaa: 1기간 변화율 급등 주의 구간 (변화율 1.88%, z=0.75)
- ecos_일별/국고채_10년_3년_스프레드: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.95)
- ecos_일별/kospi_지수: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.14)
- ecos_일별/코스피200: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.16)
- ext_일별/미국_회사채_aaa: 1기간 변화율 급등 주의 구간 (변화율 1.88%, z=0.75)
- ext_일별/국고채_10년_3년_스프레드: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.95)
- ext_일별/kospi_지수: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.14)
- ext_일별/코스피200: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.16)
- 소재/화학 기업 + 유가·가스·구리·희토류 상승 압력 → 원재료비 민감도 부담
- 딥테크/장기 성장 기업 + 금리 상승 압력 → 할인율·자금조달 민감도 부담

---

## 📊 항목별 핵심 수치 (Score Breakdown)

### ecos_일별
- 국고채_10년_level: 2.786
- 국고채_10년_diff: 0.0
- 국고채_10년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.385, 'low': 1.706, 'high_q': 0.8, 'low_q': 0.2}
- 국고채_3년_level: 2.347
- 국고채_3년_diff: 0.0
- 국고채_3년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.307, 'low': 1.281, 'high_q': 0.8, 'low_q': 0.2}
- 콜금리_level: 2.582
- 콜금리_diff: 0.0
- 콜금리_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.4512, 'low': 0.75, 'high_q': 0.8, 'low_q': 0.2}
- cd금리_91일_level: 2.59
- cd금리_91일_diff: 0.0
- cd금리_91일_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.58, 'low': 1.09, 'high_q': 0.8, 'low_q': 0.2}
- 국고채_10년_3년_스프레드: 0.439
- 국고채_10년_3년_스프레드_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.5059999999999999, 'low': 0.0889999999999999, 'high_q': 0.8, 'low_q': 0.2}
- 원달러_level: 1381.4
- 원달러_diff: 0.0
- 원달러_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 1338.7, 'low': 1127.6399999999999, 'high_q': 0.8, 'low_q': 0.2}
- 신용스프레드_bbb-_level: 6.322
- 신용스프레드_bbb-_diff: 0.0
- 신용스프레드_aa-_level: 0.57
- 신용스프레드_aa-_diff: 0.0
- 국고채_10년_zone: `neutral`
- 국고채_3년_zone: `neutral`
- 콜금리_zone: `neutral`
- cd금리_91일_zone: `neutral`
- 원달러_zone: `high`
- 신용스프레드_bbb-_zone: `low`
- 신용스프레드_aa-_zone: `neutral`

### ext_일별
- 미국_국채_10년_2년_스프레드: 0.526
- 미국_국채_10년_2년_스프레드_diff: 0.0
- 미국_국채_10년_2년_스프레드_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.5901999926567075, 'low': -0.3580001831054691, 'high_q': 0.8, 'low_q': 0.2}
- 미국_국채_10년_level: 4.416
- 미국_국채_10년_diff: 0.0
- 미국_국채_10년_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.097200107574463, 'low': 1.5194000244140624, 'high_q': 0.8, 'low_q': 0.2}
- 미국_국채_13주_level: 4.232
- 미국_국채_13주_diff: 0.0
- 미국_국채_13주_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.710000038146973, 'low': 0.0949999988079071, 'high_q': 0.8, 'low_q': 0.2}
- 달러인덱스_dxy_level: 99.33
- 달러인덱스_dxy_diff: 0.0
- 달러인덱스_dxy_criteria: {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 104.26000213623048, 'low': 93.5740005493164, 'high_q': 0.8, 'low_q': 0.2}
- 유가_평균_diff: 0.0
- 유가_wti_diff: 0.0
- 유가_brent_diff: 0.0
- 구리_diff: 0.0
- 미국_하이일드_스프레드_level: 3.32
- 미국_하이일드_스프레드_diff: 0.01
- 미국_국채_10년_zone: `high`
- 미국_국채_13주_zone: `neutral`
- 달러인덱스_dxy_zone: `neutral`

### ecos_월별
- 한국_기준금리_level: 2.5
- 한국_기준금리_diff: -0.25
- 한국_기준금리_criteria: {'method': 'empirical_percentile', 'lookback_observations': 89, 'high': 3.5, 'low': 0.75, 'high_q': 0.8, 'low_q': 0.2}
- cpi_전년비_level: 116.27
- bsi_전산업_전망_level: 65.0
- 실업률_level: 2.75
- 한국_기준금리_zone: `neutral`
- cpi_전년비_zone: `high`
- bsi_전산업_전망_zone: `low`

### ecos_분기별
- gdp성장률_전년비_level: 0.6
- gdp성장률_전기비_level: 0.7

### ext_월별
- 미국_기준금리_ffr_level: 4.33
- 미국_기준금리_ffr_diff: 0.0
- 미국_기준금리_ffr_criteria: {'method': 'empirical_percentile', 'lookback_observations': 89, 'high': 4.83, 'low': 0.09, 'high_q': 0.8, 'low_q': 0.2}
- 미국_실업률_level: 4.3
- oecd_cli_한국_level: 99.8951
- oecd_cli_한국_diff: 0.1053
- oecd_cli_미국_level: 99.7028
- oecd_cli_미국_diff: -0.019
- g20_cli_level: 99.9477
- g20_cli_diff: -0.0081
- 미국_기준금리_ffr_zone: `neutral`
- 미국_실업률_zone: `neutral`
- oecd_cli_한국_zone: `neutral`
- oecd_cli_미국_zone: `neutral`
- g20_cli_zone: `neutral`

### 뉴스

### 규제

---

## 🤖 LLM 보조 분석 (반도체 딥테크 섹터 관점)

### 요약
현재 매크로 환경은 중립 비우호적이며, 높은 리스크 레벨을 나타냅니다. 이는 고금리 환경 지속, 원달러 환율 상승 압력, 그리고 글로벌 경기 둔화 가능성 등 복합적인 요인에 기인합니다. 반도체 딥테크 기업들은 이러한 환경에서 투자 심리 위축 및 비용 부담 증가 등의 영향을 받을 수 있습니다.

### 매크로 해석
유동성 측면에서 국고채 금리, 콜금리, CD 금리 등이 과거 20% 분위수 상단에 위치하며 높은 수준을 유지하고 있습니다. 이는 시중 유동성이 풍부하지 않음을 시사하며, 반도체 섹터의 자금 조달 비용 증가 및 투자 매력도 감소로 이어질 수 있습니다. 신용 리스크는 미국 하이일드 스프레드가 소폭 상승했으나, 국내 신용 스프레드는 상대적으로 안정적인 모습을 보이고 있습니다. 환율/달러 측면에서 원달러 환율이 과거 20% 분위수 상단에 근접한 높은 수준을 기록하고 있습니다. 이는 수출 비중이 높은 반도체 기업의 단기 실적에는 긍정적일 수 있으나, 과도한 환율 상승은 수입 원자재 가격 상승 및 글로벌 수요 둔화 우려를 야기할 수 있습니다. 인플레이션은 CPI 전년비 레벨이 제시되지 않았으나, 전반적인 금리 수준은 인플레이션 압력이 여전히 존재함을 시사합니다. 이는 제조 원가 상승 요인으로 작용할 수 있습니다. 투자심리/뉴스 측면에서 BSI 전망치가 낮게 나타나고 있으며, OECD CLI 등 경기 선행 지표들이 둔화 시그널을 보이고 있습니다. 이는 반도체 수요 둔화 우려를 증폭시키며 투자 심리를 위축시킬 수 있습니다. 규제 리스크는 별도 데이터가 제시되지 않았으나, 미중 반도체 수출 규제 등 지정학적 리스크는 여전히 잠재적인 부담 요인으로 작용할 수 있습니다.

### 🔬 반도체 섹터 종합 영향
현재의 중립 비우호적인 매크로 환경은 반도체 딥테크 기업들에게 부담으로 작용할 가능성이 높습니다. 고금리 환경은 성장주 밸류에이션을 할인시키는 요인으로 작용하며, 높은 원달러 환율은 단기적으로는 긍정적일 수 있으나 장기적으로는 글로벌 수요 둔화 우려를 키울 수 있습니다. 또한, 경기 선행 지표들의 둔화는 반도체 수요에 대한 불확실성을 높이는 요인입니다.

### 주요 리스크
- 높은 원달러 환율 수준 (과도한 강세 시 수요 둔화 우려)
- 경기 선행 지표 둔화에 따른 투자 심리 위축
- 고금리 환경 지속으로 인한 성장주 밸류에이션 할인 압력

### 📌 확인 포인트 (Watch Points)

| 지표 | 현재 상태 | 주의 기준 | 반도체 관련성 |
|---|---|---|---|
| 원달러 환율 | 1381.4 수준으로 과거 20% 분위수 상단에 근접 | 지속적인 상승 또는 1338.7 상회 시 수요 둔화 우려 증폭 | 수출 기업의 실적 및 경쟁력에 직접적인 영향 |
| OECD CLI (한국) | 99.8951로 둔화 시그널 | 100 하회 지속 및 추가 하락 시 반도체 수요 둔화 가능성 확대 | 글로벌 경기 및 반도체 수요 예측의 중요한 지표 |
| 국고채 10년 금리 | 2.786 수준으로 과거 20% 분위수 상단에 위치 | 추가 상승 시 고금리 장기화 우려 증폭 및 투자 심리 위축 | 자금 조달 비용 및 투자 매력도에 영향 |

### 🔗 근거 연결 (Evidence Links)

- **[macro_ev_1]** 원달러 환율이 과거 20% 분위수 상단에 근접한 높은 수준을 기록하고 있습니다. _(출처: ecos_일별)_
- **[macro_ev_2]** 국고채 10년 금리가 과거 20% 분위수 상단에 위치하며 높은 수준을 유지하고 있습니다. _(출처: ecos_일별)_
- **[macro_ev_3]** OECD CLI 한국 지표가 둔화 시그널을 보이고 있습니다. _(출처: ext_월별)_
- **[macro_ev_4]** 미국 기준금리(FFR)가 과거 20% 분위수 상단에 위치하며 높은 수준을 유지하고 있습니다. _(출처: ext_월별)_
- **[macro_ev_5]** 한국 기준금리가 최근 하락했으나 여전히 과거 20% 분위수 상단에 위치합니다. _(출처: ecos_월별)_

---

## 📂 상세 데이터

### 시장벤치마크
- market_benchmark_available: True
- kospi_지수: 2697.6699
- kosdaq_지수: 734.35
- krx_반도체_프록시_kodex반도체: 30906.6758
- 코스피200: 359.62
- 나스닥: 19113.77
- sox_반도체_지수: 4758.0601
- s&p500: 5911.69
- 시장수익률_20일: 4.3482
- 시장수익률_60일: 3.4108
- 시장변동성_20일: 16.4531
- 시장변동성_z_252일: -0.4657
- 시장모멘텀_20_60: 0.9374
- 시장_risk_off_비율: 0.0714
- 한국시장수익률_20일: 4.4217
- 미국시장수익률_20일: 5.1381
- 반도체섹터수익률_20일: 6.1843
- 반도체섹터변동성_20일: 32.1594
- 반도체섹터모멘텀_20_60: 5.0336
- available_market_benchmark_columns: ['kospi_지수', 'kosdaq_지수', 'krx_반도체_프록시_kodex반도체', '코스피200', '나스닥', 'sox_반도체_지수', 's&p500', '시장수익률_20일', '시장수익률_60일', '시장변동성_20일', '시장변동성_z_252일', '시장모멘텀_20_60', '시장_risk_off_비율', '한국시장수익률_20일', '미국시장수익률_20일', '반도체섹터수익률_20일', '반도체섹터변동성_20일', '반도체섹터모멘텀_20_60']
- semiconductor_benchmark_note: KRX 반도체 지수 원천값이 없어서 KODEX 반도체 ETF 프록시만 사용 가능

### 변화율_rolling_기준
- score_raw: -4
- score_capped: -4
- details: {'ecos_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 5, 'triggered_items': [{'indicator': '미국_회사채_aaa', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 1.875, 'latest_zscore': 0.7478, 'score_impact': -1}, {'indicator': '국고채_10년_3년_스프레드', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.9487, 'score_impact': -1}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1416, 'score_impact': 1}, {'indicator': '코스피200', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1639, 'score_impact': 0}, {'indicator': 'oecd_cli_한국', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.0395, 'score_impact': 0}]}, 'ext_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 5, 'triggered_items': [{'indicator': '미국_회사채_aaa', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 1.875, 'latest_zscore': 0.7478, 'score_impact': -1}, {'indicator': '국고채_10년_3년_스프레드', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.9487, 'score_impact': -1}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1416, 'score_impact': 1}, {'indicator': '코스피200', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1639, 'score_impact': 0}, {'indicator': 'oecd_cli_한국', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.0395, 'score_impact': 0}]}, 'ecos_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 21, 'triggered_items': [{'indicator': '미국_국채_10년_13주_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -1515.3835, 'latest_zscore': -0.0157, 'score_impact': 2}, {'indicator': 'kospi_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -54.3752, 'latest_zscore': -0.2686, 'score_impact': -2}, {'indicator': '나스닥_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -68.3561, 'latest_zscore': -0.1741, 'score_impact': -2}, {'indicator': 'sox_반도체_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -66.1203, 'latest_zscore': -0.0355, 'score_impact': -2}, {'indicator': 's&p500_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -70.032, 'latest_zscore': -0.078, 'score_impact': -2}, {'indicator': '미국_하이일드_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.736, 'latest_zscore': -1.2595, 'score_impact': 2}, {'indicator': '미국_ig_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.5963, 'latest_zscore': -1.5636, 'score_impact': 2}, {'indicator': '원달러', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -3.9694, 'latest_zscore': 1.0053, 'score_impact': 1}, {'indicator': '한국은행_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}, {'indicator': 'kosdaq_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -58.9637, 'latest_zscore': -0.9284, 'score_impact': -1}, {'indicator': '나스닥_수익률_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -818.9173, 'latest_zscore': 0.9171, 'score_impact': -1}, {'indicator': '한국_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}]}, 'ext_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 21, 'triggered_items': [{'indicator': '미국_국채_10년_13주_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -1515.3835, 'latest_zscore': -0.0157, 'score_impact': 2}, {'indicator': 'kospi_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -54.3752, 'latest_zscore': -0.2686, 'score_impact': -2}, {'indicator': '나스닥_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -68.3561, 'latest_zscore': -0.1741, 'score_impact': -2}, {'indicator': 'sox_반도체_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -66.1203, 'latest_zscore': -0.0355, 'score_impact': -2}, {'indicator': 's&p500_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -70.032, 'latest_zscore': -0.078, 'score_impact': -2}, {'indicator': '미국_하이일드_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.736, 'latest_zscore': -1.2595, 'score_impact': 2}, {'indicator': '미국_ig_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.5963, 'latest_zscore': -1.5636, 'score_impact': 2}, {'indicator': '원달러', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -3.9694, 'latest_zscore': 1.0053, 'score_impact': 1}, {'indicator': '한국은행_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}, {'indicator': 'kosdaq_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -58.9637, 'latest_zscore': -0.9284, 'score_impact': -1}, {'indicator': '나스닥_수익률_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -818.9173, 'latest_zscore': 0.9171, 'score_impact': -1}, {'indicator': '한국_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}]}}

### 기업별_macro_민감도
- score: -3
- reasons: ['소재/화학 기업 + 유가·가스·구리·희토류 상승 압력 → 원재료비 민감도 부담', '딥테크/장기 성장 기업 + 금리 상승 압력 → 할인율·자금조달 민감도 부담']
- details: {'company': '한솔케미칼', 'company_dir': 'hansol', 'field': '반도체', 'method': 'company_exposure_from_local_disclosures_and_yaml + macro_shock_from_official_timeseries_rolling_criteria', 'score_raw': -3, 'score_capped': -3, 'basis': {'macro_level': '한국은행 ECOS/FRED 등 공식 시계열의 과거분포 20/80 분위 기준', 'macro_rolling': 'rolling z-score ±2σ watch, ±3σ extreme 및 과거분포 5/95·1/99 분위 급등/급락 cutoff', 'export_fx': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용', 'raw_material': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용', 'equipment_regulation': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭', 'memory_hbm_demand': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용', 'rate_sensitivity': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시', 'credit_spread': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}, 'context': {'slug': 'hansol', 'company_name': '한솔케미칼', 'field': '반도체', 'config_path': 'C:\\Agent_6.9\\data\\반도체\\한솔케미칼\\_company_common\\company.yaml', 'finance_csv_path': 'C:\\Agent_6.9\\data\\반도체\\한솔케미칼\\finance\\한솔케미칼_재무.csv', 'external_sensitivity_path': 'C:\\Agent_6.9\\data\\반도체\\_sector_common\\macro_company_sensitivity\\company_sensitivity_external.csv', 'role_flags': {'material_company': True, 'equipment_company': False, 'backend_packaging_company': False, 'hbm_memory_linked': False, 'deeptech_company': True, 'export_keyword_hint': False}, 'role_evidence': {'material_company': ['소재', '화학', '케미칼', '전구체', 'precursor', '고순도', 'chemical'], 'equipment_company': [], 'backend_packaging_company': [], 'hbm_memory_linked': [], 'deeptech_company': ['소재'], 'export_keyword_hint': []}, 'metrics': {'sales': 883968714104.0, 'operating_income': 156233146521.0, 'net_income': 148134823618.0, 'fcf': 116537517564.0, 'debt_ratio_pct': 35.93763458086576, 'current_ratio_pct': 163.00083223202031, 'loss_making': False, 'fcf_negative': False}, 'metric_percentiles': {'debt_ratio_pct': {'available': True, 'observations': 48, 'current': 35.93763458086576, 'pctl_rank': 0.5625, 'q20': 19.84318367852004, 'q50': 31.756309575260122, 'q80': 83.97626273385403, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'fcf': {'available': True, 'observations': 48, 'current': 116537517564.0, 'pctl_rank': 0.8958, 'q20': -5926914990.0, 'q50': 24854117993.5, 'q80': 99231903416.0, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}}}, 'axes': {'export_fx_sensitivity': {'score': 0, 'exposure_level': 'unknown', 'exposure_metric': None, 'role_keyword_hint': False, 'macro_pressure': {'available': True, 'pressure': -3, 'events': [{'dataset': 'ecos_월별', 'indicator': '원달러', 'latest': 1381.4, 'diff': -57.09999999999991, 'chg1_pct': -3.969412582551257, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -1, 'zscore': 1.0052660837813618, 'pressure_component': -2}, {'dataset': 'ext_월별', 'indicator': '원달러', 'latest': 1381.4, 'diff': -57.09999999999991, 'chg1_pct': -3.969412582551257, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -1, 'zscore': 1.0052660837813618, 'pressure_component': -2}, {'dataset': 'ecos_분기별', 'indicator': '원달러', 'latest': 1438.5, 'diff': 5.2000000000000455, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': 1}, {'dataset': 'ecos_분기별', 'indicator': '달러인덱스_dxy', 'latest': 99.47000122070312, 'diff': -8.90000152587892, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.33000183105467, 'diff': -0.1399993896484517, 'chg1_pct': -0.14074533822294732, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.19094849248010687, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.33000183105467, 'diff': -0.1399993896484517, 'chg1_pct': -0.14074533822294732, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.19094849248010687, 'pressure_component': -1}, {'dataset': 'ecos_일별', 'indicator': '원달러', 'latest': 1381.4, 'diff': 0.0, 'chg1_pct': 0.0, 'chg20_pct': -1.0458452722063027, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9125230212320103, 'pressure_component': 0}, {'dataset': 'ext_일별', 'indicator': '원달러', 'latest': 1381.4, 'diff': 0.0, 'chg1_pct': 0.0, 'chg20_pct': -1.0458452722063027, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9125230212320103, 'pressure_component': 0}]}, 'basis': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용'}, 'raw_material_sensitivity': {'score': -1, 'material_role': True, 'role_evidence': ['소재', '화학', '케미칼', '전구체', 'precursor', '고순도', 'chemical'], 'raw_material_ratio_pct': None, 'raw_material_ratio_level': 'unknown', 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_분기별', 'indicator': '유가_wti', 'latest': 58.209999084472656, 'diff': -14.319999694824219, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '유가_brent', 'latest': 63.119998931884766, 'diff': -13.640003204345703, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '유가_평균', 'latest': 60.66499900817871, 'diff': -13.980001449584961, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 4.909999847412109, 'diff': 0.6799964904785156, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '유가_wti', 'latest': 60.790000915527344, 'diff': 2.5800018310546875, 'chg1_pct': 4.432231354806704, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7193229099197688, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '유가_brent', 'latest': 63.900001525878906, 'diff': 0.7800025939941406, 'chg1_pct': 1.235745575401337, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7356486082598602, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '유가_평균', 'latest': 62.345001220703125, 'diff': 1.680002212524414, 'chg1_pct': 2.769310541483594, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7285001583336856, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 3.1100006103515625, 'diff': -1.7999992370605469, 'chg1_pct': -36.65986340120283, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.6354461046678568, 'pressure_component': -1}]}, 'basis': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용'}, 'equipment_regulation_sensitivity': {'score': 0, 'equipment_role': False, 'role_evidence': [], 'macro_pressure': {'available': False, 'pressure': 0, 'keyword_count': 0, 'method': 'no_regulation_frame'}, 'basis': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭'}, 'backend_hbm_memory_demand_sensitivity': {'score': 0, 'backend_role': False, 'hbm_memory_linked': False, 'role_evidence': [], 'macro_pressure': {'available': True, 'pressure': -3, 'events': [{'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수_변동성_20일', 'latest': 33.71160835282642, 'diff': -65.79215558049638, 'chg1_pct': -66.12026819868193, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': -0.03548281323105865, 'pressure_component': -2}, {'dataset': 'ecos_월별', 'indicator': '반도체섹터변동성_20일', 'latest': 32.15944467544357, 'diff': -41.753854787340245, 'chg1_pct': -56.49031377413179, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': 0.09299932070436237, 'pressure_component': -2}, {'dataset': 'ext_월별', 'indicator': 'sox_반도체_지수_변동성_20일', 'latest': 33.71160835282642, 'diff': -65.79215558049638, 'chg1_pct': -66.12026819868193, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': -0.03548281323105865, 'pressure_component': -2}, {'dataset': 'ext_월별', 'indicator': '반도체섹터변동성_20일', 'latest': 32.15944467544357, 'diff': -41.753854787340245, 'chg1_pct': -56.49031377413179, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': 0.09299932070436237, 'pressure_component': -2}, {'dataset': 'ecos_분기별', 'indicator': 'krx_반도체_프록시_kodex반도체', 'latest': 29238.205078125, 'diff': -2776.107421875, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': 'sox_반도체_지수', 'latest': 4230.08984375, 'diff': -785.76025390625, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': 'krx_반도체_프록시_kodex반도체_수익률_1일', 'latest': -1.3982515236381057, 'diff': -1.7775401965823614, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': 'krx_반도체_프록시_kodex반도체_수익률_5일', 'latest': -3.1580644992259432, 'diff': 2.3934543847335292, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': 1}]}, 'basis': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용'}, 'deeptech_loss_rate_sensitivity': {'score': -2, 'deeptech_role': True, 'loss_making': False, 'fcf_negative': False, 'operating_margin_pct': None, 'net_margin_pct': None, 'fcf': 116537517564.0, 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_분기별', 'indicator': '국고채_10년', 'latest': 2.563, 'diff': -0.2959999999999998, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '국고채_3년', 'latest': 2.267, 'diff': -0.30600000000000005, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '콜금리', 'latest': 2.783, 'diff': -0.2909999999999999, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': 'cd금리_91일', 'latest': 2.71, 'diff': -0.31999999999999984, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '회사채_aa-', 'latest': 2.868, 'diff': -0.3360000000000003, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '회사채_bbb-', 'latest': 8.62, 'diff': -0.34299999999999997, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '국고채_10년_3년_스프레드', 'latest': 0.2960000000000002, 'diff': 0.010000000000000231, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '국고채_10년', 'latest': 2.786, 'diff': 0.22299999999999986, 'chg1_pct': 8.700741318767058, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.08657092241921194, 'pressure_component': 1}]}, 'basis': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시'}, 'high_debt_credit_spread_sensitivity': {'score': 0, 'debt_ratio_pct': 35.93763458086576, 'debt_ratio_percentile': {'available': True, 'observations': 48, 'current': 35.93763458086576, 'pctl_rank': 0.5625, 'q20': 19.84318367852004, 'q50': 31.756309575260122, 'q80': 83.97626273385403, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'high_debt_by_same_field_p80': False, 'macro_pressure': {'available': True, 'pressure': -3, 'events': [{'dataset': 'ecos_분기별', 'indicator': '회사채_aa-', 'latest': 2.868, 'diff': -0.3360000000000003, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '회사채_bbb-', 'latest': 8.62, 'diff': -0.34299999999999997, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '신용스프레드_aa-', 'latest': 0.601, 'diff': -0.03000000000000025, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '신용스프레드_bbb-', 'latest': 6.353, 'diff': -0.036999999999999034, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '회사채_aa-', 'latest': 2.917, 'diff': 0.04899999999999993, 'chg1_pct': 1.7085076708507563, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.43556867373266195, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '회사채_bbb-', 'latest': 8.669, 'diff': 0.049000000000001265, 'chg1_pct': 0.5684454756380575, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.813874096802265, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_aa-', 'latest': 0.5699999999999998, 'diff': -0.03100000000000014, 'chg1_pct': -5.158069883527483, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7908406566877426, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_bbb-', 'latest': 6.322000000000001, 'diff': -0.030999999999998806, 'chg1_pct': -0.48795844482919515, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.4400893826897296, 'pressure_component': -1}]}, 'basis': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}}, 'note': '숫자 노출도가 없으면 임의 수치를 만들지 않고 company.yaml 명시 키워드와 로컬 산출물만 사용합니다.'}

### macro_numeric_criteria
- ecos_일별: {'국고채_10년': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.385, 'low': 1.706, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.786, 'zone': 'neutral'}, '국고채_3년': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.307, 'low': 1.281, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.347, 'zone': 'neutral'}, '콜금리': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.4512, 'low': 0.75, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.582, 'zone': 'neutral'}, 'cd금리_91일': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.58, 'low': 1.09, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.59, 'zone': 'neutral'}, '국고채_10년_3년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.5059999999999999, 'low': 0.0889999999999999, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.439, 'zone': 'neutral'}, '회사채_aa-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.037, 'low': 2.092, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.917, 'zone': 'neutral'}, '회사채_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 10.3698, 'low': 8.285, 'high_q': 0.8, 'low_q': 0.2, 'latest': 8.669, 'zone': 'neutral'}, '신용스프레드_aa-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.9536, 'low': 0.5010000000000001, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.5699999999999998, 'zone': 'neutral'}, '신용스프레드_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 7.1986, 'low': 6.515000000000001, 'high_q': 0.8, 'low_q': 0.2, 'latest': 6.322000000000001, 'zone': 'low'}, '원달러': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 1338.7, 'low': 1127.6399999999999, 'high_q': 0.8, 'low_q': 0.2, 'latest': 1381.4, 'zone': 'high'}}
- ext_일별: {'달러인덱스_dxy': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 104.26000213623048, 'low': 93.5740005493164, 'high_q': 0.8, 'low_q': 0.2, 'latest': 99.33000183105467, 'zone': 'neutral'}, '미국_국채_10년': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.097200107574463, 'low': 1.5194000244140624, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.415999889373779, 'zone': 'high'}, '미국_국채_13주': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.710000038146973, 'low': 0.0949999988079071, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.23199987411499, 'zone': 'neutral'}, '미국_국채_10년_13주_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 1.2203999914228916, 'low': -0.7462002754211426, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.184000015258789, 'zone': 'neutral'}, '미국_국채_10년_2년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.5901999926567075, 'low': -0.3580001831054691, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.5259998893737792, 'zone': 'neutral'}, '유가_wti': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 80.22800140380859, 'low': 55.40199890136718, 'high_q': 0.8, 'low_q': 0.2, 'latest': 60.790000915527344, 'zone': 'neutral'}, '유가_brent': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 84.80000305175781, 'low': 61.869998931884766, 'high_q': 0.8, 'low_q': 0.2, 'latest': 63.900001525878906, 'zone': 'neutral'}, '유가_평균': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 82.6779998779297, 'low': 58.567000198364255, 'high_q': 0.8, 'low_q': 0.2, 'latest': 62.345001220703125, 'zone': 'neutral'}, '천연가스': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.992000007629394, 'low': 2.2754000663757328, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.447000026702881, 'zone': 'neutral'}, '구리': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.320400047302246, 'low': 2.7739999294281006, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.652500152587891, 'zone': 'high'}}

