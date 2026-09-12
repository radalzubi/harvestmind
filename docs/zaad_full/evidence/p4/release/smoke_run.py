"""P4 production smoke matrix A-S against zaad-api (synthetic self-serve workspace; nothing executes)."""
import json, subprocess, sys, time, pathlib
BASE = "https://zaad-api.fly.dev"
S = pathlib.Path(__file__).parent / "smoke"
out_path = sys.argv[1]
def curl(method, path, data=None, headers=(), timeout=600):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time(); p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)
def parse(body):
    try: return json.loads(body)
    except Exception: return {"_raw": body[:400]}
def view(rep, code, s):
    if not isinstance(rep, dict): return {"code": code, "seconds": s, "raw": str(rep)[:200]}
    rc = rep.get("recourse")
    cands = {k: (v.get("status"), round(v.get("solve_seconds", 0), 1)) for k, v in (rep.get("candidates") or {}).items()} if isinstance(rep.get("candidates"), dict) else None
    return {"code": code, "seconds": s, "status": rep.get("status"), "selected": rep.get("selected_policy"), "detail": rep.get("detail"),
            "approval": rep.get("approval_required"), "epo": rep.get("executable_purchase_order"), "candidates": cands,
            "recourse": None if rc is None else {"verdict": rc.get("verdict"), "pi_status": rc.get("perfect_information_status"), "pi_cost": rc.get("perfect_information_cost"),
                                                 "pi_feasible": rc.get("perfect_information_feasible_cost"), "value": rc.get("value_of_adaptation"), "material": rc.get("material"),
                                                 "ordering": rc.get("ordering_ok"), "na": (rc.get("non_anticipativity") or {}).get("pass"), "replan": rc.get("replan_required"),
                                                 "sets": [e.get("information_sets") for e in rc.get("policy", [])], "approval": rc.get("approval_required"), "epo": rc.get("executable_purchase_order"),
                                                 "scope": rc.get("perfect_information_scope")}}
results = {}
def record(label, val):
    results[label] = val; print(label, json.dumps(val, default=str)[:900], flush=True)
    json.dump(results, open(out_path, "w"), default=str, indent=1)
code, body, s = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4 release smoke"}))
ws = parse(body); H = [f"Authorization: Bearer {ws['token']}"]; op = ws["operator_id"]
code2, body2, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4 release smoke tenant B"}))
ws2 = parse(body2); H2 = [f"Authorization: Bearer {ws2['token']}"]
record("workspace", {"code": code, "operator": op, "second": code2})
def payload(name):
    return json.dumps({**json.load(open(S / f"{name}.json")), "operator_id": op})
plan_cases = [("A_legacy", 200), ("B_enabled_false", 200), ("C_commercial_simple", 200), ("D_produce", 200), ("E_meat", 200), ("F_p2_network", 200),
              ("G_p3_source_mix", 200), ("H_correlated", 200), ("I_waiting", 200), ("J_malformed_epoch", 422), ("K_unsupported_observable", 422),
              ("L_tree_too_high", 413), ("M_shared_order_interactive", 413)]
for name, expect in plan_cases:
    code, body, s = curl("POST", "/api/zaad/network/plan", data=payload(name), headers=H)
    rep = parse(body); v = view(rep, code, s); v["expected"] = expect; v["ok"] = (code == expect)
    if name in ("A_legacy", "B_enabled_false"): v["has_recourse_block"] = isinstance(rep, dict) and "recourse" in rep
    record(name, v)
# N: the shared-order request through /jobs
code, body, s = curl("POST", "/api/zaad/network/jobs", data=payload("M_shared_order_interactive"), headers=H)
sub = parse(body); record("N_job_submit", {"code": code, "body": sub, "seconds": s})
job = sub.get("job_id") if isinstance(sub, dict) else None
if job:
    # R: tenant isolation on the job
    c2, b2, _ = curl("GET", f"/api/zaad/network/jobs/{job}", headers=H2); record("R_other_tenant_reads_job", {"code": c2, "expected": 404, "ok": c2 == 404})
    t0 = time.time(); final = None
    while time.time() - t0 < 1500:
        c, b, _ = curl("GET", f"/api/zaad/network/jobs/{job}", headers=H); j = parse(b)
        if isinstance(j, dict) and j.get("status") in ("DONE", "FAILED", "TIMEOUT", "CANCELLED"): final = j; break
        time.sleep(10)
    if final is None: record("N_job_result", {"status": "still running after 1500 s"})
    else:
        rep = final.get("report") or {}
        record("N_job_result", {"status": final["status"], "error": final.get("error"), "seconds": round(time.time() - t0), "timeout_s": final.get("timeout_s"),
                                "started": final.get("started_at"), "finished": final.get("finished_at"), "report": view(rep, 200, 0) if rep else None})
# Q: old workspace / no recourse declaration through the from-workspace path (recourse=true attaches nothing without a row)
for flag in ("false", "true"):
    c, b, s = curl("POST", f"/api/zaad/network/plan/from-workspace?skus=SKU-001&max_solve_seconds=10&recourse={flag}", data="{}", headers=H)
    rep = parse(b); record(f"Q_from_workspace_recourse_{flag}", {"code": c, "seconds": s, "selected": rep.get("selected_policy") if isinstance(rep, dict) else None,
                                                                    "has_recourse_block": isinstance(rep, dict) and "recourse" in rep, "detail": rep.get("detail") if isinstance(rep, dict) else str(rep)[:300]})
# R: tenant mismatch on /plan and unauthenticated
c, b, _ = curl("POST", "/api/zaad/network/plan", data=payload("C_commercial_simple"), headers=H2); record("R_plan_operator_mismatch", {"code": c, "expected": 403, "ok": c == 403})
c, b, _ = curl("GET", "/api/zaad/network/jobs"); record("R_jobs_unauthenticated", {"code": c, "expected": 401, "ok": c == 401})
# S: CORS preflight + health
c, b, _ = curl("OPTIONS", "/api/zaad/network/plan", headers=["Origin: https://zaadsupply.com", "Access-Control-Request-Method: POST"])
record("S_cors_preflight", {"code": c})
c, b, _ = curl("GET", "/health"); record("S_health", {"code": c, "body": parse(b)})
print("SMOKE_DONE")
