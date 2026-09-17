"""The Enterprise Analytics V1 demo loop, end to end, through the released API.

**DEMO / SYNTHETIC DATA — never a customer's workspace.** Creates a throwaway workspace (or uses
``--token`` with the explicit acknowledgement), loads the DEMO company, then walks the brief's
flow: Insights → Explore (three analyses: monthly demand by category, supplier fill rate over time,
inventory weeks of cover by SKU) → save all three → a dashboard with them → a global filter →
drill into one supplier → Ask ZAAD ("Which suppliers have been getting less reliable?") → save the
AI-built visual to the dashboard → Data & scope → the underlying supplier / PO records → the
optimizer hand-off (request built; submission only with ``--submit``). Every step prints what came
back, and the script exits non-zero on the first contradiction.

Usage:
    python3 scripts/analytics_demo_walk.py --api http://127.0.0.1:8000
    python3 scripts/analytics_demo_walk.py --api https://zaad-api.fly.dev --token <demo key> --i-know-this-replaces-the-data
"""
from __future__ import annotations

import argparse
import json
import sys

from scripts.zaad_demo_workspace import call, say

ANALYTICS = "/api/zaad/analytics"


def must(status: int, body, what: str, ok=(200, 201)):
    if status not in ok:
        raise SystemExit(f"{what}: HTTP {status} {json.dumps(body)[:400]}")
    return body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", required=True)
    ap.add_argument("--token", default=None)
    ap.add_argument("--i-know-this-replaces-the-data", action="store_true")
    ap.add_argument("--company", default="Al-Bahr Trading (DEMO)")
    ap.add_argument("--submit", action="store_true", help="also submit the hand-off plan (a minutes-long solve)")
    ap.add_argument("--keep-existing-data", action="store_true", help="do not reload the demo company")
    args = ap.parse_args()
    api = args.api.rstrip("/")
    token = args.token
    if token and not args.i_know_this_replaces_the_data and not args.keep_existing_data:
        raise SystemExit("Refusing to replace an existing workspace's data without --i-know-this-replaces-the-data.")
    if not token:
        status, ws = call(f"{api}/access/start", method="POST", body={"sector": "commercial", "company": args.company})
        must(status, ws, "create workspace")
        token = ws["token"]
        say("workspace", ws.get("operator_id", "?"))
    if not args.keep_existing_data:
        status, loaded = call(f"{api}/intake/load-demo-company", token=token, method="POST", body={})
        must(status, loaded, "load demo company")
        say("demo company loaded", json.dumps({k: v for k, v in loaded.items() if k in ("skus", "orders", "purchase_orders", "receipts", "inventory")})[:160])
    walk: list[dict] = []

    # 1. Insights
    status, ins = call(f"{api}/api/zaad/insights/summary?bucket=week", token=token)
    must(status, ins, "insights summary")
    say("insights", f"demand available={ins['demand']['available']} inventory available={ins['inventory']['available']}")
    walk.append({"step": "insights", "ok": bool(ins["demand"]["available"])})

    # 2. the semantic model
    status, model = call(f"{api}{ANALYTICS}/model", token=token)
    must(status, model, "model")
    queryable = [m["metric_id"] for m in model["metrics"] if m["queryable"]]
    say("semantic model", f"{model['semantic_model_version']} · {len(queryable)} queryable metrics · {len(model['dimensions'])} dimensions")
    walk.append({"step": "model", "metrics": len(queryable)})

    # 3. Explore: three analyses
    specs = {
        "Monthly demand by category": {"visual_type": "stacked_bar", "query": {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "category"}], "time": {"grain": "month", "range": {"last": 12, "unit": "month"}}}},
        "Supplier fill rate over time": {"visual_type": "line", "query": {"measures": [{"metric_id": "supplier_fill_rate"}], "dimensions": [{"dimension_id": "supplier"}], "time": {"grain": "month", "range": {"last": 12, "unit": "month"}}}},
        "Inventory weeks of cover by SKU": {"visual_type": "hbar", "query": {"measures": [{"metric_id": "weeks_of_cover"}, {"metric_id": "inventory_units"}], "dimensions": [{"dimension_id": "sku"}], "top_n": {"dimension_id": "sku", "n": 15, "by": "inventory_units"}}},
    }
    saved: dict[str, str] = {}
    for name, v in specs.items():
        status, res = call(f"{api}{ANALYTICS}/query", token=token, method="POST", body=v["query"])
        must(status, res, f"query {name}")
        if res["empty"]:
            raise SystemExit(f"{name}: the demo company answered empty")
        say(f"explore · {name}", f"{res['bounds']['rows']} rows · {res['timing']['executed_ms']:.0f} ms · {res['provenance']['definitions'][0]['ref']} · dataset {res['dataset_version']['dataset_version_id']}")
        status, an = call(f"{api}{ANALYTICS}/analyses", token=token, method="POST",
                          body={"name": name, "visibility": "workspace", "visual": {**v, "title": {"en": name, "ar": name}, "description": {"en": res["provenance"]["metric"], "ar": res["provenance"]["metric"]}}})
        must(status, an, f"save {name}", ok=(201,))
        saved[name] = an["analysis_id"]
        walk.append({"step": "explore+save", "name": name, "rows": res["bounds"]["rows"], "analysis_id": an["analysis_id"]})
    say("saved analyses", ", ".join(saved.values()))

    # 4. a dashboard with the three, a global filter, cross-filter (member events are applied client-side; here the same filter through the API)
    tiles = [{"tile_id": f"t{i}", "analysis_id": aid, "x": 0, "y": i, "w": 2 if i < 2 else 3, "h": 1} for i, aid in enumerate(saved.values())]
    status, dash = call(f"{api}{ANALYTICS}/dashboards", token=token, method="POST",
                        body={"name": "Operations (DEMO)", "visibility": "workspace", "spec": {"tiles": tiles, "shared_filters": [{"dimension_id": "category", "op": "eq", "values": ["Beverages"]}]}})
    must(status, dash, "create dashboard", ok=(201,))
    say("dashboard", f"{dash['dashboard_id']} · {dash['tiles']} tiles · filter category = Beverages")
    filtered_query = {**specs["Monthly demand by category"]["query"], "filters": [{"dimension_id": "category", "op": "eq", "values": ["Beverages"]}]}
    status, filtered = call(f"{api}{ANALYTICS}/query", token=token, method="POST", body=filtered_query)
    must(status, filtered, "filtered query")
    cats = {r[0] for r in filtered["rows"]}
    if cats != {"Beverages"}:
        raise SystemExit(f"the global filter did not narrow: {cats}")
    say("global filter", f"demand narrowed to {cats}")
    walk.append({"step": "dashboard+filter", "dashboard_id": dash["dashboard_id"], "categories": sorted(cats)})

    # 5. drill into one supplier: supplier → SKU (the registry's drill path), then the supplier record
    status, drill = call(f"{api}{ANALYTICS}/query", token=token, method="POST",
                         body={"measures": [{"metric_id": "supplier_fill_rate"}, {"metric_id": "matched_orders"}], "dimensions": [{"dimension_id": "sku"}], "filters": [{"dimension_id": "supplier", "op": "eq", "values": ["DEMO-SUP-02"]}], "top_n": {"dimension_id": "sku", "n": 10, "by": "matched_orders"}})
    must(status, drill, "drill")
    say("drill supplier → sku", f"{drill['bounds']['rows']} products for DEMO-SUP-02")
    status, sup = call(f"{api}/api/zaad/workspace/suppliers/DEMO-SUP-02", token=token)
    must(status, sup, "supplier record")
    say("supplier record", f"{sup['supplier_id']} · {len(sup['deliveries'])} deliveries · lateness statements {len(sup['lateness']['observed'])}")
    walk.append({"step": "drill", "rows": drill["bounds"]["rows"], "supplier_deliveries": len(sup["deliveries"])})

    # 6. Ask ZAAD
    status, answer = call(f"{api}{ANALYTICS}/ask", token=token, method="POST", body={"question": "Which suppliers have been getting less reliable?"})
    must(status, answer, "ask")
    if not answer["answered"]:
        raise SystemExit(f"Ask ZAAD did not answer: {answer.get('clarification')}")
    say("ask zaad", f"planner={answer['planner']} intent={answer['intent']} visual={answer['visual']['visual_type']} claims={len(answer['claims'])} rows={answer['result']['bounds']['rows']}")
    for c in answer["claims"][:4]:
        say("  claim", f"[{c['kind']}] {c['text'][:140]}")
    if any("saving" in c["text"].lower() for c in answer["claims"]):
        raise SystemExit("an answer called something a saving")
    status, follow = call(f"{api}{ANALYTICS}/ask", token=token, method="POST", body={"question": "only Beverages", "previous": answer["spec"]})
    must(status, follow, "follow-up")
    say("ask follow-up", f"answered={follow['answered']} filters={json.dumps(follow.get('spec', {}).get('filters'))}")
    walk.append({"step": "ask", "planner": answer["planner"], "claims": len(answer["claims"]), "follow_up_filters": follow.get("spec", {}).get("filters")})

    # 7. save the AI visual to the dashboard
    status, ai_an = call(f"{api}{ANALYTICS}/analyses", token=token, method="POST", body={"name": "Ask ZAAD: supplier reliability", "visual": answer["visual"], "origin": "ask_zaad", "visibility": "workspace"})
    must(status, ai_an, "save ai visual", ok=(201,))
    tiles.append({"tile_id": "t_ai", "analysis_id": ai_an["analysis_id"], "x": 0, "y": len(tiles), "w": 3, "h": 1})
    status, dash2 = call(f"{api}{ANALYTICS}/dashboards/{dash['dashboard_id']}", token=token, method="PATCH", body={"spec": {**dash["spec"], "tiles": tiles}})
    must(status, dash2, "add ai visual")
    say("ai visual on dashboard", f"{dash2['tiles']} tiles, origin of the last: {dash2['analyses'][ai_an['analysis_id']]['origin']}")
    walk.append({"step": "ai_visual_saved", "analysis_id": ai_an["analysis_id"], "tiles": dash2["tiles"]})

    # 8. Data & scope and the underlying records
    prov = answer["result"]["provenance"]
    say("data & scope", f"definitions={[d['ref'] for d in prov['definitions']]} cutoff={prov['data_cutoff']} last_updated={prov['last_updated']} filters={prov['filters']}")
    status, records = call(f"{api}/api/zaad/workspace/datasets/purchase_orders?fcol=supplier_id&fval=DEMO-SUP-02&limit=5", token=token)
    must(status, records, "underlying records")
    say("underlying records", f"{records.get('total', '?')} purchase-order rows for DEMO-SUP-02")
    walk.append({"step": "provenance+records", "definitions": [d["ref"] for d in prov["definitions"]], "records": records.get("total")})

    # 9. the optimizer hand-off
    status, ho = call(f"{api}{ANALYTICS}/handoff", token=token, method="POST",
                      body={"query": answer["spec"], "suppliers": answer["handoff"]["suppliers"][:1] or ["DEMO-SUP-02"], "observed_issue": "late rate rising", "submit": args.submit})
    must(status, ho, "handoff")
    say("handoff", f"request_built={ho['request_built']} skus={len(ho['context']['skus'])} summary={json.dumps(ho.get('request_summary'))[:160]} job={ho.get('job')}")
    if ho["request_built"] and ho.get("request_summary", {}).get("skus", 0) != len(ho["context"]["skus"]):
        raise SystemExit("the hand-off request does not cover the context's products")
    walk.append({"step": "handoff", "request_built": ho["request_built"], "skus": len(ho["context"]["skus"]), "job": ho.get("job")})

    # 10. audit rows exist for the material actions, with identifiers only
    status, audit = call(f"{api}/api/zaad/audit?limit=50", token=token)
    must(status, audit, "audit")
    actions = sorted({r["action"] for r in audit["rows"]})
    say("audit", ", ".join(actions))
    for needed in ("analysis_created", "dashboard_created", "dashboard_updated", "ai_query"):
        if needed not in actions:
            raise SystemExit(f"audit is missing {needed}")
    print(json.dumps({"walk": walk}, indent=2, default=str))
    print("DEMO WALK OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
