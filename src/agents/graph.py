"""LangGraph orchestration with a Human-in-the-Loop checkpoint.

Lessons applied: interrupt_before is used to pause at the review node, and a single
module-level MemorySaver is shared across invocations so that a paused workflow can be resumed
after the human decision. Node names never collide with state keys.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import nodes

# A single, module-level checkpointer shared by all invocations (not created per call).
_CHECKPOINTER = MemorySaver()


class PlanState(TypedDict, total=False):
    plan_id: str
    inputs: Any
    route: Any
    weather: Any
    access_notes: Annotated[list, operator.add]
    place_facts: Any
    recommendation: Any
    dossier: Any


def _hitl_gate(state: PlanState) -> PlanState:
    # The graph interrupts before this node; on resume it simply passes the state through.
    return {}


def build_graph():
    g = StateGraph(PlanState)
    g.add_node("run_route", nodes.run_route)
    g.add_node("run_weather", nodes.run_weather)
    g.add_node("run_access", nodes.run_access)
    g.add_node("run_culture", nodes.run_culture)
    g.add_node("run_recommend", nodes.run_recommend)
    g.add_node("run_compose", nodes.run_compose)
    g.add_node("hitl_review", _hitl_gate)

    # Gather independent data first, then recommend, compose and review.
    g.add_edge(START, "run_route")
    g.add_edge(START, "run_weather")
    g.add_edge(START, "run_access")
    g.add_edge(START, "run_culture")
    g.add_edge("run_route", "run_recommend")
    g.add_edge("run_weather", "run_recommend")
    g.add_edge("run_recommend", "run_compose")
    g.add_edge("run_access", "run_compose")
    g.add_edge("run_culture", "run_compose")
    g.add_edge("run_compose", "hitl_review")
    g.add_edge("hitl_review", END)

    # Interrupt before the review node so a human approves or modifies the draft.
    return g.compile(checkpointer=_CHECKPOINTER, interrupt_before=["hitl_review"])


def run_until_review(plan_id: str, inputs: Any) -> dict:
    """Run the workflow up to the HITL checkpoint and return the draft state."""
    graph = build_graph()
    config = {"configurable": {"thread_id": plan_id}}
    graph.invoke({"plan_id": plan_id, "inputs": inputs}, config=config)
    return graph.get_state(config).values


def resume_after_review(plan_id: str) -> dict:
    """Resume the workflow after the human decision (used when continuing past the gate)."""
    graph = build_graph()
    config = {"configurable": {"thread_id": plan_id}}
    graph.invoke(None, config=config)
    return graph.get_state(config).values
