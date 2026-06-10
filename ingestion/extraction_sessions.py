"""Extraction session store: immutable audit log, PII scrub, snapshots.

Safeguard 5 — every extraction session is logged under
training/audit_log/<session_id>/ and never overwritten. The log doubles
as the training corpus's raw side: source samples, prompt version, raw
LLM response (real mode), parsed result, and the operator's
confirmations and overrides. Mock sessions are logged identically with
mock_mode=True.

Safeguard 6 — PII is scrubbed BEFORE anything is written: email
addresses, phone numbers, and SSN/EIN-shaped numbers are redacted from
all logged text. Anything SSN/EIN-shaped additionally raises a
manual-review flag in the session metadata. Limitation, stated: personal
names cannot be reliably distinguished from company names by regex, so
free-text names are NOT scrubbed wholesale — only values in fields named
like contact_name / contact_email / phone are redacted. Real-name NER is
a known gap, recorded here rather than pretended away.

Safeguard 7 — confirming a session writes session_snapshot.json: the
exact confirmed rows that flowed downstream, so any downstream number
can be traced back to its confirmed input and replayed.

Safeguard 9 — token/cost figures from the engine are persisted with the
session; a session above 2× the median token count of prior sessions is
flagged in its metadata.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ingestion.llm_extractor import ExtractionResult, SourcePayload

AUDIT_ROOT = Path(__file__).resolve().parents[1] / "training" / "audit_log"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
_SSN_EIN_RE = re.compile(r"(?<!\d)(?:\d{3}-\d{2}-\d{4}|\d{2}-\d{7})(?!\d)")
_PII_FIELD_RE = re.compile(r"contact|email|phone", re.IGNORECASE)


def scrub_pii(text: str) -> tuple[str, bool]:
    """Redact emails/phones/SSN-EIN from text. Returns (clean, ssn_seen)."""
    ssn_seen = bool(_SSN_EIN_RE.search(text))
    clean = _EMAIL_RE.sub("[EMAIL_REDACTED]", text)
    clean = _PHONE_RE.sub("[PHONE_REDACTED]", clean)
    clean = _SSN_EIN_RE.sub("[TAXID_REDACTED]", clean)
    return clean, ssn_seen


def _scrub_result(result: ExtractionResult) -> tuple[dict, bool]:
    """Scrub a result for logging: PII-named fields redacted, all string
    values passed through the regex scrub."""
    payload = result.model_dump()
    ssn_flag = False

    def walk(obj: Any) -> Any:
        nonlocal ssn_flag
        if isinstance(obj, str):
            clean, ssn = scrub_pii(obj)
            ssn_flag = ssn_flag or ssn
            return clean
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if isinstance(v, str) and _PII_FIELD_RE.search(str(k)):
                    out[k] = "[PII_FIELD_REDACTED]"
                else:
                    out[k] = walk(v)
            return out
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        return obj

    return walk(payload), ssn_flag


def _session_dir(session_id: str, root: Path | None = None) -> Path:
    d = (root or AUDIT_ROOT) / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _median_tokens(root: Path) -> float | None:
    counts = []
    for meta_file in root.glob("*/meta.json"):
        try:
            t = json.loads(meta_file.read_text()).get("api_tokens")
            if t:
                counts.append(t)
        except Exception:  # noqa: BLE001
            continue
    if not counts:
        return None
    counts.sort()
    return float(counts[len(counts) // 2])


def log_extraction(
    result: ExtractionResult,
    payloads: list[SourcePayload],
    raw_llm_response: str | None,
    root: Path | None = None,
) -> Path:
    """Write the immutable session log (S5). Never overwrites: if the
    session directory already holds a result, a numbered revision file is
    written alongside instead."""
    base = root or AUDIT_ROOT
    d = _session_dir(result.session_id, base)

    scrubbed, ssn_flag = _scrub_result(result)

    # input samples (headers + ≤5 rows), scrubbed
    samples = []
    for p in payloads:
        text, ssn2 = scrub_pii(p.raw_text[:2000]) if p.raw_text else ("", False)
        rows_clean, ssn3 = scrub_pii(json.dumps(p.sample_rows[:5]))
        ssn_flag = ssn_flag or ssn2 or ssn3
        samples.append({
            "filename": p.filename, "kind": p.kind, "headers": p.headers,
            "n_rows": p.n_rows,
            "sample_rows": json.loads(rows_clean),
            "raw_text_sample": text,
        })

    tok = result.summary.estimated_api_tokens or 0
    median = _median_tokens(base)
    token_outlier = bool(median and tok > 2 * median)

    meta = {
        "session_id": result.session_id,
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": result.prompt_version,
        "mock_mode": result.mock_mode,
        "fallback_used": result.fallback_used,
        "source_files": result.source_files,
        "api_tokens": tok,
        "api_cost_usd": result.summary.estimated_api_cost_usd or 0.0,
        "token_outlier_2x_median": token_outlier,   # S9
        "pii_taxid_flag_manual_review": ssn_flag,   # S6
        "status": result.status,
    }

    def _write_once(name: str, content: str) -> None:
        f = d / name
        if f.exists():  # immutability: never overwrite
            n = 1
            while (d / f"{f.stem}.rev{n}{f.suffix}").exists():
                n += 1
            f = d / f"{f.stem}.rev{n}{f.suffix}"
        f.write_text(content)

    _write_once("meta.json", json.dumps(meta, indent=2, default=str))
    _write_once("input_samples.json", json.dumps(samples, indent=2,
                                                 default=str))
    _write_once("result.json", json.dumps(scrubbed, indent=2, default=str))
    if raw_llm_response is not None:
        _write_once("raw_llm_response.txt", scrub_pii(raw_llm_response)[0])
    return d


def load_session(session_id: str, root: Path | None = None) -> dict | None:
    """Load the logged (scrubbed) result for the confirmation UI / API."""
    f = (root or AUDIT_ROOT) / session_id / "result.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


def log_confirmation(
    session_id: str,
    confirmed_rows: list[dict],
    corrections: list[dict],
    root: Path | None = None,
) -> Path:
    """Record the operator's decisions (S5) and write the replay snapshot
    (S7). Corrections are the gold labels the training corpus is built
    from. Append-only: repeated confirmations get numbered files."""
    base = root or AUDIT_ROOT
    d = _session_dir(session_id, base)

    record = {
        "session_id": session_id,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "n_confirmed_rows": len(confirmed_rows),
        "corrections": json.loads(
            scrub_pii(json.dumps(corrections, default=str))[0]),
    }
    n = 0
    f = d / "confirmation.json"
    while f.exists():
        n += 1
        f = d / f"confirmation.rev{n}.json"
    f.write_text(json.dumps(record, indent=2, default=str))

    snapshot = {
        "session_id": session_id,
        "confirmed_at": record["confirmed_at"],
        "rows": json.loads(
            scrub_pii(json.dumps(confirmed_rows, default=str))[0]),
    }
    sf = d / "session_snapshot.json"
    m = 0
    while sf.exists():
        m += 1
        sf = d / f"session_snapshot.rev{m}.json"
    sf.write_text(json.dumps(snapshot, indent=2, default=str))
    return d
