"""Create or reset the DEMO workspace through the public API, end to end.

**DEMO / SYNTHETIC DATA — never a customer, never run against a customer's workspace.** The script
refuses a token unless you pass ``--i-know-this-replaces-the-data`` with it, and by default creates
its own throwaway workspace through the self-serve path.

What it does, in order, every step through a released endpoint so the recommendations that end up in
the demo come from the released engine and nothing is hard-coded:

  1. ``POST /access/start``                         a workspace (or ``--token`` for an existing one)
  2. ``POST /intake/load-demo-company``             the complete demo company (synthetic/fmcg/demo_company.py)
  3. ``GET  /api/zaad/network/request/from-workspace``  the request over the scenario products
  4. ``POST /api/zaad/network/jobs``                 the workspace plan, waited to completion
  5. responses on the plan's open-order verdicts    one ACCEPTED, one REJECTED, one OVERRIDDEN (with a reason)
  6. a proposal from a purchase the plan recommends  ``POST /api/zaad/orders`` (origin ZAAD_RECOMMENDATION)
  7. its evaluation                                  ``POST /api/zaad/orders/{id}/evaluate`` (two more runs), waited
  8. submit → approve → export → external status    the closed loop, human-recorded
  9. an outcome with a stated comparator             ``POST /api/zaad/orders/{id}/outcomes``

Every step prints what it did and the identifiers involved; the last line prints the workspace id
and the token so a person can open it. ``--skip-plan`` loads the data only (seconds); the full loop
takes as long as the engine takes (a 5-product plan is about 2–3 minutes on a rested machine).

Usage:
    python3 scripts/zaad_demo_workspace.py --api http://127.0.0.1:8000
    python3 scripts/zaad_demo_workspace.py --api https://zaad-api.fly.dev --products 5
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import date

PHASES = "horizon=12&service_target=0.95&network=true&sourcing=true&recourse=true&atp=true&commitments=true"
TERMINAL = {"DONE", "FAILED", "TIMEOUT", "CANCELLED", "ABANDONED"}


def _ssl() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _ssl()


def call(url: str, *, token: str | None = None, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: float = 120.):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:  # nosec B310 - operator-supplied https/http URL
            raw = resp.read()
            if not raw:
                return resp.status, None
            if "json" not in (resp.headers.get("Content-Type") or ""):
                return resp.status, {"bytes": len(raw), "content_type": resp.headers.get("Content-Type")}   # a file, e.g. the export
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except Exception:  # noqa: BLE001
            return exc.code, {"detail": raw.decode(errors="replace")[:300]}


def say(step: str, detail: str = "") -> None:
    print(f"{step:34s} {detail}", flush=True)


def wait_job(api: str, token: str, job_id: str, *, max_wall: float, label: str) -> dict:
    started = time.monotonic()
    last = None
    while time.monotonic() - started < max_wall:
        status, job = call(f"{api}/api/zaad/network/jobs/{job_id}", token=token)
        if status == 200 and job:
            state = job.get("status")
            if state != last:
                say(f"  {label}", f"{state}" + (f" (queue position {job.get('queue_position')})" if job.get("queue_position") else ""))
                last = state
            if state in TERMINAL:
                return job
        time.sleep(5)
    raise SystemExit(f"{label}: not finished after {max_wall:.0f}s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", required=True)
    ap.add_argument("--token", default=None, help="an existing workspace's key (its FMCG data is REPLACED)")
    ap.add_argument("--i-know-this-replaces-the-data", action="store_true")
    ap.add_argument("--company", default="Al-Bahr Trading (DEMO)")
    ap.add_argument("--as-of", default=None, help="the date the demo history ends (default: today)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--products", type=int, default=5, help="how many products the demo plan covers (the scenario products first)")
    ap.add_argument("--seconds", type=float, default=15.)
    ap.add_argument("--skip-plan", action="store_true", help="load the data only; no engine run, no decision loop")
    ap.add_argument("--max-wall", type=float, default=1500.)
    args = ap.parse_args()
    api = args.api.rstrip("/")
    token = args.token
    if token and not args.i_know_this_replaces_the_data:
        raise SystemExit("Refusing to replace an existing workspace's data without --i-know-this-replaces-the-data.")

    if not token:
        status, ws = call(f"{api}/access/start", method="POST", body={"sector": "commercial", "company": args.company})
        if status not in (200, 201) or not ws or not ws.get("token"):
            raise SystemExit(f"workspace not created: {status} {ws}")
        token = ws["token"]
        say("workspace created", f"{ws.get('operator_id')} — DEMO / SYNTHETIC DATA")
        say("  token", token)   # printed now, so a run that stops later still leaves a way in
    status, me = call(f"{api}/me", token=token)
    operator = (me or {}).get("operator_id") if status == 200 else None
    say("workspace", f"{operator or 'unknown'} ({status})")

    query = f"?seed={args.seed}" + (f"&as_of={args.as_of}" if args.as_of else "")
    status, loaded = call(f"{api}/intake/load-demo-company{query}", token=token, method="POST", body={}, timeout=900)
    if status != 200 or not loaded:
        raise SystemExit(f"demo company not loaded: {status} {loaded}")
    say("demo company loaded", f"{loaded['total_rows']:,} rows · {loaded['classification']} · as of {loaded['scenarios']['as_of']}")
    scenarios = loaded["scenarios"]
    say("  scenarios", f"spike {scenarios['spike']['week']} on {', '.join(scenarios['spike']['skus'])}; excess {scenarios['excess_sku']}; shortage {scenarios['shortage_sku']}; "
                       f"rights {scenarios['amendment_rights']}")
    if args.skip_plan:
        say("done (data only)", f"operator {operator} token {token}")
        return 0

    # the plan: the scenario products first, then the most on order, exactly as the plan button ranks
    status, full = call(f"{api}/api/zaad/network/request/from-workspace?{PHASES}&max_solve_seconds={args.seconds}", token=token, timeout=300)
    if status != 200 or not full:
        raise SystemExit(f"workspace request failed: {status} {full}")
    request = full["request"]
    wanted = [scenarios["excess_sku"], scenarios["shortage_sku"], *[s for s in (scenarios.get("imbalance_sku"),) if s]]
    rights_skus = []
    for po in request.get("pipeline", []):
        if po.get("id") in set(scenarios["amendment_rights"].values()):
            src = next((s for s in request["sources"] if s["id"] == po["source"]), None)
            if src:
                rights_skus.append(src["sku"])
    ranked = [s["id"] for s in request["skus"]]
    chosen: list[str] = []
    for sku in [*rights_skus, *wanted, *ranked]:
        if sku in ranked and sku not in chosen:
            chosen.append(sku)
        if len(chosen) >= args.products:
            break
    status, scoped = call(f"{api}/api/zaad/network/request/from-workspace?{PHASES}&max_solve_seconds={args.seconds}&skus={','.join(chosen)}", token=token, timeout=300)
    if status != 200 or not scoped:
        raise SystemExit(f"scoped request failed: {status} {scoped}")
    status, job = call(f"{api}/api/zaad/network/jobs", token=token, method="POST", body=scoped["request"], timeout=300)
    if status != 202 or not job:
        raise SystemExit(f"plan not submitted: {status} {job}")
    say("plan submitted", f"{job['job_id']} over {len(chosen)} products ({', '.join(chosen)}), cap {job.get('timeout_s')}s")
    plan = wait_job(api, token, job["job_id"], max_wall=args.max_wall, label="plan")
    if plan["status"] != "DONE":
        raise SystemExit(f"plan {plan['status']}: {plan.get('error')}")
    report = plan["report"]
    say("plan finished", f"status {report.get('status')} · {len(report.get('actions') or [])} actions · {len((report.get('commitments') or {}).get('orders') or [])} open-order verdicts")

    # responses on the open-order verdicts, in the order the engine gave them
    orders = (report.get("commitments") or {}).get("orders") or []
    outcomes = [("ACCEPTED", None, None), ("REJECTED", "supplier_relationship", "We keep this order as agreed with the supplier."),
                ("OVERRIDDEN", "customer_commitment", "The customer asked us to hold the date.")]
    for order, (status_word, code, text) in zip(orders, outcomes):
        body = {"job_id": plan["id"], "decision_id": f"po:{order['po']}", "status": status_word, "recommended": order.get("recommended_action"),
                "target_type": "po", "target_id": order["po"]}
        if code:
            body["reason_code"] = code
        if text:
            body["reason_text"] = text
        st, resp = call(f"{api}/api/zaad/decisions/responses", token=token, method="POST", body=body)
        say("  response recorded", f"{status_word} on {order.get('recommended_action')} {order['po']} ({st})")

    # a proposal from a purchase the plan recommends; failing that, from the current policy
    purchases = [a for a in (report.get("actions") or []) if a.get("action") == "purchase" and (a.get("quantity") or 0) > 0]
    if not purchases:
        purchases = [a for a in (report.get("incumbent_actions") or []) if a.get("action") == "purchase" and (a.get("quantity") or 0) > 0]
        origin = "CURRENT_POLICY"
    else:
        origin = "ZAAD_RECOMMENDATION"
    if not purchases:
        say("no purchase in the plan", "the decision loop stops here; the plan carries no buy (an honest DO NOTHING)")
        say("done", f"operator {operator} token {token}")
        return 0
    action = min(purchases, key=lambda a: a.get("period", 0))
    source = next((s for s in request["sources"] if s["id"] == action.get("source")), None)
    if source is None:
        raise SystemExit("the recommended purchase names a source the request does not carry")
    sku = source["sku"]
    unit = next((float(s.get("unit_value") or s.get("unit_cost") or 0) for s in request["skus"] if s["id"] == sku), 0.)
    body = {"origin": origin, "supplier_id": source.get("supplier"), "reference": f"DEMO proposal from plan {plan['id'][-6:]}",
            "source_decision_id": f"purchase:{action.get('source')}:{action.get('period')}", "currency": request.get("currency"),
            "lines": [{"sku": sku, "quantity": float(action["quantity"]), "unit_cost": unit or None}]}
    st, draft = call(f"{api}/api/zaad/orders", token=token, method="POST", body=body)
    if st != 201 or not draft:
        raise SystemExit(f"proposal not created: {st} {draft}")
    draft_id = draft["draft_id"]
    say("proposal created", f"{draft_id} · {origin} · {sku} × {action['quantity']:.0f} from {source.get('supplier')}")

    st, ev = call(f"{api}/api/zaad/orders/{draft_id}/evaluate?max_solve_seconds={args.seconds}", token=token, method="POST", body={}, timeout=300)
    if st != 202 or not ev:
        raise SystemExit(f"evaluation not started: {st} {ev}")
    say("evaluation submitted", f"{ev['evaluation_id']} (baseline {ev['baseline_job_id'][-6:]}, overlay {ev['proposal_job_id'][-6:]})")
    wait_job(api, token, ev["baseline_job_id"], max_wall=args.max_wall, label="baseline")
    wait_job(api, token, ev["proposal_job_id"], max_wall=args.max_wall, label="overlay")
    st, result = call(f"{api}/api/zaad/orders/{draft_id}/evaluation", token=token)
    comparison = (result or {}).get("comparison") or {}
    total = next((r for r in comparison.get("ledger", []) if r.get("component") == "TOTAL"), None)
    say("evaluation", f"{(result or {}).get('status')} · proposal vs current {total.get('proposal_vs_current') if total else 'n/a'} {comparison.get('currency', '')}")

    version = draft.get("version", 1)
    for step in ("submit", "approve"):
        st, draft = call(f"{api}/api/zaad/orders/{draft_id}/actions/{step}", token=token, method="POST",
                         body={"version": version, "reason": "DEMO: approved after evaluation." if step == "approve" else None, "acknowledge_stale": True})
        if st != 200 or not draft:
            raise SystemExit(f"{step} failed: {st} {draft}")
        version = draft.get("version", version)
        say(f"  {step}", f"state {draft.get('state')} (v{version})")
    st, exported = call(f"{api}/api/zaad/orders/{draft_id}/export?format=csv", token=token, method="POST", body={})
    say("  export", f"csv ({st}, {(exported or {}).get('bytes', '?')} bytes) — a file; ZAAD sends nothing to a supplier")
    st, draft = call(f"{api}/api/zaad/orders/{draft_id}/external-status", token=token, method="POST",
                     body={"status": "PLACED_EXTERNALLY", "external_reference": f"ERP-DEMO-{draft_id[-6:].upper()}", "note": "DEMO: placed in the ERP by the buyer."})
    say("  external status", f"{(draft or {}).get('external_status')} ({st})")
    expected_cost = float(action["quantity"]) * (unit or 0.)
    st, outcome = call(f"{api}/api/zaad/orders/{draft_id}/outcomes", token=token, method="POST",
                       body={"metric": "purchase_cost", "value": round(expected_cost * 0.985, 2), "observed_at": date.today().isoformat(),
                             "comparator_value": round(expected_cost, 2),
                             "comparator_basis": "The approved proposal's line total (quantity × unit cost) at approval time.",
                             "note": "DEMO: the invoice came in slightly under the approved line total."})
    say("  outcome recorded", f"purchase_cost with a stated comparator ({st})")
    st, outcome = call(f"{api}/api/zaad/orders/{draft_id}/outcomes", token=token, method="POST",
                       body={"metric": "received_units", "value": float(action["quantity"]), "observed_at": date.today().isoformat(),
                             "note": "DEMO: received in full. Observed after action; not attributed to ZAAD."})
    say("  outcome recorded", f"received_units, observed after action ({st})")
    say("done", f"operator {operator} token {token}")
    print(json.dumps({"operator_id": operator, "token": token, "plan_job_id": plan["id"], "draft_id": draft_id, "products": chosen}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
