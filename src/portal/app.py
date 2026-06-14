"""SHERPA Streamlit portal v2.

Improvements over v1:
- Language selector (10 EU languages, all UI strings translated)
- GPX auto-fill of Activity start/end points from the track endpoints
- GPX route summary (distance, ascent, loop) shown immediately on upload
- "How to get there" section: car, public transport, and other options
- All open-data sources active: AEMET + Open-Meteo, Wikidata, iNaturalist,
  OSM protected areas, OSRM, ORS
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src import audit, mesh  # noqa: E402
from src.agents import graph  # noqa: E402
from src.catalog import ACTIVITY_LABELS  # noqa: E402
from src.clients.route import parse_gpx  # noqa: E402
from src.clients.transport import TransportOption  # noqa: E402
from src.config import get_settings, load_streamlit_secrets  # noqa: E402
from src.dossier import render_pdf  # noqa: E402
from src.i18n import LANGUAGES, t  # noqa: E402
from src.intake import build_inputs, geocode, parse_freetext  # noqa: E402
from src.models import ActivityInputs, ActivityType, HitlDecision  # noqa: E402

load_streamlit_secrets()
get_settings.cache_clear()

# ── Language selector (sidebar) ────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

with st.sidebar:
    st.markdown("### " + t("lang_selector", st.session_state["lang"]))
    chosen = st.selectbox(
        label="Select language",
        options=list(LANGUAGES.keys()),
        format_func=lambda k: LANGUAGES[k],
        index=list(LANGUAGES.keys()).index(st.session_state["lang"]),
        label_visibility="collapsed",
    )
    if chosen != st.session_state["lang"]:
        st.session_state["lang"] = chosen
        st.rerun()

lang = st.session_state["lang"]


def T(key: str) -> str:
    return t(key, lang)


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="SHERPA", page_icon="🧭", layout="wide")
st.title(T("app_title"))
st.caption(T("app_caption"))

if "dossier" not in st.session_state:
    st.session_state.dossier = None
    st.session_state.plan_id = None
    st.session_state.gpx_summary = None
    st.session_state.gpx_start_label = ""
    st.session_state.gpx_end_label = ""
    st.session_state.transport_options = []

tab_plan, tab_review = st.tabs([T("tab_plan"), T("tab_review")])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: PLAN
# ══════════════════════════════════════════════════════════════════════════════
with tab_plan:
    mode_options = [T("mode_template"), T("mode_conversational")]
    mode = st.radio(T("intake_mode"), mode_options, horizontal=True)
    inputs: ActivityInputs | None = None
    gpx_path: str | None = None

    # ── GPX upload and immediate summary ──────────────────────────────────────
    uploaded = st.file_uploader(T("gpx_label"), type=["gpx"])
    if uploaded is not None:
        out = Path("data/gpx")
        out.mkdir(parents=True, exist_ok=True)
        gpx_path = str(out / uploaded.name)
        with open(gpx_path, "wb") as fh:
            fh.write(uploaded.getbuffer())

        # Parse GPX immediately to show summary and pre-fill fields
        try:
            summary = parse_gpx(gpx_path)
            st.session_state.gpx_summary = summary
            st.session_state.gpx_start_label = (
                summary.start_label
                or f"{summary.start.lat:.4f}, {summary.start.lon:.4f}"
            )
            st.session_state.gpx_end_label = (
                summary.end_label or f"{summary.end.lat:.4f}, {summary.end.lon:.4f}"
            )

            with st.expander(f"📍 {T('gpx_detected')}", expanded=True):
                col_a, col_b, col_c = st.columns(3)
                col_a.metric(T("gpx_distance"), f"{summary.distance_km} km")
                col_b.metric(T("gpx_ascent"), f"{summary.ascent_m:.0f} m")
                col_c.metric(T("gpx_loop"), "✓" if summary.is_loop else "—")
                st.info(T("gpx_note"))
        except Exception as e:
            st.warning(f"Could not read GPX: {e}")

    # ── Template mode ─────────────────────────────────────────────────────────
    if mode == T("mode_template"):
        col1, col2 = st.columns(2)
        with col1:
            activity = st.selectbox(
                T("field_activity"),
                list(ActivityType),
                format_func=lambda a: ACTIVITY_LABELS.get(a, a.value),
            )
            origin = st.text_input(T("field_origin"))
            # Pre-fill from GPX if available
            start_default = st.session_state.get("gpx_start_label", "")
            end_default = st.session_state.get("gpx_end_label", "")
            start_place = st.text_input(T("field_start"), value=start_default)
            end_place = st.text_input(T("field_end"), value=end_default)
        with col2:
            d = st.date_input(T("field_date"), value=date.today())
            t1 = st.time_input(T("field_start_time"), value=time(9, 0))
            t2 = st.time_input(T("field_end_time"), value=time(14, 0))
            other = st.text_area(T("field_other"), height=80)

        if st.button(T("btn_build"), type="primary"):
            # Use GPX coordinates directly for start/end if a GPX was parsed
            gpx_sum = st.session_state.get("gpx_summary")
            if gpx_sum and not start_place.strip():
                start_pt = gpx_sum.start
            else:
                start_pt = (
                    geocode(start_place)
                    if start_place.strip()
                    else (gpx_sum.start if gpx_sum else geocode(""))
                )
            if gpx_sum and not end_place.strip():
                end_pt = gpx_sum.end
            else:
                end_pt = (
                    geocode(end_place)
                    if end_place.strip()
                    else (gpx_sum.end if gpx_sum else geocode(""))
                )

            inputs = ActivityInputs(
                activity_type=activity,
                departure_origin=geocode(origin) if origin.strip() else geocode(""),
                activity_start=start_pt,
                activity_end=end_pt,
                activity_date=d,
                start_time=t1,
                end_time=t2,
                other_characteristics=other,
                gpx_path=gpx_path,
            )

    # ── Conversational mode ───────────────────────────────────────────────────
    else:
        st.info(
            "**"
            + T("mode_conversational")
            + "**: "
            + (
                "Describe your outing in natural language. The system will extract the activity, "
                "location, date, and timing automatically using AI."
                if lang == "en"
                else t("conv_describe", lang)
            )
        )
        text = st.text_area(
            T("conv_describe"),
            height=140,
            placeholder=T("conv_placeholder"),
        )
        if st.button(T("btn_understand"), type="primary") and text:
            parsed = parse_freetext(text)
            inputs = build_inputs(parsed, gpx_path)
            # Override start/end with GPX if available
            gpx_sum = st.session_state.get("gpx_summary")
            if gpx_sum and inputs:
                inputs.activity_start = gpx_sum.start
                inputs.activity_end = gpx_sum.end

    # ── Run the graph ─────────────────────────────────────────────────────────
    if inputs is not None:
        plan_id = uuid.uuid4().hex[:12]
        st.session_state.plan_id = plan_id
        audit.record("user", "submit_inputs", plan_id, inputs.model_dump(mode="json"))
        with st.spinner(T("spinner_building")):
            state = graph.run_until_review(plan_id, inputs)
            st.session_state.dossier = state.get("dossier")
            st.session_state.transport_options = state.get("transport_options", [])
        audit.record("system", "draft_ready", plan_id, {"status": "draft"})
        st.success(T("draft_ready"))

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: REVIEW & DECIDE
# ══════════════════════════════════════════════════════════════════════════════
with tab_review:
    dossier = st.session_state.dossier
    if dossier is None:
        st.info(T("no_draft"))
    else:
        st.subheader(ACTIVITY_LABELS.get(dossier.inputs.activity_type, "Outing"))

        # ── Route metrics ─────────────────────────────────────────────────────
        c1, c2, c3 = st.columns(3)
        c1.metric(T("metric_distance"), f"{dossier.route.distance_km} km")
        c2.metric(T("metric_ascent"), f"{dossier.route.ascent_m:.0f} m")
        c3.metric(T("metric_source"), dossier.route.source)

        # ── Weather ───────────────────────────────────────────────────────────
        st.markdown(f"**{T('section_weather')}**")
        w = dossier.weather
        st.write(
            f"{w.summary} Temp {w.temp_min_c} to {w.temp_max_c} C, "
            f"wind {w.wind_kmh} km/h, rain {w.rain_prob_pct}%. Source: {w.source}."
        )
        for warn in w.warnings or []:
            st.info(warn)

        # ── How to get there ──────────────────────────────────────────────────
        transport_options: list[TransportOption] = st.session_state.get(
            "transport_options", []
        )
        if transport_options:
            st.markdown(f"**{T('how_to_get_there')}**")
            _mode_labels = {
                "car": T("transport_car"),
                "public_transport": T("transport_public"),
                "other": T("transport_other"),
            }
            _mode_icons = {"car": "🚗", "public_transport": "🚉", "other": "🚲"}
            for opt in transport_options:
                label = _mode_labels.get(opt.mode, opt.mode)
                icon = _mode_icons.get(opt.mode, "•")
                with st.expander(f"{icon} {label}"):
                    if opt.distance_km and opt.mode == "car":
                        st.write(opt.summary)
                    else:
                        st.write(opt.summary)
                    for note in opt.notes:
                        st.markdown(f"- {note}")
                    if opt.map_link:
                        st.markdown(f"[Open in Google Maps]({opt.map_link})")

        # ── Equipment ─────────────────────────────────────────────────────────
        st.markdown(f"**{T('section_equipment')}**")
        rec = dossier.recommendation
        st.write("Personal: " + ", ".join(rec.checklist.personal))
        st.write("Activity: " + ", ".join(rec.checklist.activity_specific))
        st.write("Food and water: " + ", ".join(rec.checklist.nutrition_hydration))

        # ── Safety notes ──────────────────────────────────────────────────────
        if rec.risk_flags:
            st.markdown(f"**{T('section_safety')}**")
            for f in rec.risk_flags:
                (
                    st.error
                    if f.level == "warning"
                    else st.warning
                    if f.level == "caution"
                    else st.info
                )(f.message)

        # ── About this place ──────────────────────────────────────────────────
        if dossier.narrative:
            st.markdown(f"**{T('section_about')}**")
            st.write(dossier.narrative)

        # ── POIs and species ──────────────────────────────────────────────────
        if dossier.place_facts:
            pf = dossier.place_facts
            if pf.points_of_interest:
                with st.expander("📍 Points of interest / Heritage sites"):
                    for poi in pf.points_of_interest:
                        st.markdown(f"- {poi}")
            if pf.flora_fauna:
                with st.expander("🌿 Likely species nearby"):
                    for sp in pf.flora_fauna:
                        st.markdown(f"- {sp}")
            if pf.citations:
                with st.expander("📚 Sources"):
                    for c in pf.citations:
                        st.markdown(f"- {c}")

        # ── HITL decision ─────────────────────────────────────────────────────
        st.divider()
        st.markdown(f"### {T('hitl_title')}")
        decision = st.selectbox(
            T("hitl_decision_label"), [d.value for d in HitlDecision]
        )
        note = st.text_input(T("hitl_note_label"))

        if st.button(T("btn_apply"), type="primary"):
            plan_id = st.session_state.plan_id
            audit.record("reviewer", decision, plan_id, {"note": note})
            mesh.publish_event(
                plan_id, "hitl_decision", {"decision": decision, "note": note}
            )

            if decision == HitlDecision.APPROVE.value:
                dossier.status = "approved"
                path = render_pdf(dossier)
                dossier.pdf_path = path
                audit.record("system", "pdf_generated", plan_id, {"pdf_path": path})
                with open(path, "rb") as fh:
                    st.download_button(
                        T("download_pdf"),
                        fh,
                        file_name=Path(path).name,
                        mime="application/pdf",
                    )
                st.success(T("approved_msg"))
            elif decision == HitlDecision.REJECT.value:
                dossier.status = "rejected"
                st.warning(T("rejected_msg"))
            else:
                st.info(
                    f"Decision '{decision}' recorded. For a modification, rebuild with the note applied."
                )
