"""Decision audit trail: enough to reproduce a run, nothing sensitive.

Every optimization run gets a record with the run id, timestamp, operator,
model and solver versions, the configuration, a hash of the inputs, the
seed and scenario configuration, the solver outcome, the objective
breakdown and the warnings. The record is written as a JSON sidecar under
the data root and, when a connection is given and the table exists, into
``optimization_run_log``. Customer datasets are never stored here, only
their hash.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

MODEL_VERSION = "multi_period_sp/2.0-discrete"


def _hash_frame(obj) -> str:
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            return hashlib.sha256(pd.util.hash_pandas_object(obj, index=False).values.tobytes()).hexdigest()
    except Exception:  # noqa: BLE001
        pass
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _solver_version() -> str:
    try:
        import highspy
        return f"highs {getattr(highspy, '__version__', 'unknown')}"
    except Exception:  # noqa: BLE001
        return "unknown"


@dataclass
class RunRecord:
    run_id: str
    timestamp: str
    operator_id: str | None
    user_id: str | None
    domain: str
    model_version: str
    solver_version: str
    config: dict
    input_hashes: dict
    seed: int | None
    scenario_config: dict
    status: str
    usable: bool
    objective: float | None
    objective_breakdown: dict
    gap: float | None
    runtime_s: float | None
    warnings: list = field(default_factory=list)
    python: str = platform.python_version()

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1, default=str)


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def record_run(*, domain: str, config: dict, inputs: dict, result: dict,
               operator_id: str | None = None, user_id: str | None = None,
               seed: int | None = None, scenario_config: dict | None = None,
               objective_breakdown: dict | None = None, conn=None,
               data_root: str | Path | None = None) -> RunRecord:
    rec = RunRecord(
        run_id=result.get("run_id") or new_run_id(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        operator_id=operator_id, user_id=user_id, domain=domain,
        model_version=MODEL_VERSION, solver_version=_solver_version(),
        config={k: v for k, v in config.items() if k not in ("model",)},
        input_hashes={k: _hash_frame(v) for k, v in inputs.items()},
        seed=seed, scenario_config=scenario_config or {},
        status=str(result.get("status")), usable=bool(result.get("usable", False)),
        objective=result.get("objective"), objective_breakdown=objective_breakdown or {},
        gap=result.get("gap"), runtime_s=result.get("runtime_s"),
        warnings=list(result.get("warnings", [])))
    root = Path(data_root or os.getenv("HARVESTMIND_DATA_ROOT", "data")) / "runs"
    try:
        root.mkdir(parents=True, exist_ok=True)
        (root / f"{rec.run_id}.json").write_text(rec.to_json())
    except OSError:
        pass
    if conn is not None:
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info('optimization_run_log')").fetchall()}
            if {"run_id"} <= cols:
                payload = {"run_id": rec.run_id}
                for c, v in (("model_type", rec.model_version), ("solver_status", rec.status),
                             ("objective_value", rec.objective), ("solve_time_s", rec.runtime_s),
                             ("run_timestamp", rec.timestamp), ("config_json", json.dumps(rec.config)),
                             ("warnings_json", json.dumps(rec.warnings))):
                    if c in cols:
                        payload[c] = v
                keys = ", ".join(payload)
                conn.execute(f"INSERT INTO optimization_run_log ({keys}) VALUES ({', '.join('?' * len(payload))})",  # nosec B608 - columns from PRAGMA
                             list(payload.values()))
        except Exception:  # noqa: BLE001  the sidecar is the durable record
            pass
    return rec
