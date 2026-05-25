# DB하이텍 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\DB하이텍\tech\dbhitek_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\DB하이텍\tech\dbhitek_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-20T21:04:10

## 2. Core Counts
- total_patents: 269
- registered_patents_estimated: 114
- alive_patents_estimated: 6
- recent_5y_application_patents: 21
- h01l_core_patents: 15
- semiconductor_related_ipc_patents: 186
- ipc_subclass_count: 27
- tech_keyword_match_total: 565

## 3. Core Rates
- registration_rate_estimated: 0.4238
- alive_rate_among_registered_estimated: 0.0526
- recent_5y_application_rate: 0.0781
- h01l_core_rate: 0.0558
- semiconductor_related_ipc_rate: 0.6914

## 4. Year Features
- application_year_range: 1998 ~ 2024
- application_year_span: 27

## 5. Scores
- legal_stability_score_estimated: 22.33
- portfolio_momentum_score: 32.18
- ip_technology_fit_score: 67.81
- kipris_tech_ml_score: 38.93

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_WEAK
- bridge_adjustment_points: -2.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10P: 60
- H10D: 53
- H10F: 52
- H10W: 38
- H10B: 19
- H01L: 9
- G11C: 8
- G01R: 5
- G09G: 4
- H03K: 3
- C07D: 2
- G02F: 1
- G06K: 1
- H01F: 1
- B22F: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
