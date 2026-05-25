import json
from typing import Dict, Any, List

def build_prompt(company_name: str, finance_result: List[Dict[str, Any]], stock_result: Dict[str, Any], warning_info: Dict[str, Any]) -> str:
    return f"""
  너는 딥테크 기업 분석 에이전트다.

  아래는 사람이 중요하다고 판단해 정제한 재무 및 주가 데이터다.
  주어진 데이터만 바탕으로 기업에 대한 투자 의견서를 작성해라.
  딥테크 기업 특성상 일반 기업과 다른 해석이 필요할 수 있으므로,
  성장성, 수익성, 변동성, 리스크를 함께 고려해라.

  [기업명]
  {company_name}

  [재무 데이터: 2023~2025]
  {json.dumps(finance_result, ensure_ascii=False, indent=2)}

  [주가 데이터: 최근 1개월 일별 원 데이터]
  {json.dumps(stock_result.get("recent_1m", []), ensure_ascii=False, indent=2)}

  [주가 데이터: 연도별 요약 통계 (2023~)]
  {json.dumps(stock_result.get("yearly_summary", []), ensure_ascii=False, indent=2)}

  [주가 데이터: 연도별 수익률 및 MDD]
  {json.dumps(stock_result.get("annual_metrics", []), ensure_ascii=False, indent=2)}

  [투자경고 체크]
  {json.dumps(warning_info, ensure_ascii=False, indent=2)}

  [작성 규칙]
  1. 최종 출력은 json만 출력한다.
  2. warning_info.warning이 true이면 warning_note에 주의문을 반드시 반영한다.
  3. 데이터에 없는 사실은 추정하지 말고, 불확실하면 그 점을 명시한다.
  4. key_thesis와 key_risks에는 제공 데이터에서 직접 확인 가능한 핵심 수치와 판단 이유를 포함한다.
  5. summary는 기관 리포트 스타일의 중립적 문체로 작성한다.
  6. summary는 4문장 이하로 제한한다.
  7. 문장이 너무 길어지면 두 문장으로 나누지 말고 간결하게 유지한다.
  8. "흑자전환 직행", "선반영", "확실", "반드시", "급등", "폭발", "강력 추천", "매수 추천" 등 단정적이거나 과장된 표현은 사용하지 않는다.
  9. 인과관계 추론을 최소화하고, 반드시 제공된 데이터에서 직접 확인 가능한 관계만 언급한다.
  10. 결론이 약하거나 데이터가 명확하지 않을 때는 "현재 데이터로는 ... 보인다", "추가 확인이 필요하다", "확정하기 어렵다" 등 보수적 표현을 사용한다.
  11. 투자 유튜버식 문체, 감탄사, 구어체, 흥미 유도형 표현을 사용하지 않는다.

  [필수 분석 지표 및 컬럼 매핑]
  아래 지표는 반드시 summary, key_thesis 또는 key_risks에 반영한다.
  데이터 컬럼은 영어일 수 있으므로 아래 매핑을 참고하여 해석한다.

  - 매출성장률: sales_growth
  - 영업이익률: operating_margin
  - ROE: roe
  - FCF: fcf
  - 부채비율: debt_ratio
  - 연수익률: annual_metrics.annual_return_%
  - 연간 MDD: annual_metrics.annual_mdd_%
  - 거래량: volume
  - 이동평균 대비 비율: ma20_ratio
  - 변동성지수: vkospi

  필수 지표 외 추가 지표는 최대 3개까지만 허용한다.

  [필수 지표 처리 규칙]
  1. 위 필수 지표는 summary, key_thesis, key_risks 중 적절한 위치에 반영한다.
  2. 데이터로 계산할 수 없는 지표는 억지로 포함하지 말고, 필요하면 key_risks에 확인 필요 항목으로만 적는다.

  [추가 지표 규칙]
  1. 위 필수 지표 외에도 LLM이 중요하다고 판단하는 지표는 추가 가능하다.
  2. 단, 반드시 주어진 데이터에서 계산 또는 확인 가능한 경우만 포함한다.
  3. 추정 기반 지표는 금지한다.

  [추가 데이터 요청 옵션]
  현재 최근 1개월 일별 원 데이터, 연도별 요약, annual_metrics가 제공되었다.
  만약 분석 도중 특정 기간의 일별 원 데이터가 반드시 필요하다고 판단되면,
  최종 보고서 대신 아래 형식의 JSON을 출력하여 추가 데이터를 요청할 수 있다.

  {{"request_more_data": true, "reason": "요청 사유", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}}

  [추가 데이터 요청 시 주의사항 — 반드시 준수]
  1. 단순히 데이터가 많으면 좋겠다는 이유로 추가 요청하지 않는다.
  2. 최근 3개월 데이터와 연도별 요약, annual_metrics만으로 판단 가능한 경우 추가 요청하지 않는다.
  3. 추가 요청은 명확한 분석적 근거가 있을 때만 허용된다.
     예: 특정 이벤트 전후 가격 패턴 확인, 급등/급락 구간의 세부 분석 등.
  4. 요청 기간은 최대 1년으로 제한한다.
  5. 가능한 한 추가 요청 없이 분석을 완료하는 것을 우선으로 한다.
  """


def build_extended_prompt(original_prompt: str, extended_data: list, start_date: str, end_date: str) -> str:
    """에이전트가 요청한 추가 원 데이터를 포함하여 2차 프롬프트를 생성합니다."""
    return f"""{original_prompt}

  [추가 제공된 일별 원 데이터: {start_date} ~ {end_date}]
  {json.dumps(extended_data, ensure_ascii=False, indent=2)}

  위 추가 데이터를 포함하여 최종 분석 보고서를 JSON으로 출력하라.
  더 이상 추가 데이터를 요청하지 말고, 반드시 최종 보고서를 출력하라.
  """
