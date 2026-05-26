# Auditor Valuation/Credit/ML Overlay - 네패스

## Scope Control
- Chair and non-Auditor agents are not modified.
- Auditor's original evidence-contract and pass/fail gate are preserved.
- This overlay is injected into audited opinions as front-loaded claims/evidence/source_contexts so the final report can visibly reflect valuation, credit, and ML methods.

## ML 기반 신용·가치평가 교차검증
- 가치평가 ML 판단: ATTRACTIVE
- 신용위험 ML 판단: MEDIUM_RISK
- 해석: 네패스는 반도체 딥테크 peer universe 내에서 상대가치 매력은 있으나, 신용위험은 LOW_RISK가 아닌 MEDIUM_RISK로 분류된다.
- Auditor 판단: 최종 보고서에서는 성장성·저평가 가능성뿐 아니라 수익성, 현금흐름, 재무안정성 리스크도 함께 검토해야 한다.

## Credit Assessment
- signal: high_risk
- watch_grade: D
- risk_drivers: 부채비율 183.67%로 차입 부담 점검 필요; 유동비율 86.24%로 운전자본 점검 필요; 영업이익률 -4.56%로 사업 수익성 미흡; 순이익률 -3.87%로 손실 흡수력 점검 필요; ROE -8.21%로 자본효율성 부진; 기간 MDD -87.36%로 시장 신용/자본조달 리스크 확대

## Valuation Assessment
- valuation_signal: valuation_neutral
- dcf_available: True
- ev_proxy_to_sales: 1.6127
- cautions: 영업이익률 -4.56%; 기간 MDD -87.36%로 시장 할인 요인 존재

## ML / Model-Risk Overlay
- trained_proxy_available: True
- trained_valuation_signal: ATTRACTIVE
- trained_valuation_confidence: 0.8764
- trained_credit_label: MEDIUM_RISK
- trained_credit_confidence: 0.5963
- trained_credit_anomaly_score: 0.079
- trained_models: valuation=extra_trees, credit=random_forest
- trained_quality: valuation_bal_acc=0.8991666666666666, credit_bal_acc=0.8104575163398692
- fallback_model_family: dependency-free interpretable ensemble + peer z-score anomaly detection
- fallback_ml_overlay_label: balanced_watch
- downside_risk_score: 0.499
- upside_support_score: 0.5182
- peer_anomaly: 일부 재무지표가 동종 샘플 대비 차이가 있으나 단독 결론 근거로 쓰기보다는 보조 위험 신호로 활용합니다: operating_margin_pct z=+1.17

## Sources
- financial_csv=네패스_재무.csv
- stock_csv=네패스_주식.csv
- auditor_overlay_artifact=C:\Agent_6.8\workspace\audit\nepes\first_auditor\valuation_credit_overlay.json
- trained_ml_overlay_json=C:\Agent_6.8\src\auditor_agent\resources\valuation_credit_ml_overlay.json
- trained_ml_overlay_candidate_csv=C:\Agent_6.8\src\auditor_agent\resources\valuation_credit_ml_overlay_candidate.csv
- trained_ml_quality_summary_csv=C:\Agent_6.8\src\auditor_agent\resources\ml_quality_summary.csv
- trained_ml_quality=valuation_model=extra_trees, valuation_holdout_bal_acc=0.8991666666666666, credit_model=random_forest, credit_holdout_bal_acc=0.8104575163398692
