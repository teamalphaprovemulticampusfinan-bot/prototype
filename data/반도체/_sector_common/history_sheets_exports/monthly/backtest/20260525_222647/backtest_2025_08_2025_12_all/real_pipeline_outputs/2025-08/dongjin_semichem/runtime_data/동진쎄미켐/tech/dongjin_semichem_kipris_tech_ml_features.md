# 동진쎄미켐 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\동진쎄미켐\tech\dongjin_semichem_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\동진쎄미켐\tech\dongjin_semichem_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T01:35:11

## 2. Core Counts
- total_patents: 102
- registered_patents_estimated: 49
- alive_patents_estimated: 30
- recent_5y_application_patents: 25
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 34
- ipc_subclass_count: 21
- tech_keyword_match_total: 79

## 3. Core Rates
- registration_rate_estimated: 0.4804
- alive_rate_among_registered_estimated: 0.6122
- recent_5y_application_rate: 0.2451
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.3333

## 4. Year Features
- application_year_range: 1993 ~ 2025
- application_year_span: 33

## 5. Scores
- legal_stability_score_estimated: 54.36
- portfolio_momentum_score: 39.83
- ip_technology_fit_score: 36.91
- kipris_tech_ml_score: 44.77

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G03F: 43
- C07D: 12
- C07C: 8
- C23F: 6
- H10K: 5
- C09K: 3
- C08G: 3
- C09D: 2
- C08J: 2
- C25B: 2
- C23C: 2
- C07F: 2
- C08F: 2
- H01M: 2
- C01B: 2

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
