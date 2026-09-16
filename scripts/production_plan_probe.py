"""Production plan probe: one product-shaped plan against a deployed API, with the reads an
operator makes timed while it runs.

Submits exactly what the product's plan button submits (the workspace request over the ranked
products, every phase asked for, `POST /api/zaad/network/jobs`), then, until the job reaches a
terminal state, times the routine reads — health, /me, the workspace summary, the inventory list,
the purchase-order list, data readiness and the job itself — at a fixed interval, one call at a
time. Optionally submits a second plan part-way through to observe queueing. Prints a latency
table per endpoint (median / p95 / max / errors) and the job's outcome with its solve quality.

Never sends supplier orders; never touches operator data; a throwaway workspace can be created
with --self-serve (the smoke script's path).

Usage: python -m scripts.production_plan_probe --api https://zaad-api.fly.dev --token KEY --products 5
         [--interval 3] [--second-plan-after 20] [--seconds 15] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

def _ssl_context() -> ssl.SSLContext:
    """A python.org build ships no CA bundle; use certifi's when it is installed."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_SSL = _ssl_context()
PHASES = "horizon=12&service_target=0.95&network=true&sourcing=true&recourse=true&atp=true&commitments=true"


def call(url: str, *, token: str | None = None, method: str = "GET", body: dict | None = None, timeout: float = 60.):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:  # nosec B310 - https URL from the operator
            raw = resp.read()
            return resp.status, raw, time.perf_counter() - t
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), time.perf_counter() - t
    except Exception as exc:  # noqa: BLE001 - transport failure is a measurement
        return 0, str(exc).encode(), time.perf_counter() - t


def rank_products(request: dict) -> list[str]:
    by_source = {s["id"]: s["sku"] for s in request["sources"]}
    on_order: dict[str, float] = {}
    for po in request.get("pipeline", []):
        sku = by_source.get(po["source"])
        if sku:
            on_order[sku] = on_order.get(sku, 0.) + float(po.get("expected_accepted_remaining") or 0.)
    unit = {s["id"]: float(s.get("unit_value") or s.get("unit_cost") or 0.) for s in request["skus"]}
    value: dict[str, float] = {}
    for st in request.get("stock", []):
        value[st["sku"]] = value.get(st["sku"], 0.) + float(st["quantity"]) * unit.get(st["sku"], 0.)
    return sorted((s["id"] for s in request["skus"]), key=lambda s: (-on_order.get(s, 0.), -value.get(s, 0.), s))


def build_request(api: str, token: str, products: int, seconds: float) -> tuple[dict, int]:
    status, raw, _ = call(f"{api}/api/zaad/network/request/from-workspace?{PHASES}&max_solve_seconds={seconds}", token=token)
    if status != 200:
        raise SystemExit(f"workspace request failed: {status} {raw[:300]!r}")
    full = json.loads(raw)["request"]
    ranked = rank_products(full)
    chosen = ranked[:products]
    if len(chosen) >= len(full["skus"]):
        return full, len(full["skus"])
    status, raw, _ = call(f"{api}/api/zaad/network/request/from-workspace?{PHASES}&max_solve_seconds={seconds}"
                          f"&skus={','.join(chosen)}", token=token)
    if status != 200:
        raise SystemExit(f"scoped workspace request failed: {status} {raw[:300]!r}")
    return json.loads(raw)["request"], len(full["skus"])


def submit(api: str, token: str, request: dict) -> dict:
    status, raw, latency = call(f"{api}/api/zaad/network/jobs", token=token, method="POST", body=request)
    if status != 202:
        raise SystemExit(f"job submission failed: {status} {raw[:300]!r}")
    out = json.loads(raw)
    out["submit_latency_s"] = latency
    return out


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(p * (len(ordered) - 1))))
    return ordered[k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--token", default=None)
    ap.add_argument("--self-serve", action="store_true", help="create a throwaway workspace and load the sample FMCG data")
    ap.add_argument("--products", type=int, default=5)
    ap.add_argument("--seconds", type=float, default=15.)
    ap.add_argument("--interval", type=float, default=3.)
    ap.add_argument("--second-plan-after", type=float, default=None, help="seconds after the first submit to submit a second plan")
    ap.add_argument("--second-plan-products", type=int, default=None)
    ap.add_argument("--max-wall", type=float, default=2400.)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    api = args.api.rstrip("/")
    token = args.token
    if args.self_serve and not token:
        status, raw, _ = call(f"{api}/access/start", method="POST", body={"sector": "commercial", "company": "Planner performance probe"})
        ws = json.loads(raw or b"{}") if status in (200, 201) else {}
        if not ws.get("token"):
            raise SystemExit(f"self-serve workspace not created: {status} {raw[:200]!r}")
        token = ws["token"]
        status, raw, _ = call(f"{api}/intake/load-sample-fmcg", token=token, method="POST", body={})
        if status != 200:
            raise SystemExit(f"sample load failed: {status} {raw[:200]!r}")
        print(f"throwaway workspace {ws.get('operator_id')} with the sample FMCG data", flush=True)
    if not token:
        raise SystemExit("--token or --self-serve is required")

    reads = [
        ("health", f"{api}/health", None),
        ("me", f"{api}/me", token),
        ("summary", f"{api}/api/zaad/workspace/summary", token),
        ("inventory", f"{api}/api/zaad/workspace/inventory?limit=25", token),
        ("purchase_orders", f"{api}/api/zaad/workspace/purchase-orders?limit=25", token),
        ("readiness", f"{api}/api/zaad/workspace/readiness", token),
        ("insights_summary", f"{api}/api/zaad/insights/summary", token),
    ]
    idle: dict[str, list[float]] = {name: [] for name, _, _ in reads}
    for _ in range(3):
        for name, url, tok in reads:
            status, _, latency = call(url, token=tok)
            if status == 200:
                idle[name].append(latency)

    request, catalogue = build_request(api, token, args.products, args.seconds)
    t_submit = time.perf_counter()
    first = submit(api, token, request)
    job_id = first["job_id"]
    print(f"submitted {job_id}: {len(request['skus'])} of {catalogue} products, timeout {first.get('timeout_s')}s "
          f"(submit {first['submit_latency_s']:.2f}s)", flush=True)
    jobs: dict[str, dict] = {job_id: {"submitted_at": 0., "products": len(request["skus"]), "timeout_s": first.get("timeout_s")}}
    second_pending = args.second_plan_after is not None

    samples: dict[str, list[dict]] = {name: [] for name, _, _ in reads}
    samples["job"] = []
    timeline: list[dict] = []
    terminal = {"DONE", "FAILED", "TIMEOUT", "CANCELLED", "ABANDONED"}
    final: dict[str, dict] = {}
    while time.perf_counter() - t_submit < args.max_wall:
        elapsed = time.perf_counter() - t_submit
        if second_pending and elapsed >= args.second_plan_after:
            second_pending = False
            req2, _ = build_request(api, token, args.second_plan_products or args.products, args.seconds)
            second = submit(api, token, req2)
            jobs[second["job_id"]] = {"submitted_at": elapsed, "products": len(req2["skus"]), "timeout_s": second.get("timeout_s")}
            print(f"  +{elapsed:.0f}s submitted second plan {second['job_id']} ({second['submit_latency_s']:.2f}s)", flush=True)
        for name, url, tok in reads:
            status, _, latency = call(url, token=tok)
            samples[name].append({"t": round(time.perf_counter() - t_submit, 1), "status": status, "latency_s": round(latency, 3)})
        states = []
        for identity in list(jobs):
            if identity in final:
                continue
            status, raw, latency = call(f"{api}/api/zaad/network/jobs/{identity}", token=token)
            samples["job"].append({"t": round(time.perf_counter() - t_submit, 1), "status": status, "latency_s": round(latency, 3)})
            if status == 200:
                job = json.loads(raw)
                states.append(f"{identity[-6:]}={job['status']}")
                if job["status"] in terminal:
                    final[identity] = job
            else:
                states.append(f"{identity[-6:]}=http{status}")
        line = {"t": round(time.perf_counter() - t_submit, 1), "jobs": states,
                "reads_s": {name: samples[name][-1]["latency_s"] for name in samples if samples[name]}}
        timeline.append(line)
        print(f"  {line['t']:6.0f}s {' '.join(states):40s} " + " ".join(f"{k}={v:.2f}" for k, v in line["reads_s"].items()), flush=True)
        if len(final) == len(jobs):
            break
        time.sleep(args.interval)

    table = {}
    for name, rows in samples.items():
        ok = [r["latency_s"] for r in rows if r["status"] == 200]
        table[name] = {"n": len(rows), "ok": len(ok), "errors": sum(1 for r in rows if r["status"] != 200),
                       "status_counts": {str(s): sum(1 for r in rows if r["status"] == s) for s in sorted({r["status"] for r in rows})},
                       "idle_median_s": round(statistics.median(idle[name]), 3) if idle.get(name) else None,
                       "median_s": round(statistics.median(ok), 3) if ok else None, "p95_s": round(percentile(ok, .95), 3) if ok else None,
                       "max_s": round(max(ok), 3) if ok else None}
    outcomes = {}
    for identity, job in final.items():
        report = job.get("report") or {}
        quality = report.get("solve_quality") or {}
        started = job.get("started_at")
        finished = job.get("finished_at")
        outcomes[identity] = {
            **jobs[identity], "status": job["status"], "error": job.get("error"), "created_at": job.get("created_at"),
            "started_at": started, "finished_at": finished,
            "run_seconds": ((datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds()
                            if started and finished else None),
            "queued_seconds": ((datetime.fromisoformat(started) - datetime.fromisoformat(job["created_at"])).total_seconds()
                               if started and job.get("created_at") else None),
            "report_status": report.get("status"),
            "solver_seconds_total": quality.get("solver_seconds_total"), "milps_attempted": quality.get("milps_attempted"),
            "milps_optimal": quality.get("milps_optimal"), "milps_time_limited": quality.get("milps_feasible_time_limited"),
            "candidates": {k: {"status": v.get("status"), "solve_seconds": v.get("solve_seconds")} for k, v in (quality.get("candidates") or {}).items()},
        }
    unfinished = [i for i in jobs if i not in final]
    out = {"api": api, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "products": args.products,
           "catalogue": catalogue, "interval_s": args.interval, "jobs": outcomes, "unfinished": unfinished,
           "latency": table, "timeline": timeline}
    print(json.dumps({"jobs": outcomes, "latency": table, "unfinished": unfinished}, indent=2, default=str))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(out, fh, indent=2, default=str)
    sys.exit(0 if final and all(j["status"] == "DONE" for j in final.values()) and not unfinished else 1)


if __name__ == "__main__":
    main()
