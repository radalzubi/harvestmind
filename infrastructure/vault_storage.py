"""Vault file storage: immutable raw uploads, sessions, exports.

Raw uploads are WRITE-ONCE ground truth: the original bytes are copied
into the vault before any processing, named <utc-timestamp>_<original>,
and nothing in the application ever modifies or deletes them. Uploading
the same filename twice produces two distinct copies. Any future audit
or replay starts from these files.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from infrastructure.operator_registry import OperatorRegistry

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(filename: str) -> str:
    base = Path(filename or "upload.bin").name
    return _SAFE_NAME_RE.sub("_", base) or "upload.bin"


class DuplicateUploadError(ValueError):
    """The identical file content was already stored for this operator."""

    def __init__(self, existing: Path) -> None:
        super().__init__(f"identical file already uploaded as {existing.name}")
        self.existing = existing


def _content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def find_duplicate_upload(registry: OperatorRegistry, operator_id: str,
                          content: bytes) -> Path | None:
    """Return the earlier upload with identical bytes, if any."""
    # Hashes live beside, not inside, the uploads directory: the uploads
    # listing is the operator's write-once record and must contain only
    # their files.
    hashes = registry.vault_dir(operator_id) / "upload_hashes"
    if not hashes.exists():
        return None
    h = _content_hash(content)
    for side in hashes.glob("*.sha256"):
        try:
            if side.read_text().strip() == h:
                original = registry.vault_dir(operator_id) / "uploads" / side.name[:-len(".sha256")]
                return original if original.exists() else side
        except OSError:
            continue
    return None


def store_raw_upload(
    registry: OperatorRegistry,
    operator_id: str,
    filename: str,
    content: bytes,
    allow_duplicate: bool = False,
) -> Path:
    """Copy raw upload bytes into the vault, write-once. Returns the path.

    IDEMPOTENT BY CONTENT. A retried request, a double click or a re-sent
    export carries the same bytes; storing and loading them again doubles
    every quantity in the staging table. The content hash is kept beside
    each file and a repeat is refused unless the caller says it is
    deliberate.
    """
    if not allow_duplicate:
        dup = find_duplicate_upload(registry, operator_id, content)
        if dup is not None:
            raise DuplicateUploadError(dup)
    uploads = registry.vault_dir(operator_id) / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = uploads / f"{ts}_{_safe_name(filename)}"
    n = 0
    while target.exists():  # same microsecond — never overwrite
        n += 1
        target = uploads / f"{ts}.{n}_{_safe_name(filename)}"
    target.write_bytes(content)
    hashes = registry.vault_dir(operator_id) / "upload_hashes"
    hashes.mkdir(parents=True, exist_ok=True)
    (hashes / f"{target.name}.sha256").write_text(_content_hash(content))
    registry.record_upload(operator_id)
    return target


def store_session_snapshot(
    registry: OperatorRegistry,
    operator_id: str,
    session_id: str,
    snapshot_json: str,
) -> Path:
    """Copy a confirmed session snapshot into the operator's vault."""
    from ingestion.extraction_sessions import valid_session_id
    if not valid_session_id(session_id):
        raise ValueError("invalid extraction session id")
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
