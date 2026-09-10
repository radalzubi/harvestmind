"""Reproduce audit tables. Unknown market counts are never filled with guesses."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import statistics as st

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/remodel/evidence"


def csv_out(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def commercial():
    acvs = (6000, 12000, 18000, 25000, 36000, 50000, 75000, 100000)
    markets = ("Saudi Arabia", "UAE", "Jordan", "Egypt", "Kuwait", "Qatar", "Oman", "Bahrain",
               "Morocco", "Iraq", "Lebanon", "Algeria", "Tunisia", "Palestine", "US")
    (OUT / "market_inputs.json").write_text(json.dumps({
        "status": "insufficient verified eligible buying-group counts; not a numerical TAM estimate",
        "currency": "USD", "ACV_sensitivity": acvs,
        "markets": [{"country": m, "eligible_buying_groups": None, "TAM": None, "SAM": None, "SOM": None}
                    for m in markets],
        "GCC": ["Saudi Arabia", "UAE", "Kuwait", "Qatar", "Oman", "Bahrain"],
        "MENA_scope": list(markets[:-1]),
        "aggregation": "deduplicate buying groups; GCC is a subset of this MENA definition",
    }, indent=2))
    csv_out(OUT / "revenue_sensitivity.csv", [dict(active_customers=n, assumed_ACV=a, conditional_ARR=n*a,
                 evidence="arithmetic scenario, not market count or sales forecast")
                 for n in (1, 5, 10, 25, 50, 100, 250, 500, 1000, 4000) for a in acvs])
    csv_out(OUT / "roi_sensitivity.csv", [dict(annual_fee=a, benefit_fee_multiple=k,
              required_recurring_benefit=a*k, assumed_inventory_reduction=r, assumed_avoidable_carry=h,
              inventory_required_if_carry_only=a*k/(r*h))
              for a in acvs for k in (3, 5, 10) for r in (.05, .10, .15) for h in (.15, .20, .25)])
    csv_out(OUT / "gainshare_sensitivity.csv", [dict(verified_recurring_benefit=b, share=r, annual_revenue=b*r)
              for b in (50000, 125000, 250000, 500000, 1000000) for r in (.10, .15, .20, .25)])


def competitors():
    categories = {
        "forecasting": "statistical_forecasting machine_learning intermittent_demand promotions seasonality new_products",
        "inventory": "safety_stock reorder_points service_optimization right_sizing ABC_XYZ segmentation MEIO excess obsolete",
        "procurement": "supplier_allocation MOQ case_packs order_calendars lead_times fill_uncertainty dual_sourcing diversification",
        "execution": "replenishment order_generation planner_workflow exceptions ERP_writeback human_override",
        "resilience": "supplier_disruption transportation_disruption correlated_failures geopolitical_risk route_alternatives port_disruption scenarios resilience_inventory",
        "finance": "inventory_investment working_capital financing_cost cash_constraints stock_service_frontier profitability margin_impact",
        "evidence": "customer_segment implementation_time public_pricing customer_outcomes geography MENA_customer US_customer",
    }
    # Only mark capabilities explicitly supported by the reviewed page. Broad
    # platform categories do NOT imply every exact requested feature.
    vendors = {
        "GAINS": ("https://gainsystems.com/case-study/naghi-group-arabian-trading-supplies/",
                  "right_sizing replenishment working_capital customer_outcomes MENA_customer geography customer_segment"),
        "ToolsGroup": ("https://www.toolsgroup.com/solutions/inventory-optimization-software/",
                       "service_optimization right_sizing MEIO fill_uncertainty lead_times working_capital"),
        "RELEX": ("https://www.relexsolutions.com/solutions/fresh-inventory-software/",
                  "replenishment right_sizing margin_impact customer_segment"),
        "Netstock": ("https://www.netstock.com/pricing/", "implementation_time public_pricing customer_segment"),
        "Blue Yonder": ("https://blueyonder.com/customers/conagra",
                        "right_sizing inventory_investment customer_outcomes customer_segment US_customer"),
        "Kinaxis": ("https://www.kinaxis.com/sites/default/files/resources/Inventory%20management%20-%205%20building%20blocks%20to%20success-2018.pdf",
                    "MEIO service_optimization scenarios ERP_writeback segmentation safety_stock"),
        "o9": ("https://o9solutions.com/solutions/merchandise-planning/allocation-replenishment",
               "replenishment inventory_investment service_optimization scenarios"),
        "SAP": ("https://learning.sap.com/courses/discovering-sap-ibp-harmonized-planning-area/overview-of-inventory-optimization",
                "service_optimization safety_stock lead_times"),
        "Oracle Fusion / NetSuite": ("https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_1155215810.html",
                                     "safety_stock reorder_points service_optimization ABC_XYZ segmentation lead_times"),
        "Microsoft": ("https://learn.microsoft.com/en-us/dynamics365/supply-chain/master-planning/safety-stock-replenishment",
                      "safety_stock replenishment"),
        "Infor": ("https://docs.infor.com/scp/latest/en-us/sopolh/sopolhn/pjp1585570643132.html", "inventory_investment"),
        "Slimstock": ("https://www.slimstock.com/solutions/", "replenishment right_sizing service_optimization"),
        "Streamline": ("https://gmdhsoftware.com/case-study/food-retailer-inventory-optimization/",
                       "MEIO customer_segment customer_outcomes MENA_customer implementation_time"),
        "Lokad": ("https://www.lokad.com/inventory-optimization/", "right_sizing profitability MOQ"),
        "Logility": ("https://www.logility.com/solutions/inventory/", "MEIO inventory_investment service_optimization"),
        "e2open": ("https://www.e2open.com/planning/multi-echelon-inventory-optimization", "MEIO service_optimization right_sizing"),
        "Syncron": ("https://www.syncron.com/solutions/service-supply-chain/", "stock_service_frontier right_sizing service_optimization customer_segment"),
    }
    rows = []
    for vendor, (url, known) in vendors.items():
        for category, features in categories.items():
            for feature in features.split():
                yes = feature in known.split()
                rows.append(dict(vendor=vendor, category=category, feature=feature,
                    status="documented in reviewed source" if yes else "unverified; not evidence of absence",
                    source=url if yes else "", accessed="2026-09-05",
                    limitation="NetSuite evidence only; not automatically Fusion" if vendor.startswith("Oracle") else
                    "vendor documentation/selected case; not independent capability test"))
    csv_out(OUT / "competitor_features.csv", rows)


def summarize(path):
    data = json.loads((path / "runs.json").read_text())
    assert data["completed_cells"] == data["planned_cells"], "refuse an incomplete benchmark headline"
    rows = data["rows"]
    keys = [(r["cell"], r["seed"], r["policy"]) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate cell/seed/policy"
    by = defaultdict(list)
    for r in rows:
        by[(r["cell"], r["policy"])].append(r)
    summaries = []
    for (cell, policy), group in sorted(by.items()):
        xs = [r["saving_pct"] for r in group]
        assert len(xs) == len(data["seeds"])
        rng = np.random.default_rng(99000 + cell)
        boot = np.median(rng.choice(xs, size=(5000, len(xs)), replace=True), axis=1)
        s = {k: group[0][k] for k in ("cell", "policy", "target", "cover", "disruption", "demand", "lead", "supply", "margin")}
        s.update(n=len(xs), median=st.median(xs), minimum=min(xs), maximum=max(xs),
                 bootstrap_median_lo=float(np.quantile(boot, .025)), bootstrap_median_hi=float(np.quantile(boot, .975)),
                 wins=sum(r["saved"] > 1e-7 for r in group), harms=sum(r["realized_harm"] for r in group),
                 fallback_reviews=sum(len(r["failures"]) for r in group),
                 service_breaches=sum(r["service_target_breached"] for r in group),
                 fill_median=st.median(r["fill"] for r in group), fill_min=min(r["fill"] for r in group),
                 inventory_median=st.median(r["inventory_value"] for r in group),
                 holding_median=st.median(r["holding"] for r in group),
                 shortage_median=st.median(r["shortage"] for r in group),
                 total_median=st.median(r["total"] for r in group),
                 gross_contribution_median=st.median(r["gross_contribution_after_carry"] for r in group),
                 cost_CVaR90=st.mean(sorted((r["total"] for r in group), reverse=True)[:math.ceil(.1*len(group))]))
        summaries.append(s)
    csv_out(path / "cell_summary.csv", summaries)
    lines = ["# Every cell (descriptive, synthetic)", "",
             "Five seeds per cell. CI is an exploratory percentile bootstrap of the paired savings median;",
             "five independent seed paths are weak evidence, not 5,000 independent operators. Reused seeds",
             "across cells and repeated target settings are not independent replications. No pooled CI is claimed.", "",
             "| Cell | Policy | Median % | Range % | Exploratory 95% CI | Wins | Harm | Fallback reviews | Target breaches | Median fill |",
             "|---|---|---:|---|---|---:|---:|---:|---:|---:|"]
    for r in summaries:
        lines.append(f"| {r['cell']} | {r['policy']} | {r['median']:+.2f} | {r['minimum']:+.2f} to {r['maximum']:+.2f} | "
                     f"[{r['bootstrap_median_lo']:+.2f}, {r['bootstrap_median_hi']:+.2f}] | {r['wins']}/5 | {r['harms']}/5 | "
                     f"{r['fallback_reviews']} | {r['service_breaches']}/5 | {100*r['fill_median']:.2f}% |")
    (path / "EVERY_CELL.md").write_text("\n".join(lines) + "\n")
    policy_rows = []
    for p in sorted({r["policy"] for r in rows}):
        rs = [r for r in rows if r["policy"] == p]
        xs = [r["saving_pct"] for r in rs]
        policy_rows.append(dict(policy=p, n=len(rs), median=st.median(xs), minimum=min(xs), maximum=max(xs),
            wins=sum(r["saved"] > 1e-7 for r in rs), harms=sum(r["realized_harm"] for r in rs),
            fallback_reviews=sum(len(r["failures"]) for r in rs), target_breaches=sum(r["service_target_breached"] for r in rs)))
    csv_out(path / "policy_summary.csv", policy_rows)
    print(path.name, policy_rows)
    safe = [r for r in rows if r["policy"] == "safe_selected"]
    print("Selection counts:", dict(Counter(p for r in safe for p in r["selections"])))
    return summaries


def curves(summaries):
    selected = [r for r in summaries if r["cover"] == 2 and
                all(r[k] == v for k, v in dict(disruption="none", demand="stable", lead="stable", supply="reliable", margin="normal").items())]
    csv_out(OUT / "service_curve.csv", selected)
    marginal = []
    for p in sorted({r["policy"] for r in selected}):
        curve = sorted((r for r in selected if r["policy"] == p), key=lambda r: r["target"])
        for a, b in zip(curve, curve[1:]):
            ds = 100 * (b["fill_median"] - a["fill_median"])
            marginal.append(dict(policy=p, target_from=a["target"], target_to=b["target"],
                 realized_fill_change_pp=ds, median_carry_change=b["holding_median"]-a["holding_median"],
                 median_shortage_change=b["shortage_median"]-a["shortage_median"],
                 median_inventory_change=b["inventory_median"]-a["inventory_median"],
                 inventory_per_realized_pp=(b["inventory_median"]-a["inventory_median"])/ds if ds > 1e-7 else None,
                 caveat="difference of seed medians; no meaningful positive marginal price when realized service does not increase"))
    csv_out(OUT / "marginal_service.csv", marginal)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for p in ("incumbent", "stochastic_sp", "service_target", "service_periodic", "safe_selected"):
        curve = sorted((r for r in selected if r["policy"] == p), key=lambda r: r["target"])
        for ax, field, ylabel in ((axes[0], "fill_median", "Realized unit fill (%)"),
                                   (axes[1], "inventory_median", "Average stock value ($, tiny simulated operator)")):
            mult = 100 if field == "fill_median" else 1
            ax.plot([100*r["target"] for r in curve], [mult*r[field] for r in curve], marker=".", label=p)
            ax.set_xlabel("Configured target (%)")
            ax.set_ylabel(ylabel)
            ax.grid(alpha=.2)
    axes[0].plot([85, 100], [85, 100], linestyle=":", color="gray", label="target, not guarantee")
    axes[1].legend(fontsize=7)
    fig.suptitle("Synthetic 5-seed medians — fixed cover 2, stable demand/supply; not customer ROI")
    fig.tight_layout()
    fig.savefig(OUT / "service_curve.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    commercial()
    competitors()
    curves(summarize(OUT / "causal"))
    summarize(OUT / "causal/ablations")
