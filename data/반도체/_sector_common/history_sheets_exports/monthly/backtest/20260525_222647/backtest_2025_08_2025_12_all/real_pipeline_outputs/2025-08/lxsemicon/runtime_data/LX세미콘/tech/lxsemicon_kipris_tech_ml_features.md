# LX세미콘 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\LX세미콘\tech\lxsemicon_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\LX세미콘\tech\lxsemicon_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-25T23:17:39

## 2. Core Counts
- total_patents: 90
- registered_patents_estimated: 38
- alive_patents_estimated: 38
- recent_5y_application_patents: 61
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 7
- ipc_subclass_count: 14
- tech_keyword_match_total: 22

## 3. Core Rates
- registration_rate_estimated: 0.4222
- alive_rate_among_registered_estimated: 1.0
- recent_5y_application_rate: 0.6778
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.0778

## 4. Year Features
- application_year_range: 2010 ~ 2025
- application_year_span: 16

## 5. Scores
- legal_stability_score_estimated: 73.78
- portfolio_momentum_score: 67.17
- ip_technology_fit_score: 16.83
- kipris_tech_ml_score: 54.71

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G09G: 38
- H04N: 24
- G06F: 16
- H10D: 2
- G05F: 1
- G01S: 1
- H03F: 1
- H10W: 1
- H05B: 1
- H03K: 1
- F21S: 1
- H02M: 1
- H03L: 1
- G05B: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
