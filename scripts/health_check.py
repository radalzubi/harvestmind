#!/usr/bin/env python3
"""HarvestMind health check — content validation, not just 200 OK.

Hits every dashboard route + key Python entry points. Verifies the
response actually contains the expected data structure, not just that
the server didn't crash. Prints a pass/fail table and exits non-zero
if anything fails.

Usage:
  python scripts/health_check.py [--base-url http://localhost:3010]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_JSON = ROOT / "web" / "src" / "lib" / "backtest_summary.json"


def fetch(url: str, timeout: int = 10) -> tuple[int, bytes]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hm-health-check/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except (urllib.error.URLError, OSError) as e:
        return 0, str(e).encode()


def check(label: str, ok: bool, detail: str = "") -> dict:
    return {"label": label, "ok": ok, "detail": detail}


def check_route(base: str, path: str, validators: list) -> dict:
    """Hit a route and run each validator on the body. Pass if all pass."""
    url = base.rstrip("/") + path
    status, body = fetch(url)
    text = body.decode("utf-8", errors="replace")

    if status != 200:
        return check(f"{path}", False, f"HTTP {status}: {text[:120]}")

    for v in validators:
        try:
            err = v(text)
            if err:
                return check(f"{path}", False, err)
        except Exception as e:
            return check(f"{path}", False, f"validator {v.__name__} raised: {e}")
    return check(f"{path}", True, f"HTTP {status}")


# ── Validators ────────────────────────────────────────────────────────────────

def has_no_nan_or_undefined(text: str) -> str | None:
    """Reject if rendered HTML contains literal 'NaN' or unsentinelled 'undefined'.

    Next.js' React Server Components stream uses '$undefined' as a serialization
    marker — that's not a user-facing leak. We strip that pattern before checking.
    Likewise 'None' shows up in copy ("None scheduled", etc) so we don't flag it.
    """
    cleaned = text.replace("$undefined", "")
    bad = []
    if "NaN" in cleaned:
        bad.append("NaN")
    # Match standalone 'undefined' (not '$undefined' or 'undefined-something')
    import re
    leftover = re.findall(r'(?<![\w$])undefined(?![\w])', cleaned)
    if leftover:
        bad.append("undefined")
    return f"contains {', '.join(bad)}" if bad else None


def contains_brand(text: str) -> str | None:
    return None if "HarvestMind" in text else "missing HarvestMind brand text"


def contains_kpi_row(text: str) -> str | None:
    return None if "kpi-row" in text else "missing kpi-row class"


def contains_dollar(text: str) -> str | None:
    return None if "$" in text else "no dollar sign in rendered output"


def contains_period_pill(text: str) -> str | None:
    return None if "period-pill" in text else "missing period-pill"


# ── Backtest summary JSON validator ───────────────────────────────────────────

REQUIRED_KPI_FIELDS = [
    "annual_savings_usd",
    "annual_spot_premium_savings_usd",
    "annual_waste_reduction_usd",
    "fill_rate_baseline",
    "fill_rate_optimised",
    "fill_rate_lift_pts",
    "roi_multiple",
    "annual_subscription_usd",
    "confidence_low_usd",
    "confidence_high_usd",
    "spot_kg_avoided_period",
    "waste_kg_avoided_period",
    "lost_sale_kg_baseline",
    "lost_sale_kg_optimised",
    "annual_vss_usd",  # Audit 1H
]


def check_summary_json() -> dict:
    if not SUMMARY_JSON.exists():
        return check("backtest_summary.json", False,
                     f"missing — run scripts/build_dashboard_summary.py")
    try:
        data = json.loads(SUMMARY_JSON.read_text())
    except Exception as e:
        return check("backtest_summary.json", False, f"invalid JSON: {e}")
    kpis = data.get("kpis", {})
    missing = [k for k in REQUIRED_KPI_FIELDS if k not in kpis]
    if missing:
        return check("backtest_summary.json", False, f"missing fields: {missing}")
    if not data.get("per_origin"):
        return check("backtest_summary.json", False, "per_origin is empty")
    if not data.get("cost_trend"):
        return check("backtest_summary.json", False, "cost_trend is empty")
    return check("backtest_summary.json", True,
                 f"{data['config']['n_origins']} origins, vss={kpis.get('annual_vss_usd')}")


# ── Math sanity checks ────────────────────────────────────────────────────────

def check_lp_math() -> dict:
    """Verify the LP correctly produces commit + spot + lost_sale objective."""
    try:
        sys.path.insert(0, str(ROOT))
        from optimization.lp_baseline import LPBaseline
        import pandas as pd
        demand = pd.DataFrame([{"product_id":"P1","week_start":"2025-01-01","demand_kg":100.0}])
        supply = pd.DataFrame([{"supplier_id":"S1","product_id":"P1","week_start":"2025-01-01","capacity_kg":60.0,"price_per_kg":2.0}])
        result = LPBaseline(lost_sale_per_kg_usd=3.0, spot_capacity_factor=0.20).solve(demand, supply)
        if result["status"] not in ("optimal", "locallyOptimal"):
            return check("LP solves to optimal", False, f"status={result['status']}")
        # Expected: 60×2 + 20×2×1.30 + 20×3 = 232
        if not (231 < result["objective"] < 233):
            return check("LP math (commit=60, spot=20, unmet=20)",
                         False, f"objective={result['objective']:.2f}, expected 232.00")
        return check("LP math", True, f"objective={result['objective']:.2f} (expected 232.00)")
    except Exception as e:
        return check("LP math", False, f"raised: {e}")


def check_recourse_empty_supply() -> dict:
    """Verify empty realized supply ⇒ 100% spot (NOT silent zero waste fallback)."""
    try:
        sys.path.insert(0, str(ROOT))
        from optimization.recourse_simulator import simulate_recourse
        import pandas as pd
        commit = pd.DataFrame([{"supplier_id":"S1","product_id":"P1","committed_kg":100.0,"price_per_kg":2.0}])
        demand = pd.DataFrame([{"product_id":"P1","demand_kg":100.0}])
        empty = pd.DataFrame(columns=["supplier_id","product_id","actual_available_kg"])
        rec = simulate_recourse(commit, demand, empty)
        if rec["spot_kg"] != 100.0 or rec["waste_kg"] != 0.0:
            return check("Recourse empty-supply fallback", False,
                         f"spot={rec['spot_kg']}, waste={rec['waste_kg']} (expected spot=100, waste=0)")
        return check("Recourse empty-supply fallback", True,
                     "100% spot when no deliveries recorded")
    except Exception as e:
        return check("Recourse empty-supply fallback", False, f"raised: {e}")


def check_pooling() -> dict:
    """Verify supplier-A surplus offsets supplier-B shortfall."""
    try:
        sys.path.insert(0, str(ROOT))
        from optimization.recourse_simulator import simulate_recourse
        import pandas as pd
        commits = pd.DataFrame([
            {"supplier_id":"A","product_id":"P1","committed_kg":60.0,"price_per_kg":2.0},
            {"supplier_id":"B","product_id":"P1","committed_kg":40.0,"price_per_kg":2.0},
        ])
        demand = pd.DataFrame([{"product_id":"P1","demand_kg":100.0}])
        # A short, B surplus, total=100=demand
        supply = pd.DataFrame([
            {"supplier_id":"A","product_id":"P1","actual_available_kg":30.0},
            {"supplier_id":"B","product_id":"P1","actual_available_kg":70.0},
        ])
        rec = simulate_recourse(commits, demand, supply)
        if rec["spot_kg"] != 0 or rec["service_level_pct"] != 100.0:
            return check("Recourse supply pooling", False,
                         f"spot={rec['spot_kg']}, service={rec['service_level_pct']}")
        return check("Recourse supply pooling", True, "surplus offsets shortfall")
    except Exception as e:
        return check("Recourse supply pooling", False, f"raised: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://localhost:3010")
    p.add_argument("--skip-routes", action="store_true",
                   help="Skip dashboard route checks (run only Python sanity)")
    args = p.parse_args()

    results: list[dict] = []

    # Math sanity
    print("\n── Math sanity ──")
    for fn in (check_lp_math, check_recourse_empty_supply, check_pooling):
        r = fn()
        results.append(r)
        print(f"  {'✓' if r['ok'] else '✗'} {r['label']}: {r['detail']}")

    # JSON summary
    print("\n── Backtest summary JSON ──")
    r = check_summary_json()
    results.append(r)
    print(f"  {'✓' if r['ok'] else '✗'} {r['label']}: {r['detail']}")

    # Dashboard routes
    if not args.skip_routes:
        print(f"\n── Dashboard routes ({args.base_url}) ──")
        common = [has_no_nan_or_undefined, contains_brand, contains_period_pill]
        routes = [
            ("/",                 [contains_kpi_row, contains_dollar] + common),
            ("/performance",      [contains_kpi_row, contains_dollar] + common),
            ("/recommendations",  [contains_kpi_row] + common),
            ("/backtest",         [contains_kpi_row, contains_dollar] + common),
            ("/loss",             [contains_kpi_row, contains_dollar] + common),
            ("/partners",         common),
            ("/data-quality",     [contains_kpi_row] + common),
            ("/reports",          common),
        ]
        for path, validators in routes:
            r = check_route(args.base_url, path, validators)
            results.append(r)
            print(f"  {'✓' if r['ok'] else '✗'} {r['label']}: {r['detail']}")

    # Summary
    n_pass = sum(1 for r in results if r["ok"])
    n_fail = sum(1 for r in results if not r["ok"])
    print(f"\n══════════════════════════════════════════════════════════")
    print(f"  {n_pass}/{len(results)} passed   ({n_fail} failed)")
    print(f"══════════════════════════════════════════════════════════")

    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
