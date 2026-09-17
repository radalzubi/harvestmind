"""Render the structured diagnostic report (`reports/diagnostic_findings.build_report`)
as a restrained, consulting-style PDF.

The renderer holds no analysis. Every sentence and number comes from the
report model, so the PDF and the in-app view cannot disagree. Layout:
executive summary first (page 1 stands alone), then readiness, how you
order today, the policy comparison (with one per-period chart when fold
results exist), finding cards, suppliers, lanes, the action plan, and an
appendix with the methodology, assumptions, provenance and run identity.
"""
from __future__ import annotations

import io
from typing import Any
from xml.sax.saxutils import escape

INK = "#141414"
MUTED = "#5B5B5B"
RULE = "#D6D6D6"
BRAND = "#0B3D2E"
PANEL = "#F1F5F3"
SEV = {"high": "#B23A2E", "medium": "#C77D1B", "low": "#5B7F73", "info": "#7A7A7A"}
ATTN = {"ELEVATED": "#B23A2E", "WATCH": "#C77D1B", "NORMAL": "#5B7F73", "UNAVAILABLE": "#7A7A7A"}


def _e(x: Any) -> str:
    return escape("" if x is None else str(x))


def render_pdf(report: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

    ink, muted, rule, brand, panel = (colors.HexColor(c) for c in (INK, MUTED, RULE, BRAND, PANEL))
    W = A4[0] - 2 * 17 * mm
    st = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=brand, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9, leading=12, textColor=muted),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=brand, spaceBefore=14, spaceAfter=5),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=ink, spaceBefore=8, spaceAfter=3),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.2, leading=12.4, textColor=ink, alignment=TA_LEFT),
        "pb": ParagraphStyle("pb", fontName="Helvetica-Bold", fontSize=9.2, leading=12.4, textColor=ink),
        "s": ParagraphStyle("s", fontName="Helvetica", fontSize=8.4, leading=11, textColor=muted),
        "big": ParagraphStyle("big", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=ink),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=brand),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.3, leading=10.6, textColor=ink),
        "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.3, leading=10.6, textColor=ink),
        "cells": ParagraphStyle("cells", fontName="Helvetica", fontSize=7.8, leading=10, textColor=muted),
    }

    def P(text: str, style: str = "p") -> Any:
        return Paragraph(text, st[style])

    def bullets(items: list[str], style: str = "p") -> list:
        return [Paragraph(f"•&nbsp;&nbsp;{t}", st[style]) for t in items]

    def grid(rows: list[list[Any]], widths: list[float], header: bool = True, zebra: bool = False) -> Table:
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                 ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                 ("LINEBELOW", (0, 1), (-1, -1), 0.3, rule)]
        if header:
            style += [("LINEBELOW", (0, 0), (-1, 0), 0.8, brand)]
        if zebra:
            for i in range(1, len(rows)):
                if i % 2 == 0:
                    style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFAFA")))
        t.setStyle(TableStyle(style))
        return t

    def panel_box(flow: list, color: Any = None, bar: Any = None) -> Table:
        t = Table([[flow]], colWidths=[W])
        s: list = [("BACKGROUND", (0, 0), (-1, -1), color or panel), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                   ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
        if bar is not None:
            s.append(("LINEBEFORE", (0, 0), (0, -1), 3, bar))
        t.setStyle(TableStyle(s))
        return t

    company = _e(report.get("company"))
    run = (report.get("appendix") or {}).get("run") or {}
    gen = str(report.get("generated_at") or "")[:10]
    el: list = [P(f"Purchasing diagnostic: {company}", "title"),
                P(f"Prepared by ZAAD Supply · {gen} · run {_e(report.get('run_id'))} · measured on your own uploaded history, identifiers pseudonymised · not a forecast", "sub"),
                Spacer(1, 8)]

    # ── executive summary ──
    concl = report.get("conclusion") or {}
    ex = report.get("executive_summary") or {}
    box: list = [P("EXECUTIVE SUMMARY", "label"), P(_e(concl.get("headline")), "big"), Spacer(1, 3), P(_e(concl.get("body"))), Spacer(1, 6)]
    if ex.get("findings"):
        box.append(P("Most important findings", "pb"))
        for i, f in enumerate(ex["findings"], 1):
            box.append(P(f"{i}. <b>{_e(f['headline'])}</b> — {_e(f['line'])} <font color='{MUTED}'>(confidence {_e(f['confidence']).lower()})</font>"))
    if ex.get("actions"):
        box += [Spacer(1, 4), P("Recommended actions", "pb")] + bullets([_e(a) for a in ex["actions"]])
    conf = ex.get("confidence") or {}
    box += [Spacer(1, 4), P(f"<b>Data quality and confidence: {_e(conf.get('level'))}.</b> {_e(conf.get('statement'))}")]
    el.append(panel_box(box, bar=brand))

    # ── readiness ──
    rd = report.get("readiness") or {}
    el += [P("1. Data readiness and confidence", "h1"), P(f"<b>{_e(rd.get('label'))}</b> · overall confidence <b>{_e(rd.get('confidence'))}</b>"),
           P(_e(rd.get("statement")))]
    facts = rd.get("facts") or []
    if facts:
        el.append(Spacer(1, 4))
        el.append(grid([[P(_e(f["label"]), "cellb"), P(_e(f["value"]), "cell")] for f in facts], [55 * mm, W - 55 * mm], header=False))
    if rd.get("limitations"):
        el += [P("What the limitations mean for this analysis", "h2")] + bullets([_e(li["effect"]) for li in rd["limitations"]])
    if rd.get("missing_fields"):
        el.append(P("Fields that would strengthen it: " + ", ".join(_e(m["field"]) for m in rd["missing_fields"][:10]) + ("." if len(rd["missing_fields"]) <= 10 else " and others."), "s"))
    if rd.get("required_missing"):
        el.append(P("Required fields missing: " + ", ".join(_e(x) for x in rd["required_missing"]), "s"))

    # ── ordering today ──
    od = report.get("ordering_today") or {}
    if od.get("items"):
        el += [P("2. How you appear to order today", "h1"), P(_e(od.get("summary")))]
        rows = [[P("Observation", "cellb"), P("What we read", "cellb"), P("Basis", "cellb")]]
        for it in od["items"]:
            rows.append([P(_e(it["label"]), "cellb"), P(_e(it["value"]) + (f"<br/><font color='{MUTED}' size='7.8'>{_e(it['note'])}</font>" if it.get("note") else ""), "cell"),
                         P(_e(it.get("tag")), "cells")])
        el.append(grid(rows, [48 * mm, W - 48 * mm - 28 * mm, 28 * mm]))

    # ── policy comparison ──
    pc = report.get("policy_comparison") or {}
    el.append(P("3. Historical policy comparison", "h1"))
    if pc.get("available"):
        el.append(P(f"<b>{_e(pc.get('current_label'))}</b> versus <b>{_e(pc.get('candidate_label'))}</b>, replayed on your own history."))
        rows = [[P("Measure", "cellb"), P("Your current policy", "cellb"), P(_e(pc.get("candidate_label")), "cellb"), P("Reading", "cellb")]]
        for r in pc.get("rows") or []:
            rows.append([P(_e(r["metric"]) + (f"<br/><font color='{MUTED}' size='7.6'>{_e(r['note'])}</font>" if r.get("note") else ""), "cell"),
                         P(_e(r["current"]), "cell"), P(_e(r["candidate"]), "cell"), P(_e(r["difference"]), "cells")])
        el.append(grid(rows, [52 * mm, 28 * mm, 34 * mm, W - 114 * mm], zebra=True))
        el.append(Spacer(1, 4))
        for para in pc.get("explanation") or []:
            el.append(P(_e(para)))
            el.append(Spacer(1, 2))
        chart = pc.get("fold_chart")
        if chart and chart.get("selection"):
            el.append(Spacer(1, 4))
            el.append(_fold_chart(chart, W))
            el.append(P("Each bar is one historical period: the candidate's cost change against your policy on that period. Positive = the candidate cost less. The dashed line is the selection threshold; the grey bar is the average on the unseen validation periods.", "s"))
    else:
        for para in pc.get("explanation") or []:
            el.append(P(_e(para)))

    # ── findings ──
    fs = report.get("findings") or []
    if fs:
        el.append(P("4. Management attention", "h1"))
        el.append(P("Ranked by severity and, where a defensible measure exists, by the share of your demand value involved. Each card says what happened, why it matters, what appears to drive it, what to consider, and how confident ZAAD is.", "s"))
        cards = [f for f in fs if f.get("severity") in ("high", "medium")]
        rest = [f for f in fs if f not in cards]
        for f in cards:
            col = colors.HexColor(SEV.get(f.get("severity"), "#7A7A7A"))
            card: list = [P(f"<font color='{SEV.get(f.get('severity'), '#7A7A7A')}'>{_e(f.get('severity')).upper()}</font> · {_e(f.get('category')).upper()} · confidence {_e(f.get('confidence'))}", "label"),
                          P(_e(f.get("headline")), "pb"),
                          P(f"<b>What happened.</b> {_e(f.get('observation'))}"),
                          P(f"<b>Why it matters.</b> {_e(f.get('business_implication'))}")]
            if f.get("possible_driver"):
                card.append(P(f"<b>Likely cause.</b> [{_e(f.get('driver_tag'))}] {_e(f.get('possible_driver'))}"))
            card.append(P(f"<b>What to consider.</b> {_e(f.get('recommendation'))}"))
            ev = f.get("evidence") or []
            if ev:
                card.append(P("Supporting data: " + " · ".join(f"{_e(e['label'])} {_e(e['value'])}" for e in ev) + f" · basis: {_e(f.get('confidence_basis'))}", "s"))
            rel = [r for r in (f.get("related") or []) if r.get("kind") in ("sku", "supplier", "po", "screen", "decision")]
            if rel:
                card.append(P("In ZAAD: " + ", ".join(_zaad_ref(r) for r in rel[:6]), "s"))
            el.append(KeepTogether([panel_box(card, color=colors.white, bar=col), Spacer(1, 3)]))
        if rest:
            el.append(P("Also noted (lower severity)", "h2"))
            el += bullets([f"<b>{_e(f['headline'])}.</b> {_e(f.get('observation'))} <font color='{MUTED}'>What to consider: {_e(f.get('recommendation'))}</font>" for f in rest], "cell")

    # ── suppliers ──
    sp = report.get("suppliers") or {}
    el.append(P("5. Supplier analysis", "h1"))
    if sp.get("available") and sp.get("rows"):
        rows = [[P(h, "cellb") for h in ("Supplier", "Share of value", "Products", "Receipts", "Fill", "Lead time", "Spread", "Lane", "Reading")]]
        for r in sp["rows"]:
            rows.append([P(_e(r["supplier"]), "cell"), P(_e(r["share_of_value"]), "cell"), P(_e(r["products"]), "cell"), P(_e(r["receipts"]), "cell"),
                         P(_e(r["fill"]), "cell"), P(_e(r["lead_time"]), "cell"), P(_e(r["lead_spread"]), "cell"), P(_e(r["lane"]), "cell"),
                         P(_e(r["reading"]) + f"<br/><font color='{MUTED}' size='7.4'>evidence {_e(r['evidence'])}</font>", "cell")])
        el.append(grid(rows, [24 * mm, 18 * mm, 16 * mm, 16 * mm, 16 * mm, 20 * mm, 18 * mm, 20 * mm, W - 148 * mm], zebra=True))
        el.append(P(_e(sp.get("note")), "s"))
    else:
        el.append(P(_e(sp.get("note") or "Not available from current data.")))

    # ── lanes ──
    lanes = report.get("lanes") or []
    el.append(P("6. Supply lane risk", "h1"))
    if lanes:
        el.append(P(_e(lanes[0].get("score_meaning")), "s"))
        blocks = [ln for ln in lanes if ln.get("attention") in ("ELEVATED", "UNAVAILABLE")]
        compact = [ln for ln in lanes if ln not in blocks]
        for ln in blocks:
            col = colors.HexColor(ATTN.get(ln.get("attention"), "#7A7A7A"))
            block: list = [P(f"{_e(ln.get('label')).upper()} — <font color='{ATTN.get(ln.get('attention'), '#7A7A7A')}'>{_e(ln.get('attention'))}</font>"
                             f" · lane score {_e(ln.get('score'))} · evidence {_e(ln.get('evidence_strength'))}", "pb"),
                           P(_e(ln.get("evidence_note")), "s"), P("External condition", "cellb")] + bullets([_e(x) for x in ln.get("external") or []], "cell") + \
                          [P("Your exposure", "cellb")] + bullets([_e(x) for x in ln.get("exposure") or []], "cell") + \
                          [P("Recommended response", "cellb"), P(_e(ln.get("response")), "cell")]
            el.append(KeepTogether([panel_box(block, color=colors.white, bar=col), Spacer(1, 5)]))
        if compact:
            rows = [[P(h, "cellb") for h in ("Lane", "Attention", "Score", "Evidence", "External condition", "Your exposure", "Response")]]
            for ln in compact:
                rows.append([P(_e(ln.get("label")), "cellb"), P(f"<font color='{ATTN.get(ln.get('attention'), '#7A7A7A')}'>{_e(ln.get('attention'))}</font>", "cell"),
                             P(_e(ln.get("score")), "cell"), P(_e(ln.get("evidence_strength")), "cell"),
                             P("; ".join(_e(x) for x in (ln.get("external") or [])[:3]), "cells"), P("; ".join(_e(x) for x in (ln.get("exposure") or [])[:2]), "cells"),
                             P(_e(ln.get("response")), "cells")])
            el.append(grid(rows, [22 * mm, 18 * mm, 13 * mm, 16 * mm, 40 * mm, 34 * mm, W - 143 * mm], zebra=True))
    else:
        el.append(P("No shipping route is declared per supplier, so no lane evidence could be attached. Declare the route in the supplier list to enable this section."))

    # ── actions ──
    ac = report.get("actions") or {}
    el.append(P("7. Recommended actions", "h1"))
    for key, title in (("now", "NOW"), ("next", "NEXT"), ("monitor", "MONITOR")):
        items = ac.get(key) or []
        if not items:
            continue
        el.append(P(title, "h2"))
        el += bullets([_e(a["text"]) + (f" <font color='{MUTED}'>({_e(_zaad_ref(a['link']))})</font>" if a.get("link") else "") for a in items])

    # ── appendix ──
    ap = report.get("appendix") or {}
    el += [PageBreak(), P("Appendix: assumptions and methodology", "h1"),
           P("Kept apart from the narrative so the report stays readable; nothing here is hidden from the main text where it changes a conclusion.", "s")]
    if ap.get("methodology"):
        el += [P("Methodology", "h2")] + bullets([_e(m) for m in ap["methodology"]], "cell")
    if ap.get("candidates"):
        el.append(P("Policy candidates tested", "h2"))
        rows = [[P(h, "cellb") for h in ("Candidate", "Average", "Conservative estimate", "Worst period", "Periods", "Selection rule", "Unseen validation")]]
        for c in ap["candidates"]:
            rows.append([P(f"{_e(c['label'])}<br/><font color='{MUTED}' size='7.4'>{_e(c['candidate'])}</font>", "cell"), P(_e(c["mean"]), "cell"), P(_e(c["lower_bound"]), "cell"),
                         P(_e(c["worst"]), "cell"), P(_e(c["folds"]), "cell"), P(_e(c["inner_gates"]), "cell"), P(_e(c["holdout"]), "cell")])
        el.append(grid(rows, [40 * mm, 20 * mm, 28 * mm, 22 * mm, 16 * mm, 24 * mm, W - 150 * mm], zebra=True))
    g = ap.get("gates") or {}
    if g:
        el.append(P("Selection rule parameters: " + ", ".join(f"{_e(k)} = {_e(v)}" for k, v in g.items() if not isinstance(v, dict)), "s"))
    if ap.get("assumptions"):
        el.append(P("Inputs and their provenance", "h2"))
        rows = [[P("Input", "cellb"), P("Provenance", "cellb")]] + [[P(_e(a["input"]), "cell"), P(_e(a["provenance"]), "cell")] for a in ap["assumptions"]]
        el.append(grid(rows, [55 * mm, W - 55 * mm], zebra=True))
        el.append(P("operator = supplied by you · measured = derived from your transactions · public_benchmark = a published figure · assumed = a stated default · unknown = nothing known, the decision does not depend on it", "s"))
    sens = ap.get("carrying_cost_sensitivity")
    if isinstance(sens, list) and sens:
        el.append(P("Carrying-cost sensitivity: the ranking was checked at " + ", ".join(f"{float(x.get('multiplier', 0)):g}× ({float(x.get('annual_rate', 0)) * 100:.0f}%/yr)" for x in sens if isinstance(x, dict)) + ".", "s"))
    if ap.get("glossary"):
        el.append(P("Terms used in this report", "h2"))
        rows = [[P("In the report", "cellb"), P("Internal term", "cellb"), P("Meaning", "cellb")]] + \
               [[P(_e(t["term"]), "cell"), P(_e(t["internal"]), "cells"), P(_e(t["meaning"]), "cell")] for t in ap["glossary"]]
        el.append(grid(rows, [48 * mm, 40 * mm, W - 88 * mm]))
    if ap.get("warnings"):
        el += [P("Run notes (verbatim)", "h2")] + bullets([_e(w) for w in ap["warnings"][:12]], "cells")
    el.append(P("Run identity", "h2"))
    rid = [f"run {_e(run.get('run_id'))}", f"generated {_e(run.get('generated_at'))}", f"report version {_e(run.get('report_version'))}",
           f"summary version {_e(run.get('summary_version') or 'pre-2026.09.2')}", f"sector {_e(run.get('sector'))}"]
    hr = run.get("history_range") or {}
    if hr.get("orders_from"):
        rid.append(f"history {_e(hr.get('orders_from'))} to {_e(hr.get('orders_to'))} ({_e(hr.get('order_lines'))} order lines, {_e(hr.get('po_lines'))} PO lines, {_e(hr.get('receipt_lines'))} receipt lines)")
    rid += [f"internal readiness verdict {_e(run.get('internal_readiness_verdict'))}", f"internal decision {_e(run.get('internal_decision'))}: {_e(run.get('internal_reason'))}"]
    el += bullets(rid, "cells")
    el.append(Spacer(1, 6))
    el.append(P("Every number in this report is measured on your own uploaded history with identifiers pseudonymised. It is not a promise about the future, and no saving is projected.", "s"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"ZAAD purchasing diagnostic: {report.get('company')}", author="ZAAD Supply")

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(muted)
        canvas.drawString(17 * mm, 9 * mm, f"ZAAD Supply · purchasing diagnostic · {company} · run {report.get('run_id')}")
        canvas.drawRightString(A4[0] - 17 * mm, 9 * mm, f"page {d.page}")
        canvas.restoreState()

    doc.build(el, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def _zaad_ref(r: dict) -> str:
    kind, id_, label = r.get("kind"), r.get("id"), r.get("label")
    if kind == "sku":
        return f"Inventory → {id_}"
    if kind == "supplier":
        return f"Diagnostics → Supplier {id_}"
    if kind == "po":
        return "Purchase orders → open"
    if kind == "decision":
        return "Decisions → run a decision"
    if kind == "screen":
        return f"{str(id_).title()}"
    return str(label or id_)


def _fold_chart(chart: dict, width: float):
    """Horizontal bars, one per historical period, with the threshold and
    the unseen-validation average. Drawn with primitives so the chart is
    exactly the data and nothing decorative."""
    from reportlab.graphics.shapes import Drawing, Line, Rect, String
    from reportlab.lib import colors
    sel = [float(x) for x in chart.get("selection") or []]
    hold = chart.get("holdout_mean")
    thr = chart.get("threshold")
    vals = sel + ([float(hold)] if hold is not None else [])
    lo, hi = min(vals + [0.0, -0.05]), max(vals + [0.0, 0.05])
    if thr is not None:
        hi = max(hi, float(thr) + 0.02)
    span = (hi - lo) or 1.0
    row_h, gap = 11, 4
    n = len(vals)
    left, right = 78, 40
    plot_w = width - left - right
    h = 22 + n * (row_h + gap) + 12
    d = Drawing(width, h)
    d.add(String(0, h - 10, chart.get("title", ""), fontName="Helvetica-Bold", fontSize=8, fillColor=colors.HexColor(INK)))

    def x_of(v: float) -> float:
        return left + (v - lo) / span * plot_w

    base_y = h - 24
    d.add(Line(x_of(0.0), 6, x_of(0.0), base_y + 4, strokeColor=colors.HexColor(MUTED), strokeWidth=0.6))
    if thr is not None:
        d.add(Line(x_of(float(thr)), 6, x_of(float(thr)), base_y + 4, strokeColor=colors.HexColor(BRAND), strokeWidth=0.6, strokeDashArray=[2, 2]))
        d.add(String(x_of(float(thr)) + 2, base_y + 6, f"threshold {float(thr) * 100:+.0f}%", fontName="Helvetica", fontSize=6.5, fillColor=colors.HexColor(BRAND)))
    for i, v in enumerate(vals):
        y = base_y - (i + 1) * (row_h + gap)
        is_hold = i >= len(sel)
        label = "unseen validation (avg)" if is_hold else f"period {i + 1}"
        d.add(String(0, y + 2, label, fontName="Helvetica", fontSize=7, fillColor=colors.HexColor(MUTED)))
        x0, x1 = sorted((x_of(0.0), x_of(v)))
        fill = colors.HexColor("#9A9A9A") if is_hold else (colors.HexColor("#3E7D66") if v >= 0 else colors.HexColor("#B23A2E"))
        d.add(Rect(x0, y, max(x1 - x0, 0.5), row_h, fillColor=fill, strokeColor=None))
        d.add(String(x1 + 3 if v >= 0 else x0 - 28, y + 2, f"{v * 100:+.1f}%", fontName="Helvetica", fontSize=7, fillColor=colors.HexColor(INK)))
    return d
