"""Dossier rendering to PDF with ReportLab (pure Python, portable to Streamlit Cloud)."""

from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .catalog import ACTIVITY_LABELS
from .models import Dossier

GREEN = colors.HexColor("#1F5C46")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(
        ParagraphStyle(name="H1s", parent=ss["Heading1"], textColor=GREEN, fontSize=18)
    )
    ss.add(
        ParagraphStyle(name="H2s", parent=ss["Heading2"], textColor=GREEN, fontSize=13)
    )
    return ss


def render_pdf(dossier: Dossier, out_dir: str = "data/outputs") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"sherpa_{dossier.plan_id}.pdf")
    ss = _styles()
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
    )
    story = []
    inp = dossier.inputs

    story.append(Paragraph("SHERPA Activity Dossier", ss["H1s"]))
    story.append(
        Paragraph(
            ACTIVITY_LABELS.get(inp.activity_type, str(inp.activity_type)), ss["H2s"]
        )
    )
    story.append(Spacer(1, 6))

    meta = [
        ["Date", str(inp.activity_date)],
        ["Time", f"{inp.start_time} to {inp.end_time}"],
        [
            "Start",
            inp.activity_start.label
            or f"{inp.activity_start.lat}, {inp.activity_start.lon}",
        ],
        [
            "End",
            inp.activity_end.label or f"{inp.activity_end.lat}, {inp.activity_end.lon}",
        ],
        [
            "Distance",
            f"{dossier.route.distance_km} km (ascent {dossier.route.ascent_m:.0f} m)",
        ],
        ["Route type", "Loop" if dossier.route.is_loop else "Point to point"],
        ["Track source", dossier.route.source],
    ]
    tbl = Table(meta, colWidths=[35 * mm, 130 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F6F4")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Weather", ss["H2s"]))
    w = dossier.weather
    story.append(
        Paragraph(
            f"{w.summary} Temperature {w.temp_min_c} to {w.temp_max_c} C, wind {w.wind_kmh} km/h, "
            f"rain probability {w.rain_prob_pct}%. Source: {w.source}.",
            ss["BodyText"],
        )
    )
    for warn in w.warnings:
        story.append(Paragraph(f"Warning: {warn}", ss["BodyText"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Equipment checklist", ss["H2s"]))
    rec = dossier.recommendation
    items = (
        ["Personal:"]
        + rec.checklist.personal
        + ["Activity:"]
        + rec.checklist.activity_specific
        + ["Food and water:"]
        + rec.checklist.nutrition_hydration
    )
    story.append(
        ListFlowable(
            [ListItem(Paragraph(i, ss["BodyText"])) for i in items], bulletType="bullet"
        )
    )
    story.append(Spacer(1, 6))

    if rec.risk_flags:
        story.append(Paragraph("Safety notes", ss["H2s"]))
        for f in rec.risk_flags:
            story.append(Paragraph(f"[{f.level.upper()}] {f.message}", ss["BodyText"]))
        story.append(Spacer(1, 6))

    if dossier.access_notes:
        story.append(Paragraph("Access", ss["H2s"]))
        for a in dossier.access_notes:
            story.append(
                Paragraph(f"({a.certainty}) {a.note} [{a.source}]", ss["BodyText"])
            )
        story.append(Spacer(1, 6))

    if dossier.narrative:
        story.append(Paragraph("About this place", ss["H2s"]))
        story.append(Paragraph(dossier.narrative, ss["BodyText"]))
        story.append(Spacer(1, 6))

    if dossier.place_facts.citations:
        story.append(Paragraph("Sources", ss["H2s"]))
        for c in dossier.place_facts.citations:
            story.append(Paragraph(c, ss["BodyText"]))

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "This dossier is advisory. Conditions can change; verify access and weather close to "
            "the date, and use your own judgement. SHERPA does not guarantee safety.",
            ss["BodyText"],
        )
    )

    doc.build(story)
    return path
