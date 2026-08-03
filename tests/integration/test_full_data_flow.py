"""Phase E: the full flow, end to end, in one test.

operator created → file uploaded (raw copy) → LLM extraction →
confirmation → staging insert WITH lineage → pool contribution
(consented) → retraining scheduler check. Plus the gitignore audit:
nothing under the data/pool/checkpoint paths can ever be committed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
import ingestion.extraction_sessions as sessions
from infrastructure.db_manager import DBManager
from infrastructure.operator_registry import OperatorRegistry

REPO = Path(api_main.__file__).resolve().parents[1]

CSV = (
    "Customer,Item,Order Date,Qty Requested,Shipped,Unit Price\n"
    + "\n".join(
        f"City Bistro,Roma Tomatoes,2026-{(i % 5) + 1:02d}-{(i % 27) + 1:02d},"
        f"{100 + i},{95 + i},2.50"
        for i in range(12)   # ≥10 rows → clears the k-anonymity floor
    )
    + "\n"
)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    import infrastructure.operator_registry as orm
    import pool.pool_contributor as pc
    import training.data_accumulator as acc

    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(pc, "DEFAULT_POOL_ROOT", tmp_path / "pool")
    monkeypatch.setattr(sessions, "AUDIT_ROOT", tmp_path / "audit")
    monkeypatch.setattr(acc, "CORPUS_ROOT", tmp_path / "corpus")
    registry = OperatorRegistry(data_root=tmp_path / "data")
    return registry, tmp_path


def test_full_flow_operator_to_pool_to_scheduler(env):
    registry, tmp_path = env
    op = registry.create_operator("Hub A", pool_consent=True,
                                  region="midwest")
    client = TestClient(api_main.app)

    # 1. smart upload → raw copy + extraction session
    r = client.post(f"/intake/extract?operator_id={op.operator_id}",
                    files=[("files", ("orders.csv", CSV, "text/csv"))])
    assert r.status_code == 200
    session = r.json()
    assert session["mock_mode"] is True
    uploads = list((registry.vault_dir(op.operator_id) / "uploads").iterdir())
    assert len(uploads) == 1 and uploads[0].read_text() == CSV

    # 2. confirm → staging insert with lineage + pool contribution
    rows = []
    for er in session["extracted_rows"]:
        f = dict(er["fields"])
        f.setdefault("substituted_quantity", 0)
        rows.append({"row_index": er["row_index"], "table": er["table"],
                     "fields": f, "accepted": True})
    r2 = client.post("/intake/confirm", json={
        "session_id": session["session_id"],
        "operator_id": op.operator_id,
        "rows": rows, "corrections": [],
        "actioned_flag_indices": [er["row_index"]
                                  for er in session["extracted_rows"]
                                  if er["requires_confirmation"]],
    })
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["total_inserted"] == 12

    # lineage on every inserted row
    dbm = DBManager(registry)
    conn = dbm.get_read_only_connection(op.operator_id)
    n_lineage = conn.execute(
        "SELECT COUNT(*) FROM stg_buyer_orders "
        "WHERE _operator_id = ? AND _upload_session_id = ? "
        "AND _source_file IS NOT NULL AND _uploaded_at IS NOT NULL",
        [op.operator_id, session["session_id"]]).fetchone()[0]
    assert n_lineage == 12
    dbm.close_all()

    # 3. pool contribution happened (consented, ≥10 rows)
    assert body["pool_contribution"]["status"] == "contributed"
    assert "demand_patterns" in body["pool_contribution"]["signals_written"]
    from pool.pool_reader import PoolReader
    stats = PoolReader(tmp_path / "pool").get_pool_stats()
    assert stats.n_operators_contributing == 1
    assert stats.n_signals >= 1

    # 4. scheduler sees the new data and makes a gated decision
    from training.retraining_scheduler import RetrainingScheduler
    dbm = DBManager(registry)
    conn = dbm.get_operator_connection(op.operator_id)
    sched = RetrainingScheduler(checkpoints_root=tmp_path / "ckpt",
                                log_path=tmp_path / "retrain.jsonl",
                                corpus_root=tmp_path / "corpus")
    res = sched.run_all_scheduled_retrains(conn)
    dbm.close_all()
    assert set(res) == {"demand", "yield", "extraction"}
    for decision in res.values():
        assert decision["decision"] in ("deployed", "rejected", "skipped",
                                        "blocked", "failed")
    assert (tmp_path / "retrain.jsonl").exists()

    # 5. consent withdrawal stops the next contribution
    from infrastructure.consent_manager import ConsentManager
    from pool.pool_contributor import PoolContributor
    ConsentManager(registry).withdraw_consent(op.operator_id)
    res2 = PoolContributor(registry, tmp_path / "pool").contribute_session(
        op.operator_id)
    assert res2.status == "skipped"


def test_gitignore_covers_all_sensitive_paths():
    """git check-ignore must claim every operator-data path."""
    paths = [
        "data/operators/op_x/harvestmind.db",
        "data/operators/op_x/uploads/f.csv",
        "data/registry/operators.json",
        "pool/signals/demand_patterns/c.parquet",
        "pool/contributions/contribution_log.jsonl",
        "training/audit_log/s/meta.json",
        "training/corpus/corpus_v1.jsonl",
        "training/forecaster_checkpoints/demand/v0001/model.txt",
        "training/extraction_checkpoints/v0001/model.bin",
        "training/retraining_log.jsonl",
        ".env",
    ]
    r = subprocess.run(["git", "check-ignore", *paths],
                       capture_output=True, text=True, cwd=REPO)
    ignored = set(r.stdout.splitlines())
    missing = [p for p in paths if p not in ignored]
    assert not missing, f"NOT gitignored: {missing}"


def test_no_sensitive_files_tracked():
    """Nothing under the sensitive DATA roots is in the git index.

    The roots are data directories, not source packages. This previously
    listed bare "pool", which conflated the pool DATA with the pool CODE:
    pool/pool_contributor.py and pool/pool_reader.py are ordinary source,
    imported by training, the intake router and several tests, and must be
    tracked. Ignoring them made the repository unclonable — a fresh
    checkout raised ModuleNotFoundError — while this test enforced that
    breakage. The sensitive subdirectories are named explicitly instead.
    """
    r = subprocess.run(["git", "ls-files",
                        "data/operators", "data/registry",
                        "pool/contributions", "pool/signals",
                        "training/audit_log", "training/corpus",
                        "training/forecaster_checkpoints",
                        "training/extraction_checkpoints"],
                       capture_output=True, text=True, cwd=REPO)
    assert r.stdout.strip() == "", f"tracked sensitive files:\n{r.stdout}"


def test_pool_source_package_is_tracked():
    """The counterpart guard: pool CODE must be in the index.

    Without this, narrowing the ignore could silently regress and the
    package would drop out of the repository again.
    """
    r = subprocess.run(["git", "ls-files", "pool"],
                       capture_output=True, text=True, cwd=REPO)
    tracked = set(r.stdout.split())
    for required in ("pool/__init__.py", "pool/pool_contributor.py",
                     "pool/pool_reader.py"):
        assert required in tracked, f"{required} is not tracked"
