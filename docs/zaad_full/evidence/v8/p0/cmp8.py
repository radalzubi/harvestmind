"""Side-by-side per-review comparison of diag8 JSONs. usage: cmp8.py a.json b.json [c.json]"""
import sys, json
runs = [json.load(open(p)) for p in sys.argv[1:]]
names = [r["arm"] for r in runs]
def tot(r):
    rv = r["reviews"]; d = sum(x["unmet"] + (x["service"] or 0) * 0 for x in rv)
    unmet = sum(x["unmet"] for x in rv); inv = sum(x["inventory"] or 0 for x in rv) / len(rv)
    starved = sum(x["required_starved"] for x in rv); req = sum(x["required"] for x in rv); infeas = sum(x["required_infeasible"] or 0 for x in rv)
    ftl_ok = sum(1 for x in rv for c in x["candidates"].values() if c["status"] == "FEASIBLE_TIME_LIMIT" and c["physically_validated"])
    ftl_bad = sum(1 for x in rv for c in x["candidates"].values() if c["status"] == "FEASIBLE_TIME_LIMIT" and not c["physically_validated"])
    noinc = sum(1 for x in rv for c in x["candidates"].values() if c["status"] == "NO_FEASIBLE_SOLUTION")
    lats = sorted(x["latency"] for x in rv)
    q = lambda p: lats[min(len(lats)-1, int(p*(len(lats)-1)))]
    return f"svc={r['service']} unmet={unmet:.1f} inv={inv:.1f} cost={r['cost'] and round(r['cost'])} req_starved={starved}/{req} req_infeasible={infeas} FTL_valid={ftl_ok} FTL_invalid={ftl_bad} noinc={noinc} lat p50={q(.5):.1f} p90={q(.9):.1f} p95={q(.95):.1f} max={lats[-1]:.1f} wall={r['wall']:.0f}"
for n, r in zip(names, runs): print(f"{n:16s} {tot(r)}")
print()
hdr = "rev " + " | ".join(f"{n[:14]:>14s}: state sel svc unmet inv joint[status] starved" for n in names)
print(hdr)
for i in range(max(len(r["reviews"]) for r in runs)):
    cells = []
    for r in runs:
        if i >= len(r["reviews"]): cells.append("-"); continue
        x = r["reviews"][i]
        j = x["candidates"].get("joint_recovery"); jo = (x["outcomes"] or {}).get("joint_recovery", {}).get("outcome", "NOTREQ")
        js = "-" if j is None and jo == "NOTREQ" else (j["status"][:3] if j else jo[:6])
        esc = "E" if x.get("escalated") else " "
        cells.append(f"{x['state'][:7]:7s} {str(x['selected'])[:9]:9s} {x['service'] if x['service'] is None else round(x['service'],2):>4} {x['unmet']:5.1f} {x['inventory'] if x['inventory'] is None else round(x['inventory']):>4} j={js:6s}{esc} st={','.join(n[:4] for n in (x['omissions'] and [o['candidate'] for o in x['omissions'] if o['outcome']=='required_starved']) or [])}")
    print(f"r{i:02d} " + " | ".join(cells))
