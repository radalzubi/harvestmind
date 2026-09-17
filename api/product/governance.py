"""Who is acting, what they may do, and the record of what they did.

Operating Product V2's governance layer, kept deliberately small:

  * **An actor** is a person with a token in a workspace. The workspace's own pilot token is the
    administrator; named people get their own tokens with a role. The registry resolves a token to
    `{operator_id, actor_id, name, role}`; nothing else in the API reads tokens.
  * **A role** grants a fixed set of capabilities. Every write endpoint checks one, and no
    capability exists that nothing checks — the table below is the whole vocabulary.
  * **The audit log** is one append-only table written by every user-created operational action
    through `record_audit`. It carries identifiers and short labels, never a line's contents, a
    price, a dataset or a secret. No code path deletes from it.
  * **Workspace settings** are an allowlist of keys an administrator may set.
  * **Idempotency** replays a recorded response for a retried request rather than acting twice.

Nothing here decides economics, and nothing here transmits anything.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

ROLES = ("VIEWER", "BUYER", "APPROVER", "ADMIN")

#: The capability vocabulary. Every name here is checked somewhere; nothing checked is absent.
CAPABILITIES = ("view", "manageData", "createProposal", "editDraft", "evaluate", "review",
                "approve", "export", "recordExternal", "recordOutcome", "respondDecision",
                "manageProfiles", "manageSettings", "manageActors",
                # Enterprise Analytics V1: the analytics surfaces over the same four roles. A viewer
                # reads curated and workspace-shared analytics; a buyer builds, exports and asks;
                # an approver may share with the workspace; an administrator manages everything.
                "viewAnalytics", "createAnalysis", "editOwnAnalysis", "shareAnalysis", "exportAnalytics",
                "askZaad", "manageAnalytics")

ANALYTICS_CAPABILITIES = ("viewAnalytics", "createAnalysis", "editOwnAnalysis", "shareAnalysis", "exportAnalytics",
                          "askZaad", "manageAnalytics")

ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    "VIEWER": frozenset({"view", "viewAnalytics"}),
    "BUYER": frozenset({"view", "manageData", "createProposal", "editDraft", "evaluate", "review", "export",
                        "recordExternal", "recordOutcome", "respondDecision",
                        "viewAnalytics", "createAnalysis", "editOwnAnalysis", "exportAnalytics", "askZaad"}),
    "APPROVER": frozenset({"view", "createProposal", "editDraft", "evaluate", "review", "approve", "export",
                           "recordExternal", "recordOutcome", "respondDecision",
                           "viewAnalytics", "createAnalysis", "editOwnAnalysis", "shareAnalysis", "exportAnalytics", "askZaad"}),
    "ADMIN": frozenset(CAPABILITIES),
}


@dataclass(frozen=True)
class Actor:
    operator_id: str
    actor_id: str
    name: str
    role: str
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def can(self, capability: str) -> bool:
        return capability in self.capabilities


def actor_from(record: dict[str, Any]) -> Actor:
    role = str(record.get("role") or "VIEWER")
    if role not in ROLE_CAPABILITIES:
        role = "VIEWER"
    return Actor(operator_id=str(record["operator_id"]), actor_id=str(record.get("actor_id") or record["operator_id"]),
                 name=str(record.get("name") or record["operator_id"]), role=role,
                 capabilities=ROLE_CAPABILITIES[role])


class Forbidden(PermissionError):
    """The actor's role does not grant this. The message names the capability in words."""


CAPABILITY_WORDS = {
    "view": "view this workspace", "manageData": "add or replace data", "createProposal": "create a proposal",
    "editDraft": "edit a proposal", "evaluate": "ask ZAAD to evaluate a proposal", "review": "send a proposal for review",
    "approve": "approve or reject a proposal", "export": "export a proposal", "recordExternal": "record what happened outside ZAAD",
    "recordOutcome": "record an outcome", "respondDecision": "respond to a decision",
    "manageProfiles": "manage export formats", "manageSettings": "change workspace settings", "manageActors": "manage people",
    "viewAnalytics": "view analytics", "createAnalysis": "create an analysis", "editOwnAnalysis": "edit an analysis",
    "shareAnalysis": "share an analysis with the workspace", "exportAnalytics": "export an analysis", "askZaad": "use Ask ZAAD",
    "manageAnalytics": "manage every analysis and dashboard in the workspace",
}


def need(actor: Actor, capability: str) -> None:
    if capability not in CAPABILITIES:
        raise ValueError(f"unknown capability {capability!r}")
    if not actor.can(capability):
        raise Forbidden(f"Your role ({actor.role.title()}) cannot {CAPABILITY_WORDS[capability]}. "
                        "Ask the workspace administrator for the right role.")


# ── the audit log ─────────────────────────────────────────────────────────────

MAX_CONTEXT_CHARS = 2000


def record_audit(conn: Any, actor: Actor | None, *, operator: str | None = None, object_type: str, object_id: str,
                 action: str, before_revision: int | None = None, after_revision: int | None = None,
                 before_state: str | None = None, after_state: str | None = None, request_id: str | None = None,
                 context: dict[str, Any] | None = None) -> str:
    """One append-only row. `context` is bounded and holds identifiers and short labels only."""
    identity = f"audit_{uuid.uuid4().hex[:16]}"
    operator_id = operator or (actor.operator_id if actor else None)
    if not operator_id:
        raise ValueError("an audit row needs a workspace")
    text = json.dumps(context, default=str, sort_keys=True) if context else None
    if text and len(text) > MAX_CONTEXT_CHARS:
        text = text[:MAX_CONTEXT_CHARS]
    conn.execute(
        "INSERT INTO zaad_audit_log (audit_id, operator_id, actor, actor_role, object_type, object_id, action, "
        "before_revision, after_revision, before_state, after_state, request_id, context, happened_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [identity, operator_id, actor.actor_id if actor else None, actor.role if actor else None, object_type,
         str(object_id), action, before_revision, after_revision, before_state, after_state, request_id, text,
         datetime.now(timezone.utc).replace(tzinfo=None)])
    return identity


def read_audit(conn: Any, operator: str, *, object_type: str | None = None, object_id: str | None = None,
               limit: int = 50, offset: int = 0) -> dict[str, Any]:
    from api.product.catalog import _one, _rows

    where = ["operator_id = ?"]
    params: list[Any] = [operator]
    if object_type:
        where.append("object_type = ?")
        params.append(object_type)
    if object_id:
        where.append("object_id = ?")
        params.append(object_id)
    clause = " WHERE " + " AND ".join(where)
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    rows = _rows(conn, f"SELECT * FROM zaad_audit_log{clause} ORDER BY happened_at DESC LIMIT ? OFFSET ?",  # noqa: S608  # nosec B608 - code literals; values bind
                 [*params, limit, offset])
    for row in rows:
        row["context"] = json.loads(row["context"]) if row.get("context") else None
    total = int(_one(conn, f"SELECT count(*) FROM zaad_audit_log{clause}", params) or 0)  # noqa: S608  # nosec B608 - code literals; values bind
    return {"rows": rows, "total": total, "limit": limit, "offset": offset, "append_only": True}


# ── workspace settings ───────────────────────────────────────────────────────

#: The keys an administrator may set, with their allowed values (None = any bounded string).
SETTINGS: dict[str, tuple[str, ...] | None] = {
    "self_approval": ("allowed", "different_approver"),
    "default_export_profile": None,
}
SETTING_DEFAULTS = {"self_approval": "allowed", "default_export_profile": None}


class SettingRefused(ValueError):
    pass


def settings(conn: Any, operator: str) -> dict[str, Any]:
    from api.product.catalog import _rows

    out: dict[str, Any] = dict(SETTING_DEFAULTS)
    for row in _rows(conn, "SELECT key, value FROM zaad_workspace_settings WHERE operator_id = ?", [operator]):
        if row["key"] in SETTINGS:
            out[row["key"]] = row["value"]
    return out


def set_setting(conn: Any, actor: Actor, key: str, value: Any, *, request_id: str | None = None) -> dict[str, Any]:
    if key not in SETTINGS:
        raise SettingRefused(f"{key!r} is not a workspace setting. One of: {', '.join(SETTINGS)}.")
    allowed = SETTINGS[key]
    text = None if value in (None, "") else str(value)[:200]
    if allowed is not None and text not in allowed:
        raise SettingRefused(f"{key} is one of {', '.join(allowed)}.")
    before = settings(conn, actor.operator_id).get(key)
    conn.execute("DELETE FROM zaad_workspace_settings WHERE operator_id = ? AND key = ?", [actor.operator_id, key])
    conn.execute("INSERT INTO zaad_workspace_settings (operator_id, key, value, updated_by, updated_at) VALUES (?, ?, ?, ?, ?)",
                 [actor.operator_id, key, text, actor.actor_id, datetime.now(timezone.utc).replace(tzinfo=None)])
    record_audit(conn, actor, object_type="setting", object_id=key, action="setting_changed",
                 before_state=None if before is None else str(before), after_state=text, request_id=request_id)
    return settings(conn, actor.operator_id)


# ── idempotency ───────────────────────────────────────────────────────────────

IDEMPOTENCY_TTL = timedelta(hours=24)
MAX_IDEMPOTENCY_KEY = 128
MAX_REPLAY_BYTES = 2 * 1024 * 1024


def recall(conn: Any, operator: str, key: str, path: str) -> dict[str, Any] | None:
    """The recorded response for a retried request, or None."""
    from api.product.catalog import _rows

    if not key or len(key) > MAX_IDEMPOTENCY_KEY:
        return None
    rows = _rows(conn, "SELECT * FROM zaad_idempotency WHERE operator_id = ? AND key = ? AND path = ? "
                       "ORDER BY created_at DESC LIMIT 1", [operator, key, path])
    if not rows:
        return None
    row = rows[0]
    created = row.get("created_at")
    if created and datetime.now(timezone.utc).replace(tzinfo=None) - created > IDEMPOTENCY_TTL:
        return None
    return row


def remember(conn: Any, operator: str, key: str, path: str, *, status_code: int, response: str,
             media_type: str = "application/json", headers: dict[str, str] | None = None) -> None:
    if not key or len(key) > MAX_IDEMPOTENCY_KEY or len(response) > MAX_REPLAY_BYTES:
        return
    conn.execute("DELETE FROM zaad_idempotency WHERE operator_id = ? AND key = ? AND path = ?", [operator, key, path])
    conn.execute("INSERT INTO zaad_idempotency (operator_id, key, path, status_code, response, media_type, headers, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [operator, key, path, status_code, response, media_type, json.dumps(headers or {}),
                  datetime.now(timezone.utc).replace(tzinfo=None)])
