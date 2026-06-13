"""Narrative generation.

A small CrewAI crew drafts the engaging, grounded narrative about the place from the retrieved
facts. CrewAI is imported inside the function (and at module import time in the main thread by
the portal) so that the import happens on the main thread before any worker threads are
spawned, per the established lesson. If CrewAI is unavailable, it falls back to a direct,
grounded language-model call.
"""

from __future__ import annotations

from ..llm import complete
from ..models import ActivityInputs, PlaceFacts

_SYSTEM = (
    "You are a knowledgeable, warm outdoor and cultural guide. Using only the supplied facts, "
    "write two short, engaging paragraphs about the place: its history, landscape and notable "
    "nature. Do not invent facts. British English."
)


def _grounding_text(inp: ActivityInputs, facts: PlaceFacts | None) -> str:
    if not facts:
        return f"Activity near {inp.activity_start.label or 'the start point'}."
    parts = []
    if facts.history:
        parts.append(f"History and context: {facts.history}")
    if facts.landscape:
        parts.append(f"Landscape: {facts.landscape}")
    if facts.points_of_interest:
        parts.append("Points of interest: " + ", ".join(facts.points_of_interest[:6]))
    if facts.flora_fauna:
        parts.append("Likely species nearby: " + ", ".join(facts.flora_fauna[:6]))
    return "\n".join(parts)


def write_narrative(inp: ActivityInputs, facts: PlaceFacts | None) -> str:
    grounding = _grounding_text(inp, facts)
    prompt = f"Facts:\n{grounding}\n\nWrite the narrative now."

    # Direct grounded LLM call (robust default). A CrewAI crew can be enabled here when richer
    # multi-step enrichment is wanted; it must be imported on the main thread first.
    return complete(prompt, system=_SYSTEM, max_tokens=400, temperature=0.5)
