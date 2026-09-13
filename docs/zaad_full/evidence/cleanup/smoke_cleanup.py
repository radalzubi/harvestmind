"""Post-P4B cleanup production smoke (rule 30): health, no-declaration plan, P4B KEEP, P4B recommendation, P5 ATP path,
tenant isolation, job path. usage: PYTHONPATH=. python3 docs/zaad_full/evidence/cleanup/smoke_cleanup.py <out.json>"""
import json, subprocess, sys, time
from zaad.atp.fixtures import build as build_iso
from zaad.atp.fixtures_integration import build as build_int
from zaad.commitments.explain import NO_IMPROVEMENT, RECOMMENDED
from zaad.commitments.fixtures import _f20_no_options, build
BASE = "https://zaad-api.fly.dev"; out = sys.argv[1]
def curl(method, path, data=None, headers=(), timeout=600):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time(); p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)
def j(b):
    try: return json.loads(b)
    except Exception: return {"_raw": b[:300]}
res = {}
c, b, s = curl("GET", "/health", timeout=20); res["01_health"] = {"code": c, "seconds": s, "body": j(b)}
c, b, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "post-P4B cleanup smoke"})); ws = j(b); H = [f"Authorization: Bearer {ws['token']}"]; op = ws["operator_id"]
c2, b2, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "post-P4B cleanup smoke B"})); ws2 = j(b2); H2 = [f"Authorization: Bearer {ws2['token']}"]
res["workspaces"] = {"A": (c, op), "B": (c2, ws2.get("operator_id"))}
def payload(req, **over): return json.dumps({**req.model_dump(mode="json"), "operator_id": op, "max_solve_seconds": 5., **over})
def plan(req, headers=H):
    c, b, s = curl("POST", "/api/zaad/network/plan", data=payload(req), headers=headers); r = j(b); cm = r.get("commitments") or {}
    return {"code": c, "seconds": s, "status": r.get("status"), "commitments_present": "commitments" in r, "commitment_action": cm.get("commitment_action"), "commitment_verdict": cm.get("commitment_verdict"),
            "approval_required": r.get("approval_required"), "executable_purchase_order": r.get("executable_purchase_order"), "block_executable_amendment": cm.get("executable_amendment"), "atp_present": "atp" in r}
res["02_no_declaration_plan"] = plan(_f20_no_options())
res["03_p4b_keep"] = plan(build("F20_keep_optimal")); res["03_p4b_keep"]["exact_verdict"] = res["03_p4b_keep"]["commitment_verdict"] == NO_IMPROVEMENT
res["04_p4b_recommendation"] = plan(build("F01_cancel_optimal")); res["04_p4b_recommendation"]["exact_verdict"] = res["04_p4b_recommendation"]["commitment_verdict"] == RECOMMENDED
c, b, s = curl("POST", "/api/zaad/atp/promise", data=payload(build_iso("B_true_scarcity")), headers=H); r = j(b); a = r.get("atp") or {}
res["05_p5_atp_standalone"] = {"code": c, "seconds": s, "verdict": a.get("verdict"), "reservations": len(a.get("reservations") or []), "approval": r.get("approval_required"), "executable_promise": r.get("executable_promise")}
r = plan(build_int("I01_p0_protection_scarcity")); res["05_p5_atp_planner_path"] = r
c, b, s = curl("POST", "/api/zaad/network/plan", data=payload(build("F01_cancel_optimal")), headers=H2); res["06_tenant_isolation_plan"] = {"code": c, "detail": str(j(b).get("detail"))[:80]}
c, b, s = curl("POST", "/api/zaad/atp/promise", data=payload(build_iso("B_true_scarcity")), headers=H2); res["06_tenant_isolation_atp"] = {"code": c}
c, b, s = curl("POST", "/api/zaad/network/jobs", data=payload(build("F06_defer_reduces_excess")), headers=H); sub = j(b); job = sub.get("job_id"); res["07_job_submit"] = {"code": c, "job": job}
final = None; t0 = time.time()
while job and time.time() - t0 < 600:
    c, b, _ = curl("GET", f"/api/zaad/network/jobs/{job}", headers=H); jj = j(b)
    if jj.get("status") in ("DONE", "FAILED", "TIMEOUT", "CANCELLED"): final = jj; break
    time.sleep(10)
rep = (final or {}).get("report") or {}; cm = rep.get("commitments") or {}
res["07_job_result"] = {"status": (final or {}).get("status"), "wall_s": round(time.time() - t0), "commitments_present": "commitments" in rep, "commitment_action": cm.get("commitment_action"), "executable_amendment": cm.get("executable_amendment"), "error": (final or {}).get("error")}
json.dump(res, open(out, "w"), indent=1, default=str); print(json.dumps(res, indent=1, default=str)[:5000]); print("SMOKE_DONE")
