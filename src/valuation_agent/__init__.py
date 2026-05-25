"""Independent Valuation Agent for AlphaProve.

This sidecar agent is intentionally separated from finance_agent.  It uses only
its own valuation intake artifacts under data/<field>/<company>/valuation/intake.
"""

from .runner import main, run_valuation

__all__ = ["main", "run_valuation"]
