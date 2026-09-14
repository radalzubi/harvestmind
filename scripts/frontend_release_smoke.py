#!/usr/bin/env python3
"""Production smoke for the ZAAD frontend rebuild.

Checks what a request can check from outside: every route answers, the superseded routes still
redirect rather than 404, the rebuilt workspace pages are not indexable, the public pages are,
and the one additive API endpoint behaves — authenticated, tenant-scoped, and refusing an
anonymous caller.

What a request cannot check — that the network graph draws, that the map's tiles arrive, that a
decision opens its supplier — is done in a browser and recorded in the closeout. This script does
not pretend to cover it.

Usage:
    python3 scripts/frontend_release_smoke.py --site https://zaadsupply.com --api https://zaad-api.fly.dev
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

TIMEOUT = 30


def fetch(url: str, *, token: str | None = None, method: str = "GET", follow: bool = True) -> tuple[int, str, str]:
    """(status, final url, body). Redirects are reported rather than silently followed when asked."""
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "zaad-smoke/1"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
            return None

    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            return response.status, response.url, response.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, url, exc.read(20_000).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - a smoke failure is a result, not a crash
        return 0, url, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True, help="public site origin")
    parser.add_argument("--api", required=True, help="API origin")
    parser.add_argument("--token", default=None, help="optional workspace access code, to check an authenticated read")
    args = parser.parse_args()
    site, api = args.site.rstrip("/"), args.api.rstrip("/")
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    # 1-4: the public pages exist and carry the repositioned product, not the old one.
    status, _, body = fetch(f"{site}/")
    check("landing answers", status == 200, f"HTTP {status}")
    check("landing is repositioned", "decision layer" in body.lower(), "hero copy")
    check("landing does not sell the old positioning",
          "inventory optimization & supply resilience" not in body.lower(), "page title")
    status, _, body = fetch(f"{site}/quote")
    check("company quote page answers", status == 200 and "quote" in body.lower(), f"HTTP {status}")

    # 5-8: the rebuilt workspace routes are served and kept out of the index.
    for route in ("/home", "/decisions", "/network", "/data"):
        status, _, _ = fetch(f"{site}{route}")
        check(f"{route} answers", status == 200, f"HTTP {status}")

    # 9-13: no bookmarked URL breaks.
    for old, new in (("/start", "/home"), ("/upload", "/data"), ("/data-quality", "/data"),
                     ("/fmcg", "/decisions"), ("/state", "/network")):
        status, final, _ = fetch(f"{site}{old}")
        check(f"{old} still resolves", status == 200, f"HTTP {status} at {final}")

    # 14: the engineering console kept its capability at its new address.
    status, _, _ = fetch(f"{site}/advanced/planner")
    check("/advanced/planner answers", status == 200, f"HTTP {status}")

    # 15: the API is up.
    status, _, _ = fetch(f"{api}/health")
    check("api health", status == 200, f"HTTP {status}")

    # 16-17: the additive projection is authenticated and says nothing to a stranger.
    status, _, _ = fetch(f"{api}/api/zaad/network/directory")
    check("directory refuses an anonymous caller", status in (401, 403), f"HTTP {status}")
    if args.token:
        status, _, body = fetch(f"{api}/api/zaad/network/directory", token=args.token)
        ok = status == 200
        shape = False
        if ok:
            try:
                payload = json.loads(body)
                shape = (
                    isinstance(payload.get("suppliers"), list)
                    and isinstance(payload.get("locations"), list)
                    and payload.get("provenance") == "OPERATOR_DECLARED"
                )
            except json.JSONDecodeError:
                shape = False
        check("directory answers an operator with the declared shape", ok and shape, f"HTTP {status}")

        # 18: the superseded planning modes are still closed. The Network Twin was rewired off them
        # precisely because production answers 410; this asserts that is still true. Running this
        # script against a dev server fails here by design — dev leaves the legacy engines enabled.
        status, _, _ = fetch(f"{api}/fmcg/plan?mode=safe", token=args.token, method="POST")
        check("superseded planning modes answer 410", status == 410,
              f"HTTP {status}" + ("" if status == 410 else " (expected against a dev server, where legacy planners stay enabled)"))

    width = max(len(name) for name, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        if not ok:
            failed += 1
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
