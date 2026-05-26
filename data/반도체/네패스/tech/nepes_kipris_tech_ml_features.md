# 네패스 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\네패스\tech\nepes_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\네패스\tech\nepes_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T15:40:54

## 2. Core Counts
- total_patents: 423
- registered_patents_estimated: 311
- alive_patents_estimated: 242
- recent_5y_application_patents: 111
- h01l_core_patents: 6
- semiconductor_related_ipc_patents: 243
- ipc_subclass_count: 65
- tech_keyword_match_total: 858

## 3. Core Rates
- registration_rate_estimated: 0.7352
- alive_rate_among_registered_estimated: 0.7781
- recent_5y_application_rate: 0.2624
- h01l_core_rate: 0.0142
- semiconductor_related_ipc_rate: 0.5745

## 4. Year Features
- application_year_range: 1998 ~ 2025
- application_year_span: 28

## 5. Scores
- legal_stability_score_estimated: 74.36
- portfolio_momentum_score: 74.18
- ip_technology_fit_score: 65.39
- kipris_tech_ml_score: 71.62

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_POSITIVE
- bridge_adjustment_points: 2.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10W: 160
- H10B: 26
- H01M: 26
- G06F: 24
- H10P: 14
- C09D: 13
- G02F: 12
- C09K: 10
- C09J: 8
- H10H: 7
- C07F: 6
- F21V: 6
- H05K: 5
- G03F: 5
- C08G: 4

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
