# Auditor Valuation/Credit/ML Overlay - 한미반도체

## Scope Control
- Chair and non-Auditor agents are not modified.
- Auditor's original evidence-contract and pass/fail gate are preserved.
- This overlay is injected into audited opinions as front-loaded claims/evidence/source_contexts so the final report can visibly reflect valuation, credit, and ML methods.

## ML 기반 신용·가치평가 교차검증
- 가치평가 ML 판단: FAIR
- 신용위험 ML 판단: LOW_RISK
- 해석: 한미반도체는 반도체 딥테크 peer universe 내에서 가치평가 ML 판단은 FAIR, 신용위험 ML 판단은 LOW_RISK로 분류된다.
- Auditor 판단: 최종 보고서에서는 성장성·저평가 가능성뿐 아니라 수익성, 현금흐름, 재무안정성 리스크도 함께 검토해야 한다.

## Credit Assessment
- signal: watch
- watch_grade: B
- risk_drivers: 영업이익률 -43.59%로 사업 수익성 미흡; 순이익률 -37.11%로 손실 흡수력 점검 필요; ROE -31.00%로 자본효율성 부진; 기간 MDD -68.52%로 시장 신용/자본조달 리스크 확대

## Valuation Assessment
- valuation_signal: valuation_neutral
- dcf_available: True
- ev_proxy_to_sales: 2.7842
- cautions: 영업이익률 -43.59%; 기간 MDD -68.52%로 시장 할인 요인 존재

## ML / Model-Risk Overlay
- trained_proxy_available: True
- trained_valuation_signal: FAIR
- trained_valuation_confidence: 0.6181
- trained_credit_label: LOW_RISK
- trained_credit_confidence: 0.935
- trained_credit_anomaly_score: 0.2707
- trained_models: valuation=extra_trees, credit=random_forest
- trained_quality: valuation_bal_acc=0.8991666666666666, credit_bal_acc=0.8104575163398692
- fallback_model_family: dependency-free interpretable ensemble + peer z-score anomaly detection
- fallback_ml_overlay_label: balanced_watch
- downside_risk_score: 0.36
- upside_support_score: 0.5137
- peer_anomaly: 동종 샘플이 부족해 peer anomaly는 제한적으로만 해석합니다.

## Sources
- financial_csv=한미반도체_재무.csv
- stock_csv=한미반도체_주식.csv
- auditor_overlay_artifact=C:\Agent_6.8\data\반도체\한미반도체\auditor\first_auditor\valuation_credit_overlay.json
- trained_ml_overlay_json=C:\Agent_6.8\data\반도체\_sector_common\ml_universe\valuation_credit_ml_overlay.json
- trained_ml_overlay_candidate_csv=C:\Agent_6.8\data\반도체\_sector_common\ml_universe\valuation_credit_ml_overlay_candidate.csv
- trained_ml_quality_summary_csv=C:\Agent_6.8\data\반도체\_sector_common\ml_universe\ml_quality_summary.csv
- trained_ml_quality=valuation_model=extra_trees, valuation_holdout_bal_acc=0.8991666666666666, credit_model=random_forest, credit_holdout_bal_acc=0.8104575163398692
