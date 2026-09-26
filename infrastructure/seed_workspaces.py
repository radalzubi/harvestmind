"""Invited workspaces declared in the environment, created at startup.

HARVESTMIND_SEED_WORKSPACES="Customer Name|commercial|<access code, 12+ characters>|/logos/customer.svg;Other|produce|<code>|"

Each entry: name | sector | access code | logo path or URL. Idempotent: an
existing workspace of that name keeps its vault and gets the code and
logo refreshed. Codes are stored hashed.
"""
from __future__ import annotations

import logging
import os

from infrastructure.operator_registry import OperatorRegistry

log = logging.getLogger("harvestmind.seed")


def seed_workspaces_from_env(registry: OperatorRegistry | None = None) -> list:
    spec = os.getenv("HARVESTMIND_SEED_WORKSPACES", "").strip()
    if not spec:
        return []
    registry = registry or OperatorRegistry()
    out = []
    for entry in spec.split(";"):
        parts = [p.strip() for p in entry.split("|")]
        if len(parts) < 3 or not parts[0]:
            continue
        name, sector, code = parts[0], parts[1] or "commercial", parts[2]
        logo = parts[3] if len(parts) > 3 and parts[3] else None
        rec = registry.find_by_name(name)
        if rec is None:
            rec = registry.create_operator(name, sector=sector)
            log.info("seeded workspace %s (%s)", name, rec.operator_id)
        try:
            registry.set_access_code(rec.operator_id, code)
        except ValueError as exc:
            if rec.access_code_hash and len(code.strip()) >= 6:
                # a code set before the twelve-character rule keeps working until it is rotated; it is named here
                # every start so it cannot be forgotten (security review 2026-09, SEC-001)
                log.warning("workspace %s keeps a short access code: rotate it to %d+ characters", name,
                            registry.MIN_ACCESS_CODE_CHARS)
            else:
                log.warning("workspace %s: %s", name, exc)
                continue
        registry.set_profile(rec.operator_id, display_name=name, logo_url=logo)
        out.append(rec.operator_id)
    return out
