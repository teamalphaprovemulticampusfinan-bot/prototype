from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValuationPaths:
    valuation_dir: str
    intake_dir: str
    workbook_xlsx: str
    metrics_json: str
    dashboard_payload_json: str
    validation_json: str
    report_md: str
    source_map_json: str


@dataclass
class ValuationContext:
    company_dir: str
    company: str
    financials: list[dict[str, Any]] = field(default_factory=list)
    raw_accounts: list[dict[str, Any]] = field(default_factory=list)
    price_history: list[dict[str, Any]] = field(default_factory=list)
    share_count: list[dict[str, Any]] = field(default_factory=list)
    peers: list[dict[str, Any]] = field(default_factory=list)
    reference_universe: list[dict[str, Any]] = field(default_factory=list)
    reference_focus: list[dict[str, Any]] = field(default_factory=list)
    reference_summary: dict[str, Any] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    price_summary: dict[str, Any] = field(default_factory=dict)
    market_snapshot: dict[str, Any] = field(default_factory=dict)
    template_catalog: list[dict[str, Any]] = field(default_factory=list)
    source_map: dict[str, Any] = field(default_factory=dict)
    intake_manifest: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValuationResult:
    company_dir: str
    company: str
    status: str
    metrics: dict[str, Any]
    dashboard_payload: dict[str, Any]
    validation: dict[str, Any]
    output_files: dict[str, str]
