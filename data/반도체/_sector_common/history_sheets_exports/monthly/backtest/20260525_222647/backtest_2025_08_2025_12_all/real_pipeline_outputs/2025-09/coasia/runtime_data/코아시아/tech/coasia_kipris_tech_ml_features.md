# 코아시아 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\코아시아\tech\coasia_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\코아시아\tech\coasia_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T05:15:42

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 25
- alive_patents_estimated: 25
- recent_5y_application_patents: 6
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 5
- ipc_subclass_count: 8
- tech_keyword_match_total: 16

## 3. Core Rates
- registration_rate_estimated: 0.8333
- alive_rate_among_registered_estimated: 1.0
- recent_5y_application_rate: 0.2
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.1667

## 4. Year Features
- application_year_range: 2010 ~ 2024
- application_year_span: 15

## 5. Scores
- legal_stability_score_estimated: 91.17
- portfolio_momentum_score: 24.7
- ip_technology_fit_score: 17.83
- kipris_tech_ml_score: 49.23

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G02B: 13
- G06T: 5
- H10H: 4
- H04N: 3
- G06F: 2
- A61B: 1
- G07C: 1
- H05B: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
