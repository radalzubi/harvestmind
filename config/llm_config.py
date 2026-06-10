"""LLM extraction layer configuration.

The extraction layer runs in MOCK MODE by default: no API key required,
no API calls made, the mock responder exercises the full pipeline with
deterministic synthetic results. Set USE_REAL_LLM=true and inject
ANTHROPIC_API_KEY in .env to activate real Claude API calls.
See docs/LLM_ACTIVATION.md for the full activation checklist, including
setting a spend limit BEFORE flipping the flag.
"""

from __future__ import annotations

import os

USE_REAL_LLM = os.getenv("USE_REAL_LLM", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or None
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "claude-sonnet-4-20250514")
EXTRACTION_PROMPT_VERSION = "EXTRACTION_PROMPT_V1"

# Sonnet pricing used for cost logging ($/M tokens). Update if the model
# in EXTRACTION_MODEL changes price.
INPUT_COST_PER_MTOK = float(os.getenv("LLM_INPUT_COST_PER_MTOK", "3.0"))
OUTPUT_COST_PER_MTOK = float(os.getenv("LLM_OUTPUT_COST_PER_MTOK", "15.0"))

# Confidence policy (structured sources). Unstructured sources use the
# stricter floor in ingestion/llm_extractor.py.
AUTO_ACCEPT_CONFIDENCE = 0.90
REVIEW_CONFIDENCE = 0.70
OVERALL_CONFIDENCE_FLOOR = 0.65
UNSTRUCTURED_AUTO_ACCEPT = 0.95


def check_real_llm_config() -> None:
    """Fail loudly if real-LLM mode is enabled without a key.

    Called at import of the extraction engine and at API startup — never
    silently fall back when the operator believes real extraction is on.
    """
    if USE_REAL_LLM and not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "USE_REAL_LLM is True but ANTHROPIC_API_KEY is not set. "
            "Add your key to .env before activating real LLM extraction. "
            "Get your key at console.anthropic.com. Set a spend limit "
            "before use (console.anthropic.com → Billing)."
        )


check_real_llm_config()
