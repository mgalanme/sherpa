"""Agent node functions. Each node enriches the shared state and publishes a mesh event.

Node names are kept distinct from state keys to avoid the LangGraph node/state-key collision
lesson (for example, the recommendation node is named run_recommend, not recommendation).
"""

from __future__ import annotations

import traceback
from typing import Any

from .. import mesh
from ..clients import culture, geo, nature, route, weather
from ..clients.transport import get_transport_options
from ..models import (
    ActivityInputs,
    Dossier,
    EquipmentChecklist,
    Recommendation,
)
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
    protected = nature.nature_areas(inp.activity_start)
    if protected:
        existing = set(facts.points_of_interest)
        facts.points_of_interest += [p for p in protected if p not in existing]
    _emit(
        state,
        "culture",
        {"pois": len(facts.points_of_interest), "species": len(facts.flora_fauna)},
    )
    return {"place_facts": facts}


def run_transport(state: dict[str, Any]) -> dict[str, Any]:
    """Compute transport options from departure origin to activity start."""
    try:
        inp: ActivityInputs = state["inputs"]
        if inp.departure_origin.lat == 0.0 and inp.departure_origin.lon == 0.0:
            return {"transport_options": []}
        options = get_transport_options(inp.departure_origin, inp.activity_start)
        _emit(state, "transport", {"modes": [o.mode for o in options]})
        return {"transport_options": options}
    except Exception as exc:
        _emit(state, "transport_error", {"error": str(exc)})
        return {"transport_options": []}


def run_recommend(state: dict[str, Any]) -> dict[str, Any]:
    """Run the classical recommendation engine. If it fails, return a safe fallback."""
    try:
        inp: ActivityInputs = state["inputs"]
        route_info = state.get("route")
        weather_panel = state.get("weather")
        if route_info is None or weather_panel is None:
            _emit(state, "recommend_warning", {"reason": "Missing route or weather"})
            rec = Recommendation(
                checklist=EquipmentChecklist(
                    personal=[], activity_specific=[], nutrition_hydration=[]
                ),
                risk_flags=[],
                rationale=[
                    "Recommendation skipped because route or weather data was missing."
                ],
            )
        else:
            rec = recommend(inp, route_info, weather_panel)
    except Exception as e:
        _emit(
            state, "recommend_error", {"error": str(e), "trace": traceback.format_exc()}
        )
        rec = Recommendation(
            checklist=EquipmentChecklist(
                personal=[], activity_specific=[], nutrition_hydration=[]
            ),
            risk_flags=[],
            rationale=[
                f"Recommendation engine failed: {str(e)}. Please review manually."
            ],
        )
    _emit(state, "recommend", {"flags": len(rec.risk_flags)})
    return {"recommendation": rec}


def run_compose(state: dict[str, Any]) -> dict[str, Any]:
    """Compose the draft dossier and draft the narrative with the language model (grounded)."""
    from .crew import write_narrative

    inp: ActivityInputs = state["inputs"]
    facts = state.get("place_facts")
    narrative = write_narrative(inp, facts)

    recommendation = state.get("recommendation")
    if recommendation is None:
        recommendation = Recommendation(
            checklist=EquipmentChecklist(
                personal=[], activity_specific=[], nutrition_hydration=[]
            ),
            risk_flags=[],
            rationale=[
                "Recommendation was not produced. Check the graph definition or logs."
            ],
        )
        _emit(
            state,
            "compose_warning",
            {"reason": "Missing recommendation, using fallback"},
        )

    dossier = Dossier(
        plan_id=state["plan_id"],
        inputs=inp,
        route=state.get("route"),
        weather=state.get("weather"),
        access_notes=state.get("access_notes", []),
        place_facts=facts,
        recommendation=recommendation,
        narrative=narrative,
        status="draft",
    )
    _emit(state, "compose", {"status": "draft"})
    return {"dossier": dossier}
