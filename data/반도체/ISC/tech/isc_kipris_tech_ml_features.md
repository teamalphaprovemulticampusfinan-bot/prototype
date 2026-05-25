# ISC KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\ISC\tech\isc_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\ISC\tech\isc_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-20T22:29:22

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 28
- alive_patents_estimated: 28
- recent_5y_application_patents: 3
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 28
- ipc_subclass_count: 5
- tech_keyword_match_total: 31

## 3. Core Rates
- registration_rate_estimated: 0.9333
- alive_rate_among_registered_estimated: 1.0
- recent_5y_application_rate: 0.1
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.9333

## 4. Year Features
- application_year_range: 2008 ~ 2025
- application_year_span: 18

## 5. Scores
- legal_stability_score_estimated: 96.67
- portfolio_momentum_score: 22.85
- ip_technology_fit_score: 47.17
- kipris_tech_ml_score: 59.67

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_MODERATE
- bridge_adjustment_points: 1.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G01R: 24
- H01R: 3
- H10P: 1
- H01B: 1
- H02M: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
