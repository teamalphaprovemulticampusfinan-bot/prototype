# 제주반도체 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\제주반도체\tech\jeju_semicon_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\제주반도체\tech\jeju_semicon_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T20:08:14

## 2. Core Counts
- total_patents: 26
- registered_patents_estimated: 20
- alive_patents_estimated: 3
- recent_5y_application_patents: 0
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 3
- ipc_subclass_count: 5
- tech_keyword_match_total: 42

## 3. Core Rates
- registration_rate_estimated: 0.7692
- alive_rate_among_registered_estimated: 0.15
- recent_5y_application_rate: 0.0
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.1154

## 4. Year Features
- application_year_range: 2000 ~ 2015
- application_year_span: 16

## 5. Scores
- legal_stability_score_estimated: 42.52
- portfolio_momentum_score: 16.0
- ip_technology_fit_score: 24.36
- kipris_tech_ml_score: 29.12

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_WEAK
- bridge_adjustment_points: -2.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G11C: 21
- H10W: 2
- G05F: 1
- H10P: 1
- H04N: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
