from __future__ import annotations


def build_issue_prompt(
    company_name: str,
    company_context: str,
    news_context: str,
) -> str:
    return f"""
당신은 딥테크 기업 이슈 분석 에이전트다.

아래 내부 키워드, 뉴스, RSS 문맥만 바탕으로 투자 관점의 이슈 의견서를 작성해라.
데이터에 없는 사실은 추정하지 말고, 공개 근거가 약하면 그 한계를 명시해라.

[기업명]
{company_name}

[기업 관련 내부 키워드/문맥]
{company_context}

[최근 뉴스 및 RSS 문맥]
{news_context}

[작성 규칙]
1. 첫 줄은 반드시 `opinion: 매수` 또는 `opinion: 보유` 또는 `opinion: 매도` 중 하나로 작성한다.
2. 매수: 확인 가능한 긍정 이슈가 부정 이슈보다 명확하고, 단기/중기 모멘텀 근거가 있을 때만 선택한다.
3. 보유: 긍정/부정이 혼재하거나, 뉴스·RSS 근거가 부족해 방향성을 단정하기 어려울 때 선택한다.
4. 매도: 확인 가능한 악재, 규제, 소송, 수요 둔화, 실적 훼손, 자금조달 리스크가 우세할 때 선택한다.
5. 근거는 긍정/부정으로 나누고, 데이터에 없는 내용은 절대 쓰지 않는다.
6. 뉴스 0건, RSS 수집 건수 같은 수집 상태값만으로 매수/매도를 단정하지 않는다.

[출력 형식]
opinion: 매수|보유|매도
confidence: 0.00~1.00

1. 핵심 이슈 요약
2. 기업에 미치는 영향
3. 긍정 시그널
4. 부정 시그널/리스크
5. 향후 체크포인트
""".strip()


def build_issue_markdown(
    company_name: str,
    analysis_text: str,
    related_rows: list[dict] | None = None,
) -> str:
    lines = [f"# {company_name} 이슈 리포트", ""]

    if related_rows:
        lines.append("## 내부 연관 키워드")
        for row in related_rows[:10]:
            keyword = row.get("키워드") or row.get("keyword") or ""
            category = row.get("카테고리") or row.get("category") or ""
            if keyword or category:
                lines.append(f"- {keyword} ({category})" if category else f"- {keyword}")
        lines.append("")

    lines.append("## 분석 결과")
    lines.append(analysis_text.strip())
    lines.append("")

    return "\n".join(lines)