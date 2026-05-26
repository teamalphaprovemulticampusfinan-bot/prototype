# 원익IPS KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\원익IPS\tech\wonik_ips_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\원익IPS\tech\wonik_ips_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T00:16:21

## 2. Core Counts
- total_patents: 116
- registered_patents_estimated: 48
- alive_patents_estimated: 42
- recent_5y_application_patents: 45
- h01l_core_patents: 1
- semiconductor_related_ipc_patents: 18
- ipc_subclass_count: 18
- tech_keyword_match_total: 130

## 3. Core Rates
- registration_rate_estimated: 0.4138
- alive_rate_among_registered_estimated: 0.875
- recent_5y_application_rate: 0.3879
- h01l_core_rate: 0.0086
- semiconductor_related_ipc_rate: 0.1552

## 4. Year Features
- application_year_range: 2003 ~ 2025
- application_year_span: 23

## 5. Scores
- legal_stability_score_estimated: 64.12
- portfolio_momentum_score: 53.83
- ip_technology_fit_score: 31.81
- kipris_tech_ml_score: 51.34

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_NEUTRAL
- bridge_adjustment_points: 0.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- H10P: 41
- C23C: 33
- H01J: 12
- H10K: 9
- B23K: 5
- F16K: 2
- H10F: 2
- H10N: 2
- G03F: 1
- G01D: 1
- B08B: 1
- G01B: 1
- F16L: 1
- G09F: 1
- G02F: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
