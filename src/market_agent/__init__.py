"""Market agent package.

This package is imported by both the operational Market Agent and the
market evaluation/intake builders.  The evaluation builder needs the light
``market_agent.history_market_features`` helper module, but importing
``market_agent.runner`` at package import time can pull in the full runtime
agent stack and fail when only intake utilities are being executed.

To keep both paths working, runtime entry points are loaded lazily.
"""
from __future__ import annotations

from typing import Any

__all__ = ["run_market_report", "run_market_reports"]


def __getattr__(name: str) -> Any:
    if name in {"run_market_report", "run_market_reports"}:
        from .runner import run_market_report, run_market_reports

        return {"run_market_report": run_market_report, "run_market_reports": run_market_reports}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
