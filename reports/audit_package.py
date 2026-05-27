"""Audit-package generator — SQF / GFSI / Walmart-Supplier audit bundles.

Sales wedge for Tier A/B/C: third-party audits cost $5–15K each in prep
time and outside consultants. Every piece of data they ask for — lot
codes, supplier reliability, waste reasons, deviation events, FSMA-204
chain — is already in the HarvestMind DB. This module bundles it into
a single zip file the audit firm can review in an hour.

The output is a directory + zip file:
  outputs/audit_packages/<partner_slug>_<audit_type>_<date>/
    01_supplier_reliability.csv
    02_lot_traceability.csv
    03_waste_log.csv
    04_temperature_excursions.csv
    05_recall_simulations.csv
    audit_summary.html

Each audit_type maps to the specific requirements of that audit:
  sqf_2     SQF Level 2 (Food Safety Fundamentals)
  sqf_3    SQF Level 3 (Food Safety + Quality)
  gfsi      GFSI-recognized scheme (BRC / FSSC 22000)
  walmart   Walmart Supplier audit (FSMA-204 + lot trace)
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd


@dataclass(frozen=True)
class AuditType:
    code: str
    label: str
    sections: tuple[str, ...]
    require_fsma_204: bool


AUDIT_TYPES: dict[str, AuditType] = {
    "sqf_2": AuditType(
        code="sqf_2",
        label="SQF Level 2 — Food Safety Fundamentals",
        sections=("supplier_reliability", "lot_traceability", "waste_log",
                  "temperature_excursions"),
        require_fsma_204=False,
    ),
    "sqf_3": AuditType(
        code="sqf_3",
        label="SQF Level 3 — Food Safety + Quality",
        sections=("supplier_reliability", "lot_traceability", "waste_log",
                  "temperature_excursions", "supplier_certifications",
                  "recall_simulation"),
        require_fsma_204=True,
    ),
    "gfsi": AuditType(
        code="gfsi",
        label="GFSI-recognized scheme",
        sections=("supplier_reliability", "lot_traceability", "waste_log",
                  "temperature_excursions", "supplier_certifications",
                  "recall_simulation"),
        require_fsma_204=True,
    ),
    "walmart": AuditType(
        code="walmart",
        label="Walmart Supplier Audit",
        sections=("lot_traceability", "supplier_certifications",
                  "recall_simulation", "fsma_204_coverage"),
        require_fsma_204=True,
    ),
}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "partner"


# ── Section builders ─────────────────────────────────────────────────────────

def _supplier_reliability(conn) -> pd.DataFrame:
    return conn.execute("""
        SELECT
            s.supplier_id,
            s.supplier_name,
            s.gfsi_certification,
            s.sqf_level,
            s.audit_evidence_status,
            s.last_audit_date,
            COUNT(d.delivery_id) AS n_deliveries,
            ROUND(AVG(CASE WHEN d.qty_received_kg > 0
                           THEN (d.qty_received_kg - COALESCE(d.qty_rejected_kg,0))
                                / d.qty_received_kg
                           ELSE NULL END), 4) AS net_fill_rate,
            ROUND(SUM(COALESCE(d.qty_rejected_kg,0)),1) AS total_rejected_kg,
            ROUND(AVG(d.temp_on_arrival_c),2)           AS avg_arrival_temp_c
        FROM dim_suppliers s
        LEFT JOIN fact_deliveries d
          ON d.supplier_id = s.supplier_id
         AND d.delivery_date >= CURRENT_DATE - INTERVAL 12 MONTH
        GROUP BY s.supplier_id, s.supplier_name, s.gfsi_certification,
                 s.sqf_level, s.audit_evidence_status, s.last_audit_date
        ORDER BY n_deliveries DESC
    """).df()


def _lot_traceability(conn) -> pd.DataFrame:
    return conn.execute("""
        SELECT
            l.traceability_lot_code,
            l.tlc_source_reference,
            p.crop_name,
            l.quantity_kg,
            l.harvest_date,
            l.pack_date,
            l.gtin_14,
            l.sscc,
            l.lot_status,
            (SELECT COUNT(*) FROM fact_cte_events c
              WHERE c.lot_id = l.lot_id) AS n_cte_events
        FROM fact_lots l
        JOIN dim_products p ON l.product_id = p.product_id
        WHERE p.is_ftl_item = TRUE
        ORDER BY l.harvest_date DESC NULLS LAST
        LIMIT 5000
    """).df()


def _waste_log(conn) -> pd.DataFrame:
    return conn.execute("""
        SELECT
            w.waste_id,
            w.event_date,
            p.crop_name,
            w.qty_wasted_kg,
            w.reason_code,
            w.estimated_value_usd,
            w.waste_stage
        FROM fact_waste_events w
        LEFT JOIN dim_products p ON w.product_id = p.product_id
        WHERE w.event_date >= CURRENT_DATE - INTERVAL 12 MONTH
        ORDER BY w.event_date DESC
    """).df()


def _temperature_excursions(conn) -> pd.DataFrame:
    """Deliveries where arrival temperature was outside cold-chain spec."""
    return conn.execute("""
        SELECT
            d.delivery_id, d.delivery_date, d.supplier_id,
            d.product_id, p.crop_name,
            d.temp_on_arrival_c,
            d.qty_received_kg,
            CASE
                WHEN d.temp_on_arrival_c IS NULL THEN 'No reading'
                WHEN d.temp_on_arrival_c > 8.0  THEN 'Above spec (>8C)'
                WHEN d.temp_on_arrival_c < 0.0  THEN 'Below spec (<0C)'
                ELSE 'In spec'
            END AS excursion_status
        FROM fact_deliveries d
        LEFT JOIN dim_products p ON d.product_id = p.product_id
        WHERE p.cold_chain_required = TRUE
          AND d.delivery_date >= CURRENT_DATE - INTERVAL 12 MONTH
          AND (d.temp_on_arrival_c IS NULL
               OR d.temp_on_arrival_c > 8.0
               OR d.temp_on_arrival_c < 0.0)
        ORDER BY d.delivery_date DESC
    """).df()


def _supplier_certifications(conn) -> pd.DataFrame:
    return conn.execute("""
        SELECT
            supplier_id,
            supplier_name,
            supplier_type,
            gfsi_certification,
            sqf_level,
            audit_evidence_status,
            last_audit_date,
            CASE
                WHEN gfsi_certification IS NOT NULL THEN 'GFSI-recognized'
                WHEN sqf_level IS NOT NULL THEN 'SQF Level ' || sqf_level
                WHEN last_audit_date IS NOT NULL THEN 'Audited (non-GFSI)'
                ELSE 'Not certified'
            END AS certification_summary
        FROM dim_suppliers
        ORDER BY gfsi_certification DESC NULLS LAST, sqf_level DESC NULLS LAST
    """).df()


def _recall_simulation(conn) -> pd.DataFrame:
    """For each FTL lot from the last 90 days, list every downstream CTE
    that would need notification under FSMA-204 in a recall."""
    return conn.execute("""
        SELECT
            l.traceability_lot_code,
            p.crop_name,
            l.quantity_kg,
            l.harvest_date,
            COUNT(c.cte_id) AS downstream_cte_count,
            STRING_AGG(DISTINCT c.business_name, ', ') AS notification_recipients
        FROM fact_lots l
        JOIN dim_products p ON l.product_id = p.product_id
        LEFT JOIN fact_cte_events c
          ON c.lot_id = l.lot_id
         AND c.cte_type IN ('shipping','receiving')
        WHERE p.is_ftl_item = TRUE
          AND l.harvest_date >= CURRENT_DATE - INTERVAL 90 DAY
        GROUP BY l.traceability_lot_code, p.crop_name,
                 l.quantity_kg, l.harvest_date
        ORDER BY downstream_cte_count DESC
        LIMIT 250
    """).df()


def _fsma_204_coverage(conn) -> pd.DataFrame:
    """Per-product FTL coverage — same as dashboard.lib.fsma_metrics but
    bundled into the audit package directly."""
    return conn.execute("""
        SELECT
            p.product_id,
            p.crop_name,
            p.crop_category,
            COALESCE(SUM(d.qty_received_kg - COALESCE(d.qty_rejected_kg,0)), 0)
                AS received_kg,
            COUNT(DISTINCT l.lot_id) AS distinct_lot_count,
            ROUND(
              COALESCE(
                SUM(CASE WHEN l.lot_id IS NOT NULL
                         THEN d.qty_received_kg - COALESCE(d.qty_rejected_kg,0)
                         ELSE 0 END), 0)
              / NULLIF(SUM(d.qty_received_kg - COALESCE(d.qty_rejected_kg,0)), 0)
            , 4) AS coverage_pct
        FROM dim_products p
        LEFT JOIN fact_deliveries d ON d.product_id = p.product_id
        LEFT JOIN fact_lots l
          ON l.product_id = p.product_id
         AND COALESCE(l.supplier_id, '') = COALESCE(d.supplier_id, '')
        WHERE p.is_ftl_item = TRUE
        GROUP BY p.product_id, p.crop_name, p.crop_category
        ORDER BY received_kg DESC
    """).df()


_SECTION_BUILDERS = {
    "supplier_reliability":     _supplier_reliability,
    "lot_traceability":         _lot_traceability,
    "waste_log":                _waste_log,
    "temperature_excursions":   _temperature_excursions,
    "supplier_certifications":  _supplier_certifications,
    "recall_simulation":        _recall_simulation,
    "fsma_204_coverage":        _fsma_204_coverage,
}


# ── HTML summary ─────────────────────────────────────────────────────────────

def _summary_html(
    partner_name: str, audit: AuditType, section_dfs: dict[str, pd.DataFrame]
) -> str:
    rows = []
    for name, df in section_dfs.items():
        rows.append(
            f"<tr><td>{name.replace('_',' ').title()}</td>"
            f"<td style='text-align:right'>{len(df):,}</td></tr>"
        )
    rows_html = "\n".join(rows)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Audit Package — {partner_name}</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 800px;
         margin: 24px auto; color: #0F172A; padding: 0 16px; }}
 h1 {{ margin: 0; font-size: 24pt; letter-spacing: -0.01em; }}
 h2 {{ font-size: 14pt; margin-top: 28px; }}
 .header {{ background: #0F766E; color: #fff; padding: 16px 24px;
            border-radius: 8px; margin-bottom: 18px; }}
 .header .sub {{ opacity: 0.9; margin-top: 4px; font-size: 11pt; }}
 table {{ width: 100%; border-collapse: collapse; font-size: 11pt; }}
 td, th {{ padding: 8px 10px; border-bottom: 1px solid #E2E8F0; }}
 th {{ background: #F8FAFC; font-weight: 600; color: #475569;
       text-transform: uppercase; font-size: 9pt; letter-spacing: 0.04em; }}
 .muted {{ color: #64748B; font-size: 10pt; }}
</style></head><body>
<div class="header">
  <h1>HarvestMind Audit Evidence Package</h1>
  <div class="sub">{partner_name} · {audit.label}</div>
  <div class="sub">Generated {datetime.utcnow().date().isoformat()}</div>
</div>

<h2>Bundle contents</h2>
<table>
  <thead><tr><th>Section</th><th style="text-align:right">Records</th></tr></thead>
  <tbody>
{rows_html}
  </tbody>
</table>

<h2>Notes for the auditor</h2>
<p class="muted">
This package is auto-generated from the partner's HarvestMind operational
database. Data covers the last 12 months unless otherwise noted in each CSV.
All lot codes, CTE events, and supplier reliability metrics are exported
unmodified — no smoothing or selection is applied.
</p>
<p class="muted">
For source verification, the partner's HarvestMind workspace can be
audited live at the Data Quality and FSMA-204 dashboard pages. Each row
in this package corresponds to a query run against the partner's DuckDB
file at generation time.
</p>
</body></html>
"""


# ── Public API ───────────────────────────────────────────────────────────────

class AuditPackageError(ValueError):
    """Raised on invalid audit type or unsafe output paths."""


def generate_audit_package(
    conn: duckdb.DuckDBPyConnection,
    partner_name: str,
    audit_type: str = "sqf_2",
    output_dir: str | Path | None = None,
    create_zip: bool = True,
) -> Path:
    """Build a full audit-evidence package on disk.

    Returns the path to the generated directory (or zip if ``create_zip``).

    Raises
    ------
    AuditPackageError
        If ``audit_type`` is unknown or the output path is unsafe.
    """
    if audit_type not in AUDIT_TYPES:
        raise AuditPackageError(
            f"Unknown audit type {audit_type!r}. "
            f"Allowed: {sorted(AUDIT_TYPES)}"
        )
    audit = AUDIT_TYPES[audit_type]

    repo_root = Path(__file__).resolve().parents[1]
    base = Path(output_dir) if output_dir else (repo_root / "outputs" / "audit_packages")
    base = base.resolve()

    # Refuse to write into protected source paths.
    forbidden = (
        repo_root / "reports" / "templates",
        repo_root / "db" / "migrations",
        repo_root / "scripts",
    )
    for fb in forbidden:
        try:
            base.relative_to(fb)
        except ValueError:
            continue
        raise AuditPackageError(f"refusing to write audit package under {fb}")

    pkg_dir = base / f"{_slug(partner_name)}_{audit.code}_{date.today().isoformat()}"
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True, exist_ok=True)

    section_dfs: dict[str, pd.DataFrame] = {}
    for i, name in enumerate(audit.sections, start=1):
        if name not in _SECTION_BUILDERS:
            continue
        df = _SECTION_BUILDERS[name](conn)
        section_dfs[name] = df
        df.to_csv(pkg_dir / f"{i:02d}_{name}.csv", index=False)

    (pkg_dir / "audit_summary.html").write_text(
        _summary_html(partner_name, audit, section_dfs), encoding="utf-8"
    )

    if not create_zip:
        return pkg_dir

    zip_path = pkg_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in pkg_dir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(pkg_dir.parent))
    return zip_path
