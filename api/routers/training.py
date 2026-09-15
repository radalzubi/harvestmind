"""Training corpus stats API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.routers.admin import require_admin

router = APIRouter(
    prefix="/training",
    tags=["training"],
    dependencies=[Depends(require_admin)],
)


@router.get("/corpus/stats")
def training_corpus_stats():
    """Corpus size, composition, and distance to the fine-tuning gate."""
    from training.data_accumulator import corpus_stats
    from training.quality_checker import check_corpus

    return {"stats": corpus_stats(), "quality": check_corpus()}


@router.get("/status")
def training_status(conn=None):
    """Admin: model versions, last retrains, data-to-next-retrain, pool size."""
    from api.dependencies import get_db_path
    from infrastructure.db_manager import vault_cursor
    from training.retraining_scheduler import RetrainingScheduler

    conn = vault_cursor(get_db_path())
    try:
        return RetrainingScheduler().get_training_status(conn).model_dump()
    finally:
        conn.close()


@router.post("/retrain")
def run_retrains():
    """Admin: manual scheduled-retrain pass (each model keeps its own
    validation gate; nothing deploys without beating its incumbent)."""
    from api.dependencies import get_db_path
    from infrastructure.db_manager import vault_cursor
    from training.retraining_scheduler import RetrainingScheduler

    conn = vault_cursor(get_db_path())
    try:
        return RetrainingScheduler().run_all_scheduled_retrains(conn)
    finally:
        conn.close()
