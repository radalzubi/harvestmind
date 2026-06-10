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
