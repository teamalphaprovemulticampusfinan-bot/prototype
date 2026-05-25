# Technology Lifecycle Features

- company: 한솔케미칼
- status: OK
- overall_lifecycle_stage: GROWTH
- overall_lifecycle_score: 69.81
- source_patent_csv: `data\반도체\한솔케미칼\tech\hansol_kipris_bibliographic_normalized.csv`

## Summary
power_thermal_efficiency, semiconductor_materials, process_yield_quality 중심의 최근 특허 출원 밀도가 높아 기술 수명주기는 성장기 신호에 가깝습니다. 다만 논문/산업 리포트/고객 채택 속도 데이터가 없으면 확정이 아니라 특허 기반 추정입니다.

## Keyword Trends
| keyword | stage | score | total | recent | baseline | trend_ratio | reason |
|---|---:|---:|---:|---:|---:|---:|---|
| advanced_packaging | DECLINE_OR_SHIFT | 30.0 | 5 | 1 | 4 | 0.417 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| hbm_ai_memory | MATURITY | 55.0 | 3 | 1 | 1 | 1.667 | 장기간 출원이 누적되고 최근 출원도 유지되어 성숙기 신호로 분류합니다. |
| fan_out_wlp | NO_DATA | 0.0 | 0 | 0 | 0 | None | 특허 출원 추세 데이터가 없습니다. |
| bump_rdl_interposer | DECLINE_OR_SHIFT | 30.0 | 30 | 3 | 10 | 0.5 | 과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다. |
| semiconductor_test | MATURITY | 55.0 | 4 | 1 | 2 | 0.833 | 장기간 출원이 누적되고 최근 출원도 유지되어 성숙기 신호로 분류합니다. |
| semiconductor_materials | GROWTH | 67.21 | 103 | 40 | 49 | 1.361 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |
| process_yield_quality | GROWTH | 81.33 | 103 | 31 | 25 | 2.067 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |
| power_thermal_efficiency | GROWTH | 72.8 | 194 | 62 | 63 | 1.64 | 최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다. |

## External Signals
- status: NOT_PROVIDED
- summary: 논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.
