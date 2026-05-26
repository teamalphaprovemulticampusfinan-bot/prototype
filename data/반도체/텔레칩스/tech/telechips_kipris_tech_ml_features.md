# 텔레칩스 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\텔레칩스\tech\telechips_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\텔레칩스\tech\telechips_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T20:43:55

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 28
- alive_patents_estimated: 24
- recent_5y_application_patents: 13
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 2
- ipc_subclass_count: 17
- tech_keyword_match_total: 14

## 3. Core Rates
- registration_rate_estimated: 0.9333
- alive_rate_among_registered_estimated: 0.8571
- recent_5y_application_rate: 0.4333
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.0667

## 4. Year Features
- application_year_range: 2005 ~ 2023
- application_year_span: 19

## 5. Scores
- legal_stability_score_estimated: 89.23
- portfolio_momentum_score: 40.02
- ip_technology_fit_score: 21.17
- kipris_tech_ml_score: 54.05

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H04N: 7
- G06F: 5
- H04R: 2
- G06T: 2
- H04L: 2
- G01R: 1
- H05K: 1
- H03G: 1
- G07C: 1
- G10L: 1
- H04M: 1
- G06Q: 1
- G01S: 1
- H03K: 1
- G11B: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
