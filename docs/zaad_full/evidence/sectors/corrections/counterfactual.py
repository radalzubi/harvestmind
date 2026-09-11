"""Replay fixture P3_age_at_receipt (gated) with keep_requests under the code line of the cwd worktree,
for the declared physics (age at receipt 3 from src_A) and for the neutral variant (age 0).
usage: PYTHONPATH=. python3 counterfactual.py <label> <out.json>"""
import json, sys
from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.replay import replay
from zaad.meio.baselines import register_replay_methods
from zaad.sectors.fixtures import FIXTURES, sector_request

label, out_path = sys.argv[1], sys.argv[2]
register_replay_methods()
NAME = "P3_age_at_receipt"
out = {"label": label, "runs": {}}
for variant in ("declared", "neutral"):
    spec = json.loads(json.dumps(FIXTURES[NAME]))
    if variant == "neutral":
        spec["physics"]["skus"]["A"].pop("age_at_receipt_by_source", None)
    for seed in (41001, 41002):
        initial = sector_request(spec, seed)
        H = initial.horizon
        truth = long_truth(initial, seed + 10000, (-(-(7 + H) // H)) * H)
        kept = []
        res = replay(initial, truth, 8, "gated", keep_requests=kept, rolling=True)
        reviews = []
        for k, (row, req) in enumerate(zip(res["reviews"], kept)):
            s = row["settlement"]
            observed = sorted((lot.id, lot.location, lot.expires_in, round(lot.quantity, 3)) for lot in req.stock if lot.id.startswith("observed-"))
            reviews.append({"review": k, "state": (row.get("orchestration") or {}).get("state"), "status": row["warnings"][0] if row["warnings"] else None,
                            "purchases": sorted((p["source"], round(p["quantity"], 6)) for p in row["purchases"] if p["quantity"] > 1e-9),
                            "transfer_units": round(sum(e["quantity"] for e in s.get("transfer_events", [])), 6),
                            "cost": round(s["economic_cost"], 6), "served": round(sum(x["served"] for x in s["service_by_period"]), 6),
                            "demand": round(sum(x["demand"] for x in s["service_by_period"]), 6),
                            "observed_lots_in_snapshot": observed})
        out["runs"][f"{variant}:{seed}"] = {"status": res["status"], "reviews": reviews,
                                             "physics": {"shelf_life": initial.skus[0].shelf_life, "age_by_source": dict(initial.sku_physics[0].age_at_receipt_by_source) if initial.sku_physics else {}}}
        print(label, variant, seed, res["status"], [r["purchases"] for r in reviews][:2], flush=True)
json.dump(out, open(out_path, "w"), indent=1)
