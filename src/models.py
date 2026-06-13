"""Domain models for SHERPA (Pydantic v2).

These models are the shared contract between the agents, the stores and the portal.
"""

from __future__ import annotations

from datetime import date, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    CYCLING_ROAD = "cycling_road"
    CYCLING_GRAVEL = "cycling_gravel"
    CYCLING_MTB = "cycling_mtb"
    HIKING = "hiking"
    TRAIL_RUNNING = "trail_running"
    TENNIS = "tennis"
    PADEL = "padel"
    CLIMBING = "climbing"
    KAYAKING = "kayaking"
    CULTURAL = "cultural"


class GeoPoint(BaseModel):
    lat: float
    lon: float
    label: str = ""


class ActivityInputs(BaseModel):
    """The inputs captured from the user, by conversation or template."""

    activity_type: ActivityType
    departure_origin: GeoPoint  # the home address, geocoded
    activity_start: GeoPoint  # start of the GPX track
    activity_end: GeoPoint  # end of the GPX track
    activity_date: date
    start_time: time
    end_time: time
    other_characteristics: str = ""  # free-text nuance
    gpx_path: Optional[str] = None  # user-supplied GPX file, if any


class RouteInfo(BaseModel):
    distance_km: float = 0.0
    ascent_m: float = 0.0
    descent_m: float = 0.0
    is_loop: bool = False
    source: str = ""  # user_gpx | openrouteservice
    track_points: int = 0
    meeting_points: list[str] = Field(default_factory=list)


class WeatherPanel(BaseModel):
    summary: str = ""
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    wind_kmh: Optional[float] = None
    gust_kmh: Optional[float] = None
    rain_prob_pct: Optional[float] = None
    snow: bool = False
    uv_index: Optional[float] = None
    is_forecast: bool = True  # False when a climatological baseline is used
    warnings: list[str] = Field(default_factory=list)
    source: str = ""  # aemet | open-meteo


class AccessNote(BaseModel):
    note: str
    certainty: str = "uncertain"  # confirmed | likely | uncertain
    source: str = ""


class PlaceFacts(BaseModel):
    history: str = ""
    landscape: str = ""
    points_of_interest: list[str] = Field(default_factory=list)
    flora_fauna: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


class RiskFlag(BaseModel):
    level: str  # info | caution | warning
    message: str


class EquipmentChecklist(BaseModel):
    personal: list[str] = Field(default_factory=list)
    activity_specific: list[str] = Field(default_factory=list)
    nutrition_hydration: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    checklist: EquipmentChecklist
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class Dossier(BaseModel):
    plan_id: str
    inputs: ActivityInputs
    route: RouteInfo = Field(default_factory=RouteInfo)
    weather: WeatherPanel = Field(default_factory=WeatherPanel)
    access_notes: list[AccessNote] = Field(default_factory=list)
    place_facts: PlaceFacts = Field(default_factory=PlaceFacts)
    recommendation: Recommendation = Field(
        default_factory=lambda: Recommendation(checklist=EquipmentChecklist())
    )
    narrative: str = ""
    status: str = "draft"  # draft | approved | rejected
    pdf_path: Optional[str] = None


class HitlDecision(str, Enum):
    APPROVE = "approve"
    MODIFY = "modify"
    REGENERATE_SECTION = "regenerate_section"
    SAVE_DRAFT = "save_draft"
    REJECT = "reject"
    ACKNOWLEDGE = "acknowledge"
    SHARE = "share"
    SCHEDULE_REMINDER = "schedule_reminder"
