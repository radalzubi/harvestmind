"""Tenant offboarding: find every ZAAD-controlled store that holds a workspace's data, and remove it.

The inventory this module drives is the one recorded in `docs/security/TENANT_OFFBOARDING_RUNBOOK.md`. Every store is a
*stage*; a run is a plan (dry run, the default, which only counts) or an execution. The rules that make deleting the
wrong tenant hard:

- the target is the immutable operator id (`op_` + 8 hex), never a display name, and an execution repeats it;
- an unknown operator is refused unless an offboarding receipt already exists for it (a rerun is then a no-op);
- every path the module removes is checked to sit directly under the root it belongs to, symlinks are never followed
  (a link is unlinked, its target untouched), and an unexpected path fails that stage closed;
- a stage that fails is reported as failed and the run as PARTIAL; the other stages still run, and a rerun is safe;
- nothing here prints or returns a customer record — counts, ids and paths only;
- what is deliberately kept (the registry tombstone, the receipt, the security logs) is reported as RETAINED with a
  reason, and what ZAAD does not control (provider logs, volume snapshots) is named, not claimed.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from infrastructure.operator_registry import OperatorNotFoundError, OperatorRegistry

OPERATOR_ID = re.compile(r"^op_[0-9a-f]{8}$")

#: Retained on purpose, always reported. The owner of each retention is named in the runbook.
RETAINED = [
    {"store": "registry_tombstone", "reason": "the operator id, its name and the deletion time stay so the id is never reissued and the deletion is accountable; every credential hash and secret is removed"},
    {"store": "offboarding_receipt", "reason": "counts per store, times and the actor of the deletion — no customer payload; the audit record of the offboarding itself"},
    {"store": "cross_access_log", "reason": "security log of cross-vault reads (operator ids and purpose only); kept for accountability"},
    {"store": "process_logs", "reason": "stdout of the API carries operator ids in security events; retained by the platform for its log window, not by ZAAD"},
]

#: Not under ZAAD's control; named so nobody claims they were removed.
EXTERNAL = [
    "Fly.io volume snapshots (daily, retained by Fly for its snapshot window) may hold the vault until they expire",
    "Fly.io and Vercel request logs and metrics",
    "the LLM provider's request logs for extraction and Ask ZAAD, under its own retention",
    "the mail provider's copy of the access-approval email (if one was sent)",
    "backups the owner took outside the platform",
]


@dataclass
class Stage:
    store: str
    status: str            # would_remove | removed | nothing | failed | refused | retained | not_configured
    count: int = 0
    detail: str = ""
    paths: list[str] = field(default_factory=list)


@dataclass
class Result:
    operator_id: str
    mode: str              # dry-run | execute
    status: str            # complete | partial | nothing-to-do | refused
    started_at: str
    finished_at: str = ""
    stages: list[Stage] = field(default_factory=list)
    retained: list[dict] = field(default_factory=list)
    external: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    receipt: str | None = None

    def to_dict(self) -> dict:
        return {**asdict(self), "stages": [asdict(s) for s in self.stages]}

    @property
    def failed(self) -> list[Stage]:
        return [s for s in self.stages if s.status == "failed"]

    @property
    def removed_anything(self) -> bool:
        return any(s.status in ("removed", "would_remove") and s.count for s in self.stages)


class Refused(Exception):
    """The run cannot proceed at all (bad id, unknown operator, confirmation mismatch)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolved_child(path: Path, within: Path) -> bool:
    """`path` is a direct child of `within`, by resolved parent, and not itself a symlink."""
    try:
        if path.is_symlink():
            return False
        return path.resolve(strict=False).parent == within.resolve(strict=False) and path.name == path.resolve(strict=False).name
    except OSError:
        return False


def _count_tree(path: Path) -> int:
    n = 0
    for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
        n += len(files)
        # a symlinked directory counts as one entry and is never descended into
        keep = []
        for d in dirs:
            if (Path(root) / d).is_symlink():
                n += 1
            else:
                keep.append(d)
        dirs[:] = keep
    return n


def _remove_tree(path: Path) -> int:
    """Remove a directory tree without following any symlink. Returns the number of entries removed."""
    removed = 0
    for root, dirs, files in os.walk(path, topdown=False, followlinks=False):
        for f in files:
            (Path(root) / f).unlink()
            removed += 1
        for d in dirs:
            dp = Path(root) / d
            if dp.is_symlink():
                dp.unlink()          # the link only; whatever it pointed at is not ours to touch
            else:
                dp.rmdir()
            removed += 1
    path.rmdir()
    return removed


def _atomic_rewrite(path: Path, lines: list[str]) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.writelines(lines)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Offboarding:
    """One workspace's data across every store. Roots default to the deployment's environment."""

    def __init__(self, registry: OperatorRegistry, *, job_store: Path | None = None, shadow_ledger: Path | None = None,
                 sessions_root: Path | None = None, runs_root: Path | None = None, pool_root: Path | None = None,
                 corpus_file: Path | None = None, release_vault: Callable[[Path], bool] | None = None,
                 cache_clearers: dict[str, Callable[[str], int]] | None = None) -> None:
        self.registry = registry
        job_env, ledger_env = os.environ.get("ZAAD_JOB_STORE"), os.environ.get("ZAAD_SHADOW_LEDGER")
        self.job_store = job_store if job_store is not None else (Path(job_env) if job_env else None)
        self.shadow_ledger = shadow_ledger if shadow_ledger is not None else (Path(ledger_env) if ledger_env else None)
        if sessions_root is None:
            from ingestion.extraction_sessions import AUDIT_ROOT
            sessions_root = AUDIT_ROOT
        self.sessions_root = sessions_root
        self.runs_root = runs_root if runs_root is not None else registry.data_root / "runs"
        if pool_root is None:
            from pool.pool_contributor import DEFAULT_POOL_ROOT
            pool_root = DEFAULT_POOL_ROOT
        self.pool_root = pool_root
        if corpus_file is None:
            from training.data_accumulator import CORPUS_ROOT, CORPUS_VERSION
            corpus_file = CORPUS_ROOT / f"{CORPUS_VERSION}.jsonl"
        self.corpus_file = corpus_file
        if release_vault is None:
            from infrastructure.db_manager import release_idle_anchor
            release_vault = release_idle_anchor
        self.release_vault = release_vault
        self.cache_clearers = cache_clearers or {}

    # ── entry points ────────────────────────────────────────────────────────

    def plan(self, operator_id: str) -> Result:
        return self._run(operator_id, execute=False, actor="plan")

    def execute(self, operator_id: str, confirm_operator_id: str, actor: str = "cli") -> Result:
        if confirm_operator_id != operator_id:
            raise Refused("the confirmation must repeat the exact operator id")
        return self._run(operator_id, execute=True, actor=actor)

    # ── the run ─────────────────────────────────────────────────────────────

    def receipt_path(self, operator_id: str) -> Path:
        return self.registry.registry_dir / "offboarding" / f"{operator_id}.json"

    def _run(self, operator_id: str, *, execute: bool, actor: str) -> Result:
        res = Result(operator_id=operator_id, mode="execute" if execute else "dry-run", status="refused", started_at=_now(),
                     retained=list(RETAINED), external=list(EXTERNAL))
        if not OPERATOR_ID.match(operator_id or ""):
            raise Refused("operator id must be op_ followed by 8 hex characters")
        try:
            record = self.registry.get_operator(operator_id)
        except OperatorNotFoundError:
            record = None
        receipt = self.receipt_path(operator_id)
        if record is None and not receipt.exists():
            raise Refused(f"no operator {operator_id} in the registry and no offboarding receipt for it")
        if record is not None:
            seed = os.environ.get("HARVESTMIND_SEED_WORKSPACES", "")
            if record.name and any(part.split("|")[0].strip() == record.name for part in seed.split(";") if part.strip()):
                res.warnings.append("HARVESTMIND_SEED_WORKSPACES still names this workspace: remove the entry before or with the "
                                    "offboarding, or the next start re-creates an empty workspace of that name")
        session_ids: list[str] = []
        stages: list[tuple[str, Callable[[], Stage]]] = [
            ("credentials", lambda: self._credentials(record, execute)),
            ("vault", lambda: self._vault(operator_id, execute)),
            ("extraction_sessions", lambda: self._sessions(operator_id, execute, session_ids)),
            ("training_corpus", lambda: self._corpus(operator_id, execute, session_ids)),
            ("job_store", lambda: self._jobs(operator_id, execute)),
            ("shadow_ledger", lambda: self._ledger(operator_id, execute)),
            ("run_records", lambda: self._runs(operator_id, execute)),
            ("access_requests", lambda: self._access_requests(operator_id, execute)),
            ("pool_signals", lambda: self._pool(operator_id, execute)),
            ("process_caches", lambda: self._caches(operator_id, execute)),
        ]
        for name, fn in stages:
            try:
                res.stages.append(fn())
            except Exception as exc:  # noqa: BLE001  one store's failure is reported, the others still run
                res.stages.append(Stage(name, "failed", detail=f"{type(exc).__name__}: {exc}"[:300]))
        try:
            res.stages.append(self._tombstone(record, execute))
        except Exception as exc:  # noqa: BLE001
            res.stages.append(Stage("registry_tombstone", "failed", detail=f"{type(exc).__name__}: {exc}"[:300]))
        res.finished_at = _now()
        if res.failed:
            res.status = "partial"
        elif res.removed_anything:
            res.status = "complete"
        else:
            res.status = "nothing-to-do"
        if execute:
            res.receipt = str(self._write_receipt(res, actor))
        return res

    # ── stages ──────────────────────────────────────────────────────────────

    def _credentials(self, record, execute: bool) -> Stage:
        if record is None:
            return Stage("credentials", "nothing", detail="no registry record")
        live = int(bool(record.token_hash)) + int(bool(record.access_code_hash)) + sum(1 for a in record.actors.values() if not a.get("revoked_at"))
        if not execute:
            return Stage("credentials", "would_remove" if live or record.status == "active" else "nothing", count=live,
                         detail="workspace token, access code and actor tokens stop authenticating; status becomes deleted")
        if record.status != "deleted" or live:
            record.status = "deleted"
            record.token_hash = None
            record.access_code_hash = None
            record.actors = {}
            self.registry._update_record(record)  # noqa: SLF001  the registry's own locked write
            return Stage("credentials", "removed", count=live, detail="status deleted; token, access code and actor hashes removed")
        return Stage("credentials", "nothing", detail="already deleted")

    def _vault(self, operator_id: str, execute: bool) -> Stage:
        root = self.registry.operators_dir
        path = root / operator_id
        if not path.exists() and not path.is_symlink():
            return Stage("vault", "nothing", detail="no vault directory")
        if not _resolved_child(path, root):
            return Stage("vault", "failed", detail="vault path is a symlink or does not resolve under the operators root; refusing")
        n = _count_tree(path)
        if not execute:
            return Stage("vault", "would_remove", count=n, paths=[str(path)],
                         detail="the DuckDB vault and its WAL, uploads, session snapshots, exports, diagnostic reports, upload hashes, consent record")
        for db in (path / "harvestmind.db",):
            if db.exists() and not self.release_vault(db):
                return Stage("vault", "failed", count=n, paths=[str(path)], detail="the vault is open in this process (a request holds a cursor); retry when idle")
        removed = _remove_tree(path)
        return Stage("vault", "removed", count=removed, paths=[str(path)])

    def _sessions(self, operator_id: str, execute: bool, session_ids: list[str]) -> Stage:
        root = self.sessions_root
        if not root.exists():
            return Stage("extraction_sessions", "nothing", detail="no sessions root")
        mine: list[Path] = []
        for owner in root.glob("*/owner.json"):
            try:
                if json.loads(owner.read_text()).get("operator_id") == operator_id:
                    mine.append(owner.parent)
            except (OSError, ValueError):
                continue
        session_ids.extend(p.name for p in mine)
        if not mine:
            return Stage("extraction_sessions", "nothing")
        bad = [p for p in mine if not _resolved_child(p, root)]
        if bad:
            return Stage("extraction_sessions", "failed", count=len(mine), detail="a session directory is a symlink or outside the sessions root; refusing")
        n = sum(_count_tree(p) for p in mine)
        if not execute:
            return Stage("extraction_sessions", "would_remove", count=len(mine), paths=[str(p) for p in mine], detail=f"{n} files")
        for p in mine:
            _remove_tree(p)
        return Stage("extraction_sessions", "removed", count=len(mine), paths=[str(p) for p in mine])

    def _corpus(self, operator_id: str, execute: bool, session_ids: list[str]) -> Stage:
        f = self.corpus_file
        if not f.exists():
            return Stage("training_corpus", "nothing", detail="no corpus file")
        wanted = set(session_ids)
        keep, drop = [], 0
        with f.open() as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    keep.append(line)
                    continue
                if row.get("operator_id") == operator_id or row.get("session_id") in wanted:
                    drop += 1
                else:
                    keep.append(line)
        if not drop:
            return Stage("training_corpus", "nothing")
        if not execute:
            return Stage("training_corpus", "would_remove", count=drop, paths=[str(f)], detail="lines are removed; the file is rewritten")
        _atomic_rewrite(f, keep)
        return Stage("training_corpus", "removed", count=drop, paths=[str(f)])

    def _jobs(self, operator_id: str, execute: bool) -> Stage:
        p = self.job_store
        if p is None:
            return Stage("job_store", "not_configured", detail="ZAAD_JOB_STORE is not set")
        if not p.exists():
            return Stage("job_store", "nothing", detail="no job store file")
        db = sqlite3.connect(p, timeout=30)
        try:
            total = db.execute("SELECT COUNT(*) FROM jobs WHERE operator = ?", (operator_id,)).fetchone()[0]
            active = db.execute("SELECT COUNT(*) FROM jobs WHERE operator = ? AND status IN ('QUEUED','RUNNING')", (operator_id,)).fetchone()[0]
            if not total:
                return Stage("job_store", "nothing")
            if active:
                return Stage("job_store", "failed", count=total, paths=[str(p)], detail=f"{active} job(s) queued or running: cancel them first")
            if not execute:
                return Stage("job_store", "would_remove", count=total, paths=[str(p)], detail="planning job rows (requests and reports inline)")
            with db:
                db.execute("DELETE FROM jobs WHERE operator = ?", (operator_id,))
            return Stage("job_store", "removed", count=total, paths=[str(p)])
        finally:
            db.close()

    def _ledger(self, operator_id: str, execute: bool) -> Stage:
        p = self.shadow_ledger
        if p is None:
            return Stage("shadow_ledger", "not_configured", detail="ZAAD_SHADOW_LEDGER is not set")
        if not p.exists():
            return Stage("shadow_ledger", "nothing", detail="no ledger file")
        db = sqlite3.connect(p, timeout=30)
        try:
            d = db.execute("SELECT COUNT(*) FROM decisions WHERE operator = ?", (operator_id,)).fetchone()[0]
            e = db.execute("SELECT COUNT(*) FROM events WHERE operator = ?", (operator_id,)).fetchone()[0]
            if not d and not e:
                return Stage("shadow_ledger", "nothing")
            if not execute:
                return Stage("shadow_ledger", "would_remove", count=d + e, paths=[str(p)], detail=f"{d} decisions, {e} events (per-decision hash chains; other tenants' chains untouched)")
            with db:
                db.execute("DELETE FROM events WHERE operator = ?", (operator_id,))
                db.execute("DELETE FROM decisions WHERE operator = ?", (operator_id,))
            return Stage("shadow_ledger", "removed", count=d + e, paths=[str(p)])
        finally:
            db.close()

    def _runs(self, operator_id: str, execute: bool) -> Stage:
        root = self.runs_root
        if not root.exists():
            return Stage("run_records", "nothing")
        mine = []
        for f in root.glob("*.json"):
            if f.is_symlink():
                continue
            try:
                if json.loads(f.read_text()).get("operator_id") == operator_id:
                    mine.append(f)
            except (OSError, ValueError):
                continue
        if not mine:
            return Stage("run_records", "nothing")
        if not execute:
            return Stage("run_records", "would_remove", count=len(mine), paths=[str(f) for f in mine], detail="optimizer run records (config and hashes)")
        for f in mine:
            f.unlink()
        return Stage("run_records", "removed", count=len(mine), paths=[str(f) for f in mine])

    def _access_requests(self, operator_id: str, execute: bool) -> Stage:
        p = self.registry.registry_dir / "access_requests.json"
        if not p.exists():
            return Stage("access_requests", "nothing")
        try:
            rows = json.loads(p.read_text())
        except ValueError:
            return Stage("access_requests", "failed", detail="access_requests.json is not valid JSON")
        pii = ("company", "contact_name", "email", "country", "erp", "note")
        mine = [r for r in rows if isinstance(r, dict) and r.get("operator_id") == operator_id and any(r.get(k) for k in pii)]
        if not mine:
            return Stage("access_requests", "nothing")
        if not execute:
            return Stage("access_requests", "would_remove", count=len(mine), paths=[str(p)], detail="contact details are blanked; the request id, status and times stay")
        for r in mine:
            for k in pii:
                if k in r:
                    r[k] = ""
            r["offboarded_at"] = _now()
        _atomic_rewrite(p, [json.dumps(rows, indent=1, default=str)])
        return Stage("access_requests", "removed", count=len(mine), paths=[str(p)])

    def _pool(self, operator_id: str, execute: bool) -> Stage:
        root = self.pool_root
        signals = root / "signals"
        log = root / "contributions" / "contribution_log.jsonl"
        if not signals.exists() and not log.exists():
            return Stage("pool_signals", "nothing", detail="no pool directory")
        touched: list[str] = []
        rows_dropped = 0
        if signals.exists():
            import pandas as pd  # type: ignore[import-untyped]
            for f in sorted(signals.glob("*/*.parquet")):
                if f.is_symlink():
                    continue
                df = pd.read_parquet(f)
                if "operator_id" not in df.columns:
                    continue
                mask = df["operator_id"].astype(str) == operator_id
                n = int(mask.sum())
                if not n:
                    continue
                rows_dropped += n
                touched.append(str(f))
                if execute:
                    rest = df.loc[~mask]
                    if rest.empty:
                        f.unlink()
                    else:
                        tmp = f.with_name(f".{f.name}.tmp")
                        rest.to_parquet(tmp, index=False)
                        os.replace(tmp, f)
        lines_dropped = 0
        if log.exists():
            keep = []
            with log.open() as fh:
                for line in fh:
                    try:
                        if json.loads(line).get("operator_id") == operator_id:
                            lines_dropped += 1
                            continue
                    except ValueError:
                        pass
                    keep.append(line)
            if lines_dropped:
                touched.append(str(log))
                if execute:
                    _atomic_rewrite(log, keep)
        total = rows_dropped + lines_dropped
        if not total:
            return Stage("pool_signals", "nothing")
        return Stage("pool_signals", "removed" if execute else "would_remove", count=total, paths=touched,
                     detail=f"{rows_dropped} signal rows, {lines_dropped} contribution-log lines")

    def _caches(self, operator_id: str, execute: bool) -> Stage:
        if not self.cache_clearers:
            return Stage("process_caches", "not_configured", detail="process-local caches are cleared only when offboarding runs inside the API (admin route) or the API restarts")
        if not execute:
            return Stage("process_caches", "would_remove", count=len(self.cache_clearers), detail=", ".join(sorted(self.cache_clearers)))
        cleared = {name: int(fn(operator_id)) for name, fn in self.cache_clearers.items()}
        return Stage("process_caches", "removed", count=sum(cleared.values()), detail=json.dumps(cleared, sort_keys=True))

    def _tombstone(self, record, execute: bool) -> Stage:
        if record is None:
            return Stage("registry_tombstone", "retained", detail="tombstone already present from an earlier offboarding")
        if not execute:
            return Stage("registry_tombstone", "retained", detail="operator id, name, created_at and deleted_at stay; profile, consent, counts and secrets are removed")
        record.status = "deleted"
        record.display_name = None
        record.logo_url = None
        record.anon_secret = None
        record.pool_consent = False
        record.pool_consent_date = None
        record.upload_count = 0
        record.last_upload = None
        self.registry._update_record(record)  # noqa: SLF001
        return Stage("registry_tombstone", "retained", detail="operator id, name and created_at kept; everything else on the record removed")

    def _write_receipt(self, res: Result, actor: str) -> Path:
        p = self.receipt_path(res.operator_id)
        p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        history = []
        if p.exists():
            try:
                history = json.loads(p.read_text()).get("runs", [])
            except ValueError:
                history = []
        entry = {"at": res.finished_at, "actor": actor, "status": res.status,
                 "stages": {s.store: {"status": s.status, "count": s.count} for s in res.stages}}
        body = {"operator_id": res.operator_id, "runs": history + [entry]}
        _atomic_rewrite(p, [json.dumps(body, indent=1, sort_keys=True)])
        return p
