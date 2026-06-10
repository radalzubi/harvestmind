"""Versioned model registry with deploy / rollback and a retrain log.

What "keeps getting smarter" actually means here: models are REFIT on
accumulated data on a schedule, and a refit is deployed only if it beats
the current production model out-of-sample. Nothing updates itself
autonomously online; every change is logged, versioned, and reversible.

Layout (one registry per model family):

    <root>/<family>/
        v0001/ ... v000N/      artifacts + metrics.json per version
        CURRENT                file containing the deployed version name
        retrain_log.jsonl      one JSON line per retrain decision
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ModelRegistry:
    def __init__(self, root: str | Path, family: str) -> None:
        self.dir = Path(root) / family
        self.dir.mkdir(parents=True, exist_ok=True)

    # ── versions ─────────────────────────────────────────────────────────

    def versions(self) -> list[str]:
        return sorted(p.name for p in self.dir.iterdir()
                      if p.is_dir() and p.name.startswith("v"))

    def new_version_dir(self) -> Path:
        n = len(self.versions()) + 1
        d = self.dir / f"v{n:04d}"
        d.mkdir(parents=True, exist_ok=False)
        return d

    def version_dir(self, version: str) -> Path:
        return self.dir / version

    # ── current pointer ──────────────────────────────────────────────────

    @property
    def current(self) -> str | None:
        f = self.dir / "CURRENT"
        if not f.exists():
            return None
        name = f.read_text().strip()
        return name if name in self.versions() else None

    def deploy(self, version: str) -> None:
        if version not in self.versions():
            raise ValueError(f"unknown version {version!r}")
        (self.dir / "CURRENT").write_text(version)

    def rollback(self) -> str | None:
        """Redeploy the version before the current one. Returns the new
        current version, or None if there is nothing to roll back to."""
        vs = self.versions()
        cur = self.current
        if cur is None or cur not in vs:
            return None
        idx = vs.index(cur)
        if idx == 0:
            return None
        prev = vs[idx - 1]
        self.deploy(prev)
        self.log({"event": "rollback", "from": cur, "to": prev})
        return prev

    # ── metrics + log ────────────────────────────────────────────────────

    def write_metrics(self, version: str, metrics: dict[str, Any]) -> None:
        (self.version_dir(version) / "metrics.json").write_text(
            json.dumps(metrics, indent=2, default=str))

    def read_metrics(self, version: str) -> dict[str, Any] | None:
        f = self.version_dir(version) / "metrics.json"
        return json.loads(f.read_text()) if f.exists() else None

    def log(self, entry: dict[str, Any]) -> None:
        entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
        with (self.dir / "retrain_log.jsonl").open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def log_entries(self) -> list[dict[str, Any]]:
        f = self.dir / "retrain_log.jsonl"
        if not f.exists():
            return []
        return [json.loads(line) for line in f.read_text().splitlines()
                if line.strip()]
