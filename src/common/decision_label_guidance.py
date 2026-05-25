from __future__ import annotations

from typing import Final


_DEFAULT_CONTEXT: Final[str] = "Decision layer"


def build_decision_label_prompt_block(context_name: str = _DEFAULT_CONTEXT) -> str:
    """Build shared guidance for Korean Buy/Hold/Sell decision labels."""
    context = str(context_name or _DEFAULT_CONTEXT).strip() or _DEFAULT_CONTEXT
    return f"""
[Decision label guidance: {context}]
- Use exactly one of the serialized Korean labels when a decision label is required: 매수, 보유, 매도.
- Treat 매수 as a Buy-direction view supported by source-grounded upside, commercialization, valuation, momentum, or risk-adjusted posterior evidence.
- Treat 매도 as a Sell-direction view supported by source-grounded downside, overvaluation, deterioration, adverse events, or risk-adjusted posterior evidence.
- Treat 보유 as a reject/no-trade label, not as a vague neutral default. It is appropriate when direction is tied, source-limited, contradictory, unavailable, or too weak after risk and transaction-cost considerations.
- Do not invent fixed numeric thresholds for 매수/보유/매도 inside prompts. If code-produced posterior weights, label probabilities, or final recommendations are provided, preserve them and explain the evidence instead of recalculating them.
- If a 보유 label appears, state the explicit reject/no-trade reason. If no such reason exists, flag it as a mechanical Hold risk rather than hiding a clearer Buy or Sell direction.
""".strip()


__all__ = ["build_decision_label_prompt_block"]
