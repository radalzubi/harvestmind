"""A small, tenant-keyed, in-process result cache.

The key is the whole identity of an answer: tenant, dataset version, semantic model version,
permissions hash and the spec hash. A different tenant, a new upload, a new model version or a
different role can never hit another entry, by construction; there is no key without the tenant.
Entries expire, the map is bounded, and a result whose dataset version is no longer current is
never served because the version is part of the key.
"""
from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Any

TTL_S = float(os.getenv("ZAAD_ANALYTICS_CACHE_TTL_S", "120"))
MAX_ENTRIES = int(os.getenv("ZAAD_ANALYTICS_CACHE_ENTRIES", "512"))

_LOCK = threading.Lock()
_STORE: "OrderedDict[tuple, tuple[float, dict[str, Any]]]" = OrderedDict()
_HITS = {"hit": 0, "miss": 0}


def key(tenant: str, dataset_version: str, model_version: str, permissions_hash: str, spec_hash: str) -> tuple:
    if not tenant:
        raise ValueError("a cache key needs a tenant")
    return (tenant, dataset_version, model_version, permissions_hash, spec_hash)


def get(k: tuple) -> dict[str, Any] | None:
    now = time.monotonic()
    with _LOCK:
        entry = _STORE.get(k)
        if entry is None:
            _HITS["miss"] += 1
            return None
        expires, value = entry
        if expires < now:
            _STORE.pop(k, None)
            _HITS["miss"] += 1
            return None
        _STORE.move_to_end(k)
        _HITS["hit"] += 1
        return value


def put(k: tuple, value: dict[str, Any], ttl_s: float | None = None) -> None:
    with _LOCK:
        _STORE[k] = (time.monotonic() + (ttl_s or TTL_S), value)
        _STORE.move_to_end(k)
        while len(_STORE) > MAX_ENTRIES:
            _STORE.popitem(last=False)


def clear(tenant: str | None = None) -> int:
    with _LOCK:
        if tenant is None:
            n = len(_STORE)
            _STORE.clear()
            return n
        victims = [k for k in _STORE if k[0] == tenant]
        for k in victims:
            _STORE.pop(k, None)
        return len(victims)


def stats() -> dict[str, int]:
    with _LOCK:
        return {"entries": len(_STORE), **_HITS}
