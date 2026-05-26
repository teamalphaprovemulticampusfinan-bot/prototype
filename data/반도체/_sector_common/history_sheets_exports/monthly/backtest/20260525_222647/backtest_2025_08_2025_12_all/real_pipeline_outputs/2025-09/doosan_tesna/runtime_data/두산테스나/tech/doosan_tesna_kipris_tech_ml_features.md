# 두산테스나 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\두산테스나\tech\doosan_tesna_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\두산테스나\tech\doosan_tesna_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T09:27:15

## 2. Core Counts
- total_patents: 6
- registered_patents_estimated: 6
- alive_patents_estimated: 3
- recent_5y_application_patents: 0
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 2
- ipc_subclass_count: 6
- tech_keyword_match_total: 8

## 3. Core Rates
- registration_rate_estimated: 1.0
- alive_rate_among_registered_estimated: 0.5
- recent_5y_application_rate: 0.0
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.3333

## 4. Year Features
- application_year_range: 2008 ~ 2014
- application_year_span: 7

## 5. Scores
- legal_stability_score_estimated: 72.5
- portfolio_momentum_score: 7.0
- ip_technology_fit_score: 30.0
- kipris_tech_ml_score: 40.1

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10W: 1
- G01R: 1
- G06V: 1
- G06K: 1
- B42D: 1
- B23K: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
