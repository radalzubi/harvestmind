"""Extraction model training — wires the gated fine-tuning stub into the
unified pipeline. The 50-session minimum and the quality checks live in
training/finetune_pipeline.py / quality_checker.py; promotion goes
through the shared model registry (family="extraction") with the same
beat-the-incumbent-on-ALL-metrics rule and one-call rollback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from training.quality_checker import (
    MIN_SESSIONS_FOR_FINETUNING,
    check_corpus,
)

NEW_SESSIONS_RETRAIN_THRESHOLD = 20


def extraction_training_status(corpus_root: Path | None = None) -> dict[str, Any]:
    quality = check_corpus(corpus_root)
    return {
        "model": "extraction",
        "corpus_usable_sessions": quality["usable_sessions"],
        "min_required": MIN_SESSIONS_FOR_FINETUNING,
        "gate_open": quality["fine_tuning_gate_open"],
        "verdict": quality["verdict"],
    }


def retrain_extraction(corpus_root: Path | None = None) -> dict[str, Any]:
    """Attempt an extraction fine-tune. Returns the decision dict; the
    NotImplementedError from the stub is converted into an honest
    'blocked' decision for the scheduler log."""
    from training.finetune_pipeline import run_finetuning

    try:
        return run_finetuning(root=corpus_root)
    except NotImplementedError as e:
        return {"model": "extraction", "decision": "blocked",
                "reason": str(e)}
