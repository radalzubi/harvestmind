"""Unified retraining scheduler — all three models, one gated loop.

Thresholds (new data since the last DEPLOYED retrain):
    demand forecaster   > 100 new confirmed orders
    yield model         > 50 new confirmed deliveries
    extraction model    corpus ≥ 50 sessions (first run), then > 20 new

Every attempt — run, skipped, deployed, rejected, failed — lands in
training/retraining_log.jsonl. Each model keeps its own validation gate
(holdout WAPE for demand, coverage error for yield, the corpus gate for
extraction); the scheduler never deploys anything itself and never
raises — a failed retrain is a log entry, not an outage.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import cast, Any

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = REPO_ROOT / "training" / "retraining_log.jsonl"
DEFAULT_CHECKPOINTS = REPO_ROOT / "training" / "forecaster_checkpoints"

THRESHOLDS = {
    "demand": {"metric": "new_orders", "min_new": 100},
    "yield": {"metric": "new_deliveries", "min_new": 50},
    "extraction": {"metric": "new_sessions", "min_new": 20},
}


class TrainingStatus(BaseModel):
    models: dict[str, dict[str, Any]]
    pool: dict[str, Any]
    log_path: str


class RetrainingScheduler:
    def _corpus_path(self):
        from pathlib import Path
        return Path(self.corpus_root) if self.corpus_root else None

    def __init__(
        self,
        checkpoints_root: str | Path | None = None,
        log_path: str | Path | None = None,
        corpus_root: str | Path | None = None,
    ) -> None:
        self.checkpoints_root = Path(checkpoints_root) \
            if checkpoints_root else DEFAULT_CHECKPOINTS
        self.log_path = Path(log_path) if log_path else DEFAULT_LOG
        self.corpus_root = corpus_root

    # ── log ──────────────────────────────────────────────────────────────

    def _log(self, entry: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"at": datetime.now(timezone.utc).isoformat(), **entry}
        with self.log_path.open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def _log_entries(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text().splitlines()
                if line.strip()]

    def _counts_at_last_deploy(self, model: str) -> dict[str, int]:
        for e in reversed(self._log_entries()):
            if e.get("model") == model and e.get("decision") == "deployed":
                return e.get("data_counts", {})
        return {}

    # ── data counts ──────────────────────────────────────────────────────

    @staticmethod
    def _current_counts(conn) -> dict[str, int]:
        def _n(table: str) -> int:
            try:
                return int(conn.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            except Exception:  # noqa: BLE001
                return 0
        return {"new_orders": _n("stg_buyer_orders"),
                "new_deliveries": _n("stg_supplier_deliveries")}

    def _new_since_deploy(self, model: str, current: dict[str, int]) -> int:
        metric = str(THRESHOLDS[model]["metric"])
        if model == "extraction":
            from training.quality_checker import check_corpus
            usable = int(check_corpus(self._corpus_path())["usable_sessions"])
            last = int(dict(self._counts_at_last_deploy(model)).get("usable_sessions", 0))
            return usable - last
        last = int(dict(self._counts_at_last_deploy(model)).get(metric, 0))
        return int(current.get(metric, 0)) - last

    # ── the loop ─────────────────────────────────────────────────────────

    def run_all_scheduled_retrains(self, conn) -> dict[str, Any]:
        """One scheduled pass. Never raises."""
        results: dict[str, Any] = {}
        current = self._current_counts(conn)

        for model in ("demand", "yield", "extraction"):
            try:
                new_n = self._new_since_deploy(model, current)
                threshold = int(cast(int, THRESHOLDS[model]["min_new"]))
                if model == "extraction":
                    from training.quality_checker import (
                        MIN_SESSIONS_FOR_FINETUNING, check_corpus,
                    )
                    usable = check_corpus(self._corpus_path())["usable_sessions"]
                    first_run = not any(
                        e.get("model") == model and
                        e.get("decision") == "deployed"
                        for e in self._log_entries())
                    ready = (usable >= MIN_SESSIONS_FOR_FINETUNING
                             if first_run else new_n > int(threshold))
                else:
                    ready = new_n > threshold

                if not ready:
                    decision = {"model": model, "decision": "skipped",
                                "reason": f"insufficient new data "
                                          f"({new_n} new, need "
                                          f"> {threshold})",
                                "data_counts": current}
                    self._log(decision)
                    results[model] = decision
                    continue

                decision = self._retrain(model, conn)
                decision["data_counts"] = {
                    **current,
                    "usable_sessions": (self._usable_sessions()
                                        if model == "extraction" else 0),
                }
                self._log({"model": model, **decision})
                results[model] = decision
            except Exception as e:  # noqa: BLE001  log, never raise
                decision = {"model": model, "decision": "failed",
                            "error": f"{type(e).__name__}: {e}"}
                self._log(decision)
                results[model] = decision
        return results

    def _usable_sessions(self) -> int:
        from training.quality_checker import check_corpus
        return check_corpus(self._corpus_path())["usable_sessions"]

    def _retrain(self, model: str, conn) -> dict[str, Any]:
        if model == "demand":
            from retraining.pipeline import retrain_demand
            return retrain_demand(conn, self.checkpoints_root)
        if model == "yield":
            from retraining.pipeline import retrain_yield
            return retrain_yield(conn, self.checkpoints_root)
        from training.extraction_trainer import retrain_extraction
        return retrain_extraction(self._corpus_path())

    # ── status (dashboard / admin) ───────────────────────────────────────

    def get_training_status(self, conn) -> TrainingStatus:
        from retraining.registry import ModelRegistry
        from training.extraction_trainer import extraction_training_status

        current = self._current_counts(conn)
        models: dict[str, dict[str, Any]] = {}
        for model in ("demand", "yield"):
            reg = ModelRegistry(self.checkpoints_root, model)
            last_deploy = next(
                (e for e in reversed(self._log_entries())
                 if e.get("model") == model
                 and e.get("decision") == "deployed"), None)
            new_n = self._new_since_deploy(model, current)
            models[model] = {
                "current_version": reg.current,
                "last_retrain": (last_deploy or {}).get("at"),
                "new_data_since_retrain": new_n,
                "retrain_threshold": int(cast(int, THRESHOLDS[model]["min_new"])),
                "new_data_needed": max(
                    0, int(cast(int, THRESHOLDS[model]["min_new"])) + 1 - new_n),
            }
        models["extraction"] = extraction_training_status(self._corpus_path())

        try:
            from pool.pool_reader import PoolReader
            pool = PoolReader().get_pool_stats().model_dump()
        except Exception:  # noqa: BLE001
            pool = {}
        return TrainingStatus(models=models, pool=pool,
                              log_path=str(self.log_path))
