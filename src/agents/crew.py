"""Narrative generation with language-aware prompting."""

from __future__ import annotations

from ..i18n import llm_lang_instruction
from ..llm import complete
from ..models import ActivityInputs, PlaceFacts

_SYSTEM_BASE = (
    "You are a knowledgeable, warm outdoor and cultural guide. Using only the supplied facts, "
    "write two short, engaging paragraphs about the place: its history, landscape and notable "
    "nature. Do not invent facts."
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


def write_narrative(
    inp: ActivityInputs, facts: PlaceFacts | None, lang: str = "en"
) -> str:
    grounding = _grounding_text(inp, facts)
    system = _SYSTEM_BASE + llm_lang_instruction(lang)
    prompt = f"Facts:\n{grounding}\n\nWrite the narrative now."
    return complete(prompt, system=system, max_tokens=400, temperature=0.5)
