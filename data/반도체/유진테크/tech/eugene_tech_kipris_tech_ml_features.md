# 유진테크 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\유진테크\tech\eugene_tech_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\유진테크\tech\eugene_tech_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-25T21:19:16

## 2. Core Counts
- total_patents: 21
- registered_patents_estimated: 13
- alive_patents_estimated: 12
- recent_5y_application_patents: 11
- h01l_core_patents: 1
- semiconductor_related_ipc_patents: 1
- ipc_subclass_count: 8
- tech_keyword_match_total: 15

## 3. Core Rates
- registration_rate_estimated: 0.619
- alive_rate_among_registered_estimated: 0.9231
- recent_5y_application_rate: 0.5238
- h01l_core_rate: 0.0476
- semiconductor_related_ipc_rate: 0.0476

## 4. Year Features
- application_year_range: 2005 ~ 2025
- application_year_span: 21

## 5. Scores
- legal_stability_score_estimated: 78.92
- portfolio_momentum_score: 43.28
- ip_technology_fit_score: 16.43
- kipris_tech_ml_score: 49.48

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10P: 9
- H01J: 4
- C23C: 2
- H01M: 2
- H02B: 1
- B23K: 1
- B26F: 1
- B21D: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
