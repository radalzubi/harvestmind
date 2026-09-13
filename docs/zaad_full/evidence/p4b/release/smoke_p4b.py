"""P4B V1 production smoke (release audit): run against the deployed runtime from a clean checkout.
usage: PYTHONPATH=. python3 docs/zaad_full/evidence/p4b/release/smoke_p4b.py <out.json>
Creates two self-serve workspaces (tokens); then the twelve release-brief checks: health; no declaration -> released plan without
a commitments block; KEEP-only; cancel-optimal (approval only); the exact no-improvement verdict; refundable deposit reconciles;
excessive credit 422; expired option unavailable; invalid stage 422; cross-tenant 403 + from-workspace with the flag; jobs path with
the block; mixed overall-plan / commitment verdict. Nothing is persisted; every recommendation is approval-only."""
import json, subprocess, sys, time
from zaad.commitments.explain import NO_IMPROVEMENT
from zaad.commitments.fixtures import CANCEL, KEEP, _f20_no_options, base, build, build_request, open_po, with_stock
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
res = {}
c, b, s = curl("GET", "/health", timeout=20); res["01_health"] = {"code": c, "seconds": s, "body": j(b)}
code, body, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4B release smoke"}))
ws = j(body); H = [f"Authorization: Bearer {ws['token']}"]; op = ws["operator_id"]; res["workspace"] = {"code": code, "operator": op}
code2, body2, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4B release smoke tenant B"}))
ws2 = j(body2); H2 = [f"Authorization: Bearer {ws2['token']}"]; res["workspace_b"] = {"code": code2, "operator": ws2.get("operator_id")}
def payload(req, **over): return json.dumps({**req.model_dump(mode="json"), "operator_id": op, "max_solve_seconds": 5., **over})
def plan(req, headers=H):
    c, b, s = curl("POST", "/api/zaad/network/plan", data=payload(req), headers=headers); return c, j(b), s
def summary(c, r, s):
    cm = r.get("commitments") or {}
    return {"code": c, "seconds": s, "status": r.get("status"), "commitments_present": "commitments" in r, "commitment_action": cm.get("commitment_action"),
            "commitment_verdict": cm.get("commitment_verdict"), "commitment_value_vs_keep": cm.get("commitment_value_vs_keep"), "overall_plan_status": cm.get("overall_plan_status"),
            "approval_required": r.get("approval_required"), "executable_amendment": r.get("executable_amendment"), "executable_purchase_order": r.get("executable_purchase_order"),
            "reading": (cm.get("reading") or "")[:200]}
c, r, s = plan(_f20_no_options()); res["02_no_declaration"] = {**summary(c, r, s), "executable_amendment_key_present": "executable_amendment" in r}
c, r, s = plan(build("F20_keep_optimal")); res["03_keep_only_balanced"] = summary(c, r, s)
c, r, s = plan(build("F01_cancel_optimal")); res["04_cancel_optimal"] = {**summary(c, r, s), "quantities": ((r.get("commitments") or {}).get("orders") or [{}])[0].get("quantities")}
c, r, s = plan(build("F02_cancel_not_worthwhile")); res["05_no_material_improvement"] = {**summary(c, r, s), "exact": (r.get("commitments") or {}).get("commitment_verdict") == NO_IMPROVEMENT}
c, r, s = plan(build("F12_refundable_deposit")); cm = r.get("commitments") or {}
res["06_refundable_deposit"] = {**summary(c, r, s), "commitment_credit_ledger": (cm.get("commitment_ledger_lines") or {}).get("commitment_credit"),
                                "refundable_credits": ((cm.get("orders") or [{}])[0].get("economic_drivers") or {}).get("refundable_credits"), "sunk_per_unit": ((cm.get("orders") or [{}])[0].get("irreversibility") or {}).get("sunk_per_unit")}
d = with_stock(base(), 200.)
bad = json.loads(payload(build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=.5)], prepaid=2., refundable=.25)))); bad["pipeline"][0]["options"][1]["credit_per_unit"] = 3.
c, b, s = curl("POST", "/api/zaad/network/plan", data=json.dumps(bad), headers=H); res["07_excessive_credit"] = {"code": c, "detail": str(j(b).get("detail"))[:220]}
c, r, s = plan(build_request(d, open_po(d, [KEEP(d), CANCEL(d, deadline_days=-1)]))); cm = r.get("commitments") or {}
win = [w for o in (cm.get("orders") or []) for w in o.get("amendment_windows", []) if w.get("action") == "cancel"]
res["08_expired_option"] = {**summary(c, r, s), "window": win[0] if win else None}
bad = json.loads(payload(build("F01_cancel_optimal"))); bad["pipeline"][0]["stage"] = "teleported"
c, b, s = curl("POST", "/api/zaad/network/plan", data=json.dumps(bad), headers=H); res["09_invalid_stage"] = {"code": c, "detail": str(j(b).get("detail"))[:220]}
c, r, s = plan(build("F01_cancel_optimal"), headers=H2); res["10_cross_tenant_plan"] = {"code": c, "detail": str(r.get("detail"))[:120]}
c, b, s = curl("GET", "/api/zaad/network/plan/from-workspace?commitments=true&max_solve_seconds=5", headers=H2); res["10_cross_tenant_from_workspace_flag"] = {"code": c, "detail": str(j(b).get("detail"))[:160]}
c, b, s = curl("POST", "/api/zaad/network/jobs", data=payload(build("F06_defer_reduces_excess")), headers=H); sub = j(b); job = sub.get("job_id"); res["11_job_submit"] = {"code": c, "job": job, "approval_required": sub.get("approval_required")}
final = None; t0 = time.time()
while job and time.time() - t0 < 600:
    c, b, _ = curl("GET", f"/api/zaad/network/jobs/{job}", headers=H); jj = j(b)
    if jj.get("status") in ("DONE", "FAILED", "TIMEOUT", "CANCELLED"): final = jj; break
    time.sleep(10)
rep = (final or {}).get("report") or {}; cm = rep.get("commitments") or {}
res["11_job_result"] = {"status": (final or {}).get("status"), "wall_s": round(time.time() - t0), "commitments_present": "commitments" in rep, "commitment_action": cm.get("commitment_action"),
                        "commitment_verdict": cm.get("commitment_verdict"), "approval_required": cm.get("approval_required"), "executable_amendment": cm.get("executable_amendment"), "error": (final or {}).get("error")}
c, r, s = plan(build("F14_alternative_source")); cm = r.get("commitments") or {}
res["12_mixed_plan_vs_commitment"] = {**summary(c, r, s), "changes_outside": (cm.get("plan_changes_outside_commitments") or [])[:3]}
json.dump(res, open(out, "w"), indent=1, default=str); print(json.dumps(res, indent=1, default=str)[:6000]); print("SMOKE_DONE")
