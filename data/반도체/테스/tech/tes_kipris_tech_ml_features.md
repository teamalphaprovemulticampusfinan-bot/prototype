# 테스 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\테스\tech\tes_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\테스\tech\tes_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-25T21:33:41

## 2. Core Counts
- total_patents: 382
- registered_patents_estimated: 287
- alive_patents_estimated: 146
- recent_5y_application_patents: 53
- h01l_core_patents: 1
- semiconductor_related_ipc_patents: 122
- ipc_subclass_count: 83
- tech_keyword_match_total: 302

## 3. Core Rates
- registration_rate_estimated: 0.7513
- alive_rate_among_registered_estimated: 0.5087
- recent_5y_application_rate: 0.1387
- h01l_core_rate: 0.0026
- semiconductor_related_ipc_rate: 0.3194

## 4. Year Features
- application_year_range: 1990 ~ 2025
- application_year_span: 36

## 5. Scores
- legal_stability_score_estimated: 60.81
- portfolio_momentum_score: 48.7
- ip_technology_fit_score: 44.14
- kipris_tech_ml_score: 52.18

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G01R: 84
- H10P: 49
- F02D: 19
- F01N: 18
- G06F: 17
- F16H: 14
- G11C: 9
- A61B: 8
- B60W: 8
- F02M: 7
- H01J: 6
- G01M: 6
- H01R: 6
- H03K: 6
- B60L: 5

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
