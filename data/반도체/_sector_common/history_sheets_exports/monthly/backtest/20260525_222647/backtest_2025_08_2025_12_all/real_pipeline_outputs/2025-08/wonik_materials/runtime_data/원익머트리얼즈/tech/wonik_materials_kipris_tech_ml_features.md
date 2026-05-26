# 원익머트리얼즈 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\원익머트리얼즈\tech\wonik_materials_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\원익머트리얼즈\tech\wonik_materials_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T01:52:12

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 28
- alive_patents_estimated: 27
- recent_5y_application_patents: 11
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 0
- ipc_subclass_count: 13
- tech_keyword_match_total: 11

## 3. Core Rates
- registration_rate_estimated: 0.9333
- alive_rate_among_registered_estimated: 0.9643
- recent_5y_application_rate: 0.3667
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.0

## 4. Year Features
- application_year_range: 2009 ~ 2024
- application_year_span: 16

## 5. Scores
- legal_stability_score_estimated: 95.06
- portfolio_momentum_score: 33.78
- ip_technology_fit_score: 14.5
- kipris_tech_ml_score: 52.51

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- C01B: 14
- C01C: 2
- B01J: 2
- H10P: 2
- C23C: 2
- C07F: 1
- C30B: 1
- C07B: 1
- C01G: 1
- C07D: 1
- B01D: 1
- C07C: 1
- H01M: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
