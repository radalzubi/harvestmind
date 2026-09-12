"""Bounded production benchmark for the P4 performance closure: simple P4 (C), P2+P4 (F), P3+P4 (G), produce (D), and the shared-order job (N, 6 worlds) with host steal measured across the job."""
import json, subprocess, sys, time, pathlib
BASE = "https://zaad-api.fly.dev"; SM = pathlib.Path(__file__).parent.parent / "p4rel" / "smoke"; out = sys.argv[1]
def curl(method, path, data=None, headers=(), timeout=600):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers: cmd += ["-H", h]
    if data is not None: cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time(); p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)
def steal():
    p = subprocess.run(["fly", "ssh", "console", "-a", "zaad-api", "-C", "cat /proc/stat"], capture_output=True, text=True)
    f = p.stdout.split("\n")[0].split()
    return {"user": int(f[1]), "system": int(f[3]), "idle": int(f[4]), "steal": int(f[8])} if len(f) > 8 and f[0] == "cpu" else {}
def view(rep, code, s):
    rc = rep.get("recourse") or {}
    cands = {k: (v.get("status"), round(v.get("solve_seconds", 0), 1)) for k, v in (rep.get("candidates") or {}).items()} if isinstance(rep.get("candidates"), dict) else None
    return {"code": code, "seconds": s, "selected": rep.get("selected_policy"), "approval": rep.get("approval_required"), "epo": rep.get("executable_purchase_order"), "candidates": cands,
            "recourse": {x: rc.get(x) for x in ("verdict", "perfect_information_status", "value_of_adaptation", "material", "ordering_ok")} if rc else None,
            "adaptive_solve": (rc.get("engineering") or {}).get("adaptive_solve"), "static_solve": (rc.get("engineering") or {}).get("static_solve"), "perfect_solve": (rc.get("engineering") or {}).get("perfect_solve")}
res = {}
code, body, _ = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P4 perf closure production benchmark"}))
ws = json.loads(body); H = [f"Authorization: Bearer {ws['token']}"]; op = ws["operator_id"]
res["workspace"] = {"code": code, "operator": op}
def payload(name, **over):
    d = {**json.load(open(SM / f"{name}.json")), "operator_id": op, **over}; return json.dumps(d)
for name in ("C_commercial_simple", "F_p2_network", "G_p3_source_mix", "D_produce"):
    b0 = steal(); code, body, s = curl("POST", "/api/zaad/network/plan", data=payload(name), headers=H); b1 = steal()
    try: rep = json.loads(body)
    except Exception: rep = {"_raw": body[:300]}
    d = {k: b1[k] - b0[k] for k in b0 if k in b1}
    res[name] = {**view(rep, code, s), "cpu_delta": d, "steal_ratio": round(d.get("steal", 0) / max(1, d.get("user", 0) + d.get("system", 0)), 2) if d else None}
    print(name, json.dumps(res[name], default=str)[:700], flush=True); json.dump(res, open(out, "w"), indent=1, default=str)
# N: the shared-order job (6 tree worlds, budget 12 s)
b0 = steal(); t0 = time.time()
code, body, s = curl("POST", "/api/zaad/network/jobs", data=payload("M_shared_order_interactive", max_solve_seconds=12.0), headers=H)
sub = json.loads(body); job = sub.get("job_id"); res["N_submit"] = {"code": code, "timeout_s": sub.get("timeout_s")}
final = None; probes = []
while time.time() - t0 < 900:
    c, b, hs = curl("GET", "/health", timeout=20); probes.append((round(time.time() - t0), c, hs))
    c, b, _ = curl("GET", f"/api/zaad/network/jobs/{job}", headers=H); j = json.loads(b)
    if j.get("status") in ("DONE", "FAILED", "TIMEOUT", "CANCELLED"): final = j; break
    time.sleep(15)
b1 = steal(); d = {k: b1[k] - b0[k] for k in b0 if k in b1}
rep = (final or {}).get("report") or {}
res["N_job"] = {"status": (final or {}).get("status"), "error": (final or {}).get("error"), "wall_s": round(time.time() - t0), "cpu_delta": d, "steal_ratio": round(d.get("steal", 0) / max(1, d.get("user", 0) + d.get("system", 0)), 2) if d else None,
                "health_probes": {"n": len(probes), "non_200": [p for p in probes if p[1] != 200], "max_latency_s": max((p[2] for p in probes), default=None)}, "report": view(rep, 200, 0) if rep else None}
print("N_job", json.dumps(res["N_job"], default=str)[:900], flush=True)
json.dump(res, open(out, "w"), indent=1, default=str); print("BENCH_DONE")
