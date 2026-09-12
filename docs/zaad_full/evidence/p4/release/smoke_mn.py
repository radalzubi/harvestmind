"""M (413 shared-order rule with a legal solver budget) and a quiet rerun of job N with host-steal snapshots and API responsiveness probes."""
import json, subprocess, sys, time, pathlib
BASE = "https://zaad-api.fly.dev"; S = pathlib.Path(__file__).parent / "smoke"; out = sys.argv[1]
def curl(method, path, data=None, headers=(), timeout=600):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time(); p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)
def steal():
    p = subprocess.run(["fly", "ssh", "console", "-a", "zaad-api", "-C", "cat /proc/stat"], capture_output=True, text=True)
    f = p.stdout.split("\n")[0].split()
    return {"user": int(f[1]), "system": int(f[3]), "idle": int(f[4]), "steal": int(f[8])} if len(f) > 8 and f[0] == "cpu" else {"raw": p.stdout[:80]}
res = {}
code, body, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4 release smoke MN"}))
ws = json.loads(body); H = [f"Authorization: Bearer {ws['token']}"]; op = ws["operator_id"]
pl = json.load(open(S / "M_shared_order_interactive.json")); pl["operator_id"] = op; pl["max_solve_seconds"] = 12.0
code, body, s = curl("POST", "/api/zaad/network/plan", data=json.dumps(pl), headers=H)
res["M_shared_order_interactive_budget12"] = {"code": code, "expected": 413, "ok": code == 413, "detail": body[:200], "seconds": s}
print("M", res["M_shared_order_interactive_budget12"], flush=True)
before = steal(); t0 = time.time()
code, body, s = curl("POST", "/api/zaad/network/jobs", data=json.dumps(pl), headers=H)
sub = json.loads(body); job = sub.get("job_id"); res["N_submit"] = {"code": code, "timeout_s": sub.get("timeout_s"), "approval": sub.get("approval_required"), "epo": sub.get("executable_purchase_order")}
print("N submit", res["N_submit"], flush=True)
probes = []; final = None
while time.time() - t0 < 900:
    c, b, hs = curl("GET", "/health", timeout=20); probes.append((round(time.time() - t0), c, hs))
    c, b, _ = curl("GET", f"/api/zaad/network/jobs/{job}", headers=H); j = json.loads(b)
    if j.get("status") in ("DONE", "FAILED", "TIMEOUT", "CANCELLED"): final = j; break
    time.sleep(15)
after = steal(); wall = round(time.time() - t0)
d = {k: after[k] - before[k] for k in before if k in after and isinstance(after[k], int)}
rep = (final or {}).get("report") or {}
rc = rep.get("recourse") or {}
res["N_job"] = {"status": (final or {}).get("status"), "error": (final or {}).get("error"), "wall_s": wall, "started": (final or {}).get("started_at"), "finished": (final or {}).get("finished_at"),
                "cpu_jiffies_delta": d, "steal_ratio": (d.get("steal", 0) / max(1, d.get("user", 0) + d.get("system", 0))) if d else None,
                "health_probes": {"n": len(probes), "non_200": [p for p in probes if p[1] != 200], "max_latency_s": max((p[2] for p in probes), default=None)},
                "report": {"status": rep.get("status"), "selected": rep.get("selected_policy"), "approval": rep.get("approval_required"), "epo": rep.get("executable_purchase_order"),
                           "candidates": {k: (v.get("status"), round(v.get("solve_seconds", 0), 1)) for k, v in (rep.get("candidates") or {}).items()} if isinstance(rep.get("candidates"), dict) else None},
                "recourse": {x: rc.get(x) for x in ("verdict", "perfect_information_status", "value_of_adaptation", "material", "ordering_ok", "replan_required", "approval_required", "executable_purchase_order")} if rc else None}
print("N", json.dumps(res["N_job"], default=str), flush=True)
json.dump(res, open(out, "w"), indent=1, default=str); print("MN_DONE")
