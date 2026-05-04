"""Security regression tests for reports/roi_report_generator.py.

Earlier the renderer would write to any path the caller supplied. We now
refuse to overwrite anything inside the package source tree, and we
require the output path to end in .html / .htm.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from reports.roi_report_generator import ROIReportError, render_roi_report


def _ok_roi() -> dict:
    return {
        "baseline_model": "deterministic", "target_model": "two_stage_sp",
        "annual_gmv_usd": 1_000_000.0, "subscription_tier": "A",
        "monthly_subscription_usd": 1249.0, "annual_subscription_usd": 14988.0,
        "annual_spot_savings_usd": 5000.0, "annual_waste_value_savings_usd": 0.0,
        "annual_lost_sale_recovery_usd": 0.0,
        "total_annual_benefit_usd": 5000.0, "net_annual_benefit_usd": -9988.0,
        "roi_multiple": 0.3, "payback_months": 36.0,
        "baseline_service_level_pct": 99.0, "target_service_level_pct": 99.5,
        "service_level_improvement_pts": 0.5,
        "spot_savings_pct": 10.0, "waste_kg_reduction_annual": 0.0,
    }


def test_refuses_to_write_into_source_tree(tmp_path):
    """The renderer must not let a caller overwrite repo files (e.g. the
    template that generates the report itself)."""
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "reports" / "templates" / "evil.html"
    with pytest.raises(ROIReportError, match="refusing to write"):
        render_roi_report(_ok_roi(), pd.DataFrame(), output_path=target)
    assert not target.exists()


def test_extension_must_be_html(tmp_path):
    target = tmp_path / "x.txt"
    with pytest.raises(ROIReportError, match="\\.html"):
        render_roi_report(_ok_roi(), pd.DataFrame(), output_path=target)
    assert not target.exists()


def test_writes_html_to_safe_temp_path(tmp_path):
    target = tmp_path / "ok" / "report.html"
    html = render_roi_report(_ok_roi(), pd.DataFrame(), output_path=target)
    assert target.exists()
    assert "<html" in html
