# 미코 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\미코\tech\mico_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\미코\tech\mico_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T04:18:00

## 2. Core Counts
- total_patents: 115
- registered_patents_estimated: 67
- alive_patents_estimated: 33
- recent_5y_application_patents: 24
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 11
- ipc_subclass_count: 41
- tech_keyword_match_total: 53

## 3. Core Rates
- registration_rate_estimated: 0.5826
- alive_rate_among_registered_estimated: 0.4925
- recent_5y_application_rate: 0.2087
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.0957

## 4. Year Features
- application_year_range: 1986 ~ 2024
- application_year_span: 39

## 5. Scores
- legal_stability_score_estimated: 52.73
- portfolio_momentum_score: 38.1
- ip_technology_fit_score: 32.96
- kipris_tech_ml_score: 42.41

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10P: 27
- B01J: 14
- H01M: 10
- A61K: 6
- F01N: 6
- C22B: 4
- C23C: 4
- B01D: 3
- C12N: 2
- C25D: 2
- C03B: 2
- B43K: 2
- C07F: 2
- G01M: 2
- B29C: 2

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
