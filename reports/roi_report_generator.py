"""Render the partner ROI report to HTML (and optionally PDF)."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

TEMPLATE_DIR = Path(__file__).parent / "templates"


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
    """
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
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

        if as_pdf:
            try:
                from weasyprint import HTML
                pdf_path = out.with_suffix(".pdf")
                HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(str(pdf_path))
            except Exception as e:
                print(f"PDF generation failed (weasyprint): {e}")

    return html
