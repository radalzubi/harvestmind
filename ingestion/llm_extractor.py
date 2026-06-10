"""LLM data extraction engine — messy operator files → 5-table staging schema.

Sits UPSTREAM of the existing Layer-1 ingestion: whatever the operator
uploads (CSV, Excel, PDF, JSON, text, message logs) is read here, mapped
to the migration-010 staging schema, and returned as an ExtractionResult
for the confirmation UI. Nothing flows downstream until the operator
confirms; confirmed rows still pass the existing hard validators before
insert. This layer is translation + confirmation, nothing else.

MOCK MODE (default): config.llm_config.USE_REAL_LLM is False, so every
"extraction" is produced by ingestion/llm_mock_responder.py — a
deterministic alias/fuzzy mapper that returns realistic results with
confidence spread, flags, and derivations, without any API call. The
interface is identical either way; downstream code never knows which ran.
Set USE_REAL_LLM=true + ANTHROPIC_API_KEY to activate real Claude calls
(docs/LLM_ACTIVATION.md — set a spend limit first).

Schema note: this targets the REAL migration-010 staging tables
(stg_products is the 5th table). Supplier master data (contacts, payment
terms) has no staging home today; when a source contains it, the result
flags it under schema_gaps instead of inventing a table.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field

from config.llm_config import (
    ANTHROPIC_API_KEY,
    AUTO_ACCEPT_CONFIDENCE,
    EXTRACTION_MODEL,
    EXTRACTION_PROMPT_VERSION,
    INPUT_COST_PER_MTOK,
    OUTPUT_COST_PER_MTOK,
    OVERALL_CONFIDENCE_FLOOR,
    REVIEW_CONFIDENCE,
    USE_REAL_LLM,
)

# ── The real target schema (migration 010) ──────────────────────────────────

TARGET_SCHEMA: dict[str, list[str]] = {
    "stg_products": [
        "product_id", "product_name", "category", "unit",
        "default_shelf_life_days", "traceability_required",
    ],
    "stg_supplier_deliveries": [
        "delivery_id", "supplier_id", "supplier_name", "product_id",
        "product_name", "delivery_date", "ordered_quantity",
        "delivered_quantity", "accepted_quantity", "rejected_quantity",
        "unit_cost", "quality_grade", "lot_id",
    ],
    "stg_inventory_lots": [
        "lot_id", "product_id", "product_name", "supplier_id",
        "quantity_on_hand", "unit", "arrival_date", "expiration_date",
        "warehouse_location", "quality_grade", "committed_quantity",
    ],
    "stg_buyer_orders": [
        "order_id", "buyer_id", "buyer_name", "product_id", "product_name",
        "order_date", "delivery_date", "requested_quantity",
        "fulfilled_quantity", "substituted_quantity", "sales_price",
        "required_quality_grade",
    ],
    "stg_waste_adjustments": [
        "adjustment_id", "date", "product_id", "product_name", "lot_id",
        "quantity_lost", "reason", "estimated_value_lost",
    ],
}

# Fields that matter most for downstream math; used for the schema-
# sufficiency safeguard (S3).
REQUIRED_FIELDS: dict[str, list[str]] = {
    "stg_products": ["product_name"],
    "stg_supplier_deliveries": ["product_name", "delivery_date",
                                "ordered_quantity", "accepted_quantity"],
    "stg_inventory_lots": ["product_name", "quantity_on_hand",
                           "expiration_date"],
    "stg_buyer_orders": ["product_name", "requested_quantity",
                         "fulfilled_quantity", "delivery_date"],
    "stg_waste_adjustments": ["product_name", "quantity_lost"],
}

SYSTEM_PROMPT = f"""\
You are HarvestMind's data extraction specialist for US fresh-produce
distribution operations. Your job is to read messy operator data and
extract clean structured records matching HarvestMind's 5-table staging
schema exactly.

THE SCHEMA (field names must match exactly):
{json.dumps(TARGET_SCHEMA, indent=2)}

You know produce distribution deeply:
- Orders come from institutional buyers: restaurants, hotels, schools,
  hospitals, foodservice companies
- Deliveries come from farms, produce suppliers, and wholesalers
- Products are perishable: tomatoes, leafy greens, berries, roots,
  citrus, herbs, stone fruit, brassicas etc.
- Units: kg, lb, case (note case weight if inferable), unit, bunch, crate
- Missed fulfillment = requested_quantity − fulfilled_quantity −
  substituted_quantity (computed downstream; never invent a column for it,
  but DO flag rows where it is implied)
- Rejections happen at delivery: quality failure, wrong spec, short
  weight, temperature breach
- lot_id, expiration_date, arrival_date are FSMA-204 critical fields —
  extract these with high priority
- unit_cost = what the operator PAID the supplier (stg_supplier_deliveries)
- sales_price = what the operator CHARGED the buyer (stg_buyer_orders)
- These are different and must never be swapped
- Supplier master data (contact names, emails, payment terms) has NO
  staging table — report it under schema_gaps, do not force it into a table

Common column aliases you will encounter:
  ordered / requested / PO qty / units ordered → requested_quantity or ordered_quantity
  shipped / delivered / fulfilled / sent / invoiced → fulfilled_quantity or delivered_quantity
  accepted / received / good / net / usable → accepted_quantity
  rejected / returned / refused / short / damaged → rejected_quantity
  price / rate / cost / unit price / each → unit_cost or sales_price (determine from context)
  invoice date / ship date / delivery date / date sent → delivery_date
  order date / PO date / request date → order_date
  expiry / best by / use by / bb date / sell by → expiration_date
  lot / batch / lot# / batch# / trace id → lot_id
  on hand / in stock / available / qoh → quantity_on_hand
  spoiled / dumped / shrink / loss / culled → quantity_lost

Rules you must follow without exception:
1. NEVER invent data. If a value is not present in the source, mark it null.
2. NEVER guess a product_id or supplier_id — generate a slug from the name,
   flag for operator confirmation.
3. NEVER silently resolve ambiguity. Flag it.
4. If a column could map to two fields, output BOTH as candidates and flag
   confidence.
5. If a quantity is missing but mathematically inferable (e.g. ordered=100,
   delivered=80, no missed column) — infer it and set
   inference_source="derived: <the exact arithmetic>".
6. If units are inconsistent across rows — normalize to kg, flag each
   conversion.
7. Dates: normalize to ISO 8601. If the format is ambiguous (01/02/03),
   flag with both interpretations, do not guess.
8. If a file has no matching fields for a table, return empty for that
   table. Do not hallucinate rows.
9. Return ONLY valid JSON matching the ExtractionResult structure. No
   prose, no markdown fences, no explanation outside the JSON.
"""


# ── Pydantic models ──────────────────────────────────────────────────────────

class FieldMeta(BaseModel):
    confidence: float
    inference_source: str
    requires_confirmation: bool
    flag_reason: Optional[str] = None


class FieldMapping(BaseModel):
    source_column: str
    target_field: str
    confidence: float
    reasoning: str
    alternative_mapping: Optional[str] = None


class ExtractedRow(BaseModel):
    row_index: int
    table: str
    fields: dict[str, Any]
    field_metadata: dict[str, FieldMeta] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    rejected: bool = False
    rejection_reason: Optional[str] = None


class ExtractionSummary(BaseModel):
    total_rows: int = 0
    auto_accepted: int = 0
    flagged_for_review: int = 0
    rejected: int = 0
    tables_found: list[str] = Field(default_factory=list)
    tables_missing: list[str] = Field(default_factory=list)
    schema_coverage_pct: float = 0.0
    overall_confidence: float = 0.0
    estimated_api_tokens: Optional[int] = None
    estimated_api_cost_usd: Optional[float] = None


class ExtractionResult(BaseModel):
    session_id: str
    source_files: list[str]
    column_mappings: list[FieldMapping] = Field(default_factory=list)
    extracted_rows: list[ExtractedRow] = Field(default_factory=list)
    unmapped_columns: list[str] = Field(default_factory=list)
    schema_gaps: list[str] = Field(default_factory=list)
    summary: ExtractionSummary = Field(default_factory=ExtractionSummary)
    requires_human_review: bool = True
    extraction_timestamp: str = ""
    prompt_version: str = EXTRACTION_PROMPT_VERSION
    mock_mode: bool = True
    # status: "ok" | "rejected" — rejected means the confidence floor (S4)
    # tripped and the confirmation UI must NOT be shown.
    status: str = "ok"
    rejection_guidance: Optional[str] = None
    # data-sufficiency warning (S3) shown before the operator confirms
    sufficiency_warnings: list[str] = Field(default_factory=list)
    # set when the real-LLM path failed and the deterministic fallback ran
    fallback_used: bool = False


# ── Source file reading ──────────────────────────────────────────────────────

class SourcePayload(BaseModel):
    filename: str
    kind: str                      # tabular | text
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)   # full data
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)  # ≤20 for the LLM
    raw_text: str = ""             # for text-like sources
    n_rows: int = 0


_TABULAR_EXTS = {".csv", ".xlsx", ".xls"}
_TEXT_EXTS = {".txt", ".json", ".eml", ".log"}


def read_source_file(path: str | Path) -> SourcePayload:
    """Read any supported operator file into a uniform payload."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext in _TABULAR_EXTS:
        df = pd.read_csv(p) if ext == ".csv" else pd.read_excel(p)
        df.columns = [str(c) for c in df.columns]
        rows = json.loads(df.to_json(orient="records"))
        return SourcePayload(
            filename=p.name, kind="tabular", headers=list(df.columns),
            rows=rows, sample_rows=rows[:20], n_rows=len(rows),
        )

    if ext == ".pdf":
        import pdfplumber
        text_parts: list[str] = []
        tables: list[pd.DataFrame] = []
        with pdfplumber.open(p) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
                for t in page.extract_tables() or []:
                    if t and len(t) > 1:
                        tables.append(pd.DataFrame(t[1:], columns=t[0]))
        if tables:
            df = pd.concat(tables, ignore_index=True)
            df.columns = [str(c) for c in df.columns]
            rows = json.loads(df.to_json(orient="records"))
            return SourcePayload(
                filename=p.name, kind="tabular", headers=list(df.columns),
                rows=rows, sample_rows=rows[:20], n_rows=len(rows),
                raw_text="\n".join(text_parts),
            )
        return SourcePayload(filename=p.name, kind="text",
                             raw_text="\n".join(text_parts))

    if ext in _TEXT_EXTS:
        return SourcePayload(filename=p.name, kind="text",
                             raw_text=p.read_text(errors="replace"))

    raise ValueError(
        f"Unsupported file type {ext!r}. Supported: CSV, Excel, PDF, "
        f"JSON, plain text."
    )


# ── Confidence policy ────────────────────────────────────────────────────────

def apply_confidence_policy(
    result: ExtractionResult,
    auto_accept: float = AUTO_ACCEPT_CONFIDENCE,
) -> ExtractionResult:
    """Apply the threshold policy and recompute the summary.

    ≥ auto_accept → auto-accepted (operator can still override)
    REVIEW..auto_accept → flagged for review, pre-populated
    < REVIEW → uncertain: the value is BLANKED (kept in metadata for the
      UI to suggest) and the operator must fill it
    requires_confirmation=True → never flows downstream unconfirmed
    overall < OVERALL_CONFIDENCE_FLOOR → entire extraction rejected (S4)
    """
    auto = review = 0
    confidences: list[float] = []

    for row in result.extracted_rows:
        if row.rejected:
            continue
        row_needs_review = row.requires_confirmation
        for fname, meta in row.field_metadata.items():
            confidences.append(meta.confidence)
            if meta.confidence < REVIEW_CONFIDENCE:
                # uncertain: blank the value; UI shows the suggestion
                if fname in row.fields:
                    row.fields[fname] = None
                meta.requires_confirmation = True
                meta.flag_reason = meta.flag_reason or (
                    f"confidence {meta.confidence:.2f} below "
                    f"{REVIEW_CONFIDENCE} — operator must fill"
                )
                row_needs_review = True
            elif meta.confidence < auto_accept:
                meta.requires_confirmation = True
                row_needs_review = True
        row.requires_confirmation = row_needs_review
        if row_needs_review:
            review += 1
        else:
            auto += 1

    for m in result.column_mappings:
        confidences.append(m.confidence)

    overall = (sum(confidences) / len(confidences)) if confidences else 0.0
    s = result.summary
    s.total_rows = len(result.extracted_rows)
    s.auto_accepted = auto
    s.flagged_for_review = review
    s.rejected = sum(1 for r in result.extracted_rows if r.rejected)
    s.overall_confidence = round(overall, 4)

    tables_present = sorted({r.table for r in result.extracted_rows
                             if not r.rejected})
    s.tables_found = tables_present
    s.tables_missing = sorted(set(TARGET_SCHEMA) - set(tables_present))

    covered = 0
    total_fields = 0
    for t in tables_present:
        fields_seen = set()
        for r in result.extracted_rows:
            if r.table == t and not r.rejected:
                fields_seen |= {k for k, v in r.fields.items()
                                if v is not None}
        covered += len(fields_seen & set(TARGET_SCHEMA[t]))
        total_fields += len(TARGET_SCHEMA[t])
    s.schema_coverage_pct = round(covered / total_fields * 100, 1) \
        if total_fields else 0.0

    result.requires_human_review = review > 0 or s.rejected > 0

    if confidences and overall < OVERALL_CONFIDENCE_FLOOR:
        result.status = "rejected"
        result.rejection_guidance = (
            f"Extraction confidence {overall:.2f} is below the "
            f"{OVERALL_CONFIDENCE_FLOOR} floor — the file's structure could "
            f"not be read reliably. Try: (1) export with one header row and "
            f"one record per line, (2) include column names like product, "
            f"quantity, date, supplier/buyer, (3) split mixed reports into "
            f"one file per kind of data (orders, deliveries, inventory, "
            f"waste). Nothing was loaded."
        )
    return result


# ── The engine ───────────────────────────────────────────────────────────────

def extract(
    file_paths: list[str | Path],
    session_id: str | None = None,
) -> ExtractionResult:
    """Extract staged records from operator files (mock or real per config).

    The result is policy-applied, safeguarded, and logged to the audit
    trail. It is NOT inserted anywhere — insertion happens only via the
    confirmation endpoint after operator review.
    """
    from ingestion.extraction_safeguards import run_post_extraction_safeguards
    from ingestion.extraction_sessions import log_extraction

    sid = session_id or f"ext-{uuid.uuid4().hex[:12]}"
    payloads = [read_source_file(p) for p in file_paths]

    raw_response: str | None = None
    if USE_REAL_LLM:
        try:
            result, raw_response = _extract_real(payloads, sid)
        except Exception as e:  # noqa: BLE001
            # Fallback: deterministic mapper, loudly marked. The UI shows
            # "Smart mapping temporarily unavailable".
            from ingestion.llm_mock_responder import mock_extract
            result = mock_extract(payloads, sid)
            result.fallback_used = True
            result.schema_gaps.append(
                f"real LLM extraction failed ({type(e).__name__}); "
                f"deterministic fallback mapping used"
            )
    else:
        from ingestion.llm_mock_responder import mock_extract
        result = mock_extract(payloads, sid)

    result.extraction_timestamp = datetime.now(timezone.utc).isoformat()
    result.prompt_version = EXTRACTION_PROMPT_VERSION

    result = apply_confidence_policy(result)
    result = run_post_extraction_safeguards(result)
    # policy again: safeguards may have added flags/rejections that change
    # the counts (cheap; idempotent for thresholds already applied)
    result = apply_confidence_policy(result)

    log_extraction(result, payloads, raw_response)
    return result


def _extract_real(
    payloads: list[SourcePayload],
    session_id: str,
) -> tuple[ExtractionResult, str]:
    """Call Claude for extraction. Only reachable when USE_REAL_LLM=True.

    Imports the SDK lazily so mock-mode installs never need the
    `anthropic` package.
    """
    from config.llm_config import check_real_llm_config
    check_real_llm_config()

    import anthropic  # lazy: not installed in mock-mode environments

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_payload = {
        "session_id": session_id,
        "files": [
            {
                "filename": p.filename,
                "kind": p.kind,
                "headers": p.headers,
                "sample_rows": p.sample_rows,
                "n_rows_total": p.n_rows,
                "raw_text": p.raw_text[:8000] if p.kind == "text" else "",
            }
            for p in payloads
        ],
    }

    msg = client.messages.create(
        model=EXTRACTION_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(user_payload)}],
    )
    raw = "".join(block.text for block in msg.content
                  if getattr(block, "type", "") == "text")

    parsed = json.loads(raw)
    parsed.setdefault("session_id", session_id)
    parsed.setdefault("source_files", [p.filename for p in payloads])
    result = ExtractionResult.model_validate(parsed)
    result.mock_mode = False

    # Safeguard 9 — token + cost logging on every real call.
    in_tok = msg.usage.input_tokens
    out_tok = msg.usage.output_tokens
    result.summary.estimated_api_tokens = in_tok + out_tok
    result.summary.estimated_api_cost_usd = round(
        in_tok / 1e6 * INPUT_COST_PER_MTOK
        + out_tok / 1e6 * OUTPUT_COST_PER_MTOK, 6)
    return result, raw
