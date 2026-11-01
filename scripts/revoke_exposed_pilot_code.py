"""Inspect/revoke SEC-001 without logging credentials or deploying application code.

Run from a full repository checkout in GitHub Actions. The Fly token stays in
the runner environment. Only the known historical code's hash reaches Fly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import urllib.error
import urllib.request

APP = "zaad-api"
API = "https://api.machines.dev/v1/apps/" + APP

REMOTE = r'''
import json, sys
sys.path.insert(0, "/app")
from infrastructure.operator_registry import OperatorRegistry

def remediate(registry, expected_hash, old_length, apply):
    # New startups already refuse to set this old short code; clearing its
    # stored hash therefore survives restart without changing Fly secrets.
    if registry.MIN_ACCESS_CODE_CHARS <= old_length:
        raise RuntimeError("deployed seed validation cannot prevent reintroduction")
    if not registry.registry_file.is_file():
        raise RuntimeError("expected live registry is missing")
    with registry._locked():
        records = registry._load()
        targets = [r for r in records.values() if r.get("name") == "NTDCO"]
        if len(targets) != 1:
            raise RuntimeError("expected exactly one affected workspace")
        target = targets[0]
        for record in records.values():
            if record.get("token_hash") == expected_hash or expected_hash in (record.get("actors") or {}):
                raise RuntimeError("credential also occurs outside the pilot-code field")
            if record is not target and record.get("access_code_hash") == expected_hash:
                raise RuntimeError("credential is shared with another workspace")
        matched = target.get("access_code_hash") == expected_hash
        alternate = bool(target.get("token_hash")) or any(
            a.get("role") == "ADMIN" and not a.get("revoked_at")
            for a in (target.get("actors") or {}).values()
        )
        if apply and matched:
            target["access_code_hash"] = None
            registry._save(records)
        remaining = any(r.get("access_code_hash") == expected_hash for r in registry._load().values())
        if apply and remaining:
            raise RuntimeError("revocation verification failed")
    return {"marker": "ZAAD_SEC001_V1", "mode": "revoke" if apply else "inspect",
            "matched_before": matched, "revoked": bool(apply and matched),
            "historical_code_registered": remaining,
            "alternate_admin_credential_present": alternate,
            "seed_minimum_blocks_old_code": True}
'''


def historical_code() -> str:
    raw = subprocess.check_output(
        ["git", "show", "1daa6c7:docs/deploy/LIVE_MVP.md"], text=True
    )
    matches = re.findall(r'HARVESTMIND_SEED_WORKSPACES="NTDCO\|commercial\|([^|]+)\|', raw)
    if len(matches) != 1 or not 6 <= len(matches[0]) < 12:
        raise RuntimeError("historical credential could not be identified unambiguously")
    return matches[0]


def fly_request(path: str, payload=None):
    token = os.environ.get("FLY_API_TOKEN")
    if not token:
        raise RuntimeError("FLY_API_TOKEN is not configured")
    req = urllib.request.Request(
        API + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=50) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Error bodies/headers may contain private configuration; do not log them.
        raise RuntimeError(f"Fly request failed with HTTP {exc.code}") from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    code = historical_code()
    digest = hashlib.sha256(code.encode()).hexdigest()
    machines = fly_request("/machines")
    serving = [m for m in machines if m.get("config", {}).get("services")]
    if not serving or any(m.get("state") != "started" for m in serving):
        raise RuntimeError("all serving machines must be running for verification")
    for machine in serving:
        if not machine.get("config", {}).get("mounts"):
            raise RuntimeError("serving machine has no persistent registry volume")
        script = REMOTE + "\nprint(json.dumps(remediate(OperatorRegistry(), " + repr(digest) + ", " + str(len(code)) + ", " + repr(args.apply) + ")))\n"
        result = fly_request("/machines/" + machine["id"] + "/exec", {
            "cmd": shlex.join(["python", "-c", script]), "timeout": 30,
        })
        # An absent zero exit_code is permitted by Fly's omitempty response.
        # Require our explicit completion marker as well as no failure status.
        if result.get("exit_code", 0) != 0 or result.get("exit_signal", 0) != 0:
            raise RuntimeError("remote check failed; no credentials printed")
        try:
            evidence = json.loads(result.get("stdout", ""))
        except (ValueError, TypeError):
            raise RuntimeError("remote check returned no valid completion evidence") from None
        if evidence.get("marker") != "ZAAD_SEC001_V1":
            raise RuntimeError("remote completion marker missing")
        print(json.dumps({"machine_id": machine["id"], **evidence}, sort_keys=True))
    if args.apply:
        # Discard any response body. Never log a token or customer /me payload.
        for origin in ("https://api.zaadsupply.com", "https://zaad-api.fly.dev"):
            req = urllib.request.Request(origin + "/me", headers={"Authorization": "Bearer " + code})
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    status = response.status
            except urllib.error.HTTPError as exc:
                status = exc.code
            if status != 401:
                raise RuntimeError(f"historical credential rejection unverified: HTTP {status}")
            print(json.dumps({"origin": origin, "historical_credential_http_status": status}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Exception classes and our fixed RuntimeError messages only.
        message = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        raise SystemExit(message) from None
