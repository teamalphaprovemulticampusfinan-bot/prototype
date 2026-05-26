# 덕산테코피아 KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\덕산테코피아\tech\duksan_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\덕산테코피아\tech\duksan_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T16:57:16

## 2. Core Counts
- total_patents: 38
- registered_patents_estimated: 30
- alive_patents_estimated: 29
- recent_5y_application_patents: 5
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 11
- ipc_subclass_count: 16
- tech_keyword_match_total: 22

## 3. Core Rates
- registration_rate_estimated: 0.7895
- alive_rate_among_registered_estimated: 0.9667
- recent_5y_application_rate: 0.1316
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.2895

## 4. Year Features
- application_year_range: 2005 ~ 2024
- application_year_span: 20

## 5. Scores
- legal_stability_score_estimated: 86.92
- portfolio_momentum_score: 26.86
- ip_technology_fit_score: 29.25
- kipris_tech_ml_score: 51.6

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G03F: 7
- C07F: 7
- H10W: 5
- H10P: 3
- C09J: 3
- B22F: 2
- C23C: 2
- F26B: 1
- C01B: 1
- C08L: 1
- B23K: 1
- B01J: 1
- C09D: 1
- C01G: 1
- C07D: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
