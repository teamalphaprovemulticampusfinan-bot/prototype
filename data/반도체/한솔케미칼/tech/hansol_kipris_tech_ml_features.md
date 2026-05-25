# 한솔케미칼 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\한솔케미칼\tech\hansol_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\한솔케미칼\tech\hansol_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-20T19:58:35

## 2. Core Counts
- total_patents: 656
- registered_patents_estimated: 413
- alive_patents_estimated: 351
- recent_5y_application_patents: 358
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 40
- ipc_subclass_count: 138
- tech_keyword_match_total: 135

## 3. Core Rates
- registration_rate_estimated: 0.6296
- alive_rate_among_registered_estimated: 0.8499
- recent_5y_application_rate: 0.5457
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.061

## 4. Year Features
- application_year_range: 1987 ~ 2025
- application_year_span: 39

## 5. Scores
- legal_stability_score_estimated: 74.06
- portfolio_momentum_score: 84.1
- ip_technology_fit_score: 29.19
- kipris_tech_ml_score: 63.61

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_MODERATE
- bridge_adjustment_points: 1.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H01M: 56
- C08F: 47
- B60R: 41
- B60N: 26
- B32B: 24
- C07F: 23
- C09K: 20
- C23C: 18
- B41M: 17
- H10P: 17
- C08L: 14
- C09D: 14
- C08G: 13
- C03C: 11
- B29C: 9

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
