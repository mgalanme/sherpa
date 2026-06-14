"""LangGraph orchestration with a Human-in-the-Loop checkpoint.

Lessons applied: interrupt_before is used to pause at the review node, and a single
module-level MemorySaver is shared across invocations so that a paused workflow can be resumed
after the human decision. Node names never collide with state keys.

LangGraph msgpack registration: all Pydantic models used in the graph state are registered
via the environment variable so that MemorySaver can deserialise them cleanly without warnings,
and to be ready for when LANGGRAPH_STRICT_MSGPACK becomes the default.
"""

from __future__ import annotations

import operator
import os
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import nodes

# Register Pydantic models used in graph state before the checkpointer is created.
os.environ.setdefault(
    "LANGGRAPH_ALLOWED_MSGPACK_MODULES",
    "src.models,src.clients.transport",
)

_CHECKPOINTER = MemorySaver()


class PlanState(TypedDict, total=False):
    plan_id: str
    inputs: Any
    route: Any
    weather: Any
    access_notes: Annotated[list, operator.add]
    place_facts: Any
    recommendation: Any
    transport_options: Any
    dossier: Any


def _hitl_gate(state: PlanState) -> PlanState:
    return {}


def build_graph():
    g = StateGraph(PlanState)
    g.add_node("run_route", nodes.run_route)
    g.add_node("run_weather", nodes.run_weather)
    g.add_node("run_access", nodes.run_access)
    g.add_node("run_culture", nodes.run_culture)
    g.add_node("run_transport", nodes.run_transport)
    g.add_node("run_recommend", nodes.run_recommend)
    g.add_node("run_compose", nodes.run_compose)
    g.add_node("hitl_review", _hitl_gate)

    g.add_edge(START, "run_route")
    g.add_edge(START, "run_weather")
    g.add_edge(START, "run_access")
    g.add_edge(START, "run_culture")
    g.add_edge(START, "run_transport")
    g.add_edge("run_route", "run_recommend")
    g.add_edge("run_weather", "run_recommend")
    g.add_edge("run_recommend", "run_compose")
    g.add_edge("run_access", "run_compose")
    g.add_edge("run_culture", "run_compose")
    g.add_edge("run_transport", "run_compose")
    g.add_edge("run_compose", "hitl_review")
    g.add_edge("hitl_review", END)

    return g.compile(checkpointer=_CHECKPOINTER, interrupt_before=["hitl_review"])


def run_until_review(plan_id: str, inputs: Any) -> dict:
    graph = build_graph()
    config = {"configurable": {"thread_id": plan_id}}
    graph.invoke({"plan_id": plan_id, "inputs": inputs}, config=config)
    return graph.get_state(config).values


def resume_after_review(plan_id: str) -> dict:
    graph = build_graph()
    config = {"configurable": {"thread_id": plan_id}}
    graph.invoke(None, config=config)
    return graph.get_state(config).values
