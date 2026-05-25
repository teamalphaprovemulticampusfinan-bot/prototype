import re
from html import escape
from pathlib import Path

import streamlit as st

from dashboard.state import get_chair_report_dir


def _resolve_report_path(chair_dir: Path) -> Path | None:
    report_files = sorted(
        chair_dir.glob("*_chair_report.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return report_files[0] if report_files else None


@st.cache_data(show_spinner=False)
def _load_report_text(report_path: str, modified_time: float) -> str:
    _ = modified_time
    return Path(report_path).read_text(encoding="utf-8")


def _inline_markdown(text: str) -> str:
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def _markdown_to_report_html(markdown: str) -> str:
    html: list[str] = []
    in_list: str | None = None
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html.append(f"</{in_list}>")
            in_list = None

    def open_list(kind: str) -> None:
        nonlocal in_list
        if in_list != kind:
            close_list()
            html.append(f'<{kind} class="chair-report-list">')
            in_list = kind

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                html.append(
                    "<pre><code>"
                    + escape("\n".join(code_lines))
                    + "</code></pre>"
                )
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            close_list()
            continue

        if re.fullmatch(r"-{3,}", stripped):
            close_list()
            html.append("<hr>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            close_list()
            level = min(len(heading.group(1)) + 1, 6)
            html.append(
                f"<h{level}>{_inline_markdown(heading.group(2))}</h{level}>"
            )
            continue

        ordered = re.match(r"^(\s*)\d+\.\s+(.+)$", line)
        unordered = re.match(r"^(\s*)[-*]\s+(.+)$", line)
        if ordered or unordered:
            match = ordered or unordered
            kind = "ol" if ordered else "ul"
            indent = len(match.group(1))
            margin = min(indent * 10, 44)
            open_list(kind)
            html.append(
                f'<li style="margin-left:{margin}px;">'
                f"{_inline_markdown(match.group(2))}</li>"
            )
            continue

        close_list()
        html.append(f"<p>{_inline_markdown(stripped)}</p>")

    close_list()
    if in_code:
        html.append("<pre><code>" + escape("\n".join(code_lines)) + "</code></pre>")

    return "\n".join(html)


def render_chair_report() -> None:
    selected_sector = st.session_state.get("selected_sector")
    company_name = st.session_state.get("company_name")
    sector_label = escape(selected_sector or "")
    company_label = escape(company_name or "")
    chair_dir = get_chair_report_dir()

    if chair_dir is None or not selected_sector or not company_name:
        st.markdown(
            f"""
            <main class="main-shell">
                <div class="selection-row">
                    <span class="selection-pill">{sector_label or "분야 미선택"}</span>
                </div>
                <h1 class="page-title">Chair 보고서</h1>
                <p class="page-copy">기업을 선택하면 Chair Agent 최종 보고서가 표시됩니다.</p>
            </main>
            """,
            unsafe_allow_html=True,
        )
        return

    report_path = _resolve_report_path(chair_dir)

    if report_path is None:
        st.markdown(
            f"""
            <main class="main-shell">
                <div class="chair-report-header">
                    <div>
                        <h1 class="page-title">{company_label}</h1>
                        <p class="page-copy">Chair Agent 최종 보고서</p>
                    </div>
                    <div class="selection-row chair-report-pills">
                        <span class="selection-pill">{sector_label}</span>
                        <span class="selection-pill">{company_label}</span>
                    </div>
                </div>
                <div class="chair-report-empty">Chair 보고서 파일을 찾을 수 없습니다.</div>
            </main>
            """,
            unsafe_allow_html=True,
        )
        return

    report_text = _load_report_text(str(report_path), report_path.stat().st_mtime)
    report_html = _markdown_to_report_html(report_text)
    st.markdown(
        f"""
        <main class="main-shell">
            <div class="chair-report-header">
                <div>
                    <h1 class="page-title">{company_label}</h1>
                    <p class="page-copy">Chair Agent 최종 보고서</p>
                </div>
                <div class="selection-row chair-report-pills">
                    <span class="selection-pill">{sector_label}</span>
                    <span class="selection-pill">{company_label}</span>
                </div>
            </div>
            <section class="chair-report-body">{report_html}</section>
        </main>
        """,
        unsafe_allow_html=True,
    )
