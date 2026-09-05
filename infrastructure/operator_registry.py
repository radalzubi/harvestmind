"""Operator registry — the single source of truth for company vaults.

Every operator gets an isolated vault under data/operators/<operator_id>/:
their own DuckDB (all migrations applied at creation), immutable raw
uploads, LLM session snapshots, exports, and their consent record. No
code path ever resolves another operator's files from one operator's id.

The registry file (data/registry/operators.json) holds the metadata;
consent is ALSO mirrored in each vault's consent.json — the
ConsentManager is the only writer of both (single-writer invariant).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


def _hash_token(raw: str) -> str:
    """SHA-256 of a raw API token. Only the hash is ever persisted."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path(os.getenv("HARVESTMIND_DATA_ROOT", REPO_ROOT / "data"))


class OperatorNotFoundError(KeyError):
    pass


class OperatorRecord(BaseModel):
    operator_id: str                      # "op_" + 8 hex chars, immutable
    name: str
    created_at: datetime
    db_path: str                          # relative to the data root
    status: Literal["active", "suspended", "deleted"] = "active"
    region: str = "unspecified"           # operator-level; pool yield signals
    upload_count: int = 0
    last_upload: Optional[datetime] = None
    data_window_days: Optional[int] = None
    pool_consent: bool = False
    pool_consent_date: Optional[datetime] = None
    pool_contribution_count: int = 0
    token_hash: Optional[str] = None       # sha256 of the operator's API token
    anon_secret: Optional[str] = None      # HMAC key for id pseudonymisation; never leaves the registry
    sector: str = "produce"                # produce | commercial: which intake and planner the UI shows


class OperatorRegistry:
    def __init__(self, data_root: str | Path | None = None) -> None:
        self.data_root = Path(data_root) if data_root else DEFAULT_DATA_ROOT
        self.operators_dir = self.data_root / "operators"
        self.registry_dir = self.data_root / "registry"
        self.registry_file = self.registry_dir / "operators.json"

    # ── persistence ──────────────────────────────────────────────────────

    def _load(self) -> dict[str, dict]:
        if not self.registry_file.exists():
            return {}
        return json.loads(self.registry_file.read_text())

    def _save(self, records: dict[str, dict]) -> None:
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file.write_text(
            json.dumps(records, indent=2, default=str))

    def _update_record(self, record: OperatorRecord) -> None:
        records = self._load()
        records[record.operator_id] = json.loads(record.model_dump_json())
        self._save(records)

    # ── lifecycle ────────────────────────────────────────────────────────

    def create_operator(
        self,
        name: str,
        pool_consent: bool = False,
        region: str = "unspecified",
        sector: str = "produce",
    ) -> OperatorRecord:
        """Create the vault: directories, a fresh fully-migrated DuckDB,
        the consent record, and the registry entry."""
        operator_id = f"op_{secrets.token_hex(4)}"
        vault = self.operators_dir / operator_id
        for sub in ("uploads", "sessions", "exports"):
            (vault / sub).mkdir(parents=True, exist_ok=False)

        db_rel = f"operators/{operator_id}/harvestmind.db"
        import duckdb
        from scripts.setup_db import setup_db
        conn = duckdb.connect(str(self.data_root / db_rel))
        try:
            setup_db(conn)
        finally:
            conn.close()

        now = datetime.now(timezone.utc)
        record = OperatorRecord(
            operator_id=operator_id, name=name, created_at=now,
            db_path=db_rel, region=region,
            sector=sector,
            pool_consent=pool_consent,
            pool_consent_date=now if pool_consent else None,
        )
        self._update_record(record)

        from infrastructure.consent_manager import ConsentManager
        ConsentManager(self).record_consent(
            operator_id, pool_consent, method="onboarding_form")
        return self.get_operator(operator_id)

    def get_operator(self, operator_id: str) -> OperatorRecord:
        rec = self._load().get(operator_id)
        if rec is None:
            raise OperatorNotFoundError(
                f"No operator {operator_id!r} in the registry")
        return OperatorRecord.model_validate(rec)

    def list_operators(self, status: str = "active") -> list[OperatorRecord]:
        return [OperatorRecord.model_validate(r)
                for r in self._load().values()
                if status is None or r.get("status") == status]

    def get_db_path(self, operator_id: str) -> Path:
        rec = self.get_operator(operator_id)
        p = self.data_root / rec.db_path
        if not p.exists():
            raise FileNotFoundError(
                f"Vault database missing for {operator_id}: {p}")
        return p

    def vault_dir(self, operator_id: str) -> Path:
        self.get_operator(operator_id)  # raises if unknown
        return self.operators_dir / operator_id

    def update_consent(self, operator_id: str, pool_consent: bool) -> OperatorRecord:
        """Thin wrapper — the ConsentManager is the single writer."""
        from infrastructure.consent_manager import ConsentManager
        ConsentManager(self).record_consent(
            operator_id, pool_consent, method="api_call")
        return self.get_operator(operator_id)

    # ── API tokens (authentication) ──────────────────────────────────────

    def anonymization_secret(self, operator_id: str) -> str:
        """Per-operator HMAC key used to hash identifiers before storage.
        Created on first use, kept only in the registry file (0600), never
        written to the operator's database or returned by any endpoint."""
        rec = self.get_operator(operator_id)
        if not rec.anon_secret:
            rec.anon_secret = secrets.token_hex(32)
            self._update_record(rec)
        return rec.anon_secret

    def issue_token(self, operator_id: str) -> str:
        """Generate a fresh API token for an operator, store only its hash,
        and return the raw token ONCE (it cannot be recovered later)."""
        rec = self.get_operator(operator_id)
        raw = secrets.token_urlsafe(32)
        rec.token_hash = _hash_token(raw)
        self._update_record(rec)
        return raw

    def operator_id_for_token(self, raw_token: str) -> str | None:
        """Resolve a raw API token to its (active) operator_id, or None.

        Constant-time hash comparison; suspended/deleted operators never
        authenticate.
        """
        if not raw_token:
            return None
        candidate = _hash_token(raw_token)
        for rec in self._load().values():
            th = rec.get("token_hash")
            if (th and rec.get("status") == "active"
                    and hmac.compare_digest(th, candidate)):
                return rec["operator_id"]
        return None

    def record_upload(self, operator_id: str) -> None:
        rec = self.get_operator(operator_id)
        rec.upload_count += 1
        rec.last_upload = datetime.now(timezone.utc)
        self._update_record(rec)

    def record_pool_contribution(self, operator_id: str) -> None:
        rec = self.get_operator(operator_id)
        rec.pool_contribution_count += 1
        self._update_record(rec)

    def suspend_operator(self, operator_id: str) -> OperatorRecord:
        rec = self.get_operator(operator_id)
        rec.status = "suspended"
        self._update_record(rec)
        return rec

    def delete_operator(self, operator_id: str) -> OperatorRecord:
        """Mark deleted and stop all future pool contributions.

        Vault files are NOT deleted (retention policy — configurable
        operationally, not silently in code). Anonymized signals already
        in the pool cannot be reversed to this operator and therefore
        cannot be selectively removed — operators are told this at
        consent time (docs/POOL_PRIVACY.md).
        """
        from infrastructure.consent_manager import ConsentManager
        rec = self.get_operator(operator_id)
        if rec.pool_consent:
            ConsentManager(self).withdraw_consent(operator_id)
            rec = self.get_operator(operator_id)
        rec.status = "deleted"
        self._update_record(rec)
        return rec
