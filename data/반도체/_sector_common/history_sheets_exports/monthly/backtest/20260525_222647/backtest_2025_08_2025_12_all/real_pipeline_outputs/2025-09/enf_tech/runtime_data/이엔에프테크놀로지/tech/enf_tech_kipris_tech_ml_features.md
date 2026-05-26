# 이엔에프테크놀로지 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\이엔에프테크놀로지\tech\enf_tech_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\이엔에프테크놀로지\tech\enf_tech_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T07:49:12

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 14
- alive_patents_estimated: 14
- recent_5y_application_patents: 17
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 4
- ipc_subclass_count: 8
- tech_keyword_match_total: 30

## 3. Core Rates
- registration_rate_estimated: 0.4667
- alive_rate_among_registered_estimated: 1.0
- recent_5y_application_rate: 0.5667
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.1333

## 4. Year Features
- application_year_range: 2014 ~ 2026
- application_year_span: 13

## 5. Scores
- legal_stability_score_estimated: 76.0
- portfolio_momentum_score: 40.48
- ip_technology_fit_score: 21.33
- kipris_tech_ml_score: 48.94

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- C09K: 10
- C23F: 6
- G03F: 5
- C08G: 4
- C09G: 2
- C11D: 1
- C07D: 1
- C07C: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
