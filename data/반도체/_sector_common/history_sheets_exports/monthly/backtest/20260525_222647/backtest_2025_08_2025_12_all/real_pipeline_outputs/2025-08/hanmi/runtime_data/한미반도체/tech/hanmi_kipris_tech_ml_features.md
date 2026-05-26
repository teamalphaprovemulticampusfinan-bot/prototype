# 한미반도체 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\한미반도체\tech\hanmi_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\한미반도체\tech\hanmi_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-25T22:34:42

## 2. Core Counts
- total_patents: 901
- registered_patents_estimated: 516
- alive_patents_estimated: 320
- recent_5y_application_patents: 186
- h01l_core_patents: 1
- semiconductor_related_ipc_patents: 226
- ipc_subclass_count: 77
- tech_keyword_match_total: 910

## 3. Core Rates
- registration_rate_estimated: 0.5727
- alive_rate_among_registered_estimated: 0.6202
- recent_5y_application_rate: 0.2064
- h01l_core_rate: 0.0011
- semiconductor_related_ipc_rate: 0.2508

## 4. Year Features
- application_year_range: 1983 ~ 2025
- application_year_span: 43

## 5. Scores
- legal_stability_score_estimated: 58.5
- portfolio_momentum_score: 72.22
- ip_technology_fit_score: 43.9
- kipris_tech_ml_score: 58.24

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_MODERATE
- bridge_adjustment_points: 1.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10P: 362
- A61K: 128
- H10W: 108
- C07D: 77
- C07K: 50
- C12N: 16
- G01R: 13
- B29C: 8
- A23L: 8
- C09D: 8
- G06Q: 7
- C07H: 6
- H05K: 5
- B02C: 4
- B07B: 4

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
