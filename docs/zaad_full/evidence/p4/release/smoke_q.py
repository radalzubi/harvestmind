"""Q: an existing workspace with staging data but no recourse declaration -> recourse=true attaches nothing; reports identical (timing / hash stripped)."""
import json, re, subprocess, sys, time
BASE = "https://zaad-api.fly.dev"; out = sys.argv[1]
def curl(method, path, data=None, headers=(), timeout=600):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time(); p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)
def strip(s): return re.sub(r'"information_hash": "[0-9a-f]+"|"solve_seconds": [0-9.e-]+|"solver_seconds_total": [0-9.e-]+|"seconds": [0-9.e-]+|"plan_wall_s": [0-9.e-]+|"generated_at": "[^"]+"|"timestamp": "[^"]+"', "", s)
res = {}
code, body, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4 release smoke Q"}))
ws = json.loads(body); H = [f"Authorization: Bearer {ws['token']}"]
code, body, s = curl("POST", "/intake/load-sample-fmcg?seed=7", data="{}", headers=H); res["load_sample"] = {"code": code, "seconds": s, "body": body[:200]}
print("load", res["load_sample"], flush=True)
code, body, s = curl("GET", "/api/zaad/network/request/from-workspace?skus=SKU-0001,SKU-0002&max_solve_seconds=10&recourse=true", headers=H)
req = json.loads(body) if code == 200 else {"_raw": body[:300]}
res["request_recourse_true"] = {"code": code, "recourse_field": (req.get("request") or req).get("recourse", "absent") if isinstance(req, dict) else None}
print("request", res["request_recourse_true"], flush=True)
reports = {}
for flag in ("false", "true"):
    code, body, s = curl("POST", f"/api/zaad/network/plan/from-workspace?skus=SKU-0001,SKU-0002&max_solve_seconds=10&recourse={flag}", data="{}", headers=H)
    rep = json.loads(body) if code == 200 else {"_raw": body[:300]}
    reports[flag] = body
    res[f"plan_recourse_{flag}"] = {"code": code, "seconds": s, "status": rep.get("status"), "selected": rep.get("selected_policy"), "approval": rep.get("approval_required"), "epo": rep.get("executable_purchase_order"), "has_recourse_block": "recourse" in rep, "detail": rep.get("detail") or rep.get("_raw")}
    print(flag, res[f"plan_recourse_{flag}"], flush=True)
res["identical_stripped"] = strip(reports["false"]) == strip(reports["true"])
print("identical (timing/hash stripped):", res["identical_stripped"])
json.dump(res, open(out, "w"), indent=1, default=str); print("Q_DONE")
