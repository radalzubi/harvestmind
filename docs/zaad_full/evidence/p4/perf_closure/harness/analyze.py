"""Summarise the P4 perf profile JSON: per cell, the adaptive compare solve's dimensions / binaries / node columns /
presolve / timings, plus planner wall, build vs solve, candidate solve count."""
import json, sys
rows = json.load(open(sys.argv[1]))
def solve_of(row, tag):
    return next((c for c in row.get("compare_solves", []) if c["kind"] == "solve" and c["label"].endswith("compare")), None)
print("| class | h | epochs | c | worlds | sets | solve | build s | rows | cols | int | bin | nnz | presolved rows/cols/bin | bin by class | node cols | first inc s | nodes | LP it | solve s | obj | gap | matrix range |")
for r in rows:
    if "error" in r: print("| ERROR", r["class"], r.get("error")); continue
    solves = [c for c in r["compare_solves"] if c["kind"] == "solve"]
    for label, c in zip(("static", "adaptive", "perfect"), solves[:3]):
        lp = c.get("log_parsed", {}); pm = lp.get("presolved_model", {})
        print(f"| {r['class']} | {r['histories']} | {r['epochs']} | {r['continuations']} | {r['worlds']} | {r['information_sets']} | {label} | {c['build_s']} | {c['rows']} | {c['cols']} | {c['integer']} | {c['binary']} | {c['nnz']} | {pm.get('rows')}/{pm.get('cols')}/{pm.get('binary')} | {c['binaries_by_class']} | {c['node_columns']} | {lp.get('first_incumbent_s')} | {c['bb_nodes']} | {lp.get('lp_iterations')} | {c['solve_wall_s']} | {round(c['objective'],1) if c['objective'] is not None else None} | {c['gap']} | {lp.get('coefficient_ranges',{}).get('matrix')} |")
print()
print("| class | h | epochs | worlds | compare wall | planner wall | planner solves | planner solver wall | planner build wall | verdict |")
for r in rows:
    if "error" in r: continue
    print(f"| {r['class']} | {r['histories']} | {r['epochs']} | {r['worlds']} | {r['compare_wall_s']} | {r.get('planner_wall_s')} | {r.get('planner_candidate_solves')} | {r.get('planner_solver_wall_s')} | {r.get('planner_build_wall_s')} | {r.get('planner_verdict', r.get('planner_error'))} |")
print()
print("planner solves of the heaviest cells:")
for r in rows:
    if "error" in r or r["class"] not in ("D_p3_shared_order", "E_produce") or r["worlds"] < 12: continue
    print(r["class"], r["histories"], r["epochs"], r["worlds"])
    for s in r.get("planner_solves", []):
        print("   ", {k: s.get(k) for k in ("label", "kind", "solve_wall_s", "build_s", "rows", "cols", "binary", "status", "bb_nodes")})
