"""Vault file storage: immutable raw uploads, sessions, exports.

Raw uploads are WRITE-ONCE ground truth: the original bytes are copied
into the vault before any processing, named <utc-timestamp>_<original>,
and nothing in the application ever modifies or deletes them. Uploading
the same filename twice produces two distinct copies. Any future audit
or replay starts from these files.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from infrastructure.operator_registry import OperatorRegistry

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(filename: str) -> str:
    base = Path(filename or "upload.bin").name
    return _SAFE_NAME_RE.sub("_", base) or "upload.bin"


def store_raw_upload(
    registry: OperatorRegistry,
    operator_id: str,
    filename: str,
    content: bytes,
) -> Path:
    """Copy raw upload bytes into the vault, write-once. Returns the path."""
    uploads = registry.vault_dir(operator_id) / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = uploads / f"{ts}_{_safe_name(filename)}"
    n = 0
    while target.exists():  # same microsecond — never overwrite
        n += 1
        target = uploads / f"{ts}.{n}_{_safe_name(filename)}"
    target.write_bytes(content)
    registry.record_upload(operator_id)
    return target


def store_session_snapshot(
    registry: OperatorRegistry,
    operator_id: str,
    session_id: str,
    snapshot_json: str,
) -> Path:
    """Copy a confirmed session snapshot into the operator's vault."""
    d = registry.vault_dir(operator_id) / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    target = d / f"{session_id}.json"
    n = 0
    while target.exists():
        n += 1
        target = d / f"{session_id}.rev{n}.json"
    target.write_text(snapshot_json)
    return target


def store_export(
    registry: OperatorRegistry,
    operator_id: str,
    filename: str,
    content: bytes | str,
) -> Path:
    """Reports / confirmed CSVs into the vault exports/ directory."""
    d = registry.vault_dir(operator_id) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    target = d / f"{ts}_{_safe_name(filename)}"
    if isinstance(content, str):
        target.write_text(content)
    else:
        target.write_bytes(content)
    return target
