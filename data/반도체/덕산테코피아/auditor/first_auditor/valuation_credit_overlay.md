# Auditor Valuation/Credit/ML Overlay - 덕산테코피아

## Scope Control
- Chair and non-Auditor agents are not modified.
- Auditor's original evidence-contract and pass/fail gate are preserved.
- This overlay is injected into audited opinions as front-loaded claims/evidence/source_contexts so the final report can visibly reflect valuation, credit, and ML methods.

## ML 기반 신용·가치평가 교차검증
- 가치평가 ML 판단: EXPENSIVE
- 신용위험 ML 판단: HIGH_RISK
- 해석: 덕산테코피아는 반도체 딥테크 peer universe 내에서 가치평가 ML 판단은 EXPENSIVE, 신용위험 ML 판단은 HIGH_RISK로 분류된다.
- Auditor 판단: 최종 보고서에서는 성장성·저평가 가능성뿐 아니라 수익성, 현금흐름, 재무안정성 리스크도 함께 검토해야 한다.

## Credit Assessment
- signal: high_risk
- watch_grade: D
- risk_drivers: 부채비율 507.37%로 레버리지 부담이 큼; 유동비율 35.58%로 단기 유동성 압력; 영업이익률 -38.39%로 사업 수익성 미흡; 순이익률 -94.18%로 손실 흡수력 점검 필요; FCF가 음수라 내부 현금창출 기반 상환능력 확인 필요; ROE -99.13%로 자본효율성 부진

## Valuation Assessment
- valuation_signal: valuation_risky
- dcf_available: True
- ev_proxy_to_sales: -7.9963
- cautions: FCF가 음수라 DCF의 안정성이 낮음; 영업이익률 -38.39%; DCF proxy가 음수라 가치평가 결론을 보수적으로 제한; 기간 MDD -75.49%로 시장 할인 요인 존재

## ML / Model-Risk Overlay
- trained_proxy_available: True
- trained_valuation_signal: EXPENSIVE
- trained_valuation_confidence: 0.9683
- trained_credit_label: HIGH_RISK
- trained_credit_confidence: 0.9663
- trained_credit_anomaly_score: 0.3844
- trained_models: valuation=extra_trees, credit=random_forest
- trained_quality: valuation_bal_acc=0.8991666666666666, credit_bal_acc=0.8104575163398692
- fallback_model_family: dependency-free interpretable ensemble + peer z-score anomaly detection
- fallback_ml_overlay_label: downside_guardrail
- downside_risk_score: 0.6991
- upside_support_score: 0.2593
- peer_anomaly: 동종 샘플이 부족해 peer anomaly는 제한적으로만 해석합니다.

## Sources
- financial_csv=덕산테코피아_재무.csv
- stock_csv=덕산테코피아_주식.csv
- auditor_overlay_artifact=C:\Agent_6.8\data\반도체\덕산테코피아\auditor\first_auditor\valuation_credit_overlay.json
- trained_ml_overlay_json=C:\Agent_6.8\data\반도체\_sector_common\ml_universe\valuation_credit_ml_overlay.json
- trained_ml_overlay_candidate_csv=C:\Agent_6.8\data\반도체\_sector_common\ml_universe\valuation_credit_ml_overlay_candidate.csv
- trained_ml_quality_summary_csv=C:\Agent_6.8\data\반도체\_sector_common\ml_universe\ml_quality_summary.csv
- trained_ml_quality=valuation_model=extra_trees, valuation_holdout_bal_acc=0.8991666666666666, credit_model=random_forest, credit_holdout_bal_acc=0.8104575163398692
