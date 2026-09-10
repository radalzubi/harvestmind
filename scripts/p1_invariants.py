"""P1 economic invariants, checked on every fixture's first review (all three seeds) and written to
docs/zaad_full/evidence/p1/P1_INVARIANTS.json. Each invariant is a statement the economics must
satisfy regardless of which plan wins; a violation is a defect, not a benchmark result."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.p1_fixtures import FIXTURES, SEEDS, build
from zaad.full.economics import COMPONENTS, order_waterfall, provenance, reconcile, supplier_order_view
from zaad.full.model import pallet_units, supplier_orders
from zaad.full.planner import plan


def check_fixture(name: str, seed: int) -> dict:
    req = build(name, seed)
    report = plan(req)
    e = report["economics"]
    out = {"fixture": name, "seed": seed, "status": report["status"], "checks": {}}
    c = out["checks"]
    # 1. every settled world reconciles component sums to economic cost and carries no ledger residual
    c["components_reconcile"] = e["reconciled"] in (True, None)
    # 2. every order's attribution partitions its quantity exactly
    c["attribution_partitions"] = all(abs(o["attribution_sum"] - o["quantity"]) < 1e-6 for o in e["orders"] + e["incumbent_orders"])
    # 3. no attribution category is negative
    c["attribution_nonnegative"] = all(v >= -1e-9 for o in e["orders"] for v in o["attribution"].values())
    # 4. every supplier order in the selected plan clears the MOV and the maximum load
    ok = True
    for v in e["supplier_orders"]:
        if v["minimum_order_value"] and v["order_value"] < v["minimum_order_value"] - 1e-6:
            ok = False
    for supplier, srcs, st in supplier_orders(req):
        top = st.max_pallets if st.max_pallets is not None else (st.freight_tiers[-1].up_to_pallets if st.freight_tiers else None)
        for v in e["supplier_orders"]:
            if v["supplier"] == supplier and top is not None and v["pallets"] is not None and v["pallets"] > top:
                ok = False
    c["mov_and_load_respected"] = ok
    # 5. operating components are non-negative (only the inventory value change may be negative)
    for label in ("incumbent_costs", "selected_costs"):
        costs = e[label]
        c[f"{label}_nonnegative"] = costs is None or all(costs[k] >= -1e-6 for k in COMPONENTS if k != "INVENTORY_VALUE_CHANGE")
    # 6. every economic input carries a provenance label from the closed set
    labels = {v["provenance"] for v in e["provenance"].values()}
    c["provenance_closed_set"] = labels <= {"CUSTOMER_PROVIDED", "INFERRED_FROM_HISTORY", "CONFIGURED_ASSUMPTION", "NOT_AVAILABLE"}
    c["no_customer_provided_in_fixtures"] = "CUSTOMER_PROVIDED" not in labels
    # 7. no unmapped ledger keys anywhere in the confirmation rows
    c["no_unmapped_ledger_keys"] = not e["unmapped_ledger_keys"]
    # 8. materiality verdict is one of the closed set and the recommendation agrees with the status
    m = e["materiality"]
    c["materiality_verdict_closed"] = m is None or m["verdict"] in ("MATERIAL_IMPROVEMENT", "NO MATERIAL IMPROVEMENT AVAILABLE", "NOT_COMPARABLE")
    c["recommendation_matches_status"] = (report["status"] == "PENDING_REVIEW") == e["action_recommended"]
    # 9. when the incumbent is retained for immateriality the reason says so
    if report["status"] == "RETAIN_INCUMBENT" and m and m["verdict"] == "NO MATERIAL IMPROVEMENT AVAILABLE" and report["candidate_gates"].get(report["selected_policy"], {}).get("accepted"):
        c["abstention_reason_stated"] = any("NO MATERIAL IMPROVEMENT" in r for r in report["reasons"])
    # 10. the timing audit and the waterfall agree on arrival periods
    timing = {(x["source"], x["period"]): x["arrival_period"] for x in (report["procurement_timing"] or [])}
    c["timing_agrees_with_waterfall"] = all(timing.get((o["source"], o["period"]), o["arrival_period"]) == o["arrival_period"] for o in e["orders"])
    out["pass"] = all(c.values())
    out["explanations"] = [o["explanation"] for o in e["orders"]]
    out["materiality"] = m["reason"] if m else None
    return out


def main():
    rows = [check_fixture(name, seed) for name in FIXTURES for seed in SEEDS]
    Path("docs/zaad_full/evidence/p1/P1_INVARIANTS.json").write_text(json.dumps(rows, indent=1, default=float))
    failing = [r for r in rows if not r["pass"]]
    print(json.dumps({"checked": len(rows), "passing": len(rows) - len(failing),
                      "failures": [{"fixture": r["fixture"], "seed": r["seed"], "failed": [k for k, v in r["checks"].items() if not v]} for r in failing]}, indent=1))
    sys.exit(1 if failing else 0)


if __name__ == "__main__":
    main()
