# 티씨케이 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\티씨케이\tech\tck_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\티씨케이\tech\tck_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-20T22:25:13

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 22
- alive_patents_estimated: 21
- recent_5y_application_patents: 7
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 5
- ipc_subclass_count: 12
- tech_keyword_match_total: 21

## 3. Core Rates
- registration_rate_estimated: 0.7333
- alive_rate_among_registered_estimated: 0.9545
- recent_5y_application_rate: 0.2333
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.1667

## 4. Year Features
- application_year_range: 2009 ~ 2024
- application_year_span: 16

## 5. Scores
- legal_stability_score_estimated: 83.62
- portfolio_momentum_score: 27.32
- ip_technology_fit_score: 22.83
- kipris_tech_ml_score: 48.49

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10P: 12
- H01M: 3
- H10D: 3
- C01B: 2
- C23C: 2
- B26D: 2
- C30B: 1
- G01M: 1
- H10H: 1
- B28D: 1
- C04B: 1
- B24B: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
