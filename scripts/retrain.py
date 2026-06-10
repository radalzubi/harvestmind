"""Scheduled retraining entry point.

Run on a schedule (cron example below). Each run refits both forecasters
on accumulated staged data and deploys a refit ONLY if it beats the
current production model on a holdout. Decisions are versioned and
logged under the registry; a bad deploy is reversible with rollback().

    # crontab: retrain Mondays at 02:00, log to file
    0 2 * * 1 cd /path/to/harvestmind && python3 -m scripts.retrain >> outputs/retrain.log 2>&1
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parents[1] / "harvestmind.duckdb"
REGISTRY_ROOT = Path(__file__).resolve().parents[1] / "outputs" / "model_registry"


def main() -> None:
    from retraining.pipeline import retrain_all

    conn = duckdb.connect(str(DB_PATH))
    try:
        result = retrain_all(conn, REGISTRY_ROOT)
    finally:
        conn.close()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
