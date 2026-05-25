# SFA반도체 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\SFA반도체\tech\sfa_semicon_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\SFA반도체\tech\sfa_semicon_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-25T12:47:58

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 20
- alive_patents_estimated: 9
- recent_5y_application_patents: 1
- h01l_core_patents: 1
- semiconductor_related_ipc_patents: 28
- ipc_subclass_count: 6
- tech_keyword_match_total: 87

## 3. Core Rates
- registration_rate_estimated: 0.6667
- alive_rate_among_registered_estimated: 0.45
- recent_5y_application_rate: 0.0333
- h01l_core_rate: 0.0333
- semiconductor_related_ipc_rate: 0.9333

## 4. Year Features
- application_year_range: 2000 ~ 2021
- application_year_span: 22

## 5. Scores
- legal_stability_score_estimated: 53.25
- portfolio_momentum_score: 21.62
- ip_technology_fit_score: 58.33
- kipris_tech_ml_score: 45.28

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10W: 24
- H10B: 2
- H01L: 1
- H10P: 1
- G06K: 1
- H10F: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
