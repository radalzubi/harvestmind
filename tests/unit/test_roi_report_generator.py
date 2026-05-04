"""Tests for the ROI report renderer.

Regression: previously calling render_roi_report on an error-shape dict
raised an opaque jinja2 ``Undefined.__format__`` TypeError because the
template assumed every roi.* key was populated. Now we surface a clear
ROIReportError.
"""

from __future__ import annotations

import pandas as pd
import pytest

from reports.roi_report_generator import ROIReportError, render_roi_report


def _full_roi() -> dict:
    return {
        "baseline_model": "deterministic",
        "target_model": "two_stage_sp",
        "annual_gmv_usd": 3_000_000.0,
        "subscription_tier": "A",
        "monthly_subscription_usd": 1249.0,
        "annual_subscription_usd": 14988.0,
        "annual_spot_savings_usd": 100_000.0,
        "annual_waste_value_savings_usd": 5_000.0,
        "annual_lost_sale_recovery_usd": 0.0,
        "total_annual_benefit_usd": 105_000.0,
        "net_annual_benefit_usd": 90_012.0,
        "roi_multiple": 7.0,
        "payback_months": 1.7,
        "baseline_service_level_pct": 95.0,
        "target_service_level_pct": 96.0,
        "service_level_improvement_pts": 1.0,
        "spot_savings_pct": 30.0,
        "waste_kg_reduction_annual": 1500.0,
    }


def test_error_dict_raises_explicit_exception():
    with pytest.raises(ROIReportError) as excinfo:
        render_roi_report({"error": "No backtest data"}, pd.DataFrame())
    assert "No backtest data" in str(excinfo.value)


def test_missing_keys_raises_with_key_list():
    with pytest.raises(ROIReportError) as excinfo:
        render_roi_report({"total_annual_benefit_usd": 0.0}, pd.DataFrame())
    assert "missing required keys" in str(excinfo.value).lower()


def test_complete_roi_renders_html(tmp_path):
    out = tmp_path / "report.html"
    backtest_df = pd.DataFrame(
        [
            {"model": "deterministic", "origin_week": "2025-01-06",
             "horizon_weeks": 4, "service_level_pct": 95.0,
             "spot_kg": 1000, "waste_kg": 50, "spot_cost_usd": 2600,
             "total_cost_usd": 5000},
            {"model": "two_stage_sp", "origin_week": "2025-01-06",
             "horizon_weeks": 4, "service_level_pct": 96.0,
             "spot_kg": 700, "waste_kg": 30, "spot_cost_usd": 1820,
             "total_cost_usd": 4500},
        ]
    )
    html = render_roi_report(_full_roi(), backtest_df, output_path=out)
    assert out.exists()
    assert "<html" in html
    assert "$105,000" in html  # total annual benefit


def test_render_does_not_require_disk_write():
    html = render_roi_report(_full_roi(), pd.DataFrame())
    assert "<html" in html
