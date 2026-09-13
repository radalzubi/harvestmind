"""Production baseline before the P4B release: the keep-only demo state (F20 without options) on the deployed runtime.
usage: PYTHONPATH=. python3 docs/zaad_full/evidence/p4b/release/baseline_pre_p4b.py <out.json>"""
import json, subprocess, sys, time
BASE = "https://zaad-api.fly.dev"; out = sys.argv[1]
def curl(method, path, data=None, headers=(), timeout=300):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time(); p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)
from zaad.commitments.fixtures import _f20_no_options
res = {}
c, b, _ = curl("GET", "/health", timeout=20); res["health"] = {"code": c, "body": b[:200]}
code, body, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4B release baseline"}))
ws = json.loads(body); H = [f"Authorization: Bearer {ws['token']}"]; op = ws["operator_id"]; res["workspace"] = {"code": code, "operator": op}
req = _f20_no_options().model_dump(mode="json"); req.update(operator_id=op, max_solve_seconds=5.)
for po in req["pipeline"]:                      # the released contract has no P4B fields
    po.pop("minimum_remaining_quantity", None); po.pop("deposit_refundable_fraction", None)
    for o in po["options"]: o.pop("credit_per_unit", None); o.pop("provenance", None)
c, b, s = curl("POST", "/api/zaad/network/plan", data=json.dumps(req), headers=H)
res["keep_only_plan_on_released_runtime"] = {"code": c, "seconds": s, "body": b[:300]}
json.dump(res, open(out, "w"), indent=1); print(json.dumps(res, indent=1)[:900])
