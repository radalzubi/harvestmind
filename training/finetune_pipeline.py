"""Fine-tuning pipeline — STUBBED until the corpus earns it.

Converts the confirmed-session corpus into instruction-tuning format and
holds the promotion gate. The actual fine-tuning call is deliberately
NotImplemented until >= 50 usable real sessions exist: training a
domain model on a handful of examples would produce confident noise.

Provider-agnostic: the same instruction format serves the Anthropic
fine-tuning API or an open-weights run (Llama 3 / Mistral via Hugging
Face) — pick via the `provider` parameter when the gate opens.

Promotion rule (mirrors retraining/pipeline.py): a fine-tuned extraction
model is registered in the shared model registry (family="extraction")
and promoted ONLY if it beats the incumbent prompt-based extractor on
ALL evaluation metrics on a held-out split. Rollback is one call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from training.quality_checker import (
    MIN_SESSIONS_FOR_FINETUNING,
    usable_entries,
)

TRAIN_SPLIT = 0.80


def to_instruction_format(
    root: Path | None = None,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    """Corpus → instruction-tuning examples.

    {"system": <extraction prompt>, "user": <raw input>,
     "assistant": <the operator-corrected clean output>}
    The assistant target is the FINAL clean output — what the model
    should have produced — not its original attempt.
    """
    import json

    if system_prompt is None:
        from ingestion.llm_extractor import SYSTEM_PROMPT
        system_prompt = SYSTEM_PROMPT

    examples = []
    for e in usable_entries(root):
        examples.append({
            "system": system_prompt,
            "user": e.get("raw_input_sample", ""),
            "assistant": json.dumps(e.get("final_clean_output", {}),
                                    default=str),
        })
    return examples


def train_val_split(
    examples: list[dict[str, str]],
    entries: list[dict[str, Any]] | None = None,
    root: Path | None = None,
) -> tuple[list[dict], list[dict]]:
    """80/20 split, stratified by operator so no operator's style exists
    only in validation (or only in training)."""
    entries = entries if entries is not None else usable_entries(root)
    by_operator: dict[str, list[int]] = {}
    for i, e in enumerate(entries):
        by_operator.setdefault(str(e.get("operator_id", "default")),
                               []).append(i)
    train_idx: set[int] = set()
    for idxs in by_operator.values():
        cut = max(int(len(idxs) * TRAIN_SPLIT), 1) if len(idxs) > 1 \
            else len(idxs)
        train_idx.update(idxs[:cut])
    train = [examples[i] for i in sorted(train_idx) if i < len(examples)]
    val = [examples[i] for i in range(len(examples))
           if i not in train_idx]
    return train, val


def run_finetuning(
    provider: str = "anthropic",
    root: Path | None = None,
) -> dict[str, Any]:
    """Fire a fine-tuning run. GATED: raises until the corpus is ready.

    # TODO: activate when corpus >= 50 confirmed sessions
    # See docs/LLM_ACTIVATION.md for the activation checklist
    """
    corpus_size = len(usable_entries(root))
    if corpus_size < MIN_SESSIONS_FOR_FINETUNING:
        raise NotImplementedError(
            f"Fine-tuning requires >= {MIN_SESSIONS_FOR_FINETUNING} "
            f"confirmed sessions. Current corpus: {corpus_size} sessions. "
            f"Keep collecting operator data."
        )
    # When the gate opens, the implementation here:
    # 1. examples = to_instruction_format(root)
    # 2. train, val = train_val_split(examples)
    # 3. dispatch to the provider's fine-tuning API
    # 4. evaluate candidate vs incumbent on val — ALL metrics must improve
    # 5. register in retraining.registry.ModelRegistry(root, "extraction"),
    #    deploy only on a clean sweep, keep rollback one call away
    raise NotImplementedError(
        f"Corpus gate open ({corpus_size} sessions) but the {provider} "
        f"fine-tuning dispatch is not yet implemented — implement steps "
        f"1-5 in run_finetuning before promoting any model."
    )
