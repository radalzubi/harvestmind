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

import contextlib
import fcntl
import tempfile
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
    access_code_hash: Optional[str] = None # sha256 of a short human key (pilot invites); accepted like a token
    display_name: Optional[str] = None     # how the welcome screen greets them, if different from name
    logo_url: Optional[str] = None         # path or URL of the customer's logo for the welcome screen
    # Operating Product V2: named people in the workspace, each with their own token and a role.
    # Keyed by the sha256 of the actor's token; the value carries actor_id, name, role, created_at
    # and, once revoked, revoked_at. The workspace token above stays the pilot administrator.
    actors: dict[str, dict] = {}


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
        """Atomic and private: written to a sibling file, permissions 0600, then renamed over the registry, so a
        reader never sees a half-written file and the token hashes and HMAC secrets are not world-readable
        (security review 2026-09, SEC-016)."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.registry_dir, prefix=".operators.", suffix=".json")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(json.dumps(records, indent=2, default=str))
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.registry_file)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _update_record(self, record: OperatorRecord) -> None:
        with self._locked():
            records = self._load()
            records[record.operator_id] = json.loads(record.model_dump_json())
            self._save(records)

    @contextlib.contextmanager
    def _locked(self):
        """One writer at a time across processes (an advisory lock beside the registry), so a token rotation or a
        revocation is never undone by a concurrent upload counter (SEC-016)."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        with open(self.registry_dir / ".operators.lock", "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

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
            # HARDENING V1, H3b: this vault's whole life is under recommendation-exposure recording, and the stamp
            # names the file it was created as (a copy served from elsewhere is not this vault)
            from api.product.operator_plans import stamp_vault_creation
            stamp_vault_creation(conn, str((self.data_root / db_rel).resolve()))
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

    #: A code authenticates like the workspace token (ADMIN), so it must not be guessable: at least
    #: twelve characters (security review 2026-09, SEC-001). Codes set before that rule keep working
    #: until they are rotated; `seed_workspaces` names them at startup.
    MIN_ACCESS_CODE_CHARS = 12

    def set_access_code(self, operator_id: str, code: str) -> None:
        """A human key that authenticates like a token (ADMIN). Stored as a hash. Meant for a handful of
        invited workspaces, not for the public: rotate or clear it after the pilot."""
        if not code or len(code.strip()) < self.MIN_ACCESS_CODE_CHARS:
            raise ValueError(f"access code must be at least {self.MIN_ACCESS_CODE_CHARS} characters")
        rec = self.get_operator(operator_id)
        rec.access_code_hash = _hash_token(code.strip())
        self._update_record(rec)

    def clear_access_code(self, operator_id: str) -> None:
        rec = self.get_operator(operator_id)
        rec.access_code_hash = None
        self._update_record(rec)

    def set_profile(self, operator_id: str, display_name: str | None = None, logo_url: str | None = None) -> None:
        rec = self.get_operator(operator_id)
        if display_name is not None:
            rec.display_name = display_name
        if logo_url is not None:
            rec.logo_url = logo_url
        self._update_record(rec)

    def find_by_name(self, name: str):
        for rec in self.list_operators():
            if rec.name == name:
                return rec
        return None

    def issue_token(self, operator_id: str) -> str:
        """Generate a fresh API token for an operator, store only its hash,
        and return the raw token ONCE (it cannot be recovered later)."""
        rec = self.get_operator(operator_id)
        raw = secrets.token_urlsafe(32)
        rec.token_hash = _hash_token(raw)
        self._update_record(rec)
        return raw

    # ── actors (Operating Product V2) ────────────────────────────────────

    def issue_actor_token(self, operator_id: str, name: str, role: str) -> tuple[str, str]:
        """A token for one named person in the workspace, with a role. Returns (actor_id, raw token) once."""
        rec = self.get_operator(operator_id)
        name = str(name).strip()[:120]
        if not name:
            raise ValueError("an actor needs a name")
        actor_id = f"act_{secrets.token_hex(4)}"
        raw = secrets.token_urlsafe(32)
        rec.actors[_hash_token(raw)] = {"actor_id": actor_id, "name": name, "role": str(role),
                                        "created_at": datetime.now(timezone.utc).isoformat()}
        self._update_record(rec)
        return actor_id, raw

    def list_actors(self, operator_id: str) -> list[dict]:
        """Every actor without its token hash. The pilot administrator is not listed; it is the workspace."""
        rec = self.get_operator(operator_id)
        return [{k: v for k, v in a.items()} for a in rec.actors.values()]

    def revoke_actor(self, operator_id: str, actor_id: str) -> bool:
        rec = self.get_operator(operator_id)
        for a in rec.actors.values():
            if a.get("actor_id") == actor_id and not a.get("revoked_at"):
                a["revoked_at"] = datetime.now(timezone.utc).isoformat()
                self._update_record(rec)
                return True
        return False

    def actor_for_token(self, raw_token: str) -> dict | None:
        """Who a token is: {operator_id, actor_id, name, role}, or None.

        The workspace's own token (and its pilot access code) is the pilot administrator:
        actor_id is the operator id, the name is the workspace's, the role ADMIN — so every
        deployment upgrades without a behaviour change. A revoked actor never authenticates.
        """
        if not raw_token:
            return None
        candidate = _hash_token(raw_token)
        for rec in self._load().values():
            if rec.get("status") != "active":
                continue
            for field_name in ("token_hash", "access_code_hash"):
                th = rec.get(field_name)
                if th and hmac.compare_digest(th, candidate):
                    return {"operator_id": rec["operator_id"], "actor_id": rec["operator_id"],
                            "name": rec.get("display_name") or rec.get("name") or rec["operator_id"], "role": "ADMIN"}
            for th, actor in (rec.get("actors") or {}).items():
                if hmac.compare_digest(th, candidate):
                    if actor.get("revoked_at"):
                        return None
                    return {"operator_id": rec["operator_id"], "actor_id": actor["actor_id"],
                            "name": actor.get("name") or actor["actor_id"], "role": actor.get("role") or "VIEWER"}
        return None

    def operator_id_for_token(self, raw_token: str) -> str | None:
        """Resolve a raw API token to its (active) operator_id, or None.

        Constant-time hash comparison; suspended/deleted operators never
        authenticate.
        """
        if not raw_token:
            return None
        candidate = _hash_token(raw_token)
        for rec in self._load().values():
            if rec.get("status") != "active":
                continue
            for field_name in ("token_hash", "access_code_hash"):
                th = rec.get(field_name)
                if th and hmac.compare_digest(th, candidate):
                    return rec["operator_id"]
            for th, actor in (rec.get("actors") or {}).items():
                if hmac.compare_digest(th, candidate) and not actor.get("revoked_at"):
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
