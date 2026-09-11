"""Bounded P3 production smoke (sections 21-43 of the release brief).
usage: python3 p3_prod_smoke.py https://api.zaadsupply.com p3_smoke_payloads.json out.json"""
import json, subprocess, sys, time

BASE, PAYLOADS, OUT_PATH = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = {}


def curl(method, path, data=None, headers=(), timeout=300):
    cmd = ["curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}", "-X", method, BASE + path, "--max-time", str(timeout)]
    for h in headers:
        cmd += ["-H", h]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    t = time.time()
    p = subprocess.run(cmd, input=data, capture_output=True, text=True)
    return int(p.stdout.strip() or 0), p.stderr, round(time.time() - t, 1)


def J(body):
    try:
        return json.loads(body)
    except Exception:
        return {"_raw": body[:300]}


def rec(label, code, secs, view):
    OUT[label] = {"code": code, "seconds": secs, "view": view}
    print(f"{label}: HTTP {code} ({secs}s) {json.dumps(view, default=str)[:900]}", flush=True)


# 21-22: health, auth, CORS, legacy
code, body, s = curl("GET", "/health"); rec("21.health", code, s, J(body))
for p, m in (("/api/zaad/demo", "GET"), ("/api/zaad/plan", "POST")):
    code, body, s = curl(m, p, data="{}" if m == "POST" else None); rec(f"22.legacy {p}", code, s, {"detail": str(J(body).get("detail"))[:100]})
for p in ("/fmcg/status", "/api/zaad/network/jobs", "/api/zaad/network/request/from-workspace"):
    code, body, s = curl("GET", p); rec(f"22.anon {p}", code, s, {})
for origin in ("https://zaadsupply.com", "https://www.zaadsupply.com", "https://evil.example.com"):
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-D", "-", "-X", "OPTIONS", BASE + "/api/zaad/network/plan", "-H", f"Origin: {origin}",
                        "-H", "Access-Control-Request-Method: POST", "-H", "Access-Control-Request-Headers: authorization,content-type"], capture_output=True, text=True)
    allowed = [line.strip() for line in p.stdout.splitlines() if line.lower().startswith("access-control-allow-origin")]
    rec(f"22.cors {origin}", (p.stdout.splitlines() or ["?"])[0], 0, {"allow_origin": allowed})

# 23 + 40: self-serve workspace (new vault -> migrations incl. 018), legacy path and P3 flag on a vault with no declarations
code, body, s = curl("POST", "/access/start", data=json.dumps({"sector": "commercial", "company": "P3 release smoke"}))
ws = J(body); rec("23.start", code, s, {k: ws.get(k) for k in ("operator_id", "sector")})
H = [f"Authorization: Bearer {ws['token']}"]
code, body, s = curl("POST", "/intake/load-sample-fmcg", data="{}", headers=H); rec("23.sample_fmcg", code, s, {"total_rows": J(body).get("total_rows")})
code, body, s = curl("GET", "/api/zaad/network/request/from-workspace?max_solve_seconds=5", headers=H); req = J(body)
skus = [x["id"] for x in req["request"]["skus"]][:2]
rec("23.legacy_request", code, s, {"skus": len(req["request"]["skus"]), "sourcing_field": req["request"].get("sourcing"), "build_sourcing": req["build"].get("sourcing")})
q = "&skus=" + ",".join(skus)
code, body, s = curl("GET", f"/api/zaad/network/request/from-workspace?max_solve_seconds=5{q}&sourcing=true", headers=H); r2 = J(body)
rec("23.flag_on_vault_without_declarations", code, s, {"sourcing_field": r2["request"].get("sourcing"), "build_sourcing": r2["build"].get("sourcing"), "sources": len(r2["request"]["sources"])})
code, body, s = curl("POST", f"/api/zaad/network/plan/from-workspace?max_solve_seconds=5{q}", headers=H, timeout=400); j = J(body)
rec("40.legacy_plan_p1", code, s, {k: j.get(k) for k in ("engine", "mode_run", "planner_owner", "solver_status", "approval_required", "executable_purchase_order")})
OUT["_workspace"] = {"operator_id": ws["operator_id"], "skus": skus}

# 24-37, 41: payload smokes
payloads = json.load(open(PAYLOADS))
for key, payload in payloads.items():
    if key == "_malformed":
        continue
    payload = dict(payload); payload["operator_id"] = ws["operator_id"]
    code, body, s = curl("POST", "/api/zaad/network/plan", data=json.dumps(payload), headers=H, timeout=400); r = J(body)
    orch = r.get("orchestration", {}); blk = r.get("sourcing"); ph = r.get("physics") or {}
    view = {"status": r.get("status"), "owner": orch.get("planner_owner"), "state": orch.get("state"), "selected": r.get("selected_policy"),
            "approval_required": r.get("approval_required"), "executable_purchase_order": r.get("executable_purchase_order"),
            "p0_purchases": [(a["source"], round(a["quantity"], 1)) for a in r.get("actions", []) if a.get("action") == "purchase" and a.get("period") == 0],
            "transfers_p0": round(sum(a["quantity"] for a in r.get("actions", []) if a.get("action") == "transfer" and a.get("period") == 0), 1),
            "sourcing": None if blk is None else [(x["sku"], x["recommendation"], round(x["total_committed_plan"], 1),
                                                    [(o["source"], round(o["quantity_plan"], 1), o["share_plan"] and round(o["share_plan"], 3), o["eligible"], o["capacity_binding"],
                                                      (o["switching_cost"] or {}).get("charged"), [g["id"] for g in o["risk_groups"]]) for o in x["options"]]) for x in blk["pairs"]],
            "risk_groups": None if blk is None else [(g["id"], g["kind"], g["correlation"], g["provenance"]) for g in blk["risk_groups"]],
            "explanations": None if blk is None else blk["explanations"][:5],
            "reconciled": (r.get("economics") or {}).get("reconciled"), "unmapped": (r.get("economics") or {}).get("unmapped_ledger_keys"),
            "materiality": ((r.get("economics") or {}).get("materiality") or {}).get("verdict"),
            "physics_profiles": [(p["sku"], p["sector"], p["age_at_receipt_by_source"], p["shelf_life_periods"]) for p in ph.get("profiles", [])],
            "physics_explanations": ph.get("explanations", [])[:3],
            "conservation": [x.get("conservation_residual") for x in (r.get("confirmation", {}).get("candidate", {}).get("rows", []) or [])][:1]}
    rec(f"payload.{key}", code, s, view)

# 38: malformed
for name, payload in payloads["_malformed"].items():
    payload = dict(payload); payload["operator_id"] = ws["operator_id"]
    code, body, s = curl("POST", "/api/zaad/network/plan", data=json.dumps(payload), headers=H, timeout=60)
    rec(f"38.{name}", code, s, {"detail": str(J(body).get("detail"))[:160]})

# 43: frontend routes
for path in ("/", "/overview", "/upload", "/fmcg", "/state", "/access"):
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "30", "https://zaadsupply.com" + path], capture_output=True, text=True)
    rec(f"43.frontend {path}", int(p.stdout.strip() or 0), 0, {})
json.dump(OUT, open(OUT_PATH, "w"), indent=1, default=str)
