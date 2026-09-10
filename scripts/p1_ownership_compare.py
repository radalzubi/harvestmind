"""Decision-level bit-identity of the frozen P0 path under the ownership router (stage 11).
usage: PYTHONPATH=. python3 -m scripts.p1_ownership_compare clean_reference router
Compares, review by review on the six P0 cells, the candidate request set, built set, selected
candidate, status, period-0 order, recovery admission, feasible set and materiality verdict of the
two arms (`closure/p0_arm_<arm>.json`), and reports the owner the router assigned. Time-limit
variation with identical architectural inputs is classed as frozen numerical variability."""
from __future__ import annotations
import json, sys
P = "docs/zaad_full/evidence/p1/closure"
a_name, b_name = sys.argv[1], sys.argv[2]
A = json.load(open(f"{P}/p0_arm_{a_name}.json")); B = json.load(open(f"{P}/p0_arm_{b_name}.json"))
KEYS = ("state", "requested", "built", "selected", "status", "recovery_mode", "feasible", "chosen")


def norm(v):
    if isinstance(v, dict):
        return {k: (round(x, 6) if isinstance(x, float) else x) for k, x in v.items()}
    return v


total_reviews = identical = 0
for cid in ("15", "16", "20", "21", "90", "108"):
    ra, rb = A[cid]["per_review"], B[cid]["per_review"]
    owners = {}
    for r in rb:
        owners[r.get("owner") or "?"] = owners.get(r.get("owner") or "?", 0) + 1
    diffs = []
    for i, (x, y) in enumerate(zip(ra, rb)):
        total_reviews += 1
        arch = all(x.get(k) == y.get(k) for k in KEYS) and norm(x.get("final_p0")) == norm(y.get("final_p0")) \
            and (x.get("materiality") or {}).get("material") == (y.get("materiality") or {}).get("material") \
            and (y.get("p1_classes_added") or []) == []
        if arch:
            identical += 1
        else:
            diffs.append((i, {k: (x.get(k), y.get(k)) for k in KEYS if x.get(k) != y.get(k)},
                          {"final_p0": (norm(x.get("final_p0")), norm(y.get("final_p0")))} if norm(x.get("final_p0")) != norm(y.get("final_p0")) else {},
                          {"p1_added": y.get("p1_classes_added")} if y.get("p1_classes_added") else {},
                          {"unmet": (round(x["unmet"], 1), round(y["unmet"], 1))}))
    print(f"cell {cid:>3}: reviews {len(ra)} | owners (router arm) {owners} | p1 classes added {B[cid].get('p1_classes_added')} "
          f"| decision-identical reviews {len(ra) - len(diffs)}/{len(ra)} | cost {A[cid]['cost']:.0f} -> {B[cid]['cost']:.0f} | service {A[cid]['service']:.3f} -> {B[cid]['service']:.3f} "
          f"| unmet {A[cid]['total_unmet']:.1f} -> {B[cid]['total_unmet']:.1f} | starved {A[cid]['required_starved']} -> {B[cid]['required_starved']}")
    for i, d, f, p, u in diffs:
        first = " <<< first divergence" if (i, d, f, p, u) == diffs[0] else ""
        print(f"    r{i:2d} {d} {f} {p} unmet {u}{first}")
print(f"\nP0-owned reviews decision-identical: {identical}/{total_reviews}")
