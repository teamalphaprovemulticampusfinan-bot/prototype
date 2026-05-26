# GST KIPRIS Tech ML Features

## 1. Source
- source_csv: `data\반도체\GST\tech\gst_kipris_patents_normalized.csv`
- enriched_csv: `data\반도체\GST\tech\gst_kipris_tech_ml_enriched.csv`
- generated_at: 2026-05-26T00:52:08

## 2. Core Counts
- total_patents: 30
- registered_patents_estimated: 14
- alive_patents_estimated: 2
- recent_5y_application_patents: 2
- h01l_core_patents: 0
- semiconductor_related_ipc_patents: 4
- ipc_subclass_count: 11
- tech_keyword_match_total: 10

## 3. Core Rates
- registration_rate_estimated: 0.4667
- alive_rate_among_registered_estimated: 0.1429
- recent_5y_application_rate: 0.0667
- h01l_core_rate: 0.0
- semiconductor_related_ipc_rate: 0.1333

## 4. Year Features
- application_year_range: 2001 ~ 2022
- application_year_span: 22

## 5. Scores
- legal_stability_score_estimated: 28.1
- portfolio_momentum_score: 23.23
- ip_technology_fit_score: 17.17
- kipris_tech_ml_score: 23.36

## 6. Tech-to-Value Bridge Adjustment
- bridge_signal: IP_QUALITY_WEAK
- bridge_adjustment_points: -2.0
- usage_rule: Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.

## 7. Top IPC Subclass
- G11B: 16
- H10N: 3
- G11C: 2
- B21D: 2
- E05F: 1
- B03B: 1
- F01M: 1
- F16L: 1
- C02F: 1
- G06F: 1
- G05F: 1

## 8. Cautions
- final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.
- register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.
- KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.
