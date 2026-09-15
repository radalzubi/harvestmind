"""All vault database access goes through here. CONVENTION (enforced by
review + the isolation tests): application code never calls
duckdb.connect on a vault path directly — only DBManager resolves
operator ids to connections, so isolation has exactly one place to be
right.

Cross-operator visibility exists in ONE method only:
get_cross_operator_connection — read-only, requires a stated purpose
(logged to data/registry/cross_access_log.jsonl), and is used solely by
the pool contribution pipeline. The diagnostic and the optimizer never
touch it.

One database instance per file, for the life of the process
------------------------------------------------------------
Every request used to open its own ``duckdb.connect(path)`` and close it
afterwards. DuckDB keeps one instance per file in a process-wide cache
and destroys it when the last connection closes — so when request A's
connection was the last one open and closed while request B was connecting
to the same vault, B missed the cache, tried to attach the file a second
time and failed with ``Binder Error: Unique file handle conflict``. That
is a 500 on an ordinary page load whenever two requests to one workspace
overlap, and it was observed three times in one browsing session and
reproduced at 712 failures in ten seconds under a small thread storm.

So the process now holds one long-lived *anchor* connection per vault
path and serves every request a ``cursor()`` on it: a cursor is its own
connection (its own transaction), but it shares the anchor's instance, so
the file is attached exactly once and never re-attached. Anchors are
never closed while a cursor is open on them (a cursor does not survive its
parent), and their number is bounded so a process that has seen many
vaults does not hold every file for ever.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from infrastructure.operator_registry import OperatorRegistry

#: An anchor that has gone idle is checkpointed no more often than this. DuckDB checkpoints on
#: its own once the WAL is large, and on a clean close; neither happens to a connection held open
#: for the life of the process, so the write-ahead log would otherwise carry every write until a
#: threshold — and a crash would have to replay all of it. A checkpoint of an unchanged file costs
#: about a millisecond, so idle moments are the right time.
CHECKPOINT_INTERVAL_S = float(os.getenv("HARVESTMIND_VAULT_CHECKPOINT_SECONDS", "2"))

#: How many vault files this process keeps attached at once. Beyond it, the least recently used
#: anchor with no open cursor is closed. A deployment serves a handful of operators; 64 is a bound,
#: not a target.
MAX_ANCHORS = int(os.getenv("HARVESTMIND_VAULT_ANCHORS", "64"))

_ANCHOR_LOCK = threading.Lock()
_ANCHORS: dict[str, duckdb.DuckDBPyConnection] = {}
_LIVE: dict[str, int] = {}          # open cursors per anchor
_LAST_USED: dict[str, float] = {}   # monotonic, for eviction order
_LAST_CHECKPOINT: dict[str, float] = {}


def _key(path: str | Path) -> str:
    return str(Path(path).resolve())


def _evict_idle_locked() -> None:
    """Close the least recently used anchors that have no cursor open, down to the bound."""
    while len(_ANCHORS) >= MAX_ANCHORS:
        idle = sorted((k for k in _ANCHORS if _LIVE.get(k, 0) <= 0), key=lambda k: _LAST_USED.get(k, 0.0))
        if not idle:
            return  # every anchor is in use; exceeding the bound beats closing a live file
        victim = idle[0]
        try:
            _ANCHORS.pop(victim).close()
        except Exception:  # noqa: BLE001  a file that would not close is still not in the map
            pass
        _LIVE.pop(victim, None)
        _LAST_USED.pop(victim, None)


class VaultConnection:
    """A request's connection: a cursor on the vault's anchor, counted while it is open.

    Everything is forwarded to the DuckDB cursor. `close()` is the one method that matters here:
    it closes the cursor and tells the anchor it is idle — once, however many times it is called —
    so the count of live cursors is right whether a caller closes directly or through
    :meth:`DBManager.close_all`. Only an accurate count lets an idle anchor be checkpointed, evicted
    or released for a read-only attach without breaking a request in flight.
    """

    __slots__ = ("_cursor", "_key", "_released")

    def __init__(self, cursor: duckdb.DuckDBPyConnection, key: str):
        self._cursor = cursor
        self._key = key
        self._released = False

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)

    def close(self) -> None:
        try:
            self._cursor.close()
        finally:
            if not self._released:
                self._released = True
                release_cursor(self._key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def vault_cursor(path: str | Path) -> Any:
    # Typed Any on purpose: the handle forwards every DuckDB connection method, and callers are
    # written against the connection's own interface (execute, fetchone, register, begin, close).
    """A connection to ``path`` that shares the process's single instance of that file.

    Used by :class:`DBManager` and by the places that open the legacy root database, so no code
    path opens a file a second way. Close it when the request is done.
    """
    key = _key(path)
    with _ANCHOR_LOCK:
        anchor = _ANCHORS.get(key)
        if anchor is None:
            _evict_idle_locked()
            anchor = duckdb.connect(key)
            _ANCHORS[key] = anchor
        _LIVE[key] = _LIVE.get(key, 0) + 1
        _LAST_USED[key] = time.monotonic()
        cursor = anchor.cursor()
    return VaultConnection(cursor, key)


def release_cursor(key: str) -> None:
    """A request has closed its cursor. When the anchor is idle, fold the WAL into the file."""
    anchor = None
    with _ANCHOR_LOCK:
        if key in _LIVE:
            _LIVE[key] = max(0, _LIVE[key] - 1)
        now = time.monotonic()
        if _LIVE.get(key, 0) == 0 and now - _LAST_CHECKPOINT.get(key, 0.0) >= CHECKPOINT_INTERVAL_S:
            anchor = _ANCHORS.get(key)
            _LAST_CHECKPOINT[key] = now
    if anchor is not None:
        try:
            anchor.execute("CHECKPOINT")
        except Exception:  # noqa: BLE001 - a transaction opened meanwhile; the next idle moment checkpoints
            pass


def checkpoint_all() -> int:
    """Checkpoint every idle anchor now — for a clean shutdown. Returns how many were written."""
    written = 0
    with _ANCHOR_LOCK:
        idle = [(k, a) for k, a in _ANCHORS.items() if _LIVE.get(k, 0) == 0]
    for key, anchor in idle:
        try:
            anchor.execute("CHECKPOINT")
            written += 1
        except Exception:  # noqa: BLE001
            pass
    return written


def release_idle_anchor(path: str | Path) -> bool:
    """Close the anchor for ``path`` if no request holds a cursor on it. True when it is now free.

    A read-only ATTACH of a vault (the pool pipeline's cross-operator read) cannot share a file the
    process already holds read-write, so the anchor is let go first. A file with an open cursor is
    left alone and False is returned; the caller decides what that means.
    """
    key = _key(path)
    with _ANCHOR_LOCK:
        if key not in _ANCHORS:
            return True
        if _LIVE.get(key, 0) > 0:
            return False
        try:
            _ANCHORS.pop(key).close()
        except Exception:  # noqa: BLE001
            pass
        _LIVE.pop(key, None)
        _LAST_USED.pop(key, None)
        _LAST_CHECKPOINT.pop(key, None)
        return True


def anchored_files() -> list[str]:
    """The files this process currently holds open — for tests and diagnostics."""
    with _ANCHOR_LOCK:
        return sorted(_ANCHORS)


class DBManager:
    def __init__(self, registry: OperatorRegistry | None = None) -> None:
        self.registry = registry or OperatorRegistry()
        self._open: list[Any] = []

    # ── single-operator access ───────────────────────────────────────────

    def get_operator_connection(self, operator_id: str) -> Any:
        """A cursor on the process's anchor for this operator's vault (see the module docstring).

        Returns a :class:`VaultConnection`, which behaves as a DuckDB connection; typed ``Any`` so
        every caller written against the connection's interface type-checks unchanged.
        """
        path = self.registry.get_db_path(operator_id)
        conn = vault_cursor(path)
        self._open.append(conn)
        return conn

    def get_read_only_connection(self, operator_id: str) -> Any:
        """The same cursor as above.

        DuckDB refuses to open one file read-only while the process holds it read-write, so a
        separate read-only instance is not possible without giving the race back. Read-only intent
        is a convention of the caller; the isolation this method provides — one operator's vault
        and no other — is unchanged.
        """
        return self.get_operator_connection(operator_id)

    # ── the ONLY multi-operator path ─────────────────────────────────────

    def get_cross_operator_connection(
        self,
        operator_ids: list[str],
        purpose: str,
    ) -> duckdb.DuckDBPyConnection:
        """Read-only view across EXACTLY the named operators.

        Each vault is ATTACHed READ_ONLY into an in-memory connection
        under the alias ``op_<id>`` — queries must name the operator they
        read from (``op_xxx.stg_buyer_orders``), so no query can
        accidentally sweep everyone. Purpose is mandatory and logged.
        """
        if not operator_ids:
            raise ValueError(
                "get_cross_operator_connection requires explicit operator "
                "ids — there is no 'all operators' shortcut by design")
        if not purpose or not purpose.strip():
            raise ValueError("a stated purpose is required and is logged")

        paths = {oid: self.registry.get_db_path(oid)  # raises on unknown
                 for oid in operator_ids}

        # A vault held open read-write by this process cannot also be attached read-only. The
        # anchors are released when idle; a vault a request is using right now is reported.
        busy = [oid for oid, path in paths.items() if not release_idle_anchor(path)]
        if busy:
            raise RuntimeError(f"cross-operator read refused: vault(s) in use by a request right now: {busy}")

        conn = duckdb.connect(":memory:")
        for oid, path in paths.items():
            conn.execute(
                f"ATTACH '{path}' AS {oid} (READ_ONLY)")
        self._open.append(conn)

        log_dir = self.registry.registry_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "cross_access_log.jsonl").open("a") as f:
            f.write(json.dumps({
                "at": datetime.now(timezone.utc).isoformat(),
                "operator_ids": sorted(operator_ids),
                "purpose": purpose,
            }) + "\n")
        return conn

    def close_all(self) -> None:
        for c in self._open:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        self._open = []
