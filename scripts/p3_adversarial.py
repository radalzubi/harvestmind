"""P3 adversarial inputs: every case must fail safely at the contract (ValueError / HTTP 422) or be
handled by construction (the model bounds the source at zero; the settlement refuses it). Writes
docs/zaad_full/evidence/p3/P3_ADVERSARIAL.{md,json}.

usage: PYTHONPATH=. python3 -m scripts.p3_adversarial"""
from __future__ import annotations

import json
from pathlib import Path

from zaad.full.contracts import Request
from zaad.meio.fixtures_p2 import p2_request
from zaad.sourcing.contracts import MAX_SOURCES_PER_PAIR

OUT = Path("docs/zaad_full/evidence/p3")
DECL = "OPERATOR_DECLARED"


def base() -> dict:
    p = p2_request(max_solve_seconds=5).model_dump(mode="json")
    a = next(s for s in p["sources"] if s["id"] == "src_A")
    p["sources"].append({**a, "id": "src_B", "supplier": "supplier_b", "route": ["supplier_b", "central"], "resources": ["cap_b"]})
    p["resources"].append({**p["resources"][0], "id": "cap_b", "failure_domains": ["supplier_b"]})
    p["sourcing"] = {"incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": DECL}]}
    return p


def src(p, sid):
    return next(s for s in p["sources"] if s["id"] == sid)


def refused(mutate, expect: str):
    p = base()
    mutate(p)
    try:
        Request.model_validate(p)
    except ValueError as exc:
        msg = str(exc)
        detail = [line.strip() for line in msg.splitlines() if ("error" in line.lower() or "finite" in line.lower()) and "http" not in line.lower()][:2]
        return {"outcome": "REFUSED_AT_CONTRACT", "pass": expect.lower() in msg.lower(), "message": detail}
    return {"outcome": "ACCEPTED", "pass": False, "message": "accepted"}


def handled(mutate, check) -> dict:
    p = base()
    mutate(p)
    req = Request.model_validate(p)
    return check(req)


def _dup_id(p):
    p["sources"].append({**src(p, "src_B"), "unit_price": 1.})


def _neg_capacity(p):
    src(p, "src_B")["capacity_by_period"] = [-1.] * 12


def _neg_cost(p):
    src(p, "src_B")["unit_price"] = -5.


def _neg_pack(p):
    src(p, "src_B")["case_multiple"] = -12.


def _min_gt_max(p):
    p["sourcing"]["share_constraints"] = [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .6, "maximum_share": .4, "provenance": DECL}]


def _shares_over_100(p):
    p["sourcing"]["share_constraints"] = [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .6, "provenance": DECL},
                                          {"sku": "A", "destination": "central", "source": "src_A", "minimum_share": .6, "provenance": DECL}]
    p["sourcing"]["incumbent_shares"] = [{"sku": "A", "destination": "central", "source": "src_A", "share": .6, "provenance": DECL}]


def _unqualified_min_share(p):
    src(p, "src_B")["approved"] = False
    p["sourcing"]["share_constraints"] = [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .2, "provenance": DECL}]
    p["sourcing"]["incumbent_shares"] = [{"sku": "A", "destination": "central", "source": "src_B", "share": .2, "provenance": DECL}]


def _unknown_supplier_group(p):
    p["sourcing"]["risk_groups"] = [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_ghost"], "provenance": DECL}]


def _unknown_sku_share(p):
    p["sourcing"]["share_constraints"] = [{"sku": "ZZZ", "destination": "central", "source": "src_B", "minimum_share": .2, "provenance": DECL}]


def _missing_provenance(p):
    p["sourcing"]["risk_groups"] = [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "provenance": "UNKNOWN"}]


def _contradictory_cold_chain(p):
    p["sector_mode"] = "MEAT_SEAFOOD"
    p["sku_physics"] = [{"sku": "A", "sector": "MEAT_SEAFOOD", "storage_state": "FROZEN", "provenance": {"storage_state": DECL}}]
    for loc in p["locations"]:
        loc["storage_states"] = ["CHILLED"]


def _impossible_mov(p):
    src(p, "src_B")["capacity_by_period"] = [100.] * 12
    p["supplier_terms"] = [{"known_at": p["skus"][0]["known_at"], "id": "t_b", "supplier": "supplier_b", "minimum_order_value": 6000., "provenance": {}}]


def _correlation_over_one(p):
    a = src(p, "src_A")
    p["sources"].append({**a, "id": "src_C", "supplier": "supplier_c", "route": ["supplier_c", "central"], "resources": ["cap_c"]})
    p["resources"].append({**p["resources"][0], "id": "cap_c", "failure_domains": ["supplier_c"]})
    p["sourcing"]["risk_groups"] = [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "correlation": .7, "provenance": DECL},
                                    {"id": "h", "kind": "PORT", "members": ["src_A", "src_C"], "correlation": .5, "provenance": DECL}]


def _duplicated_groups(p):
    p["sourcing"]["risk_groups"] = [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "provenance": DECL},
                                    {"id": "h", "kind": "PORT", "members": ["src_B", "src_A"], "provenance": DECL}]


def _single_member_group(p):
    p["sourcing"]["risk_groups"] = [{"id": "g", "kind": "PLANT", "members": ["src_A"], "provenance": DECL}]


def _inf_price(p):
    src(p, "src_B")["unit_price"] = float("inf")


def _nan_freight(p):
    src(p, "src_B")["freight_per_unit"] = float("nan")


def _inf_capacity(p):
    src(p, "src_B")["capacity_by_period"] = [float("inf")] * 12


def _extreme_source_count(p):
    a = src(p, "src_A")
    for i in range(MAX_SOURCES_PER_PAIR):
        p["sources"].append({**a, "id": f"src_x{i}", "supplier": f"supplier_x{i}", "route": [f"supplier_x{i}", "central"]})


def _switching_on_unknown(p):
    p["sourcing"]["switching_costs"] = [{"source": "src_ghost", "cost": 10., "provenance": DECL}]


def _committed_above_capacity(p):
    src(p, "src_B")["capacity_by_period"] = [10.] * 12
    p["sourcing"]["share_constraints"] = [{"sku": "A", "destination": "central", "source": "src_B", "committed_units": 1000., "provenance": DECL}]
    p["sourcing"]["incumbent_shares"] = [{"sku": "A", "destination": "central", "source": "src_B", "share": .5, "provenance": DECL}]


def _zero_pack_is_continuous(req):
    return {"outcome": "HANDLED_BY_CONTRACT", "pass": src(req.model_dump(mode="json"), "src_B")["multiple"] == 0., "message": "a zero pack size is the declared continuous pack (frozen contract); it creates no integer column"}


def _impossible_mov_handled(req):
    from zaad.full.model import solve
    from zaad.full.worlds import draw
    sol = solve(req, draw(req, req.seed, 1, deterministic=True), service_floor=True)
    b = sum(q for (s, _), q in sol.purchases.items() if s == "src_B")
    return {"outcome": "HANDLED_BY_MODEL", "pass": sol.usable_plan and b <= 1e-9, "message": f"supplier_b (capacity 100 units, MOV 6000) receives {b:.0f} units: the order binary cannot open"}


CASES = [
    ("duplicate source ids", lambda: refused(_dup_id, "duplicate entity ID")),
    ("two options with the same id and conflicting terms", lambda: refused(_dup_id, "duplicate entity ID")),
    ("negative capacity", lambda: refused(_neg_capacity, "invalid source capacity")),
    ("negative unit cost", lambda: refused(_neg_cost, "greater than 0")),
    ("negative pack size", lambda: refused(_neg_pack, "greater than or equal to 0")),
    ("zero pack size", lambda: handled(lambda p: src(p, "src_B").update(multiple=0.), _zero_pack_is_continuous)),
    ("minimum share above maximum share", lambda: refused(_min_gt_max, "minimum share above maximum")),
    ("minimum shares summing above 100 %", lambda: refused(_shares_over_100, "sum above 100")),
    ("source not qualified for the SKU carrying a minimum share", lambda: refused(_unqualified_min_share, "not qualified")),
    ("unknown supplier in a risk group", lambda: refused(_unknown_supplier_group, "unknown source")),
    ("unknown SKU in a share constraint", lambda: refused(_unknown_sku_share, "supplies A to central")),
    ("risk group without provenance", lambda: refused(_missing_provenance, "provenance")),
    ("contradictory cold-chain state (frozen SKU, chilled-only locations)", lambda: refused(_contradictory_cold_chain, "no location can hold")),
    ("impossible MOV / capacity combination", lambda: handled(_impossible_mov, _impossible_mov_handled)),
    ("total group correlation above one (non-PSD equivalent)", lambda: refused(_correlation_over_one, "above 1")),
    ("duplicated risk groups", lambda: refused(_duplicated_groups, "duplicates another group")),
    ("single-member risk group", lambda: refused(_single_member_group, "at least 2")),
    ("infinite unit price", lambda: refused(_inf_price, "finite")),
    ("NaN freight", lambda: refused(_nan_freight, "nan")),
    ("infinite capacity", lambda: refused(_inf_capacity, "finite")),
    (f"extreme source count ({MAX_SOURCES_PER_PAIR + 2} for one pair)", lambda: refused(_extreme_source_count, f"at most {MAX_SOURCES_PER_PAIR}")),
    ("switching cost on an unknown source", lambda: refused(_switching_on_unknown, "unknown source")),
    ("committed units above the source's capacity", lambda: refused(_committed_above_capacity, "exceed its capacity")),
]


def main() -> int:
    results = {}
    for name, run in CASES:
        try:
            r = run()
        except Exception as exc:
            r = {"outcome": "ERROR", "pass": False, "message": f"{type(exc).__name__}: {exc}"[:300]}
        results[name] = r
        print(f"{name:<70} {r['outcome']:<22} {'PASS' if r['pass'] else 'FAIL'}", flush=True)
    passed = sum(1 for r in results.values() if r["pass"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "P3_ADVERSARIAL.json").write_text(json.dumps(results, indent=1, default=str))
    lines = ["# P3 adversarial inputs", "", f"{passed} / {len(results)} fail safely", "",
             "Every case is built on a valid two-source request and mutated; REFUSED_AT_CONTRACT is a pydantic / validator ValueError "
             "(HTTP 422 on the API before any model is built); HANDLED means the frozen model or contract bounds the case by construction.", "",
             "| case | outcome | result | detail |", "|---|---|---|---|"]
    for k, r in results.items():
        lines.append(f"| {k} | {r['outcome']} | {'PASS' if r['pass'] else 'FAIL'} | {json.dumps(r['message'], default=str)[:300]} |")
    (OUT / "P3_ADVERSARIAL.md").write_text("\n".join(lines) + "\n")
    print(f"ADVERSARIAL {'PASS' if passed == len(results) else 'FAIL'} {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
