from __future__ import annotations

from typing import Final

from common.decision_label_guidance import build_decision_label_prompt_block

# AlphaProve DMA / reject-option prompt guidance.
# This file contains prompt text only. It must not introduce agent weights or
# Buy/Hold/Sell numeric decision thresholds.
# The serialized Korean labels are intentionally preserved because downstream
# evaluation code maps recommendations with the labels: 매수, 보유, 매도.

DECISION_LABEL_PROMPT_BLOCK: Final[str] = build_decision_label_prompt_block("Auditor and Chair shared decision layer")

DMA_NON_INTERFERENCE_POLICY: Final[str] = """
[DMA non-interference and reject/no-trade interpretation policy]
- Do not recalculate DMA posterior weights, posterior probabilities, or final_recommendation inside the prompt.
- Do not create fixed Buy/Hold/Sell thresholds such as weighted_signal > X or weighted_signal < X.
- Do not propose new agent weights in the prompt. When agent outputs are available, the code should rely on DMA posterior weights; when no realized-history performance exists, use the code-level prior only.
- HOLD DISCIPLINE: Treat Hold (보유) only as a genuine reject/no-trade option, NOT as a neutral default. It is justified ONLY when: (1) buy/sell posterior probabilities are tied (within 0.15), (2) direction-critical data is missing, (3) conflicting high-confidence signals exist, or (4) risk/reward edge is too small after transaction costs.
- HOLD SUPPRESSION RULE: If DMA-weighted agent signals show a 2/3+ consensus direction (both Buy and Sell), DO NOT apply Hold even if individual agents are uncertain. Preserve the consensus direction and document the minority/risk view separately.
- For Buy/Sell, explain the larger directional posterior and the agent evidence that produced it. If Hold is proposed, EXPLICITLY document its reason: (a) tied posterior, (b) missing data location, (c) conflicting evidence detail, (d) insufficient edge. Generic "mixed evidence" is NOT a valid reason.
- If Hold appears and has no explicit reason from categories (a)-(d), REJECT it as mechanical/over-conservative. Instead, preserve the directional posterior for the Chair.
- If the DMA posterior and the Chair/Auditor final view differ, separate the cause explicitly: missing data, delayed source availability, stale agent signal, posterior tie, or explicit risk-control logic.
- Transaction costs and uncertainty exist; however, mechanical Holds created by fixed thresholds, over-caution, or "we want safety" are NOT allowed. Deeptech is inherently uncertain; do not use Hold to hide that. Instead, clearly state which specific risk makes the edge too small.
"""

AGENT_RELATION_GUIDE: Final[str] = """
[How to interpret relationships among agents]
- Finance: current operating strength, cash-flow quality, and balance-sheet resilience. If short-term distress is strong, it should challenge the long-term Tech/Valuation thesis.
- Valuation: price attractiveness versus intrinsic value, peer multiples, and reverse DCF. If Finance is weak but Valuation looks attractive, verify whether the weakness is already priced in.
- Tech: patent quality, customer adoption, manufacturability, and the path to revenue and FCF. For deeptech firms this can explain long-term upside, but it should not be used as a standalone Buy reason without commercialization evidence.
- Market: price, trading value, relative strength, and trend. This is the timing/positioning layer that checks whether the fundamental thesis is already reflected in the stock price.
- Issue: disclosures, news, orders, regulation, litigation, and event risk. Current-month issues can affect short-term prices, and prior-month issues can have delayed effects; use history features for lag structure, not label thresholds.
- Macro: rates, FX, cycle, and liquidity. This adjusts discount-rate and risk-appetite context for growth/deeptech names and should usually refine Finance/Valuation/Market interpretation rather than flip the label alone.
"""

FEWSHOT_NARRATIVE_EXAMPLES: Final[str] = """
[Few-shot examples: DMA posterior plus reject/no-trade]

Example 1. Buy-direction posterior dominance
- Situation: Valuation and Tech posteriors lean Buy. Finance is weak because of near-term losses. Market is neutral and Macro is mildly adverse.
- Wrong interpretation: "Finance is weak, therefore Hold."
- Correct interpretation: "Do not create an arbitrary Hold band. If the combined posterior supports Buy more than Sell, keep the Buy label while separating weak Finance as the key risk. The next checks are commercialization, revenue conversion, and cash-flow improvement."

Example 2. True Hold as reject/no-trade
- Situation: Buy posterior and Sell posterior are nearly tied. Core agents disagree. Valuation looks cheap, but Finance liquidity has deteriorated and Issue has a negative event.
- Correct interpretation: "Here Hold is a reject/no-trade decision, not a neutral default. Direction is not identified, so additional source verification is more important than opening a new Buy/Sell position."

Example 3. Sell-direction posterior dominance
- Situation: Finance cash flow worsens, Valuation indicates overpricing, Market is weak, and Issue has a negative event. Tech has long-term potential but weak commercialization evidence.
- Wrong interpretation: "Because it is deeptech, keep Hold."
- Correct interpretation: "Preserve Tech potential as a risk note, but the current posterior is Sell-dominant. Hold is reserved for directional ties, not for avoiding an uncomfortable Sell."
"""


def build_dma_prompt_prefix() -> str:
    return "\n\n".join([
        DECISION_LABEL_PROMPT_BLOCK,
        DMA_NON_INTERFERENCE_POLICY,
        AGENT_RELATION_GUIDE,
        FEWSHOT_NARRATIVE_EXAMPLES,
    ])


def build_quantity_auditor_prompt(task_prompt: str) -> str:
    return build_dma_prompt_prefix() + "\n\n[Object to verify]\n" + str(task_prompt or "")


def get_quantity_prompt_context() -> dict[str, str]:
    return {
        "decision_label_prompt_block": DECISION_LABEL_PROMPT_BLOCK,
        "dma_non_interference_policy": DMA_NON_INTERFERENCE_POLICY,
        "agent_relation_guide": AGENT_RELATION_GUIDE,
        "fewshot_narrative_examples": FEWSHOT_NARRATIVE_EXAMPLES,
    }


AUDITOR_PROMPT_INSERT: Final[str] = build_dma_prompt_prefix()
CHAIR_PROMPT_INSERT: Final[str] = build_dma_prompt_prefix()

__all__ = [
    "DECISION_LABEL_PROMPT_BLOCK",
    "DMA_NON_INTERFERENCE_POLICY",
    "AGENT_RELATION_GUIDE",
    "FEWSHOT_NARRATIVE_EXAMPLES",
    "AUDITOR_PROMPT_INSERT",
    "CHAIR_PROMPT_INSERT",
    "build_dma_prompt_prefix",
    "build_quantity_auditor_prompt",
    "get_quantity_prompt_context",
]
