"""Training-corpus quality gate — runs BEFORE any fine-tuning attempt.

A model trained on a bad corpus is worse than no model: duplicated
sessions overweight one operator's quirks, contradictory labels teach
noise, and a corpus dominated by one correction type produces a model
that only knows one trick. Every check reports what it excluded and why.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from training.data_accumulator import load_corpus

MIN_SESSIONS_FOR_FINETUNING = 50
CLASS_BALANCE_MAX_SHARE = 0.80


def _input_hash(entry: dict) -> str:
    return hashlib.md5(
        (str(entry.get("operator_id")) +
         str(entry.get("raw_input_sample"))).encode()).hexdigest()


def check_corpus(root: Path | None = None) -> dict[str, Any]:
    """Quality report over the corpus. Mock sessions are excluded from
    training counts up front."""
    entries = load_corpus(root)
    real = [e for e in entries if not e.get("mock_mode")]

    # 1. Label consistency FIRST, across ALL entries (pre-dedup): the same
    # (input, field) corrected to two different targets is contradictory —
    # running dedup first would keep only the latest and hide a session
    # that contradicts its own duplicate. Conflicted inputs are excluded
    # entirely.
    label_map: dict[tuple[str, str], set[str]] = {}
    for e in real:
        h = _input_hash(e)
        for c in e.get("operator_corrections", []):
            key = (h, str(c.get("field")))
            label_map.setdefault(key, set()).add(
                str(c.get("operator_corrected")))
    conflicted_inputs = {key[0] for key, labels in label_map.items()
                         if len(labels) > 1}
    consistent_pool = [e for e in real
                       if _input_hash(e) not in conflicted_inputs]

    # 2. Deduplicate same-input same-operator uploads (keep latest)
    seen: dict[str, dict] = {}
    duplicates = 0
    for e in consistent_pool:
        h = _input_hash(e)
        if h in seen:
            duplicates += 1
        seen[h] = e
    consistent = list(seen.values())
    excluded_for_conflict = len({_input_hash(e) for e in real}
                                & conflicted_inputs)

    # 3. Class balance across correction types
    by_type: dict[str, int] = {}
    for e in consistent:
        for c in e.get("operator_corrections", []):
            t = c.get("correction_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
    total_corr = sum(by_type.values())
    imbalance_warning = None
    if total_corr > 0:
        top_type, top_n = max(by_type.items(), key=lambda kv: kv[1])
        if top_n / total_corr > CLASS_BALANCE_MAX_SHARE:
            imbalance_warning = (
                f"{top_type} is {top_n / total_corr:.0%} of all corrections "
                f"(> {CLASS_BALANCE_MAX_SHARE:.0%}) — the model would mostly "
                f"learn one correction type; collect more varied sessions")

    usable = len(consistent)
    gate_open = usable >= MIN_SESSIONS_FOR_FINETUNING

    return {
        "total_entries": len(entries),
        "mock_excluded": len(entries) - len(real),
        "duplicates_removed": duplicates,
        "label_conflicts_excluded": excluded_for_conflict,
        "usable_sessions": usable,
        "corrections_by_type": by_type,
        "class_imbalance_warning": imbalance_warning,
        "min_sessions_required": MIN_SESSIONS_FOR_FINETUNING,
        "fine_tuning_gate_open": gate_open,
        "verdict": ("corpus ready for a fine-tuning run"
                    if gate_open and not imbalance_warning else
                    f"fine-tuning blocked: {usable}/"
                    f"{MIN_SESSIONS_FOR_FINETUNING} usable sessions"
                    + (f"; {imbalance_warning}" if imbalance_warning else "")),
    }


def usable_entries(root: Path | None = None) -> list[dict[str, Any]]:
    """The deduplicated, conflict-free, real-mode entries — what a
    fine-tuning run is allowed to see."""
    entries = [e for e in load_corpus(root) if not e.get("mock_mode")]
    # conflicts detected across ALL entries first (see check_corpus)
    label_map: dict[tuple[str, str], set[str]] = {}
    for e in entries:
        h = _input_hash(e)
        for c in e.get("operator_corrections", []):
            key = (h, str(c.get("field")))
            label_map.setdefault(key, set()).add(
                str(c.get("operator_corrected")))
    conflicted = {k[0] for k, v in label_map.items() if len(v) > 1}
    seen: dict[str, dict] = {}
    for e in entries:
        if _input_hash(e) not in conflicted:
            seen[_input_hash(e)] = e
    return list(seen.values())
