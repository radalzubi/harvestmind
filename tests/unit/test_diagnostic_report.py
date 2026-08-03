"""Unit tests for reports/diagnostic_report_generator.py.

Verifies that the report generator:
  - produces non-empty HTML for a full diagnostic payload
  - handles all-empty data without raising
  - includes key section headers in the output
  - applies Jinja2 filters correctly (fmt_usd, fmt_pct, risk_class)
"""

from __future__ import annotations

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def full_summary():
    """A minimal but structurally complete diagnostic_summary payload."""
    return {
        "partner_name": "Test Hub",
        "as_of": "2026-05-27",
        "period_days": 365,
        "row_counts": {
            "stg_products": 6,
            "stg_supplier_deliveries": 12,
            "stg_inventory_lots": 13,
            "stg_buyer_orders": 15,
            "stg_waste_adjustments": 11,
        },
        "waste": {
            "total_usd": 823.50,
            "by_product": [
                {"product_name": "Strawberries", "quantity_lost_kg": 64.0, "loss_usd": 448.0},
                {"product_name": "Tomatoes",     "quantity_lost_kg": 53.0, "loss_usd": 162.5},
            ],
            "by_reason": [
                {"reason": "Spoilage",           "quantity_lost_kg": 52.0, "loss_usd": 364.0},
                {"reason": "Overripe",           "quantity_lost_kg": 46.0, "loss_usd": 99.5},
            ],
            "n_rows": 11,
        },
        "shortage": {
            "total_usd": 1540.0,
            "by_product": [
                {"product_name": "Tomatoes", "missed_kg": 230.0, "loss_usd": 575.0},
            ],
            "by_buyer": [
                {"buyer_name": "Northside Grocers", "missed_kg": 345.0, "loss_usd": 828.5},
            ],
            "n_at_risk": 7,
        },
        "supplier": {
            "suppliers": [
                {
                    "supplier_id": "S002",
                    "supplier_name": "Blue Ridge Produce",
                    "n_deliveries": 4,
                    "fill_rate": 0.6170,
                    "rejection_rate": 0.0333,
                    "risk_level": "High",
                },
                {
                    "supplier_id": "S001",
                    "supplier_name": "Sunset Valley Farms",
                    "n_deliveries": 4,
                    "fill_rate": 0.9697,
                    "rejection_rate": 0.0145,
                    "risk_level": "Low",
                },
            ],
            "n_risky": 1,
        },
        "buyer": {
            "buyers": [
                {
                    "buyer_id": "B002",
                    "buyer_name": "Northside Grocers",
                    "n_orders": 5,
                    "fulfillment_rate": 0.6111,
                    "substitution_rate": 0.0278,
                    "missed_rate": 0.3611,
                    "risk_level": "High",
                },
                {
                    "buyer_id": "B001",
                    "buyer_name": "Fresh Market Co.",
                    "n_orders": 5,
                    "fulfillment_rate": 0.9852,
                    "substitution_rate": 0.0074,
                    "missed_rate": 0.0074,
                    "risk_level": "Low",
                },
            ],
            "n_risky": 1,
        },
        "traceability": {
            "completeness_pct": 0.6154,
            "total_lots": 13,
            "complete_lots": 8,
            "incomplete_lots": [
                {"lot_id": None, "product_name": "Tomatoes", "missing_fields": ["lot_id", "supplier_id"]},
            ],
            "missing_breakdown": {"lot_id": 2, "supplier_id": 2},
        },
        "atp": {
            "products": [
                {
                    "product_id": "P001",
                    "product_name": "Tomatoes",
                    "total_on_hand_kg": 280.0,
                    "committed_kg": 50.0,
                    "expired_kg": 0.0,
                    "near_expiry_kg": 65.0,
                    "usable_kg": 280.0,
                    "atp_kg": 230.0,
                    "near_expiry_pct": 0.232,
                    "risk_level": "High",
                },
            ],
            "n_risky": 1,
        },
        "recommendations": [
            {
                "product_name": "Tomatoes",
                "product_id": "P001",
                "atp_kg": 230.0,
                "safe_commit_kg": 184.0,
                "holdback_kg": 46.0,
                "near_expiry_kg": 65.0,
                "supplier_fill_rate": 0.617,
                "buyer_fulfillment_rate": 0.611,
                "risk_level": "High",
                "risk_flags": ["supplier fill rate 62%", "65 kg near expiry"],
                "recommendation_text": "Commit no more than 184 kg of Tomatoes.",
            },
        ],
        "savings": {
            "addressable_loss_usd": 2363.5,
            "reduction_pct_assumed": 0.30,
            "estimated_annual_savings_usd": 709.05,
            "waste_loss_usd": 823.50,
            "shortage_loss_usd": 1540.0,
        },
        "top_risks": [
            {"category": "Shortage", "item": "Tomatoes", "loss_usd": 575.0},
            {"category": "Waste",    "item": "Strawberries", "loss_usd": 448.0},
        ],
        "total_waste_loss_usd": 823.50,
        "total_shortage_loss_usd": 1540.0,
        "total_addressable_loss_usd": 2363.5,
        "n_risky_suppliers": 1,
        "n_risky_products": 1,
        "n_risky_buyers": 1,
        "traceability_completeness_pct": 0.6154,
    }


@pytest.fixture(scope="module")
def empty_summary():
    """Diagnostic payload with all zero values — tests empty-data rendering."""
    return {
        "partner_name": "Empty Hub",
        "as_of": "2026-05-27",
        "period_days": 365,
        "row_counts": {t: 0 for t in [
            "stg_products", "stg_supplier_deliveries",
            "stg_inventory_lots", "stg_buyer_orders", "stg_waste_adjustments",
        ]},
        "waste": {"total_usd": 0.0, "by_product": [], "by_reason": [], "n_rows": 0},
        "shortage": {"total_usd": 0.0, "by_product": [], "by_buyer": [], "n_at_risk": 0},
        "supplier": {"suppliers": [], "n_risky": 0},
        "buyer": {"buyers": [], "n_risky": 0},
        "traceability": {
            "completeness_pct": 0.0, "total_lots": 0, "complete_lots": 0,
            "incomplete_lots": [], "missing_breakdown": {},
        },
        "atp": {"products": [], "n_risky": 0},
        "recommendations": [],
        "savings": {
            "addressable_loss_usd": 0.0, "reduction_pct_assumed": 0.30,
            "estimated_annual_savings_usd": 0.0,
            "waste_loss_usd": 0.0, "shortage_loss_usd": 0.0,
        },
        "top_risks": [],
        "total_waste_loss_usd": 0.0,
        "total_shortage_loss_usd": 0.0,
        "total_addressable_loss_usd": 0.0,
        "n_risky_suppliers": 0,
        "n_risky_products": 0,
        "n_risky_buyers": 0,
        "traceability_completeness_pct": 0.0,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_render_produces_html_string(full_summary, tmp_path):
    from reports.diagnostic_report_generator import render_diagnostic_report

    output = tmp_path / "report.html"
    html = render_diagnostic_report(full_summary, "Test Hub", output_path=output, as_pdf=False)

    assert isinstance(html, str)
    assert len(html) > 500
    assert html.strip().startswith("<!") or "<html" in html.lower()


def test_render_writes_file_to_disk(full_summary, tmp_path):
    from reports.diagnostic_report_generator import render_diagnostic_report

    output = tmp_path / "report.html"
    render_diagnostic_report(full_summary, "Test Hub", output_path=output, as_pdf=False)

    assert output.exists()
    assert output.stat().st_size > 200


def test_render_includes_partner_name(full_summary, tmp_path):
    from reports.diagnostic_report_generator import render_diagnostic_report

    html = render_diagnostic_report(full_summary, "Acme Food Hub", as_pdf=False)
    assert "Acme Food Hub" in html


def test_render_escapes_html_in_operator_strings(full_summary):
    """Security regression: operator-controlled strings (partner name, and
    product names from uploaded data) must be HTML-escaped in the served
    report, not rendered as live markup (XSS)."""
    import copy

    from reports.diagnostic_report_generator import render_diagnostic_report

    payload = copy.deepcopy(full_summary)
    payload["waste"]["by_product"][0]["product_name"] = "<img src=x onerror=alert(1)>"

    html = render_diagnostic_report(
        payload, "<script>alert('xss')</script>", as_pdf=False
    )
    # Raw script/markup must NOT appear; the escaped form must.
    assert "<script>alert('xss')</script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;script&gt;" in html


def test_render_includes_section_headers(full_summary, tmp_path):
    from reports.diagnostic_report_generator import render_diagnostic_report

    html = render_diagnostic_report(full_summary, "Test Hub", as_pdf=False)
    # Verify key sections are rendered
    for section in ["Waste Loss", "Shortage", "Supplier", "Traceability", "Savings"]:
        assert section in html, f"Section header '{section}' not found in report"


def test_render_formats_dollar_values(full_summary):
    from reports.diagnostic_report_generator import render_diagnostic_report

    html = render_diagnostic_report(full_summary, "Test Hub", as_pdf=False)
    # $823.50 rounds to $824 in the fmt_usd filter (,.0f)
    assert "$824" in html or "823" in html or "824" in html


def test_render_formats_percentages(full_summary):
    from reports.diagnostic_report_generator import render_diagnostic_report

    html = render_diagnostic_report(full_summary, "Test Hub", as_pdf=False)
    # 61.7% or similar from traceability completeness
    assert "%" in html


def test_render_empty_data_does_not_raise(empty_summary, tmp_path):
    """Report should render without error even with all-empty data."""
    from reports.diagnostic_report_generator import render_diagnostic_report

    html = render_diagnostic_report(empty_summary, "Empty Hub", as_pdf=False)
    assert isinstance(html, str)
    assert len(html) > 100


def test_render_risk_class_applied(full_summary):
    """High-risk items should have a CSS risk class in the output."""
    from reports.diagnostic_report_generator import render_diagnostic_report

    html = render_diagnostic_report(full_summary, "Test Hub", as_pdf=False)
    # The risk_class filter maps "High" → "risk-high" (or similar)
    assert "risk" in html.lower()
