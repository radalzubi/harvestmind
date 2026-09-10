"""Render the partner pilot-summary HTML/PDF.

Two-page document:
  Page 1: executive summary (KPIs, breakdown, service-level bar, methodology)
  Page 2: backtest detail (policy comparison, data quality, assumptions, next steps)

Usage
-----
  from reports.pilot_summary_generator import render_pilot_summary
  html = render_pilot_summary(roi, backtest_df, partner_name="...", output_path="...")
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

TEMPLATE_DIR = Path(__file__).parent / "templates"

REQUIRED_KEYS = (
    "total_annual_benefit_usd",
    "net_annual_benefit_usd",
    "roi_multiple",
    "payback_months",
    "annual_spot_savings_usd",
    "annual_waste_value_savings_usd",
    "annual_lost_sale_recovery_usd",
    "annual_subscription_usd",
    "baseline_service_level_pct",
    "target_service_level_pct",
    "service_level_improvement_pts",
)


class PilotSummaryError(ValueError):
    """Raised when the pilot-summary inputs are incomplete or malformed."""


def _validate_roi(roi: dict) -> None:
    if not isinstance(roi, dict):
        raise PilotSummaryError(f"roi must be a dict, got {type(roi).__name__}")
    if "error" in roi:
        raise PilotSummaryError(f"ROI calculation reported an error: {roi['error']}")
    missing = [k for k in REQUIRED_KEYS if k not in roi]
    if missing:
        raise PilotSummaryError(
            "ROI dict is missing required keys: " + ", ".join(missing)
        )


def _currency(v) -> str:
    """Jinja filter: format float as $XX,XXX. Handles None / NaN cleanly."""
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if n != n:  # NaN
        return "—"
    return f"{int(round(n)):,}"


def _stress_band(stress_test_df: pd.DataFrame | None) -> tuple[str, str]:
    """Return (dollar_band, roi_band) strings for the KPI boxes."""
    if stress_test_df is None or stress_test_df.empty:
        return "$30K – $40K", "1.5× – 2.0×"
    if "missing_rate" not in stress_test_df.columns:
        return "$30K – $40K", "1.5× – 2.0×"

    rows = stress_test_df.copy()
    # Find the 30% and 50% rows; fall back to range over all rows if not present
    lo = rows[rows["missing_rate"] == 0.30]
    hi = rows[rows["missing_rate"] == 0.50]
    if lo.empty or hi.empty:
        # Use min/max across whatever's available
        usd_lo = float(rows["annual_saved_usd"].min())
        usd_hi = float(rows["annual_saved_usd"].max())
        roi_lo = float(rows["roi"].min())
        roi_hi = float(rows["roi"].max())
    else:
        usd_lo, usd_hi = float(lo["annual_saved_usd"].iloc[0]), float(hi["annual_saved_usd"].iloc[0])
        roi_lo, roi_hi = float(lo["roi"].iloc[0]),               float(hi["roi"].iloc[0])
    return (
        f"${_currency(min(usd_lo, usd_hi))} – ${_currency(max(usd_lo, usd_hi))}",
        f"{min(roi_lo, roi_hi):.1f}× – {max(roi_lo, roi_hi):.1f}×",
    )


_MODEL_LABELS = {
    "naive_lastyear": "Your current method (naive)",
    "deterministic":  "Deterministic LP",
    "gamma_robust":   "HarvestMind (Γ-robust)",
    "two_stage_sp":   "HarvestMind (two-stage SP)",
}


def _model_comparison(backtest_df: pd.DataFrame, target_model: str = "two_stage_sp") -> list[dict]:
    """Build one row per model, in display order, for the policy table."""
    if backtest_df.empty or "model" not in backtest_df.columns:
        return []
    horizons_per_year = 13.0
    if "horizon_weeks" in backtest_df.columns and not backtest_df["horizon_weeks"].dropna().empty:
        h = float(backtest_df["horizon_weeks"].dropna().iloc[0])
        if h > 0:
            horizons_per_year = 52.0 / h

    rows: list[dict] = []
    order = ["naive_lastyear", "deterministic", "gamma_robust", "two_stage_sp"]
    for model in order:
        sub = backtest_df[backtest_df["model"] == model]
        if sub.empty:
            continue
        annual_cost = float(sub["total_cost_usd"].mean()) * horizons_per_year
        rows.append({
            "label": _MODEL_LABELS.get(model, model),
            "model_id": model,
            "annual_cost": round(annual_cost, 0),
            "fill_pct": round(float(sub["service_level_pct"].mean()), 1),
            "spot_kg":  int(round(float(sub["spot_kg"].mean()))),
            "waste_kg": int(round(float(sub["waste_kg"].mean()))),
            "is_target": model == target_model,
        })
    return rows


def render_pilot_summary(
    roi: dict,
    backtest_df: pd.DataFrame,
    partner_name: str = "Partner",
    output_path: str | Path | None = None,
    as_pdf: bool = False,
    stress_test_df: pd.DataFrame | None = None,
    data_quality: list | None = None,
) -> str:
    """Render the pilot summary HTML. Returns the HTML string.

    If ``output_path`` is provided, also writes the file to disk. With
    ``as_pdf=True``, the .pdf is produced via weasyprint when available;
    weasyprint missing → returns HTML and the caller can decide.

    Raises PilotSummaryError on invalid inputs or unsafe output paths.
    """
    _validate_roi(roi)

    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["currency"] = _currency
    tmpl = env.get_template("pilot_summary.html")

    backtest_start = backtest_end = "—"
    if not backtest_df.empty and "origin_week" in backtest_df.columns:
        backtest_start = str(backtest_df["origin_week"].min())
        backtest_end = str(backtest_df["origin_week"].max())

    n_backtest_origins = (
        int(backtest_df["origin_week"].nunique())
        if not backtest_df.empty and "origin_week" in backtest_df.columns
        else 0
    )
    horizon_weeks = (
        int(backtest_df["horizon_weeks"].dropna().iloc[0])
        if not backtest_df.empty and "horizon_weeks" in backtest_df.columns
        and not backtest_df["horizon_weeks"].dropna().empty
        else 4
    )

    stress_dollar, stress_roi = _stress_band(stress_test_df)

    html = tmpl.render(
        partner_name=partner_name,
        generated_date=date.today().isoformat(),
        backtest_start=backtest_start,
        backtest_end=backtest_end,
        n_backtest_origins=n_backtest_origins,
        horizon_weeks=horizon_weeks,
        roi=roi,
        model_comparison=_model_comparison(backtest_df, target_model=roi.get("target_model", "two_stage_sp")),
        data_quality=data_quality or [],
        stress_band_dollar=stress_dollar,
        stress_band_roi=stress_roi,
    )

    if output_path is not None:
        out = Path(output_path).resolve()

        # Forbid writes inside source tree. Keep parity with roi_report_generator.
        repo_root = Path(__file__).resolve().parents[1]
        forbidden_roots = (
            repo_root / "reports" / "templates",
            repo_root / "db" / "migrations",
            repo_root / "db" / "seeds",
            repo_root / "synthetic",
            repo_root / "scripts",
        )
        for forbidden in forbidden_roots:
            try:
                out.relative_to(forbidden)
            except ValueError:
                continue
            raise PilotSummaryError(
                f"refusing to write report to a source path under {forbidden}"
            )

        if out.suffix.lower() not in (".html", ".htm"):
            raise PilotSummaryError(
                f"output_path must end in .html / .htm; got {out.suffix!r}"
            )

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

        if as_pdf:
            try:
                from weasyprint import HTML
            except ImportError:
                # Caller asked for PDF; weasyprint isn't installed. Return the
                # HTML and let the script log "weasyprint not found" — do NOT
                # raise; the user prompt prefers a graceful fallback.
                return html
            try:
                pdf_path = out.with_suffix(".pdf")
                HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(str(pdf_path))
            except OSError:
                # Native libs missing (cairo/pango). Fall back to HTML only.
                pass

    return html
