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

- 생성 시각: 2026-05-25 12:50:20
- 신호: **SELL**
- 점수: -3
- 위험도: MEDIUM_HIGH
- 신뢰도: 0.5
- 커버리지: 100% (penalty: 0.0)

---

## 📌 한 줄 요약

매크로 환경 점수는 -3점으로, 위험자산에 비우호적인 환경입니다. 위험도는 MEDIUM_HIGH입니다.

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
- 뉴스 긍정/부정 신호 중립
- 규제 리스크 신호 약함
- ecos_일별/미국_회사채_aaa: 1기간 변화율 급등 주의 구간 (변화율 1.88%, z=0.75)
- ecos_일별/국고채_10년_3년_스프레드: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.95)
- ecos_일별/kospi_지수: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.14)
- ecos_일별/코스피200: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.16)
- ext_일별/미국_회사채_aaa: 1기간 변화율 급등 주의 구간 (변화율 1.88%, z=0.75)
- ext_일별/국고채_10년_3년_스프레드: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.95)
- ext_일별/kospi_지수: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.14)
- ext_일별/코스피200: rolling z-score 상단 2σ 이상 (변화율 0.00%, z=2.16)
- 적자·FCF 음수 기업 + 금리 상승 압력 → 할인율·자금조달 민감도 부담

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
- positive_keyword_count: 0
- negative_keyword_count: 0

### 규제
- regulation_risk_keyword_count: 0

---

## 🤖 LLM 보조 분석 (반도체 딥테크 섹터 관점)

### 요약
현재 매크로 환경은 중립적인 수준으로, 금리 및 환율 변동성이 크지 않으나 고금리 장기화 가능성과 지정학적 리스크는 여전히 잠재적 부담 요인으로 작용합니다. 반도체 섹터는 AI 관련 수요 증가 기대감과 함께 원달러 환율 변동성에 주목할 필요가 있습니다.

### 매크로 해석
유동성 측면에서 국고채 금리(10년물 2.786%, 3년물 2.347%) 및 콜금리(2.582%), CD금리(91일 2.59%)가 과거 분포 대비 중간 수준을 유지하며 유동성 환경이 급격히 악화되지는 않았습니다. 이는 반도체 섹터의 자금 조달 및 투자 활동에 직접적인 부정적 영향은 제한적임을 시사합니다. 신용 리스크는 국고채 10년-3년 스프레드(0.439%)가 과거 분포 대비 중간 수준이며, 신용 스프레드(BBB- 6.322%, AA- 0.57%) 역시 안정적인 흐름을 보여 신용 경색 우려는 낮은 상태입니다. 이는 반도체 기업들의 신용 위험이 현재로서는 관리 가능한 수준임을 나타냅니다. 환율/달러 측면에서 원달러 환율(1381.4)은 과거 분포 상단에 위치하며 다소 높은 수준을 유지하고 있습니다. 이는 반도체 수출 비중이 높은 기업들에게 단기적으로 실적에 긍정적일 수 있으나, 과도한 환율 상승은 글로벌 수요 둔화 우려를 야기할 수 있습니다. 인플레이션은 CPI 전년비 레벨(116.27)이 제시되지 않았으나, 전반적인 금리 수준이 과거 대비 높은 점을 감안할 때 인플레이션 압력은 완화되는 추세로 해석될 수 있습니다. 이는 반도체 제조 원가에 간접적인 영향을 미칠 수 있습니다. 투자심리/뉴스 측면에서 긍정적/부정적 키워드 수가 모두 0으로 나타나 특별한 투자 심리 변화나 시장 뉴스가 감지되지 않았습니다. 이는 반도체 섹터에 대한 투자 심리가 현재 중립적인 상태임을 의미합니다. 규제 리스크 측면에서 규제 관련 키워드 수가 0으로 나타나 현재 시점에서 직접적인 규제 리스크는 부각되지 않고 있습니다. 이는 미중 반도체 수출 규제와 같은 외부 규제 요인이 현재 시장에 직접적인 영향을 미치고 있지 않음을 시사합니다.

### 🔬 반도체 섹터 종합 영향
현재 매크로 환경은 반도체 딥테크 기업들에게 중립적인 영향을 미치고 있습니다. 높은 원달러 환율은 수출 기업의 단기 실적에 긍정적일 수 있으나, 글로벌 수요 둔화 가능성을 내포하고 있어 주의가 필요합니다. 고금리 환경은 성장주 밸류에이션에 부담으로 작용할 수 있습니다.

### 주요 리스크
- 원달러 환율 레벨(1381.4)이 과거 분포 상단에 위치하여 과도한 환율 상승 시 글로벌 수요 둔화 우려 증폭 가능성
- 국고채 10년물 금리(2.786%) 및 미국 국채 10년물 금리(4.416%)가 과거 분포 상단에 위치하여 고금리 장기화 시 성장주 밸류에이션 할인 요인으로 작용 가능성
- 미국 국채 10년-2년 스프레드(0.526%)가 과거 분포 상단에 위치하여 경기 침체 가능성에 대한 잠재적 우려

### 📌 확인 포인트 (Watch Points)

| 지표 | 현재 상태 | 주의 기준 | 반도체 관련성 |
|---|---|---|---|
| 원달러 환율 | 1381.4로 과거 분포 상단에 위치 | 지속적인 상승 또는 1400선 돌파 시 수요 둔화 우려 증폭 | 수출 비중 높은 반도체 기업의 실적 및 경쟁력에 직접적 영향 |
| 미국 국채 10년물 금리 | 4.416%로 과거 분포 상단에 위치 | 4.5% 이상 지속 시 성장주 밸류에이션 부담 가중 | 고금리 환경은 반도체 딥테크 기업의 투자 및 자금 조달 비용 증가 요인 |
| AI Capex 사이클 (HBM/첨단패키징 수요) | 글로벌 AI Capex 사이클에 따른 HBM/첨단패키징 수요 증가 기대감 | 수요 증가세 둔화 또는 예상치 하회 시 섹터 성장성 둔화 우려 | 반도체 딥테크 기업의 핵심 성장 동력으로 직접적인 영향 |

### 🔗 근거 연결 (Evidence Links)

- **[macro_ev_1]** 원달러 환율이 과거 분포 상단에 위치하여 높은 수준을 유지하고 있습니다. _(출처: ecos_일별)_
- **[macro_ev_2]** 국고채 10년물 금리가 과거 분포 중간 수준을 유지하고 있습니다. _(출처: ecos_일별)_
- **[macro_ev_3]** 미국 국채 10년물 금리가 과거 분포 상단에 위치하여 높은 수준을 유지하고 있습니다. _(출처: ext_일별)_
- **[macro_ev_4]** 미국 국채 10년물-2년물 스프레드가 과거 분포 상단에 위치하고 있습니다. _(출처: ext_일별)_
- **[macro_ev_5]** 뉴스 섹터에서 긍정적/부정적 키워드 수가 모두 0으로 나타나 투자 심리 변화가 감지되지 않았습니다. _(출처: 뉴스)_

---

## 📂 상세 데이터

### 시장벤치마크
- market_benchmark_available: True
- kospi_지수: 2697.67
- kosdaq_지수: 734.35
- krx_반도체_지수: 3218.54
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
- 반도체섹터수익률_20일: 6.2191
- 반도체섹터변동성_20일: 32.5753
- 반도체섹터모멘텀_20_60: 5.2687
- available_market_benchmark_columns: ['kospi_지수', 'kosdaq_지수', 'krx_반도체_지수', '코스피200', '나스닥', 'sox_반도체_지수', 's&p500', '시장수익률_20일', '시장수익률_60일', '시장변동성_20일', '시장변동성_z_252일', '시장모멘텀_20_60', '시장_risk_off_비율', '한국시장수익률_20일', '미국시장수익률_20일', '반도체섹터수익률_20일', '반도체섹터변동성_20일', '반도체섹터모멘텀_20_60']

### 변화율_rolling_기준
- score_raw: -4
- score_capped: -4
- details: {'ecos_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 5, 'triggered_items': [{'indicator': '미국_회사채_aaa', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 1.875, 'latest_zscore': 0.7478, 'score_impact': -1}, {'indicator': '국고채_10년_3년_스프레드', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.9487, 'score_impact': -1}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1416, 'score_impact': 1}, {'indicator': '코스피200', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1639, 'score_impact': 0}, {'indicator': 'oecd_cli_한국', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.0395, 'score_impact': 0}]}, 'ext_일별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 5, 'triggered_items': [{'indicator': '미국_회사채_aaa', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': 1, 'latest_1_period_change_pct': 1.875, 'latest_zscore': 0.7478, 'score_impact': -1}, {'indicator': '국고채_10년_3년_스프레드', 'direction_rule': 'risk_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.9487, 'score_impact': -1}, {'indicator': 'kospi_지수', 'direction_rule': 'market_up', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1416, 'score_impact': 1}, {'indicator': '코스피200', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.1639, 'score_impact': 0}, {'indicator': 'oecd_cli_한국', 'direction_rule': 'neutral', 'z_alert': 1, 'shock_flag': 0, 'latest_1_period_change_pct': 0.0, 'latest_zscore': 2.0395, 'score_impact': 0}]}, 'ecos_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 21, 'triggered_items': [{'indicator': '미국_국채_10년_13주_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -1515.3835, 'latest_zscore': -0.0157, 'score_impact': 2}, {'indicator': 'kospi_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -54.3752, 'latest_zscore': -0.2655, 'score_impact': -2}, {'indicator': '나스닥_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -68.3561, 'latest_zscore': -0.1741, 'score_impact': -2}, {'indicator': 'sox_반도체_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -66.1203, 'latest_zscore': -0.0355, 'score_impact': -2}, {'indicator': 's&p500_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -70.032, 'latest_zscore': -0.078, 'score_impact': -2}, {'indicator': '미국_하이일드_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.736, 'latest_zscore': -1.2595, 'score_impact': 2}, {'indicator': '미국_ig_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.5963, 'latest_zscore': -1.5636, 'score_impact': 2}, {'indicator': '원달러', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -3.9694, 'latest_zscore': 1.0053, 'score_impact': 1}, {'indicator': '한국은행_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}, {'indicator': 'kosdaq_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -58.9637, 'latest_zscore': -0.9308, 'score_impact': -1}, {'indicator': '나스닥_수익률_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -818.9173, 'latest_zscore': 0.9171, 'score_impact': -1}, {'indicator': '한국_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}]}, 'ext_월별': {'rolling_available': True, 'method': 'backward_looking_pct_change + rolling_zscore + empirical_quantile_cutoff', 'basis': {'daily_horizons': ['1영업일', '5영업일', '20영업일', '60영업일'], 'monthly_horizons': ['1개월', '3개월', '6개월', '12개월'], 'zscore_watch': '|z| >= 2.0', 'zscore_extreme': '|z| >= 3.0', 'shock_watch_quantile': '5% / 95%', 'shock_extreme_quantile': '1% / 99%', 'no_lookahead': '현재값은 rolling 평균/표준편차/cutoff 산정에서 제외'}, 'dataset_score_raw': -1, 'dataset_score_capped': -1, 'triggered_count': 21, 'triggered_items': [{'indicator': '미국_국채_10년_13주_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -1515.3835, 'latest_zscore': -0.0157, 'score_impact': 2}, {'indicator': 'kospi_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -54.3752, 'latest_zscore': -0.2655, 'score_impact': -2}, {'indicator': '나스닥_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -68.3561, 'latest_zscore': -0.1741, 'score_impact': -2}, {'indicator': 'sox_반도체_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -66.1203, 'latest_zscore': -0.0355, 'score_impact': -2}, {'indicator': 's&p500_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -70.032, 'latest_zscore': -0.078, 'score_impact': -2}, {'indicator': '미국_하이일드_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.736, 'latest_zscore': -1.2595, 'score_impact': 2}, {'indicator': '미국_ig_스프레드', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -2, 'latest_1_period_change_pct': -15.5963, 'latest_zscore': -1.5636, 'score_impact': 2}, {'indicator': '원달러', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -3.9694, 'latest_zscore': 1.0053, 'score_impact': 1}, {'indicator': '한국은행_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}, {'indicator': 'kosdaq_지수_변동성_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -58.9637, 'latest_zscore': -0.9308, 'score_impact': -1}, {'indicator': '나스닥_수익률_20일', 'direction_rule': 'market_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -818.9173, 'latest_zscore': 0.9171, 'score_impact': -1}, {'indicator': '한국_기준금리', 'direction_rule': 'risk_up', 'z_alert': 0, 'shock_flag': -1, 'latest_1_period_change_pct': -9.0909, 'latest_zscore': 0.2438, 'score_impact': 1}]}}

### 기업별_macro_민감도
- score: -2
- reasons: ['적자·FCF 음수 기업 + 금리 상승 압력 → 할인율·자금조달 민감도 부담']
- details: {'company': 'SFA반도체', 'company_dir': 'sfa_semicon', 'field': '반도체', 'method': 'company_exposure_from_local_disclosures_and_yaml + macro_shock_from_official_timeseries_rolling_criteria', 'score_raw': -2, 'score_capped': -2, 'basis': {'macro_level': '한국은행 ECOS/FRED 등 공식 시계열의 과거분포 20/80 분위 기준', 'macro_rolling': 'rolling z-score ±2σ watch, ±3σ extreme 및 과거분포 5/95·1/99 분위 급등/급락 cutoff', 'export_fx': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용', 'raw_material': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용', 'equipment_regulation': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭', 'memory_hbm_demand': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용', 'rate_sensitivity': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시', 'credit_spread': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}, 'context': {'slug': 'sfa_semicon', 'company_name': 'SFA반도체', 'field': '반도체', 'config_path': 'C:\\Agent_6.9\\data\\반도체\\SFA반도체\\_company_common\\company.yaml', 'finance_csv_path': 'C:\\Agent_6.9\\data\\반도체\\SFA반도체\\finance\\SFA반도체_재무.csv', 'external_sensitivity_path': 'C:\\Agent_6.9\\data\\반도체\\_sector_common\\macro_company_sensitivity\\company_sensitivity_external.csv', 'role_flags': {'material_company': False, 'equipment_company': False, 'backend_packaging_company': False, 'hbm_memory_linked': False, 'deeptech_company': False, 'export_keyword_hint': False}, 'role_evidence': {'material_company': [], 'equipment_company': [], 'backend_packaging_company': [], 'hbm_memory_linked': [], 'deeptech_company': [], 'export_keyword_hint': []}, 'metrics': {'sales': 367389147993.0, 'operating_income': -19626671175.0, 'net_income': -19130997781.0, 'fcf': -16603600772.0, 'debt_ratio_pct': 16.20621915618083, 'current_ratio_pct': 368.72033886552026, 'loss_making': True, 'fcf_negative': True}, 'metric_percentiles': {'debt_ratio_pct': {'available': True, 'observations': 48, 'current': 16.20621915618083, 'pctl_rank': 0.1042, 'q20': 19.84318367852004, 'q50': 31.756309575260122, 'q80': 83.97626273385403, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'fcf': {'available': True, 'observations': 48, 'current': -16603600772.0, 'pctl_rank': 0.125, 'q20': -5926914990.0, 'q50': 24854117993.5, 'q80': 99231903416.0, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}}}, 'axes': {'export_fx_sensitivity': {'score': 0, 'exposure_level': 'unknown', 'exposure_metric': None, 'role_keyword_hint': False, 'macro_pressure': {'available': True, 'pressure': -3, 'events': [{'dataset': 'ecos_월별', 'indicator': '원달러', 'latest': 1381.4, 'diff': -57.09999999999991, 'chg1_pct': -3.969412582551257, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -1, 'zscore': 1.0052660837813618, 'pressure_component': -2}, {'dataset': 'ext_월별', 'indicator': '원달러', 'latest': 1381.4, 'diff': -57.09999999999991, 'chg1_pct': -3.969412582551257, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -1, 'zscore': 1.0052660837813618, 'pressure_component': -2}, {'dataset': 'ecos_분기별', 'indicator': '원달러', 'latest': 1438.5, 'diff': 5.2000000000000455, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.33000183105467, 'diff': -0.1399993896484517, 'chg1_pct': -0.14074533822294732, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.19094849248010687, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '달러인덱스_dxy', 'latest': 99.33000183105467, 'diff': -0.1399993896484517, 'chg1_pct': -0.14074533822294732, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.19094849248010687, 'pressure_component': -1}, {'dataset': 'ecos_분기별', 'indicator': '달러인덱스_dxy', 'latest': 99.47000122070312, 'diff': -8.90000152587892, 'chg1_pct': None, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': None, 'pressure_component': -1}, {'dataset': 'ecos_일별', 'indicator': '원달러', 'latest': 1381.4, 'diff': 0.0, 'chg1_pct': 0.0, 'chg20_pct': -1.0458452722063027, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9125230212320103, 'pressure_component': 0}, {'dataset': 'ext_일별', 'indicator': '원달러', 'latest': 1381.4, 'diff': 0.0, 'chg1_pct': 0.0, 'chg20_pct': -1.0458452722063027, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9125230212320103, 'pressure_component': 0}]}, 'basis': 'DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용'}, 'raw_material_sensitivity': {'score': 0, 'material_role': False, 'role_evidence': [], 'raw_material_ratio_pct': None, 'raw_material_ratio_level': 'unknown', 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': '유가_wti', 'latest': 60.790000915527344, 'diff': 2.5800018310546875, 'chg1_pct': 4.432231354806704, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7193229099197688, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '유가_brent', 'latest': 63.900001525878906, 'diff': 0.7800025939941406, 'chg1_pct': 1.235745575401337, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7356486082598602, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '유가_평균', 'latest': 62.345001220703125, 'diff': 1.680002212524414, 'chg1_pct': 2.769310541483594, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7285001583336856, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 3.1100006103515625, 'diff': -1.7999992370605469, 'chg1_pct': -36.65986340120283, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.6354461046678568, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '유가_wti', 'latest': 60.790000915527344, 'diff': 2.5800018310546875, 'chg1_pct': 4.432231354806704, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7193229099197688, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '유가_brent', 'latest': 63.900001525878906, 'diff': 0.7800025939941406, 'chg1_pct': 1.235745575401337, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7356486082598602, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '유가_평균', 'latest': 62.345001220703125, 'diff': 1.680002212524414, 'chg1_pct': 2.769310541483594, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7285001583336856, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '유가_브렌트_wti_스프레드', 'latest': 3.1100006103515625, 'diff': -1.7999992370605469, 'chg1_pct': -36.65986340120283, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.6354461046678568, 'pressure_component': -1}]}, 'basis': 'DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용'}, 'equipment_regulation_sensitivity': {'score': 0, 'equipment_role': False, 'role_evidence': [], 'macro_pressure': {'available': True, 'pressure': 0, 'keyword_count': 0, 'method': 'recent_regulation_keyword_count_tail30'}, 'basis': 'BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭'}, 'backend_hbm_memory_demand_sensitivity': {'score': 0, 'backend_role': False, 'hbm_memory_linked': False, 'role_evidence': [], 'macro_pressure': {'available': True, 'pressure': -3, 'events': [{'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수_변동성_20일', 'latest': 33.71160835282642, 'diff': -65.79215558049638, 'chg1_pct': -66.12026819868193, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': -0.03548281323105865, 'pressure_component': -2}, {'dataset': 'ecos_월별', 'indicator': '반도체섹터변동성_20일', 'latest': 32.57525401706052, 'diff': -42.790312295301085, 'chg1_pct': -56.77700624971291, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': 0.08353512693601556, 'pressure_component': -2}, {'dataset': 'ext_월별', 'indicator': 'sox_반도체_지수_변동성_20일', 'latest': 33.71160835282642, 'diff': -65.79215558049638, 'chg1_pct': -66.12026819868193, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': -0.03548281323105865, 'pressure_component': -2}, {'dataset': 'ext_월별', 'indicator': '반도체섹터변동성_20일', 'latest': 32.57525401706052, 'diff': -42.790312295301085, 'chg1_pct': -56.77700624971291, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': -2, 'zscore': 0.08353512693601556, 'pressure_component': -2}, {'dataset': 'ecos_월별', 'indicator': 'krx_반도체_지수', 'latest': 3218.54, 'diff': 171.88999999999987, 'chg1_pct': 5.64193458388722, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.21173640284639889, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': 'sox_반도체_지수', 'latest': 4758.06005859375, 'diff': 527.97021484375, 'chg1_pct': 12.481300264197248, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 1.2909628285214174, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': 'krx_반도체_지수_수익률_1일', 'latest': -2.028801987099682, 'diff': -0.5162463855686972, 'chg1_pct': 34.13073774254387, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.9325455701271008, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': 'krx_반도체_지수_수익률_5일', 'latest': 2.7722784923301047, 'diff': 5.736555561622902, 'chg1_pct': -193.52292068269787, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.7738011148670009, 'pressure_component': 1}]}, 'basis': 'WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용'}, 'deeptech_loss_rate_sensitivity': {'score': -2, 'deeptech_role': False, 'loss_making': True, 'fcf_negative': True, 'operating_margin_pct': None, 'net_margin_pct': None, 'fcf': -16603600772.0, 'macro_pressure': {'available': True, 'pressure': 3, 'events': [{'dataset': 'ecos_월별', 'indicator': '국고채_10년', 'latest': 2.786, 'diff': 0.22299999999999986, 'chg1_pct': 8.700741318767058, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.08657092241921194, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '국고채_3년', 'latest': 2.347, 'diff': 0.08000000000000007, 'chg1_pct': 3.5288928098809125, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.19408192999406407, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '콜금리', 'latest': 2.582, 'diff': -0.20100000000000007, 'chg1_pct': -7.222421846927773, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.22619541048015662, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': 'cd금리_91일', 'latest': 2.59, 'diff': -0.1200000000000001, 'chg1_pct': -4.428044280442811, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.12370992042409401, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '회사채_aa-', 'latest': 2.917, 'diff': 0.04899999999999993, 'chg1_pct': 1.7085076708507563, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.43556867373266195, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '회사채_bbb-', 'latest': 8.669, 'diff': 0.049000000000001265, 'chg1_pct': 0.5684454756380575, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.813874096802265, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '국고채_10년_3년_스프레드', 'latest': 0.439, 'diff': 0.1429999999999998, 'chg1_pct': 48.3108108108107, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': 0.48175320989729226, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '국고채_10년', 'latest': 2.786, 'diff': 0.22299999999999986, 'chg1_pct': 8.700741318767058, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.08657092241921194, 'pressure_component': 1}]}, 'basis': 'DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시'}, 'high_debt_credit_spread_sensitivity': {'score': 0, 'debt_ratio_pct': 16.20621915618083, 'debt_ratio_percentile': {'available': True, 'observations': 48, 'current': 16.20621915618083, 'pctl_rank': 0.1042, 'q20': 19.84318367852004, 'q50': 31.756309575260122, 'q80': 83.97626273385403, 'method': 'same_field_cross_section_percentile_latest_finance_csv'}, 'high_debt_by_same_field_p80': False, 'macro_pressure': {'available': True, 'pressure': -3, 'events': [{'dataset': 'ecos_월별', 'indicator': '회사채_aa-', 'latest': 2.917, 'diff': 0.04899999999999993, 'chg1_pct': 1.7085076708507563, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.43556867373266195, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '회사채_bbb-', 'latest': 8.669, 'diff': 0.049000000000001265, 'chg1_pct': 0.5684454756380575, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.813874096802265, 'pressure_component': 1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_aa-', 'latest': 0.5699999999999998, 'diff': -0.03100000000000014, 'chg1_pct': -5.158069883527483, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7908406566877426, 'pressure_component': -1}, {'dataset': 'ecos_월별', 'indicator': '신용스프레드_bbb-', 'latest': 6.322000000000001, 'diff': -0.030999999999998806, 'chg1_pct': -0.48795844482919515, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.4400893826897296, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '회사채_aa-', 'latest': 2.917, 'diff': 0.04899999999999993, 'chg1_pct': 1.7085076708507563, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.43556867373266195, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '회사채_bbb-', 'latest': 8.669, 'diff': 0.049000000000001265, 'chg1_pct': 0.5684454756380575, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.813874096802265, 'pressure_component': 1}, {'dataset': 'ext_월별', 'indicator': '신용스프레드_aa-', 'latest': 0.5699999999999998, 'diff': -0.03100000000000014, 'chg1_pct': -5.158069883527483, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -0.7908406566877426, 'pressure_component': -1}, {'dataset': 'ext_월별', 'indicator': '신용스프레드_bbb-', 'latest': 6.322000000000001, 'diff': -0.030999999999998806, 'chg1_pct': -0.48795844482919515, 'chg20_pct': None, 'z_alert': 0, 'shock_flag': 0, 'zscore': -1.4400893826897296, 'pressure_component': -1}]}, 'basis': '회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합'}}, 'note': '숫자 노출도가 없으면 임의 수치를 만들지 않고 company.yaml 명시 키워드와 로컬 산출물만 사용합니다.'}

### macro_numeric_criteria
- ecos_일별: {'국고채_10년': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.385, 'low': 1.706, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.786, 'zone': 'neutral'}, '국고채_3년': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.307, 'low': 1.281, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.347, 'zone': 'neutral'}, '콜금리': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.4512, 'low': 0.75, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.582, 'zone': 'neutral'}, 'cd금리_91일': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.58, 'low': 1.09, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.59, 'zone': 'neutral'}, '국고채_10년_3년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.5059999999999999, 'low': 0.0889999999999999, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.439, 'zone': 'neutral'}, '회사채_aa-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.037, 'low': 2.092, 'high_q': 0.8, 'low_q': 0.2, 'latest': 2.917, 'zone': 'neutral'}, '회사채_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 10.3698, 'low': 8.285, 'high_q': 0.8, 'low_q': 0.2, 'latest': 8.669, 'zone': 'neutral'}, '신용스프레드_aa-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.9536, 'low': 0.5010000000000001, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.5699999999999998, 'zone': 'neutral'}, '신용스프레드_bbb-': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 7.1986, 'low': 6.515000000000001, 'high_q': 0.8, 'low_q': 0.2, 'latest': 6.322000000000001, 'zone': 'low'}, '원달러': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 1338.7, 'low': 1127.6399999999999, 'high_q': 0.8, 'low_q': 0.2, 'latest': 1381.4, 'zone': 'high'}}
- ext_일별: {'달러인덱스_dxy': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 104.26000213623048, 'low': 93.5740005493164, 'high_q': 0.8, 'low_q': 0.2, 'latest': 99.33000183105467, 'zone': 'neutral'}, '미국_국채_10년': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.097200107574463, 'low': 1.5194000244140624, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.415999889373779, 'zone': 'high'}, '미국_국채_13주': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.710000038146973, 'low': 0.0949999988079071, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.23199987411499, 'zone': 'neutral'}, '미국_국채_10년_13주_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 1.2203999914228916, 'low': -0.7462002754211426, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.184000015258789, 'zone': 'neutral'}, '미국_국채_10년_2년_스프레드': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 0.5901999926567075, 'low': -0.3580001831054691, 'high_q': 0.8, 'low_q': 0.2, 'latest': 0.5259998893737792, 'zone': 'neutral'}, '유가_wti': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 80.22800140380859, 'low': 55.40199890136718, 'high_q': 0.8, 'low_q': 0.2, 'latest': 60.790000915527344, 'zone': 'neutral'}, '유가_brent': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 84.80000305175781, 'low': 61.869998931884766, 'high_q': 0.8, 'low_q': 0.2, 'latest': 63.900001525878906, 'zone': 'neutral'}, '유가_평균': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 82.6779998779297, 'low': 58.567000198364255, 'high_q': 0.8, 'low_q': 0.2, 'latest': 62.345001220703125, 'zone': 'neutral'}, '천연가스': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 3.992000007629394, 'low': 2.2754000663757328, 'high_q': 0.8, 'low_q': 0.2, 'latest': 3.447000026702881, 'zone': 'neutral'}, '구리': {'method': 'empirical_percentile', 'lookback_observations': 2708, 'high': 4.320400047302246, 'low': 2.7739999294281006, 'high_q': 0.8, 'low_q': 0.2, 'latest': 4.652500152587891, 'zone': 'high'}}

