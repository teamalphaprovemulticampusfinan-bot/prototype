# 에스티아이 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\에스티아이\tech\sti_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\에스티아이\tech\sti_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T15:08:30

## 2. Core Counts
- total_patents: 58
- registered_patents_estimated: 26
- alive_patents_estimated: 13
- recent_5y_application_patents: 26
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 4
- ipc_subclass_count: 24
- tech_keyword_match_total: 33

## 3. Core Rates
- registration_rate_estimated: 0.4483
- alive_rate_among_registered_estimated: 0.5
- recent_5y_application_rate: 0.4483
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.069

## 4. Year Features
- application_year_range: 1996 ~ 2025
- application_year_span: 30

## 5. Scores
- legal_stability_score_estimated: 47.5
- portfolio_momentum_score: 47.39
- ip_technology_fit_score: 28.1
- kipris_tech_ml_score: 41.65

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G02F: 11
- H10P: 9
- B41J: 9
- B67B: 3
- B23K: 3
- B65G: 2
- C03C: 2
- B08B: 2
- F16L: 2
- B65D: 1
- B29C: 1
- B01D: 1
- H02K: 1
- B67D: 1
- B24B: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
