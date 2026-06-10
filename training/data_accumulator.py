"""Training-data accumulator: every confirmed session becomes a labeled
example.

The operator's corrections are the gold labels: each one says "the model
predicted X, the human who owns this data said Y." Accumulated across
sessions they become the fine-tuning corpus for a domain-specific
extraction model.

Corpus format: training/corpus/corpus_v1.jsonl — append-only, one JSON
object per confirmed session, never overwritten. A new corpus VERSION
(corpus_v2.jsonl) is only created deliberately (schema change), never by
this module on its own.

PII: everything written here passes the same scrub as the audit log.
Mock-mode sessions are recorded with mock_mode=true so the quality
checker can exclude them from real fine-tuning runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CORPUS_ROOT = Path(__file__).resolve().parent / "corpus"
CORPUS_VERSION = "corpus_v1"


def _corpus_file(root: Path | None = None) -> Path:
    d = root or CORPUS_ROOT
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{CORPUS_VERSION}.jsonl"


def record_confirmed_session(
    session_id: str,
    *,
    mock_mode: bool,
    prompt_version: str,
    raw_input_sample: str,
    llm_response: dict | str | None,
    operator_corrections: list[dict[str, Any]],
    final_clean_output: dict[str, Any],
    operator_id: str = "default",
    root: Path | None = None,
) -> Path:
    """Append one confirmed session to the corpus (PII-scrubbed)."""
    from ingestion.extraction_sessions import scrub_pii

    entry = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operator_id": operator_id,
        "mock_mode": mock_mode,
        "prompt_version": prompt_version,
        "raw_input_sample": scrub_pii(raw_input_sample[:4000])[0],
        "llm_response": json.loads(scrub_pii(
            json.dumps(llm_response, default=str))[0])
        if llm_response is not None else None,
        "operator_corrections": json.loads(scrub_pii(
            json.dumps(operator_corrections, default=str))[0]),
        "final_clean_output": json.loads(scrub_pii(
            json.dumps(final_clean_output, default=str))[0]),
    }
    f = _corpus_file(root)
    with f.open("a") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")
    return f


def load_corpus(root: Path | None = None) -> list[dict[str, Any]]:
    f = _corpus_file(root)
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text().splitlines()
            if line.strip()]


def corpus_stats(root: Path | None = None) -> dict[str, Any]:
    """Corpus size and composition — GET /training/corpus/stats."""
    entries = load_corpus(root)
    real = [e for e in entries if not e.get("mock_mode")]
    corrections = [c for e in entries
                   for c in e.get("operator_corrections", [])]
    by_type: dict[str, int] = {}
    for c in corrections:
        t = c.get("correction_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "corpus_version": CORPUS_VERSION,
        "total_sessions": len(entries),
        "real_sessions": len(real),
        "mock_sessions": len(entries) - len(real),
        "total_corrections": len(corrections),
        "corrections_by_type": by_type,
        "fine_tuning_threshold": 50,
        "sessions_until_fine_tuning": max(0, 50 - len(real)),
        "note": "fine-tuning unlocks at 50 REAL confirmed sessions; mock "
                "sessions exercise the pipeline but never train a model",
    }
