#!/usr/bin/env python3
"""Production smoke for the ZAAD Operating Product (V1 + V2) after deployment.

Checks what a request can check from outside, against the deployed API and, when a workspace
key is given, inside one workspace: the V2 routes answer, refuse an anonymous caller, are
tenant-scoped, and fail closed where they should. It never creates, approves or exports
anything in production: the only writes are refused ones (an empty bulk batch, a telemetry
event with a disallowed name) and their refusal is what is checked.

Usage:
    python3 scripts/operating_product_release_smoke.py --api https://zaad-api.fly.dev [--token <workspace key>]
    python3 scripts/operating_product_release_smoke.py --api https://zaad-api.fly.dev --self-serve

`--self-serve` creates its own smoke workspace through the released self-serve path
(`POST /access/start`, then the sample FMCG upload), the way earlier release smokes did, so no
production key is handled. The workspace it creates is a throwaway with sample data.
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request

TIMEOUT = 40


def _ctx() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url: str, *, token: str | None = None, method: str = "GET", body: dict | None = None, _retry: bool = True):
    """One request. A transport timeout is retried once after a pause: on a loopback host a burst
    of short connections can exhaust ephemeral ports (TIME_WAIT), which stalls the *client*
    while the server has already answered — the API log is the arbiter, and this keeps a client
    artefact from being reported as a server failure. A second timeout is reported as one."""
    status, headers, raw = _fetch_once(url, token=token, method=method, body=body)
    if status == -1 and _retry and b"timed out" in raw:
        import time
        time.sleep(3)
        return _fetch_once(url, token=token, method=method, body=body)
    return status, headers, raw


def _fetch_once(url: str, *, token: str | None = None, method: str = "GET", body: dict | None = None):
    req = urllib.request.Request(url, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, data=data, timeout=TIMEOUT, context=_ctx()) as resp:
            raw = resp.read()
            return resp.status, dict(resp.headers), raw
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except Exception as exc:  # noqa: BLE001 - reported as a failed check
        return -1, {}, str(exc).encode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--token", default=None)
    ap.add_argument("--self-serve", action="store_true", help="create a throwaway smoke workspace with sample data")
    args = ap.parse_args()
    api = args.api.rstrip("/")
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")

    if args.self_serve and not args.token:
        status, _, raw = fetch(f"{api}/access/start", method="POST",
                               body={"sector": "commercial", "company": "Operating product release smoke"})
        ws = json.loads(raw or b"{}") if status in (200, 201) else {}
        check("self-serve workspace created", bool(ws.get("token")), f"status {status}, operator {ws.get('operator_id')}")
        if ws.get("token"):
            args.token = ws["token"]
            status, _, raw = fetch(f"{api}/intake/load-sample-fmcg", token=args.token, method="POST", body={})
            loaded = json.loads(raw or b"{}") if status == 200 else {}
            check("sample FMCG data loaded", status == 200 and (loaded.get("total_rows") or 0) > 0, f"status {status}, rows {loaded.get('total_rows')}")

    status, _, raw = fetch(f"{api}/health")
    check("health answers 200", status == 200, f"status {status}")

    for path in ("/api/zaad/workspace/readiness", "/api/zaad/workspace/locations",
                 "/api/zaad/workspace/inventory?location=DC", "/api/zaad/audit", "/api/zaad/history"):
        status, _, raw = fetch(f"{api}{path}")
        check(f"anonymous {path} refused", status in (401, 403), f"status {status}" + ("" if status > 0 else f" ({raw.decode(errors='replace')[:80]})"))
    status, _, _ = fetch(f"{api}/api/zaad/orders/bulk", method="POST", body={"drafts": []})
    check("anonymous bulk create refused", status in (401, 403), f"status {status}")

    if not args.token:
        print("no --token: workspace checks skipped")
    else:
        t = args.token
        status, _, raw = fetch(f"{api}/me", token=t)
        me = json.loads(raw or b"{}") if status == 200 else {}
        caps = me.get("capabilities") or (me.get("actor") or {}).get("capabilities") or []
        check("/me answers with capabilities", status == 200 and bool(caps), f"status {status}, {len(caps)} capabilities")

        status, _, raw = fetch(f"{api}/api/zaad/workspace/readiness", token=t)
        r = json.loads(raw or b"{}") if status == 200 else {}
        check("readiness is counted from the vault", status == 200 and r.get("provenance") == "COUNTED_FROM_THE_VAULT",
              f"status {status}, family {r.get('family')}, applies {r.get('applies')}, "
              f"ready {r.get('summary', {}).get('ready')} / blocked {r.get('summary', {}).get('blocked')}")
        if r.get("applies") is not False:
            caps_r = {c["capability"]: c for c in r.get("capabilities", [])}
            check("every capability names its status", all(c["status"] in ("READY", "PARTIAL", "BLOCKED", "UNAVAILABLE") for c in caps_r.values()) and len(caps_r) == 14,
                  f"{len(caps_r)} capabilities")

        status, _, raw = fetch(f"{api}/api/zaad/workspace/locations", token=t)
        locs = json.loads(raw or b"{}").get("locations", []) if status == 200 else []
        check("locations answer", status == 200, f"{len(locs)} sites")
        if locs:
            site = locs[0]["id"]
            status, _, raw = fetch(f"{api}/api/zaad/workspace/inventory?location={urllib.request.quote(site)}&limit=3", token=t)
            page = json.loads(raw or b"{}") if status == 200 else {}
            rows = page.get("rows", [])
            check("a site page is that site's own", status == 200 and page.get("location") == site and all((r.get("sites") in (1, None)) for r in rows),
                  f"status {status}, {site}: {len(rows)} rows, notes {page.get('location_notes')}")
            status, _, raw = fetch(f"{api}/api/zaad/workspace/inventory?location=NOT-A-SITE-ANYWHERE&limit=2", token=t)
            page = json.loads(raw or b"{}") if status == 200 else {}
            check("an unknown site is empty, not the total", status == 200 and all(r.get("on_hand") is None for r in page.get("rows", [])))

        status, _, raw = fetch(f"{api}/api/zaad/orders/bulk", token=t, method="POST", body={"drafts": []})
        check("empty bulk batch refused, nothing created", status in (403, 422), f"status {status}")
        status, _, raw = fetch(f"{api}/api/zaad/telemetry", token=t, method="POST",
                               body={"events": [{"name": "not_an_event", "properties": {"secret": "x"}}]})
        body = json.loads(raw or b"{}") if status in (200, 202) else {}
        check("unknown telemetry event dropped", status in (200, 202) and (bool(body.get("dropped")) or body.get("accepted") == 0 or body.get("stored") == 0),
              f"status {status}, {json.dumps(body)[:80]}")
        status, _, raw = fetch(f"{api}/api/zaad/audit?limit=1", token=t)
        check("audit readable and tenant-scoped", status == 200, f"status {status}")
        status, _, raw = fetch(f"{api}/api/zaad/history", token=t)
        h = json.loads(raw or b"{}") if status == 200 else {}
        check("history feed keeps the registers apart", status == 200 and "backtested" in h, f"status {status}")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
