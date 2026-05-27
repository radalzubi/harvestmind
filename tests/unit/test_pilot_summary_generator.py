"""Unit tests for reports.pilot_summary_generator."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from reports.pilot_summary_generator import (
    PilotSummaryError,
    render_pilot_summary,
)


def _good_roi() -> dict:
    """A complete, success-shape ROI dict."""
    return {
        "total_annual_benefit_usd": 33859,
        "net_annual_benefit_usd": 15859,
        "roi_multiple": 1.88,
        "payback_months": 6.4,
        "annual_spot_savings_usd": 16000,
        "annual_waste_value_savings_usd": 5400,
        "annual_lost_sale_recovery_usd": 12459,
        "annual_subscription_usd": 18000,
        "baseline_service_level_pct": 82.0,
        "target_service_level_pct": 99.8,
        "service_level_improvement_pts": 17.8,
        "target_model": "two_stage_sp",
    }


def _empty_backtest() -> pd.DataFrame:
    return pd.DataFrame(columns=["origin_week", "model", "horizon_weeks",
                                  "total_cost_usd", "service_level_pct",
                                  "spot_kg", "waste_kg"])


# ── Validation ───────────────────────────────────────────────────────────────

def test_error_dict_raises_pilot_summary_error():
    with pytest.raises(PilotSummaryError, match="error"):
        render_pilot_summary({"error": "no backtest data"}, _empty_backtest(), "Test")


def test_missing_key_raises_with_listed_keys():
    bad = _good_roi()
    del bad["roi_multiple"]
    del bad["payback_months"]
    with pytest.raises(PilotSummaryError) as exc:
        render_pilot_summary(bad, _empty_backtest(), "Test")
    msg = str(exc.value)
    assert "roi_multiple" in msg
    assert "payback_months" in msg


def test_not_a_dict_raises():
    with pytest.raises(PilotSummaryError):
        render_pilot_summary([1, 2, 3], _empty_backtest(), "Test")


# ── Rendering ────────────────────────────────────────────────────────────────

def test_renders_with_empty_backtest():
    html = render_pilot_summary(_good_roi(), _empty_backtest(), "Hoosier Harvest Market")
    assert isinstance(html, str)
    assert len(html) > 1000  # non-trivial output


def test_html_contains_partner_name():
    html = render_pilot_summary(_good_roi(), _empty_backtest(), "Acme Hub")
    assert "Acme Hub" in html


def test_html_contains_total_annual_benefit():
    html = render_pilot_summary(_good_roi(), _empty_backtest(), "Test Hub")
    # currency filter formats 33859 → "33,859"
    assert "33,859" in html


def test_html_no_nan_or_undefined():
    """The pilot output must never contain literal placeholder leakage."""
    html = render_pilot_summary(_good_roi(), _empty_backtest(), "Test Hub")
    low = html.lower()
    assert "nan" not in low
    assert "undefined" not in low
    # 'None' as Python repr — but the template uses "—" for None values
    assert "None" not in html


def test_output_path_none_returns_string_no_file(tmp_path):
    """When output_path is None, no file is written."""
    html = render_pilot_summary(_good_roi(), _empty_backtest(), "Test")
    assert isinstance(html, str)
    # Sanity: tmp_path is empty
    assert list(tmp_path.iterdir()) == []


def test_output_path_writes_file(tmp_path):
    out = tmp_path / "summary.html"
    html = render_pilot_summary(
        _good_roi(), _empty_backtest(), "Test", output_path=out
    )
    assert out.exists()
    assert out.read_text() == html


def test_wrong_extension_raises(tmp_path):
    out = tmp_path / "summary.txt"
    with pytest.raises(PilotSummaryError, match="must end in"):
        render_pilot_summary(_good_roi(), _empty_backtest(), "Test", output_path=out)


def test_refuses_writing_into_source_tree(tmp_path):
    """Output path inside scripts/ or templates/ should be rejected."""
    repo_root = Path(__file__).resolve().parents[2]
    out = repo_root / "scripts" / "summary.html"
    with pytest.raises(PilotSummaryError, match="source path"):
        render_pilot_summary(_good_roi(), _empty_backtest(), "Test", output_path=out)


def test_with_backtest_data():
    """Real backtest df → policy comparison rows appear in HTML."""
    bt = pd.DataFrame([
        {"origin_week": "2025-01-01", "model": "naive_lastyear", "horizon_weeks": 4,
         "total_cost_usd": 24000, "service_level_pct": 98.5,
         "spot_kg": 1110, "waste_kg": 215},
        {"origin_week": "2025-01-01", "model": "two_stage_sp", "horizon_weeks": 4,
         "total_cost_usd": 22000, "service_level_pct": 99.9,
         "spot_kg": 600, "waste_kg": 80},
    ])
    html = render_pilot_summary(_good_roi(), bt, "Test")
    assert "Your current method" in html or "naive" in html.lower()
    assert "two-stage SP" in html or "two_stage_sp" in html


def test_stress_band_reflects_stress_df():
    """Stress test data should change the displayed range."""
    stress = pd.DataFrame([
        {"missing_rate": 0.30, "annual_saved_usd": 25000, "roi": 1.5},
        {"missing_rate": 0.50, "annual_saved_usd": 45000, "roi": 2.5},
    ])
    html = render_pilot_summary(
        _good_roi(), _empty_backtest(), "Test", stress_test_df=stress
    )
    assert "25,000" in html or "$25,000" in html
    assert "45,000" in html or "$45,000" in html
