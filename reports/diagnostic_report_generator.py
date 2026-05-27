"""Render the HarvestMind diagnostic report to HTML (and optionally PDF).

The diagnostic report is the primary sales artifact for pilot conversion:
it translates operational data into dollar-value losses and actionable
available-to-promise recommendations.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

TEMPLATE_DIR = Path(__file__).parent / "templates"


class DiagnosticReportError(ValueError):
    """Raised when the diagnostic data is incomplete or malformed."""


def _fmt_usd(value: float) -> str:
    """Format a float as a dollar string: $47,231."""
    try:
        return f"${value:,.0f}"
    except (TypeError, ValueError):
        return "$—"


def _fmt_pct(value: float) -> str:
    """Format a float fraction as a percentage: 84.2%."""
    try:
        return f"{value * 100:.1f}%"
    except (TypeError, ValueError):
        return "—%"


def _risk_class(risk_level: str) -> str:
    """Return a CSS class name for a risk level badge."""
    return {
        "High": "risk-high",
        "Medium": "risk-medium",
        "Low": "risk-low",
    }.get(str(risk_level), "risk-low")


def render_diagnostic_report(
    summary: dict[str, Any],
    partner_name: str | None = None,
    output_path: str | Path | None = None,
    as_pdf: bool = False,
) -> str:
    """Render the diagnostic report HTML.

    Parameters
    ----------
    summary       : output of diagnostic_metrics.diagnostic_summary()
    partner_name  : override name shown in report header
    output_path   : if provided, write HTML to disk
    as_pdf        : also render PDF via weasyprint (optional dep)

    Returns
    -------
    HTML string.
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    env.filters["fmt_usd"] = _fmt_usd
    env.filters["fmt_pct"] = _fmt_pct
    env.filters["risk_class"] = _risk_class

    tmpl = env.get_template("diagnostic_report.html")

    name = partner_name or summary.get("partner_name", "Operator")

    html = tmpl.render(
        partner_name=name,
        generated_date=date.today().isoformat(),
        period_days=summary.get("period_days", 365),
        row_counts=summary.get("row_counts", {}),
        waste=summary.get("waste", {}),
        shortage=summary.get("shortage", {}),
        supplier=summary.get("supplier", {}),
        buyer=summary.get("buyer", {}),
        traceability=summary.get("traceability", {}),
        atp=summary.get("atp", {}),
        recommendations=summary.get("recommendations", []),
        savings=summary.get("savings", {}),
        top_risks=summary.get("top_risks", []),
        total_waste_loss_usd=summary.get("total_waste_loss_usd", 0.0),
        total_shortage_loss_usd=summary.get("total_shortage_loss_usd", 0.0),
        total_addressable_loss_usd=summary.get("total_addressable_loss_usd", 0.0),
        n_risky_suppliers=summary.get("n_risky_suppliers", 0),
        n_risky_products=summary.get("n_risky_products", 0),
        n_risky_buyers=summary.get("n_risky_buyers", 0),
        traceability_completeness_pct=summary.get("traceability_completeness_pct", 0.0),
    )

    if output_path is not None:
        out = Path(output_path).resolve()
        if out.suffix.lower() not in (".html", ".htm"):
            raise DiagnosticReportError(
                f"output_path must end in .html / .htm; got {out.suffix!r}"
            )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

        if as_pdf:
            try:
                from weasyprint import HTML as WP
            except ImportError as e:
                raise DiagnosticReportError(
                    "PDF requested but weasyprint is not importable. "
                    "Install system deps and retry."
                ) from e
            try:
                pdf_path = out.with_suffix(".pdf")
                WP(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(str(pdf_path))
            except OSError as e:
                raise DiagnosticReportError(f"PDF rendering failed: {e}") from e

    return html
