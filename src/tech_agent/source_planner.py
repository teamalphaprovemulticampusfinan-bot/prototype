from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from openpyxl import load_workbook
except Exception:  # pragma: no cover
    load_workbook = None

from .config import DEFAULT_TEMPLATE_BASE_PATH, DEFAULT_TEMPLATE_PATH, OUTPUT_DIR
from .utils import clean_text, ensure_dir


@dataclass
class TechTemplateItem:
    category: str
    item_name: str
    axis: str
    major_source: str = ""
    middle_source: str = ""
    quantifiable: str = ""
    formula_rules: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "item_name": self.item_name,
            "axis": self.axis,
            "major_source": self.major_source,
            "middle_source": self.middle_source,
            "quantifiable": self.quantifiable,
            "formula_rules": self.formula_rules,
        }


AXIS_BY_CATEGORY = {
    "대표 기술": "기술성",
    "핵심 제품/서비스": "수익성 기여",
    "고객 구매 이유": "고객 채택도",
    "경쟁 우위 요소/대체가능성": "진입장벽",
    "경쟁 우위/대체가능성": "진입장벽",
    "활용 및 확장 산업": "확장성",
    "진입 부담/장벽": "양산성",
    "R&D 강도": "투자 지속성",
}

CATEGORY_ALIASES = {
    "경쟁 우위 요소/대체가능성": "경쟁 우위/대체가능성",
}

DEFAULT_ITEMS = {
    "대표 기술": ["핵심 기술 키워드", "적용 방식", "핵심 성능 요소"],
    "핵심 제품/서비스": ["제품명/서비스명", "적용 기술", "주요 고객군"],
    "고객 구매 이유": ["고객 효익", "경쟁 제품 대비 장점", "실제 적용 사례"],
    "경쟁 우위/대체가능성": ["등록 특허", "제조 노하우", "대체가능성"],
    "활용 및 확장 산업": ["활용 산업", "확장 가능 제품", "전방 시장"],
    "진입 부담/장벽": ["인증/승인", "양산 난이도", "전환 비용"],
    "R&D 강도": ["연구개발비", "개발 과제", "설비투자/인력"],
}


def _norm_category(category: Any) -> str:
    c = clean_text(category)
    return CATEGORY_ALIASES.get(c, c)


def _row_values(row: tuple[Any, ...]) -> list[str]:
    return [clean_text(v) for v in row]


def _find_header(rows: list[tuple[Any, ...]]) -> tuple[int, list[str]]:
    for idx, row in enumerate(rows[:20]):
        vals = _row_values(row)
        joined = " ".join(vals)
        if "대분류" in joined and "항목명" in joined:
            return idx, vals
    return 0, _row_values(rows[0]) if rows else []


def _idx(headers: list[str], candidates: list[str], default: int) -> int:
    for i, h in enumerate(headers):
        if any(c in h for c in candidates):
            return i
    return default


def _load_formula_rules(template_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    from .formula_rules import load_formula_rules

    by_cat: dict[str, list[dict[str, Any]]] = {}
    for rule in load_formula_rules(template_path):
        cat = _norm_category(rule.get("category")) or "공통"
        by_cat.setdefault(cat, []).append(rule)
    return by_cat


def _candidate_workbooks(template_path: str | Path, base_template_path: str | Path | None) -> list[Path]:
    out: list[Path] = []
    for p in [base_template_path, template_path]:
        if not p:
            continue
        pp = Path(p)
        if pp.exists() and pp not in out:
            out.append(pp)
    return out


def load_template_framework(
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
    base_template_path: str | Path | None = DEFAULT_TEMPLATE_BASE_PATH,
) -> dict[str, Any]:
    """Load only the Excel *framework*.

    This function intentionally does not use the company-specific example sheet values
    as evidence.  The workbook is used as a routing map: category -> major source ->
    middle source -> quantifiable metric -> item names.
    """

    formula_by_category = _load_formula_rules(template_path)
    sections: dict[str, dict[str, Any]] = {}

    if load_workbook is not None:
        for wb_path in _candidate_workbooks(template_path, base_template_path):
            try:
                wb = load_workbook(wb_path, data_only=True, read_only=True)
            except Exception:
                continue
            sheet_names = [s for s in wb.sheetnames if s in {"베이스", "Base", "base"}]
            sheet_names += [s for s in wb.sheetnames if s not in sheet_names and ("베이스" in s or "base" in s.lower())]
            for sname in sheet_names[:1]:
                ws = wb[sname]
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    continue
                header_i, headers = _find_header(rows)
                ci = _idx(headers, ["대분류", "category"], 1)
                maj_i = _idx(headers, ["대 출처", "대출처", "major"], 2)
                mid_i = _idx(headers, ["중 출처", "중출처", "middle", "sub"], 3)
                q_i = _idx(headers, ["정량화", "quant"], 4)
                item_i = _idx(headers, ["항목명", "item"], 5)

                current_category = ""
                current_major = ""
                current_middle = ""
                current_quant = ""
                for row in rows[header_i + 1 :]:
                    vals = _row_values(row)
                    if not any(vals):
                        continue
                    category = _norm_category(vals[ci] if ci < len(vals) else "") or current_category
                    major = vals[maj_i] if maj_i < len(vals) and vals[maj_i] else current_major
                    middle = vals[mid_i] if mid_i < len(vals) and vals[mid_i] else current_middle
                    quant = vals[q_i] if q_i < len(vals) and vals[q_i] else current_quant
                    item = vals[item_i] if item_i < len(vals) else ""
                    if not category:
                        continue
                    current_category, current_major, current_middle, current_quant = category, major, middle, quant
                    if category not in AXIS_BY_CATEGORY:
                        continue
                    sec = sections.setdefault(
                        category,
                        {
                            "category": category,
                            "axis": AXIS_BY_CATEGORY.get(category, "기술성"),
                            "major_source": major,
                            "middle_source": middle,
                            "quantifiable": quant,
                            "items": [],
                        },
                    )
                    if major and not sec.get("major_source"):
                        sec["major_source"] = major
                    if middle and not sec.get("middle_source"):
                        sec["middle_source"] = middle
                    if quant and not sec.get("quantifiable"):
                        sec["quantifiable"] = quant
                    if item:
                        sec["items"].append(
                            TechTemplateItem(
                                category=category,
                                item_name=item,
                                axis=AXIS_BY_CATEGORY.get(category, "기술성"),
                                major_source=major,
                                middle_source=middle,
                                quantifiable=quant,
                                formula_rules=formula_by_category.get(category, []),
                            ).as_dict()
                        )
                if sections:
                    break
            if sections:
                break

    # Fallback if the workbook cannot be opened.
    for category, items in DEFAULT_ITEMS.items():
        sec = sections.setdefault(
            category,
            {
                "category": category,
                "axis": AXIS_BY_CATEGORY.get(category, "기술성"),
                "major_source": "사업보고서, 공식 홈페이지, IR, 특허/공시",
                "middle_source": "사업의 내용, 제품/기술 소개, 연구개발, 매출 구성, 고객 적용 사례",
                "quantifiable": "키워드 빈도, 제품/공정 수, 매출/성장률, 특허/인증/고객 적용 건수",
                "items": [],
            },
        )
        existing = {x.get("item_name") for x in sec["items"]}
        for item in items:
            if item not in existing:
                sec["items"].append(
                    TechTemplateItem(
                        category=category,
                        item_name=item,
                        axis=AXIS_BY_CATEGORY.get(category, "기술성"),
                        major_source=sec.get("major_source", ""),
                        middle_source=sec.get("middle_source", ""),
                        quantifiable=sec.get("quantifiable", ""),
                        formula_rules=formula_by_category.get(category, []),
                    ).as_dict()
                )

    ordered_categories = [c for c in DEFAULT_ITEMS if c in sections]
    ordered = [sections[c] for c in ordered_categories]
    return {
        "template_path": str(template_path),
        "base_template_path": str(base_template_path) if base_template_path else "",
        "mode": "framework_only_no_company_example_values",
        "sections": ordered,
        "formula_rules_by_category": formula_by_category,
    }


def write_template_framework_catalog(
    company_dir: str,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
    base_template_path: str | Path | None = DEFAULT_TEMPLATE_BASE_PATH,
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, str]:
    framework = load_template_framework(template_path, base_template_path)
    out = ensure_dir(Path(output_dir))
    jp = out / f"{company_dir}_tech_template_framework.json"
    mp = out / f"{company_dir}_tech_template_framework.md"
    jp.write_text(json.dumps(framework, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Tech Template Framework Catalog",
        "",
        "- 사용 방식: 기업별 예시 시트의 내용을 근거로 복사하지 않고, 베이스/수식 시트의 대분류·대출처·중출처·정량화 규칙만 추출 설계로 사용합니다.",
        f"- template_path: {framework.get('template_path')}",
        f"- base_template_path: {framework.get('base_template_path')}",
    ]
    for sec in framework.get("sections", []):
        lines += [
            "",
            f"## {sec.get('category')} ({sec.get('axis')})",
            f"- 대 출처: {sec.get('major_source')}",
            f"- 중 출처: {sec.get('middle_source')}",
            f"- 정량화 가능 부분: {sec.get('quantifiable')}",
            "- 항목명: " + ", ".join(x.get("item_name", "") for x in sec.get("items", [])),
        ]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(jp), "md": str(mp)}
