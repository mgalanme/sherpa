"""Agent node functions. Each node enriches the shared state and publishes a mesh event.

Node names are kept distinct from state keys to avoid the LangGraph node/state-key collision
lesson (for example, the recommendation node is named run_recommend, not recommendation).
"""

from __future__ import annotations

from typing import Any

from .. import mesh
from ..clients import culture, geo, nature, route, weather
from ..models import ActivityInputs, Dossier
from ..recommend import recommend


def _emit(state: dict, stage: str, info: dict) -> None:
    mesh.publish_event(state.get("plan_id", "unknown"), stage, info)


def run_route(state: dict[str, Any]) -> dict[str, Any]:
    inp: ActivityInputs = state["inputs"]
    info = route.resolve_route(
        inp.activity_type, inp.activity_start, inp.activity_end, inp.gpx_path
    )
    info.meeting_points = [
        "Parking or transport stop near the start",
        inp.activity_start.label or "Start point",
    ]
    _emit(state, "route", {"distance_km": info.distance_km, "source": info.source})
    return {"route": info}


def run_weather(state: dict[str, Any]) -> dict[str, Any]:
    inp: ActivityInputs = state["inputs"]
    panel = weather.get_weather(inp.activity_start, inp.activity_date)
    _emit(state, "weather", {"source": panel.source, "is_forecast": panel.is_forecast})
    return {"weather": panel}


def run_access(state: dict[str, Any]) -> dict[str, Any]:
    inp: ActivityInputs = state["inputs"]
    notes = geo.access_notes(inp.activity_start)
    _emit(state, "access", {"count": len(notes)})
    return {"access_notes": notes}


def run_culture(state: dict[str, Any]) -> dict[str, Any]:
    inp: ActivityInputs = state["inputs"]
    facts = culture.place_facts(inp.activity_start)
    facts.flora_fauna = nature.likely_species(inp.activity_start)
    _emit(
        state,
        "culture",
        {"pois": len(facts.points_of_interest), "species": len(facts.flora_fauna)},
    )
    return {"place_facts": facts}


def run_recommend(state: dict[str, Any]) -> dict[str, Any]:
    inp: ActivityInputs = state["inputs"]
    rec = recommend(inp, state["route"], state["weather"])
    _emit(state, "recommend", {"flags": len(rec.risk_flags)})
    return {"recommendation": rec}


def run_compose(state: dict[str, Any]) -> dict[str, Any]:
    """Compose the draft dossier and draft the narrative with the language model (grounded)."""
    from .crew import write_narrative

    inp: ActivityInputs = state["inputs"]
    facts = state.get("place_facts")
    narrative = write_narrative(inp, facts)
    dossier = Dossier(
        plan_id=state["plan_id"],
        inputs=inp,
        route=state["route"],
        weather=state["weather"],
        access_notes=state.get("access_notes", []),
        place_facts=facts,
        recommendation=state["recommendation"],
        narrative=narrative,
        status="draft",
    )
    _emit(state, "compose", {"status": "draft"})
    return {"dossier": dossier}
