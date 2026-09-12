"""P5 production smoke (release audit): run against the deployed runtime from a clean checkout.
usage: PYTHONPATH=. python3 docs/zaad_full/evidence/p5/release/smoke_p5.py <out.json>
Creates a self-serve workspace (token), then: health; P5 disabled-path identity (frozen plan without a
block); standalone /atp/promise (B scarcity, I17 every unit state, R07 refusal 422, absent block 422, bounds
413); planner path /plan with a block (I01: frozen keys + atp block, protection overlay); tenant mismatch 403
from a second workspace; jobs path 202 -> report with the block. Nothing is persisted; approval flags checked."""
import json, subprocess, sys, time
BASE = "https://zaad-api.fly.dev"; out = sys.argv[1]
def curl(method, path, data=None, headers=(), timeout=600):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time(); p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)
def j(body):
    try: return json.loads(body)
    except Exception: return {"_raw": body[:300]}
from zaad.atp.fixtures import build as build_iso
from zaad.atp.fixtures_integration import build as build_int
from zaad.atp.contracts import ServiceClass
from zaad.atp.fixtures import STD, base, line, order, scene, with_atp
res = {}
code, body, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P5 release smoke"}))
ws = j(body); H = [f"Authorization: Bearer {ws['token']}"]; op = ws["operator_id"]; res["workspace"] = {"code": code, "operator": op}
code2, body2, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P5 release smoke tenant B"}))
ws2 = j(body2); H2 = [f"Authorization: Bearer {ws2['token']}"]; res["workspace_b"] = {"code": code2, "operator": ws2.get("operator_id")}
def payload(req, **over): return json.dumps({**req.model_dump(mode="json"), "operator_id": op, "max_solve_seconds": 5., **over})
c, b, s = curl("GET", "/health", timeout=20); res["health"] = {"code": c, "seconds": s}
# disabled path: the released P2 request without a block -> frozen plan, no atp key
c, b, s = curl("POST", "/api/zaad/network/plan", data=payload(build_int("I20_disabled_exact_pre_p5")), headers=H); r = j(b)
res["A_disabled_plan"] = {"code": c, "seconds": s, "atp_key_present": "atp" in r, "status": r.get("status"), "approval": r.get("approval_required")}
# standalone endpoint
for name, req in (("B_scarcity", build_iso("B_true_scarcity")), ("I17_every_state", build_int("I17_ledger_reconciliation"))):
    c, b, s = curl("POST", "/api/zaad/atp/promise", data=payload(req), headers=H); r = j(b); a = r.get("atp") or {}
    res[f"S_{name}"] = {"code": c, "seconds": s, "verdict": a.get("verdict"), "ledger": a.get("ledger"), "reservations": len(a.get("reservations") or []),
                        "p2_transfers": (a.get("fulfilment") or {}).get("p2_transfers_created"), "approval": r.get("approval_required"), "executable_promise": r.get("executable_promise"), "path": a.get("path")}
    print(name, json.dumps(res[f"S_{name}"], default=str)[:400], flush=True)
# refusals: double shortage declaration (R07), absent block, bounds
bad = scene(base(), 10.); bad_json = {**bad.model_dump(mode="json"), "operator_id": op, "max_solve_seconds": 5., "atp": {"enabled": True, "orders": [{"id": "o1", "customer": "c1", "service_class": "k", "lines": [{"id": "l1", "sku": "A", "quantity": 10.0, "requested_period": 0}]}], "service_classes": [{"id": "k", "shortage_penalty_per_unit": 2.5}]}}
c, b, s = curl("POST", "/api/zaad/atp/promise", data=json.dumps(bad_json), headers=H); res["R_double_declaration"] = {"code": c, "detail": str(j(b).get("detail"))[:220]}
c, b, s = curl("POST", "/api/zaad/atp/promise", data=payload(build_int("I20_disabled_exact_pre_p5")), headers=H); res["R_absent_block"] = {"code": c, "detail": str(j(b).get("detail"))[:120]}
big = json.loads(payload(build_iso("B_true_scarcity"))); big["atp"]["orders"] = [{**big["atp"]["orders"][0], "id": f"o{i}", "lines": [{**big["atp"]["orders"][0]["lines"][0], "id": f"l{i}"}]} for i in range(201)]
c, b, s = curl("POST", "/api/zaad/atp/promise", data=json.dumps(big), headers=H); res["R_bounds"] = {"code": c, "detail": str(j(b).get("detail"))[:120]}
# planner path with a block (I01), overlay present, frozen keys present
c, b, s = curl("POST", "/api/zaad/network/plan", data=payload(build_int("I01_p0_protection_scarcity")), headers=H); r = j(b); a = r.get("atp") or {}
res["P_planner_with_block"] = {"code": c, "seconds": s, "status": r.get("status"), "selected": r.get("selected_policy"), "atp_verdict": a.get("verdict"), "path": a.get("path"),
                               "overlay_rows": len(a.get("protection_overlay") or []), "overlay_available": a.get("protection_overlay_available"), "approval": r.get("approval_required"), "epo": r.get("executable_purchase_order")}
print("planner", json.dumps(res["P_planner_with_block"], default=str)[:400], flush=True)
# tenant mismatch: tenant B's token on operator A's request -> 403 on both paths
c, b, s = curl("POST", "/api/zaad/atp/promise", data=payload(build_iso("B_true_scarcity")), headers=H2); res["T_standalone_other_tenant"] = {"code": c}
c, b, s = curl("POST", "/api/zaad/network/plan", data=payload(build_int("I01_p0_protection_scarcity")), headers=H2); res["T_planner_other_tenant"] = {"code": c}
c, b, s = curl("POST", "/api/zaad/network/jobs", data=payload(build_int("I01_p0_protection_scarcity")), headers=H2); res["T_jobs_other_tenant"] = {"code": c}
# jobs path with a block
c, b, s = curl("POST", "/api/zaad/network/jobs", data=payload(build_int("I01_p0_protection_scarcity")), headers=H); sub = j(b); job = sub.get("job_id"); res["J_submit"] = {"code": c, "job": job}
final = None; t0 = time.time()
while job and time.time() - t0 < 600:
    c, b, _ = curl("GET", f"/api/zaad/network/jobs/{job}", headers=H); jj = j(b)
    if jj.get("status") in ("DONE", "FAILED", "TIMEOUT", "CANCELLED"): final = jj; break
    time.sleep(10)
rep = (final or {}).get("report") or {}
res["J_job"] = {"status": (final or {}).get("status"), "wall_s": round(time.time() - t0), "atp_present": "atp" in rep, "atp_verdict": (rep.get("atp") or {}).get("verdict")}
json.dump(res, open(out, "w"), indent=1, default=str); print("SMOKE_DONE")
