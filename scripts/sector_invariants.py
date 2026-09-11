"""Sector physics invariants (SECTOR_PHYSICS_INVARIANTS.md): the 21 required properties, each proved on
synthetic requests through the contract, the model, the settlement and the planner, with the evidence
recorded. Writes docs/zaad_full/evidence/sectors/SECTOR_PHYSICS_INVARIANTS.{md,json}.

usage: PYTHONPATH=. python3 -m scripts.sector_invariants [--benchmark sector_authoritative]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from zaad.full.contracts import Request
from zaad.full.model import Solution, solve
from zaad.full.planner import plan
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.terminal import continuation_value
from zaad.full.worlds import draw, forecast_all
from zaad.meio.fixtures_p2 import p2_request
from zaad.sectors.contracts import resolve
from zaad.sectors.fixtures import build

OUT = Path("docs/zaad_full/evidence/sectors")
DECL = "OPERATOR_DECLARED"
EMPTY = Solution("OPTIMAL", {}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])


def _payload(req: Request) -> dict:
    return req.model_dump(mode="json")


def _validate(payload: dict) -> Request:
    return Request.model_validate(payload)


def _physics(req: Request, sku: str = "A", sector: str = "PRODUCE", **fields) -> Request:
    payload = _payload(req)
    payload["sku_physics"] = [p for p in payload.get("sku_physics", []) if p["sku"] != sku] + [{"sku": sku, "sector": sector, "provenance": {k: DECL for k in fields}, **fields}]
    return _validate(payload)


def _lots(req: Request, lots: list[tuple[str, str, int, float]]) -> Request:
    payload = _payload(req)
    known = {"known_at": payload["skus"][0]["known_at"]}
    payload["stock"] = [{**known, "id": f"lot_{i}", "sku": sku, "location": loc, "quantity": q, "reserved": 0., "damaged": 0., "quarantined": 0., "expires_in": e, "age_periods": 0}
                        for i, (sku, loc, e, q) in enumerate(lots)]
    return _validate(payload)


def _shelf(req: Request, life: int, sku: str = "A") -> Request:
    payload = _payload(req)
    for s in payload["skus"]:
        if s["id"] == sku:
            s["shelf_life"] = life
    for lot in payload["stock"]:
        if lot["sku"] == sku:
            lot["expires_in"] = min(lot["expires_in"], life)
    return _validate(payload)


def _world(req: Request):
    return draw(req, req.seed, 1, deterministic=True)[0]


def _det(req: Request, **kw) -> Solution:
    return solve(req, draw(req, req.seed, 1, deterministic=True), **kw)


def _conservation(result: dict) -> float:
    return abs(float(result.get("conservation_residual") or 0.))


def inv_01_legacy_unchanged() -> dict:
    """A request without a sector profile plans identically with and without the sector code paths reachable."""
    req = p2_request()
    a = plan(req)
    b = plan(_validate({**_payload(req), "sector_mode": None, "sku_physics": []}))
    same = a["actions"] == b["actions"] and a["status"] == b["status"] and a["orchestration"]["state"] == b["orchestration"]["state"]
    return {"pass": same and resolve(req) is None and "physics" not in a, "actions": len(a["actions"]), "note": "canonical regression (B/T/Q/A, P0 cell 15) is the authoritative frozen-identity gate; recorded in the closeout"}


def inv_02_commercial_packs_executable() -> dict:
    req = build("C1_case_pack_rounding", 41001)
    sol = _det(req, service_floor=True)
    bad = [q for (s, t), q in sol.purchases.items() if abs(q / 12 - round(q / 12)) > 1e-6]
    settle(req, sol, _world(req))
    return {"pass": sol.usable_plan and not bad, "purchases": {f"{s}@{t}": round(q, 3) for (s, t), q in sol.purchases.items() if q > 0}}


def inv_03_produce_expired_cannot_serve() -> dict:
    req = _physics(_lots(_shelf(p2_request(opening_central=0.), 6), [("A", "north", 2, 1000.), ("A", "south", 2, 1000.)]), minimum_remaining_life_at_sale=0)
    result = settle(req, EMPTY, _world(req), steps=5)
    served_after = sum(x["served"] for x in result["service_by_period"] if x["period"] >= 2)
    return {"pass": served_after == 0. and result["trace"][-1]["expired_units"] > 0, "served_after_expiry": served_after, "expired_units": result["trace"][-1]["expired_units"]}


def inv_04_terminal_monotone_in_life() -> dict:
    req = _physics(_shelf(p2_request(), 10), minimum_remaining_life_at_sale=1)
    fits = forecast_all(req)
    values = [continuation_value(req, [{"sku": "A", "location": "north", "expiry": e, "quantity": 100.}], [], fits, window_end=1)["continuation_credit"] for e in (10, 8, 6, 4, 3, 2, 1)]
    return {"pass": all(a >= b - 1e-9 for a, b in zip(values, values[1:])), "credit_by_expiry": dict(zip((10, 8, 6, 4, 3, 2, 1), [round(v, 2) for v in values]))}


def inv_05_fefo_settlement() -> dict:
    req = build("P7_fefo_settlement", 41001)
    result = settle(req, EMPTY, _world(req), steps=1)
    ok = True
    detail = {}
    for loc in ("north", "south"):
        rows = sorted(((x["expiry"], x["quantity"]) for x in result["end_stock"] if x["location"] == loc), key=lambda r: r[0])
        detail[loc] = rows
        # the older cohort is consumed before any of the younger one
        older_left = next((q for e, q in rows if e == 2), 0.)
        younger_left = next((q for e, q in rows if e == 5), 0.)
        ok &= older_left <= 1e-9 or younger_left >= 90. - 1e-9
    return {"pass": ok, "end_stock": detail}


def inv_06_fefo_symmetry_elimination_active() -> dict:
    """Cohorts that outlive the window still carry no FEFO indicator; in-window cohorts of a perishable carry theirs."""
    import zaad.full.model as M
    from zaad.full.worlds import draw as _draw

    def binaries(req):
        counts = {}
        original = M.Linear.solve

        def wrapped(self, *a, **k):
            counts["fefo"] = sum(1 for n in self.names if n[0] == "fefo")
            counts["binary"] = sum(1 for i, u in zip(self.integer, self.upper) if i and u <= 1)
            return original(self, *a, **k)
        M.Linear.solve = wrapped
        try:
            solve(req, _draw(req, req.seed, 3), service_floor=True)
        finally:
            M.Linear.solve = original
        return counts
    long_life = binaries(_physics(p2_request(), sector="COMMERCIAL"))            # shelf 52: no in-window cohort
    perishable = binaries(build("P5_spoilage_vs_service", 41001))                   # shelf 3: in-window cohorts
    return {"pass": long_life["fefo"] == 0 and perishable["fefo"] > 0 and perishable["fefo"] < 2000, "commercial": long_life, "produce": perishable}


def inv_07_transfer_never_gains_life() -> dict:
    req = build("P4_transfer_becomes_useless", 41001)
    sol = _det(req)
    result = settle(req, sol, _world(req), steps=1)
    opening = max(lot.expires_in for lot in req.stock)
    bad = [(e, due) for _, _, e, due, q, kind in result["pending"] if kind == "transfer" and e > opening]
    return {"pass": sol.usable_plan and not bad, "in_transit": [(e, due, round(q, 1)) for _, _, e, due, q, kind in result["pending"] if kind == "transfer"]}


def inv_08_incompatible_location_cannot_hold() -> dict:
    req = build("M3_storage_state_infeasibility", 41001)
    sol = _det(req, service_floor=False)
    result = settle(req, sol, _world(req))
    held = [x for x in result["end_stock"] if x["location"] == "south" and x["quantity"] > 1e-9]
    try:
        settle(req, Solution("OPTIMAL", {}, {("lane_south", 40, 0): 5.}, {}, {}, None, [], 0., 0, 0, None, 0., []), _world(req), steps=1)
        refused = False
    except PhysicalViolation:
        refused = True
    try:
        _validate({**_payload(req), "stock": [*_payload(req)["stock"], {**_payload(req)["stock"][0], "id": "bad", "location": "south"}]})
        contract = False
    except ValueError:
        contract = True
    return {"pass": not held and refused and contract, "south_transfer_in_plan": sum(q for (a, e, t), q in sol.transfers.items() if a == "lane_south")}


def inv_09_incompatible_lane_cannot_move() -> dict:
    req = build("M4_cold_chain_lane", 41001)
    sol = _det(req, service_floor=True)
    used = {a: sum(q for (aa, e, t), q in sol.transfers.items() if aa == a) for a in ("lane_south", "reefer_south", "lane_north")}
    try:
        settle(req, Solution("OPTIMAL", {}, {("lane_south", 6, 0): 5.}, {}, {}, None, [], 0., 0, 0, None, 0., []), _world(req), steps=1)
        refused = False
    except PhysicalViolation:
        refused = True
    return {"pass": used["lane_south"] <= 1e-9 and refused, "lane_units": used}


def inv_10_meat_expired_cannot_serve() -> dict:
    req = _physics(_lots(_shelf(p2_request(opening_central=0.), 6), [("A", "north", 2, 1000.), ("A", "south", 2, 1000.)]), sector="MEAT_SEAFOOD", storage_state="CHILLED", minimum_remaining_life_at_sale=0)
    result = settle(req, EMPTY, _world(req), steps=5)
    served_after = sum(x["served"] for x in result["service_by_period"] if x["period"] >= 2)
    return {"pass": served_after == 0., "served_after_expiry": served_after}


def inv_11_mixed_isolation() -> dict:
    req = build("X1_commercial_plus_produce", 41001)
    physics = resolve(req)
    single = _validate({**_payload(p2_request()), "sector_mode": "COMMERCIAL"})
    # A's physics in the mixed request equals its single-SKU commercial profile
    same_profile = physics.sku["A"].model_dump() == resolve(single).sku["A"].model_dump()
    sol = _det(req)
    result = settle(req, sol, _world(req))
    a_unsellable = [x for x in result["end_stock"] if x["sku"] == "A" and not x["sellable"] and x["expiry"] > 12]
    return {"pass": same_profile and not a_unsellable and physics.min_sale("B") == 1, "A_profile": physics.sku["A"].model_dump()}


def inv_12_network_conservation() -> dict:
    worst = 0.
    for name in ("P2_near_expiry_inventory", "M6_transfer_usable_lot", "X3_three_sectors"):
        req = build(name, 41001)
        sol = _det(req)
        result = settle(req, sol, _world(req))
        worst = max(worst, _conservation(result))
    return {"pass": worst <= 1e-9, "worst_residual": worst}


def inv_13_no_double_allocation() -> dict:
    req = build("P7_fefo_settlement", 41001)
    result = settle(req, EMPTY, _world(req), steps=1)
    served = sum(x["served"] for x in result["service_by_period"])
    opening = sum(lot.usable for lot in req.stock if lot.location != "central")
    return {"pass": served <= opening + 1e-9, "served": served, "opening_branch_units": opening}


def inv_14_no_negative_inventory() -> dict:
    worst = 0.
    for name in ("P4_transfer_becomes_useless", "M6_transfer_usable_lot", "X2_produce_plus_frozen_seafood"):
        req = build(name, 41001)
        result = settle(req, _det(req), _world(req))
        worst = min(worst, min((x["quantity"] for x in result["end_stock"]), default=0.))
    return {"pass": worst >= -1e-9, "most_negative": worst}


def inv_15_no_resurrection() -> dict:
    req = _physics(_lots(_shelf(p2_request(opening_central=0.), 6), [("A", "north", 2, 1000.)]), minimum_remaining_life_at_sale=0)
    result = settle(req, EMPTY, _world(req), steps=6)
    north = [x for x in result["end_stock"] if x["location"] == "north"]
    trace = [row["expired_units"] for row in result["trace"]]
    return {"pass": not north and trace[-1] > 0 and all(b >= a for a, b in zip(trace, trace[1:])), "expired_cumulative": trace}


def inv_16_no_shelf_life_reset_on_transfer() -> dict:
    req = build("M6_transfer_usable_lot", 41001)
    sol = _det(req)
    result = settle(req, sol, _world(req), steps=1)
    moved = [(e, due) for _, loc, e, due, q, kind in result["pending"] if kind == "transfer" and q > 0]
    return {"pass": sol.usable_plan and all(e == 4 for e, _ in moved) and bool(moved), "in_transit_expiry": moved}


def inv_17_18_no_autonomous_po_and_approval() -> dict:
    reps = [plan(build(n, 41001)) for n in ("C3_moq_mov_economics", "P3_age_at_receipt", "M2_frozen_shelf_life")]
    return {"pass": all(r["approval_required"] is True and r["executable_purchase_order"] is False for r in reps), "reviews": len(reps)}


def inv_19_20_21_ownership_unchanged() -> dict:
    owners = {}
    for n in ("C7_no_material_improvement", "P1_fresh_no_unnecessary_purchase", "M1_chilled_shelf_life", "X3_three_sectors"):
        rep = plan(build(n, 41001))
        owners[n] = (rep["orchestration"]["planner_owner"], rep["orchestration"]["state"])
    allowed = {"PURCHASING_ECONOMICS", "PROTECTION_RECOVERY"}
    return {"pass": all(o in allowed for o, _ in owners.values()), "owners": owners, "note": "no sector owner exists; P0 / P1 / P2 labels only"}


INVARIANTS = [
    ("01_legacy_unchanged", inv_01_legacy_unchanged), ("02_commercial_packs_executable", inv_02_commercial_packs_executable),
    ("03_produce_expired_cannot_serve", inv_03_produce_expired_cannot_serve), ("04_terminal_monotone_in_life", inv_04_terminal_monotone_in_life),
    ("05_fefo_settlement", inv_05_fefo_settlement), ("06_fefo_symmetry_elimination_active", inv_06_fefo_symmetry_elimination_active),
    ("07_transfer_never_gains_life", inv_07_transfer_never_gains_life), ("08_incompatible_location_cannot_hold", inv_08_incompatible_location_cannot_hold),
    ("09_incompatible_lane_cannot_move", inv_09_incompatible_lane_cannot_move), ("10_meat_expired_cannot_serve", inv_10_meat_expired_cannot_serve),
    ("11_mixed_isolation", inv_11_mixed_isolation), ("12_network_conservation", inv_12_network_conservation),
    ("13_no_double_allocation", inv_13_no_double_allocation), ("14_no_negative_inventory", inv_14_no_negative_inventory),
    ("15_no_resurrection", inv_15_no_resurrection), ("16_no_shelf_life_reset_on_transfer", inv_16_no_shelf_life_reset_on_transfer),
    ("17_18_no_autonomous_po_and_approval", inv_17_18_no_autonomous_po_and_approval), ("19_20_21_ownership_unchanged", inv_19_20_21_ownership_unchanged),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default=None)
    a = ap.parse_args()
    rows = []
    for name, fn in INVARIANTS:
        started = time.time()
        try:
            result = fn()
        except Exception as exc:
            result = {"pass": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
        result["seconds"] = round(time.time() - started, 1)
        rows.append({"invariant": name, **result})
        print(f"{name:<40} {'PASS' if result['pass'] else 'FAIL':<5} {result['seconds']}s", flush=True)
    benchmark_note = ""
    if a.benchmark:
        records = [json.loads(line) for line in (OUT / f"{a.benchmark}.jsonl").read_text().splitlines()]
        zaad = [r for r in records if r["policy"] == "gated" and r.get("per_review")]
        worst = max((x["conservation_residual"] for r in zaad for x in r["per_review"]), default=0.)
        failures = [(r["fixture"], r["seed"]) for r in records if r.get("status") == "PHYSICAL_FAILURE" and r["policy"] == "gated"]
        benchmark_note = f"benchmark {a.benchmark}: {len(zaad)} ZAAD cells, worst conservation residual {worst:.2e}, ZAAD physical failures {failures}"
        rows.append({"invariant": "12b_benchmark_conservation", "pass": worst <= 1e-9 and not failures, "worst_residual": worst, "physical_failures": failures, "seconds": 0.})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "SECTOR_PHYSICS_INVARIANTS.json").write_text(json.dumps(rows, indent=1, default=str))
    passed = sum(1 for r in rows if r["pass"])
    text = "# Sector physics invariants\n\n| invariant | result | evidence |\n|---|---|---|\n"
    for r in rows:
        text += f"| {r['invariant']} | {'PASS' if r['pass'] else 'FAIL'} | {json.dumps({k: v for k, v in r.items() if k not in ('invariant', 'pass', 'seconds')}, default=str)[:400]} |\n"
    text += f"\n{passed} / {len(rows)} PASS. {benchmark_note}\n"
    (OUT / "SECTOR_PHYSICS_INVARIANTS.md").write_text(text)
    print(f"INVARIANTS {'PASS' if passed == len(rows) else 'FAIL'} {passed}/{len(rows)}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
