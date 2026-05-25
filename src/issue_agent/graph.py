from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes import run_collect_node, run_generate_node
from .state import IssueAgentState


def build_issue_graph():
    workflow = StateGraph(IssueAgentState)

    workflow.add_node("collect", run_collect_node)
    workflow.add_node("generate", run_generate_node)

    workflow.set_entry_point("collect")
    workflow.add_edge("collect", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()