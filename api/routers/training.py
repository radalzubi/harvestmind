"""Training corpus stats API."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/corpus/stats")
def training_corpus_stats():
    """Corpus size, composition, and distance to the fine-tuning gate."""
    from training.data_accumulator import corpus_stats
    from training.quality_checker import check_corpus

    return {"stats": corpus_stats(), "quality": check_corpus()}


@router.get("/status")
def training_status(conn=None):
    """Admin: model versions, last retrains, data-to-next-retrain, pool size."""
    import duckdb
    from api.dependencies import get_db_path
    from training.retraining_scheduler import RetrainingScheduler

    conn = duckdb.connect(get_db_path(), read_only=True)
    try:
        return RetrainingScheduler().get_training_status(conn).model_dump()
    finally:
        conn.close()


@router.post("/retrain")
def run_retrains():
    """Admin: manual scheduled-retrain pass (each model keeps its own
    validation gate; nothing deploys without beating its incumbent)."""
    import duckdb
    from api.dependencies import get_db_path
    from training.retraining_scheduler import RetrainingScheduler

    conn = duckdb.connect(get_db_path())
    try:
        return RetrainingScheduler().run_all_scheduled_retrains(conn)
    finally:
        conn.close()
