"""Render the partner ROI report to HTML (and optionally PDF)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

TEMPLATE_DIR = Path(__file__).parent / "templates"

REQUIRED_ROI_KEYS = (
    "total_annual_benefit_usd",
    "annual_subscription_usd",
    "roi_multiple",
    "payback_months",
    "annual_spot_savings_usd",
    "annual_waste_value_savings_usd",
    "annual_lost_sale_recovery_usd",
    "net_annual_benefit_usd",
    "service_level_improvement_pts",
    "baseline_service_level_pct",
    "target_service_level_pct",
    "spot_savings_pct",
    "waste_kg_reduction_annual",
    "subscription_tier",
    "monthly_subscription_usd",
)


class ROIReportError(ValueError):
    """Raised when the ROI dict is incomplete or contains an error marker."""


def _validate_roi(roi: dict) -> None:
    if not isinstance(roi, dict):
        raise ROIReportError(f"roi must be a dict, got {type(roi).__name__}")
    if "error" in roi:
        raise ROIReportError(f"ROI calculation reported an error: {roi['error']}")
    missing = [k for k in REQUIRED_ROI_KEYS if k not in roi]
    if missing:
        raise ROIReportError(
            "ROI dict is missing required keys: " + ", ".join(missing)
        )


def render_roi_report(
    roi: dict,
    backtest_df: pd.DataFrame,
    partner_name: str = "Hoosier Harvest Market",
    output_path: str | Path | None = None,
    as_pdf: bool = False,
) -> str:
    """Render the ROI HTML report. Returns the HTML string.

    Parameters
    ----------
    roi         : output of roi_calculator.compute_roi()
    backtest_df : output of RollingOriginEngine.run()
    output_path : if provided, writes file to disk
    as_pdf      : if True, also writes PDF via weasyprint

    Raises
    ------
    ROIReportError
        If ``roi`` is not a complete success-shape dict from
        :func:`backtesting.roi_calculator.compute_roi`. Callers should
        either retry the backtest or branch on the error before rendering.
    """
    _validate_roi(roi)

    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    tmpl = env.get_template("roi_report.html")

    from backtesting.procurement_metrics import cost_per_kg_by_model
    model_comparison = cost_per_kg_by_model(backtest_df).to_dict("records")

    backtest_start = backtest_end = ""
    if not backtest_df.empty and "origin_week" in backtest_df.columns:
        backtest_start = str(backtest_df["origin_week"].min())
        backtest_end = str(backtest_df["origin_week"].max())

    html = tmpl.render(
        partner_name=partner_name,
        generated_date=date.today().isoformat(),
        backtest_start=backtest_start,
        backtest_end=backtest_end,
        roi=roi,
        model_comparison=model_comparison,
        n_backtest_origins=len(backtest_df["origin_week"].unique()) if not backtest_df.empty else 0,
        target_model=roi.get("target_model", "two_stage_sp"),
    )

    if output_path is not None:
        out = Path(output_path).resolve()
        # Refuse to overwrite anything inside the package source tree (e.g.
        # the report template itself). Outputs must go to a separate location.
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
            raise ROIReportError(
                f"refusing to write report to a source path under {forbidden}"
            )
        # Validate extension — generator only emits .html (or .pdf when as_pdf).
        if out.suffix.lower() not in (".html", ".htm"):
            raise ROIReportError(
                f"output_path must end in .html / .htm; got {out.suffix!r}"
            )

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

        if as_pdf:
            # weasyprint may be unavailable on systems without its native
            # libs (cairo, pango, etc.). We narrow the catch so we don't
            # swallow programming errors — only the import + render path
            # is treated as best-effort.
            try:
                from weasyprint import HTML
            except ImportError as e:
                raise ROIReportError(
                    "PDF requested but weasyprint is not importable. "
                    "Install system deps (cairo, pango) and retry."
                ) from e
            try:
                pdf_path = out.with_suffix(".pdf")
                HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(str(pdf_path))
            except OSError as e:
                # OSError covers missing native libs; surface clearly.
                raise ROIReportError(f"PDF rendering failed: {e}") from e

    return html
