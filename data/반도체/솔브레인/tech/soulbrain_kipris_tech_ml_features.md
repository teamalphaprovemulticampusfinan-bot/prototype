# 솔브레인 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\솔브레인\tech\soulbrain_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\솔브레인\tech\soulbrain_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-20T22:11:03

## 2. Core Counts
- total_patents: 90
- registered_patents_estimated: 21
- alive_patents_estimated: 17
- recent_5y_application_patents: 31
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 10
- ipc_subclass_count: 24
- tech_keyword_match_total: 61

## 3. Core Rates
- registration_rate_estimated: 0.2333
- alive_rate_among_registered_estimated: 0.8095
- recent_5y_application_rate: 0.3444
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.1111

## 4. Year Features
- application_year_range: 2000 ~ 2025
- application_year_span: 26

## 5. Scores
- legal_stability_score_estimated: 52.15
- portfolio_momentum_score: 46.0
- ip_technology_fit_score: 30.67
- kipris_tech_ml_score: 43.86

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H01M: 20
- C09G: 13
- A61K: 10
- C09K: 8
- H10P: 6
- G01R: 5
- C07D: 4
- C01B: 3
- C11D: 3
- H01B: 2
- C23F: 2
- C23C: 2
- B01D: 1
- C25B: 1
- C09D: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
