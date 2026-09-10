"""Compare two review profiles (`scripts.p2_profile_review`) candidate by candidate: the equivalence
check of a performance change. Reports decision identity (state, selected policy, status, period-zero
purchases and transfers, every action), per-candidate status / objective / dimensions / nodes / time,
and the wall-time change.

usage: PYTHONPATH=. python3 -m scripts.p2_profile_compare BEFORE.json AFTER.json [--rel 1e-6]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _close(a, b, rel: float) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) <= rel * max(1., abs(a), abs(b))


def compare(before: dict, after: dict, rel: float) -> dict:
    db, da = before["decision"], after["decision"]
    decision_keys = {k: (db[k] == da[k]) for k in ("state", "owner", "selected_policy", "status", "purchases_t0", "transfers_t0", "actions", "requested", "built")}
    cands = []
    by_label_b = {s["label"]: s for s in before["solves"] if "total_seconds" in s}
    by_label_a = {s["label"]: s for s in after["solves"] if "total_seconds" in s}
    for label in by_label_b:
        b, a = by_label_b[label], by_label_a.get(label)
        if a is None:
            cands.append({"candidate": label, "note": "absent after"})
            continue
        eb, ea = b["linear"][-1] if b["linear"] else {}, a["linear"][-1] if a["linear"] else {}
        cands.append({"candidate": label, "status": (b["status"], a["status"]), "same_status": b["status"] == a["status"],
                      "objective": (b.get("projected_cost"), a.get("projected_cost")),
                      "same_objective": _close(b.get("projected_cost"), a.get("projected_cost"), rel),
                      "variables": (b["variables"], a["variables"]), "rows": (b["constraints"], a["constraints"]),
                      "binaries": (eb.get("binary"), ea.get("binary")), "nonzeros": (eb.get("nonzeros"), ea.get("nonzeros")),
                      "nodes": (b.get("nodes"), a.get("nodes")), "gap": (b.get("gap"), a.get("gap")),
                      "total_s": (round(b["total_seconds"], 1), round(a["total_seconds"], 1)),
                      "completion_s": (round(b["completion_seconds"], 1), round(a["completion_seconds"], 1)),
                      "milp_s": (round(b["linear_seconds"], 1), round(a["linear_seconds"], 1)),
                      "warm_outcome": ((b.get("warm_start") or {}).get("outcome"), (a.get("warm_start") or {}).get("outcome"))})
    return {"decision_identical": all(decision_keys.values()), "decision_keys": decision_keys,
            "wall": (before["wall_seconds"], after["wall_seconds"]), "candidates": cands,
            "objective_identical": all(c.get("same_objective", True) and c.get("same_status", True) for c in cands),
            "switches_before": before.get("switches"), "switches_after": after.get("switches")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--rel", type=float, default=1e-6)
    a = ap.parse_args()
    r = compare(json.loads(Path(a.before).read_text()), json.loads(Path(a.after).read_text()), a.rel)
    print(f"decision identical {r['decision_identical']} {r['decision_keys']}\nobjective identical {r['objective_identical']}  wall {r['wall'][0]:.1f}s -> {r['wall'][1]:.1f}s")
    for c in r["candidates"]:
        if "note" in c:
            print(f"  {c['candidate']:<24} {c['note']}")
            continue
        flag = "" if (c["same_status"] and c["same_objective"]) else "  <-- DIFFERS"
        print(f"  {c['candidate']:<24} status {c['status'][0]}->{c['status'][1]} obj {c['objective'][0]}->{c['objective'][1]} vars {c['variables'][0]}->{c['variables'][1]} bin {c['binaries'][0]}->{c['binaries'][1]} "
              f"nodes {c['nodes'][0]}->{c['nodes'][1]} total {c['total_s'][0]}->{c['total_s'][1]}s compl {c['completion_s'][0]}->{c['completion_s'][1]}s milp {c['milp_s'][0]}->{c['milp_s'][1]}s warm {c['warm_outcome'][0]}->{c['warm_outcome'][1]}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
