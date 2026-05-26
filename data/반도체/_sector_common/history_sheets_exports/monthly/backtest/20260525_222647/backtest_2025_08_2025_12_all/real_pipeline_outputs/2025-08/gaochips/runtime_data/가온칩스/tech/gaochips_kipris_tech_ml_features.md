# 가온칩스 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\가온칩스\tech\gaochips_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\가온칩스\tech\gaochips_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T00:01:53

## 2. Core Counts
- total_patents: 4
- registered_patents_estimated: 4
- alive_patents_estimated: 4
- recent_5y_application_patents: 4
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 1
- ipc_subclass_count: 3
- tech_keyword_match_total: 4

## 3. Core Rates
- registration_rate_estimated: 1.0
- alive_rate_among_registered_estimated: 1.0
- recent_5y_application_rate: 1.0
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.25

## 4. Year Features
- application_year_range: 2021 ~ 2025
- application_year_span: 5

## 5. Scores
- legal_stability_score_estimated: 100.0
- portfolio_momentum_score: 41.8
- ip_technology_fit_score: 21.25
- kipris_tech_ml_score: 58.91

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_MODERATE
- bridge_adjustment_points: 1.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H03K: 2
- G01R: 1
- G06F: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
