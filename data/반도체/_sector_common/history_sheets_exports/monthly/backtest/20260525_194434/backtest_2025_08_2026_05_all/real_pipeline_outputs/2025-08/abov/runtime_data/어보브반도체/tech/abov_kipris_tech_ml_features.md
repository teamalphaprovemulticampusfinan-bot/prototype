# 어보브반도체 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\어보브반도체\tech\abov_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\어보브반도체\tech\abov_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-25T20:41:01

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 26
- alive_patents_estimated: 19
- recent_5y_application_patents: 10
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 5
- ipc_subclass_count: 12
- tech_keyword_match_total: 13

## 3. Core Rates
- registration_rate_estimated: 0.8667
- alive_rate_among_registered_estimated: 0.7308
- recent_5y_application_rate: 0.3333
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.1667

## 4. Year Features
- application_year_range: 2004 ~ 2025
- application_year_span: 22

## 5. Scores
- legal_stability_score_estimated: 78.89
- portfolio_momentum_score: 36.17
- ip_technology_fit_score: 20.17
- kipris_tech_ml_score: 48.46

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G06F: 6
- H04L: 5
- H02J: 4
- H03K: 3
- H03F: 2
- G01R: 2
- G01J: 2
- H02P: 2
- H04B: 1
- H04W: 1
- H02M: 1
- F04B: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
