#!/usr/bin/env python3
"""HarvestMind master orchestration script — tier-aware.

Replaces the older `demo_run.py` for production / pilot use. Runs the
full HarvestMind pipeline scaled to one of the three customer tiers:

    tier        segment                           annual price
    A           Food hub                          $11,988
    A_HIGH      Food hub (premium)                $17,988
    B           Multi-site aggregator             $45,000
    C           Regional distributor              $75,000
    D           Enterprise distributor            $250,000

The script tunes backtest scope, scenario count, and report bundle
to the tier — a $250K Tier-D customer gets per-state cost trends and
SOC-2-shaped audit packaging; a $12K Tier-A hub gets the slim version.

Usage:
  python scripts/master_plan.py --tier A   --partner "Hoosier Harvest"  --gmv 3000000
  python scripts/master_plan.py --tier B   --partner "Indy Aggregator"  --gmv 25000000
  python scripts/master_plan.py --tier C   --partner "Piazza Produce"   --gmv 150000000
  python scripts/master_plan.py --tier D   --partner "Sysco Indianapolis" --gmv 750000000

The orchestration:
  1. Schema check + migration apply
  2. Validate / ingest partner data (hub) OR run against existing DB (tier B+)
  3. Run multi-tier backtest with tier-appropriate scope
  4. Compute ROI under live USDA pricing
  5. Generate audit-evidence package (SQF / GFSI / Walmart shape per tier)
  6. Generate FSMA-204 coverage report
  7. Generate carbon (Scope 3) report
  8. Generate grant-application metrics export
  9. Build pilot summary HTML
 10. Print verdict

Outputs land in outputs/master_run_<partner_slug>_<date>/ — everything
in one folder, ready to email or attach to a contract.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtesting.roi_calculator import (  # noqa: E402  (sys.path set above so the script runs from any cwd)
    SUBSCRIPTION_TIERS,
    benchmark_scenarios,
    compute_roi,
    _resolve_tier_pricing,
)
from backtesting.rolling_origin_engine import BacktestConfig, RollingOriginEngine  # noqa: E402  (sys.path set above so the script runs from any cwd)
from dashboard.lib.carbon_metrics import backfill_estimated_co2e, carbon_summary  # noqa: E402  (sys.path set above so the script runs from any cwd)
from dashboard.lib.fsma_metrics import fsma_coverage_score  # noqa: E402  (sys.path set above so the script runs from any cwd)
from dashboard.lib.metrics import data_quality_breakdown  # noqa: E402  (sys.path set above so the script runs from any cwd)
from reports.audit_package import generate_audit_package  # noqa: E402  (sys.path set above so the script runs from any cwd)
from reports.grant_export import generate_grant_csv  # noqa: E402  (sys.path set above so the script runs from any cwd)
from reports.pilot_summary_generator import render_pilot_summary  # noqa: E402  (sys.path set above so the script runs from any cwd)
from scripts.stress_test_backtest import SCENARIOS as STRESS_SCENARIOS  # noqa: E402  (sys.path set above so the script runs from any cwd)
from scripts.stress_test_backtest import run_one as stress_run_one  # noqa: E402  (sys.path set above so the script runs from any cwd)


# Tier → orchestration profile.
# Higher tiers = longer training window, more SAA scenarios, GFSI audit,
# more comprehensive deliverables.
TIER_PROFILES: dict[str, dict] = {
    "A": {
        "audit_type":      "sqf_2",
        "n_train_weeks":   26,
        "n_scenarios":     20,
        "step_weeks":      8,
        "stress_test":     True,
        "soc2_required":   False,
        "include_carbon":  True,
        "include_grants":  True,
    },
    "A_HIGH": {
        "audit_type":      "sqf_3",
        "n_train_weeks":   26,
        "n_scenarios":     30,
        "step_weeks":      8,
        "stress_test":     True,
        "soc2_required":   False,
        "include_carbon":  True,
        "include_grants":  True,
    },
    "B": {
        "audit_type":      "sqf_3",
        "n_train_weeks":   52,
        "n_scenarios":     50,
        "step_weeks":      4,
        "stress_test":     True,
        "soc2_required":   True,
        "include_carbon":  True,
        "include_grants":  True,
    },
    "C": {
        "audit_type":      "gfsi",
        "n_train_weeks":   52,
        "n_scenarios":     75,
        "step_weeks":      4,
        "stress_test":     True,
        "soc2_required":   True,
        "include_carbon":  True,
        "include_grants":  False,   # distributors don't typically apply for these
    },
    "D": {
        "audit_type":      "walmart",
        "n_train_weeks":   78,
        "n_scenarios":     100,
        "step_weeks":      2,
        "stress_test":     True,
        "soc2_required":   True,
        "include_carbon":  True,
        "include_grants":  False,
    },
}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "partner"


def _hr(c: str = "─") -> None:
    print(c * 78)


def _section(title: str) -> None:
    print()
    _hr()
    print(f"  {title}")
    _hr()


# ── Pipeline stages ──────────────────────────────────────────────────────────

def stage_schema(db_path: Path) -> None:
    """Apply any pending migrations + assert basic schema."""
    con = duckdb.connect(str(db_path))
    for sql in sorted((ROOT / "db" / "migrations").glob("*.sql")):
        con.execute(sql.read_text())
    con.close()


def stage_load(db_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect(str(db_path), read_only=True)
    orders = con.execute("""
        SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg
        FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id
    """).df()
    deliveries = con.execute("""
        SELECT supplier_id, product_id, delivery_date,
               qty_received_kg, qty_rejected_kg
        FROM fact_deliveries
    """).df()
    con.close()
    return orders, deliveries


def stage_backtest(orders, deliveries, profile: dict) -> pd.DataFrame:
    cfg = BacktestConfig(
        n_train_weeks=profile["n_train_weeks"],
        horizon_weeks=4,
        step_weeks=profile["step_weeks"],
        n_scenarios=profile["n_scenarios"],
        gammas=[0, 4],
        run_stochastic=True,
        run_naive_baseline=True,
    )
    return RollingOriginEngine(cfg).run(orders, deliveries)


def stage_stress(orders, deliveries, profile: dict) -> pd.DataFrame:
    """Run the 4-scenario degradation sweep. Returns DataFrame."""
    base_cfg = BacktestConfig(
        n_train_weeks=profile["n_train_weeks"],
        horizon_weeks=4,
        step_weeks=profile["step_weeks"],
        n_scenarios=profile["n_scenarios"],
        gammas=[0],
        run_stochastic=True,
        run_naive_baseline=True,
    )
    rows = []
    for s in STRESS_SCENARIOS:
        r = stress_run_one(orders, deliveries, s, base_cfg)
        if "error" not in r:
            rows.append(r)
    return pd.DataFrame(rows)


def stage_outputs(
    db_path: Path,
    out_dir: Path,
    partner: str,
    tier: str,
    profile: dict,
    backtest_df: pd.DataFrame,
    roi: dict,
    stress_df: pd.DataFrame | None,
) -> dict[str, Path]:
    """Produce every customer-facing artifact in one folder."""
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {}

    # 1. Backtest CSV
    bt_csv = out_dir / "backtest_results.csv"
    backtest_df.to_csv(bt_csv, index=False)
    artifacts["backtest"] = bt_csv

    # 2. ROI JSON
    roi_json = out_dir / "roi.json"
    roi_json.write_text(json.dumps(roi, indent=2, default=str))
    artifacts["roi"] = roi_json

    # 3. Audit package (zip)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        audit_zip = generate_audit_package(
            con,
            partner_name=partner,
            audit_type=profile["audit_type"],
            output_dir=out_dir / "audit_package",
            create_zip=True,
        )
        artifacts["audit"] = audit_zip
    except Exception as e:
        print(f"  ⚠ audit package skipped: {e}")
    con.close()

    # 4. FSMA-204 coverage
    con = duckdb.connect(str(db_path), read_only=True)
    fsma = fsma_coverage_score(con)
    con.close()
    fsma_json = out_dir / "fsma_204_coverage.json"
    fsma_json.write_text(json.dumps(fsma, indent=2, default=str))
    artifacts["fsma_204"] = fsma_json

    # 5. Carbon (Scope 3)
    if profile.get("include_carbon"):
        con = duckdb.connect(str(db_path))
        try:
            backfill_estimated_co2e(con)
            summary = carbon_summary(con)
        finally:
            con.close()
        cb_json = out_dir / "carbon_scope3_summary.json"
        cb_json.write_text(json.dumps(summary, indent=2, default=str))
        artifacts["carbon"] = cb_json

    # 6. Grant export
    if profile.get("include_grants"):
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            grant_csv = out_dir / "grant_application_metrics.csv"
            generate_grant_csv(con, grant_csv, partner_name=partner)
            artifacts["grants"] = grant_csv
        finally:
            con.close()

    # 7. Pilot summary HTML
    con = duckdb.connect(str(db_path), read_only=True)
    dq = [{"dataset": d.dataset, "rows": d.rows, "status": d.status}
          for d in data_quality_breakdown(con)]
    con.close()

    pilot_html = out_dir / "pilot_summary.html"
    try:
        render_pilot_summary(
            roi=roi,
            backtest_df=backtest_df,
            partner_name=partner,
            output_path=pilot_html,
            stress_test_df=stress_df,
            data_quality=dq,
        )
        artifacts["pilot_summary"] = pilot_html
    except Exception as e:
        print(f"  ⚠ pilot summary skipped: {e}")

    return artifacts


# ── Verdict + print ──────────────────────────────────────────────────────────

def _verdict(roi: dict, tier: str) -> tuple[bool, str]:
    """Tier-specific commercial-claim verdict.

    Higher tiers need higher absolute benefit to justify their fee, but
    can tolerate lower ROI multiples because the fee is large.
    """
    benefit = float(roi.get("total_annual_benefit_usd") or 0)
    sub = float(roi.get("annual_subscription_usd") or 1)
    multiple = benefit / sub
    if tier in ("A", "A_HIGH") and multiple >= 1.5:
        return True, "Hub-tier ROI meets the 1.5×+ commercial floor."
    if tier == "B" and multiple >= 1.5:
        return True, "Aggregator-tier ROI clears the 1.5× threshold."
    if tier in ("C", "D") and multiple >= 1.2:
        return True, "Distributor-tier ROI clears the 1.2× threshold."
    return False, (
        f"ROI multiple {multiple:.2f}× is below the {tier}-tier floor. "
        "Recalibrate scope or tier-down before going to partner."
    )


def _print_summary(
    partner: str, tier: str, roi: dict, fsma: dict, carbon: dict | None,
    out_dir: Path, artifacts: dict[str, Path], elapsed_s: float,
    supported: bool, msg: str,
) -> None:
    pricing = _resolve_tier_pricing(tier)
    _hr("═")
    print(f"  HarvestMind master run — {partner}")
    print(f"  Tier {tier} ({pricing['label']}) · ${int(pricing['annual']):,}/yr")
    _hr("═")
    print(f"  Annual benefit:        ${int(roi.get('total_annual_benefit_usd', 0)):,}")
    print(f"  Net annual benefit:    ${int(roi.get('net_annual_benefit_usd', 0)):,}")
    print(f"  ROI multiple:          {roi.get('roi_multiple', 0)}×")
    print(f"  Payback period:        {roi.get('payback_months', 0)} mo")
    print(f"  Fill rate:             {roi.get('baseline_service_level_pct',0)}% → "
          f"{roi.get('target_service_level_pct',0)}%")
    print(f"  FSMA-204 coverage:     {fsma['coverage_pct']*100:.0f}% ({fsma['status']})")
    if carbon is not None:
        print(f"  Scope-3 CO2e (12 mo):  {carbon['total_co2e_t']:,.2f} t  ·  "
              f"{carbon['coverage_pct']*100:.0f}% coverage")
    _hr()
    print(f"  Output bundle: {out_dir}")
    for k, v in artifacts.items():
        print(f"    {k:<14} {v.name}")
    _hr()
    print(f"  Verdict: {'✓ SUPPORTED' if supported else '✗ NEEDS REVISION'}")
    print(f"  {msg}")
    print(f"  Run time: {elapsed_s:.1f}s")
    _hr("═")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=str(ROOT / "harvestmind.duckdb"))
    p.add_argument("--partner", required=True, help="Partner / customer display name")
    p.add_argument("--tier", choices=list(SUBSCRIPTION_TIERS), default="A",
                   help="Customer tier (A, A_HIGH, B, C, D)")
    p.add_argument("--gmv", type=float, default=3_000_000.0,
                   help="Annual GMV in USD (used for lost-sale recovery)")
    p.add_argument("--out", default=None,
                   help="Output directory (default: outputs/master_run_<slug>_<date>)")
    p.add_argument("--skip-stress", action="store_true",
                   help="Skip the degradation stress test sweep")
    args = p.parse_args()

    profile = TIER_PROFILES[args.tier]
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] DB not found: {db_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.out) if args.out else (
        ROOT / "outputs" / f"master_run_{_slug(args.partner)}_{date.today().isoformat()}"
    )
    if out_dir.exists():
        shutil.rmtree(out_dir)

    t0 = time.time()
    _hr("═")
    print(f"  HarvestMind master plan — Tier {args.tier} ({profile['audit_type'].upper()} audit)")
    print(f"  Partner: {args.partner}   GMV: ${int(args.gmv):,}")
    _hr("═")

    _section("1. Schema check + migrations")
    stage_schema(db_path)

    _section("2. Load data")
    orders, deliveries = stage_load(db_path)
    print(f"  orders: {len(orders):,}   deliveries: {len(deliveries):,}")

    _section(f"3. Backtest ({profile['n_train_weeks']}w train · "
             f"{profile['n_scenarios']} SAA scenarios · "
             f"step={profile['step_weeks']}w)")
    backtest_df = stage_backtest(orders, deliveries, profile)
    if backtest_df.empty:
        print("[ERROR] backtest returned no results", file=sys.stderr)
        return 1

    _section("4. ROI under live USDA basket pricing")
    con = duckdb.connect(str(db_path), read_only=True)
    roi = compute_roi(
        backtest_df,
        baseline_model="naive_lastyear",
        target_model="two_stage_sp",
        annual_gmv_usd=args.gmv,
        subscription_tier=args.tier,
    )
    bench_df = benchmark_scenarios(
        backtest_df, annual_gmv_usd=args.gmv, conn=con,
    )
    con.close()

    if not bench_df.empty:
        bench_df.to_csv(out_dir / "benchmark_scenarios.csv", index=False) \
            if out_dir.exists() else None  # ensure dir exists below

    stress_df = None
    if not args.skip_stress and profile["stress_test"]:
        _section("5. Stress test — degraded baselines")
        stress_df = stage_stress(orders, deliveries, profile)
        if not stress_df.empty:
            for _, row in stress_df.iterrows():
                print(f"  {row['label']:<25}  ROI {row['roi']:>5.2f}×  "
                      f"Δfill {row['fill_lift_pts']:+.1f} pts  "
                      f"saved ${int(row['annual_saved_usd']):,}/yr")

    _section("6. Build customer-facing bundle")
    artifacts = stage_outputs(
        db_path, out_dir, args.partner, args.tier, profile,
        backtest_df, roi, stress_df,
    )
    if not bench_df.empty:
        bench_df.to_csv(out_dir / "benchmark_scenarios.csv", index=False)
        artifacts["benchmark_scenarios"] = out_dir / "benchmark_scenarios.csv"

    # Pull FSMA + carbon summaries for the printed verdict
    con = duckdb.connect(str(db_path), read_only=True)
    fsma_summary = fsma_coverage_score(con)
    con.close()
    carbon_data = None
    if profile.get("include_carbon"):
        con = duckdb.connect(str(db_path))
        try:
            carbon_data = carbon_summary(con)
        finally:
            con.close()

    supported, msg = _verdict(roi, args.tier)
    elapsed = time.time() - t0
    _print_summary(
        args.partner, args.tier, roi, fsma_summary, carbon_data,
        out_dir, artifacts, elapsed, supported, msg,
    )
    return 0 if supported else 1


if __name__ == "__main__":
    sys.exit(main())
