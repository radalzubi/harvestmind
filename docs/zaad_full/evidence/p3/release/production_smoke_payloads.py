"""Bounded P3 production smoke payloads from the pre-registered fixture builder (interactive caps:
sources <= 40, horizon 12, scenarios <= 4, max_solve x (10 + services) <= 180)."""
import json, sys
from zaad.sourcing.fixtures import build, variant
from zaad.meio.fixtures_p2 import p2_request
from zaad.full.contracts import Request

MAX_SOLVE = 5.
DECL = "OPERATOR_DECLARED"

def dump(req: Request) -> dict:
    p = req.model_dump(mode="json")
    p["max_solve_seconds"] = MAX_SOLVE
    p["scenarios"] = min(int(p["scenarios"]), 3)
    return p

payloads = {}
payloads["legacy_no_p3"] = dump(p2_request())                                   # 23: frozen path, sourcing None
p = dump(build("A5_single_source_legacy_identity", 41001)); payloads["single_source"] = p   # 24
payloads["economics_two_source"] = dump(build("E2_landed_beats_unit_price", 41001))         # 25
payloads["capacity_split"] = dump(build("R2_capacity_forces_split", 41001))                # 26
payloads["moq_mov"] = dump(build("E4_moq_mov_small_order", 41001))                          # 27
payloads["packs"] = dump(build("S4_commercial_pallets", 41001))                             # 27
payloads["payment_terms"] = dump(build("E5_payment_terms_preference", 41001))               # 28
payloads["switching_small"] = dump(build("E6_switching_cost_retains_incumbent", 41001))      # 29
big = build("E6_switching_cost_retains_incumbent", 41001).model_dump(mode="json")
for s in big["sources"]:
    if s["id"] == "src_B":
        s["unit_price"] = 4.0                                                               # 20 % cheaper: exceeds 2,000 over the plan
big["sourcing"]["switching_costs"][0]["cost"] = 300.
payloads["switching_large"] = dump(Request.model_validate(big))                             # 29b
payloads["shares"] = dump(build("C2_declared_min_max_share", 41001))                        # 30
# 31: A + B share a plant, C independent
r4 = build("R4_shared_plant_no_fake_diversification", 41001).model_dump(mode="json")
a = next(s for s in r4["sources"] if s["id"] == "src_A")
r4["sources"].append({**a, "id": "src_C", "supplier": "supplier_c", "route": ["supplier_c", "central"], "resources": ["cap_supplier_c"], "unit_price": 5.05})
r4["resources"].append({**r4["resources"][0], "id": "cap_supplier_c", "failure_domains": ["supplier_c"]})
payloads["correlated_risk"] = dump(Request.model_validate(r4))
payloads["independent_sources"] = dump(build("R6_identical_no_split", 41001))               # 32
payloads["produce"] = dump(build("S1_produce_short_life", 41001))                           # 33 + 41 (age 5 of 8 -> life 3)
payloads["meat"] = dump(build("S3_frozen_invalid_route", 41001))                            # 34
payloads["network"] = dump(build("N1_source_to_central_with_transfers", 41001))             # 35
payloads["multi_sku_capacity"] = dump(build("C5_shared_capacity_multi_sku", 41001))         # 36
payloads["shared_mov"] = dump(build("C6_shared_mov_multi_sku", 41001))                      # 37
# 41: PRODUCE, nominal shelf life 6, declared age at receipt 3 for the import
pr = p2_request(max_solve_seconds=MAX_SOLVE).model_dump(mode="json")
pr["skus"][0]["shelf_life"] = 6
for lot in pr["stock"]:
    lot["expires_in"] = min(lot["expires_in"], 6)
pr["sector_mode"] = "PRODUCE"
pr["sku_physics"] = [{"sku": "A", "sector": "PRODUCE", "minimum_remaining_life_at_sale": 1, "age_at_receipt_by_source": {"src_A": 3},
                      "provenance": {"minimum_remaining_life_at_sale": DECL, "age_at_receipt_by_source": DECL}}]
pr["sourcing"] = {"incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": DECL}]}
payloads["age_at_receipt"] = dump(Request.model_validate(pr))
# 38: malformed (each built from the two-source economics payload)
base = payloads["economics_two_source"]
bad = {}
bad["unknown_supplier_in_group"] = {**base, "sourcing": {**base["sourcing"], "risk_groups": [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_ghost"], "provenance": DECL}]}}
bad["source_not_approved_with_min_share"] = {**base, "sources": [{**s, "approved": s["id"] != "src_B"} for s in base["sources"]],
    "sourcing": {**base["sourcing"], "share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .2, "provenance": DECL}],
                 "incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_B", "share": .2, "provenance": DECL}]}}
bad["negative_capacity"] = {**base, "sources": [{**s, "capacity_by_period": [-1.] * 12} if s["id"] == "src_B" else s for s in base["sources"]]}
bad["min_share_above_max"] = {**base, "sourcing": {**base["sourcing"], "share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .6, "maximum_share": .4, "provenance": DECL}]}}
bad["shares_impossible"] = {**base, "sourcing": {**base["sourcing"], "share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "maximum_share": .3, "provenance": DECL}, {"sku": "A", "destination": "central", "source": "src_A", "maximum_share": .3, "provenance": DECL}],
                                                  "incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": .3, "provenance": DECL}]}}
bad["missing_provenance"] = {**base, "sourcing": {**base["sourcing"], "risk_groups": [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_B"], "provenance": "UNKNOWN"}]}}
bad["infinite_price"] = json.loads(json.dumps({**base, "sources": [{**s, "unit_price": 1e308} if s["id"] == "src_B" else s for s in base["sources"]]}))
bad["infinite_price"]["sources"][1]["unit_price"] = "Infinity"
many = json.loads(json.dumps(base))
for i in range(9):
    many["sources"].append({**a, "id": f"src_x{i}", "supplier": f"supplier_x{i}", "route": [f"supplier_x{i}", "central"], "unit_price": 5.0 + i * .01})
bad["excessive_sources"] = many
payloads["_malformed"] = bad
json.dump(payloads, open(sys.argv[1], "w"), default=str)
print({k: (len(v["sources"]) if k != "_malformed" else len(v)) for k, v in payloads.items()})
