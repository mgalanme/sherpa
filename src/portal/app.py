"""SHERPA Streamlit portal: conversational and template intake, plus the Human-in-the-Loop
review console. Run with: streamlit run src/portal/app.py

CrewAI is imported here, on the main thread, before any worker threads are spawned (lesson).
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, time
from pathlib import Path

import streamlit as st

# Ensure the project root is importable (PYTHONPATH=. equivalent for Streamlit Cloud)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src import audit, mesh  # noqa: E402
from src.agents import graph  # noqa: E402
from src.catalog import ACTIVITY_LABELS  # noqa: E402
from src.config import get_settings, load_streamlit_secrets  # noqa: E402
from src.dossier import render_pdf  # noqa: E402
from src.intake import build_inputs, geocode, parse_freetext  # noqa: E402
from src.models import ActivityInputs, ActivityType, HitlDecision  # noqa: E402

load_streamlit_secrets()
get_settings.cache_clear()  # pick up secrets copied into the environment

st.set_page_config(page_title="SHERPA", page_icon="🧭", layout="wide")
st.title("SHERPA")
st.caption("Sports, Heritage and Excursion Recommendation and Planning Agent")

if "dossier" not in st.session_state:
    st.session_state.dossier = None
    st.session_state.plan_id = None

tab_plan, tab_review = st.tabs(["Plan an outing", "Review and decide"])

with tab_plan:
    mode = st.radio("Intake mode", ["Template", "Conversational"], horizontal=True)
    inputs: ActivityInputs | None = None
    gpx_path = None

    uploaded = st.file_uploader(
        "Optional GPX track (recommended, since Wikiloc has no public API)",
        type=["gpx"],
    )
    if uploaded is not None:
        out = Path("data/gpx")
        out.mkdir(parents=True, exist_ok=True)
        gpx_path = str(out / uploaded.name)
        with open(gpx_path, "wb") as fh:
            fh.write(uploaded.getbuffer())

    if mode == "Template":
        col1, col2 = st.columns(2)
        with col1:
            activity = st.selectbox(
                "Activity",
                list(ActivityType),
                format_func=lambda a: ACTIVITY_LABELS.get(a, a.value),
            )
            origin = st.text_input("Departure origin (home address)")
            start_place = st.text_input("Activity start point")
            end_place = st.text_input("Activity end point")
        with col2:
            d = st.date_input("Date", value=date.today())
            t1 = st.time_input("Start time", value=time(9, 0))
            t2 = st.time_input("End time", value=time(14, 0))
            other = st.text_area("Other characteristics", height=80)
        if st.button("Build draft", type="primary"):
            inputs = ActivityInputs(
                activity_type=activity,
                departure_origin=geocode(origin),
                activity_start=geocode(start_place),
                activity_end=geocode(end_place),
                activity_date=d,
                start_time=t1,
                end_time=t2,
                other_characteristics=other,
                gpx_path=gpx_path,
            )
    else:
        text = st.text_area(
            "Describe your outing in your own words",
            height=140,
            placeholder="A gravel ride on Saturday from home in Cercedilla, "
            "starting at the reservoir at 9am, back by 1pm...",
        )
        if st.button("Understand and build draft", type="primary") and text:
            parsed = parse_freetext(text)
            inputs = build_inputs(parsed, gpx_path)

    if inputs is not None:
        plan_id = uuid.uuid4().hex[:12]
        st.session_state.plan_id = plan_id
        audit.record("user", "submit_inputs", plan_id, inputs.model_dump(mode="json"))
        with st.spinner(
            "Gathering weather, access, route, heritage and recommendations..."
        ):
            state = graph.run_until_review(plan_id, inputs)
            st.session_state.dossier = state.get("dossier")
        audit.record("system", "draft_ready", plan_id, {"status": "draft"})
        st.success("Draft ready. Open the Review and decide tab.")

with tab_review:
    dossier = st.session_state.dossier
    if dossier is None:
        st.info("No draft yet. Build one in the Plan an outing tab.")
    else:
        st.subheader(ACTIVITY_LABELS.get(dossier.inputs.activity_type, "Outing"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Distance", f"{dossier.route.distance_km} km")
        c2.metric("Ascent", f"{dossier.route.ascent_m:.0f} m")
        c3.metric("Track source", dossier.route.source)

        st.markdown("**Weather**")
        w = dossier.weather
        st.write(
            f"{w.summary} Temp {w.temp_min_c} to {w.temp_max_c} C, wind {w.wind_kmh} km/h, "
            f"rain {w.rain_prob_pct}%. Source: {w.source}."
        )

        st.markdown("**Equipment**")
        rec = dossier.recommendation
        st.write("Personal: " + ", ".join(rec.checklist.personal))
        st.write("Activity: " + ", ".join(rec.checklist.activity_specific))
        st.write("Food and water: " + ", ".join(rec.checklist.nutrition_hydration))

        if rec.risk_flags:
            st.markdown("**Safety notes**")
            for f in rec.risk_flags:
                (
                    st.error
                    if f.level == "warning"
                    else st.warning
                    if f.level == "caution"
                    else st.info
                )(f"{f.message}")

        if dossier.narrative:
            st.markdown("**About this place**")
            st.write(dossier.narrative)

        st.divider()
        st.markdown("### Human decision")
        decision = st.selectbox("Decision", [d.value for d in HitlDecision])
        note = st.text_input("If modifying, describe the change in your own words")

        if st.button("Apply decision", type="primary"):
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
                        "Download dossier PDF",
                        fh,
                        file_name=Path(path).name,
                        mime="application/pdf",
                    )
                st.success("Approved and PDF generated.")
            elif decision == HitlDecision.REJECT.value:
                dossier.status = "rejected"
                st.warning("Draft rejected and recorded.")
            else:
                st.info(
                    f"Decision '{decision}' recorded. For a modification, rebuild with the note applied."
                )
