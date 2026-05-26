# 피에스케이 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\피에스케이\tech\psk_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\피에스케이\tech\psk_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T22:17:45

## 2. Core Counts
- total_patents: 25
- registered_patents_estimated: 6
- alive_patents_estimated: 6
- recent_5y_application_patents: 22
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 0
- ipc_subclass_count: 4
- tech_keyword_match_total: 26

## 3. Core Rates
- registration_rate_estimated: 0.24
- alive_rate_among_registered_estimated: 1.0
- recent_5y_application_rate: 0.88
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.0

## 4. Year Features
- application_year_range: 2015 ~ 2025
- application_year_span: 11

## 5. Scores
- legal_stability_score_estimated: 65.4
- portfolio_momentum_score: 51.7
- ip_technology_fit_score: 13.73
- kipris_tech_ml_score: 45.79

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10P: 11
- H01J: 10
- F16K: 3
- B25B: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
