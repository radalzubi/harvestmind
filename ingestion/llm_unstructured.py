"""Unstructured-text extraction: WhatsApp / SMS / email / PDF text.

Text sources are the least reliable input the system accepts, so the
confidence policy is STRICTER than for structured files: auto-accept
requires ≥ 0.95, and every extracted row defaults to
requires_confirmation=True unless it clears that bar. Nothing from a
message log ever silently passes through.

The mock parser handles the message shapes produce operators actually
send ("need 200 cases roma tomatoes Thursday", "delivered 180 cases
tomatoes spinach short only had 40") with simple deterministic patterns;
the real LLM path handles the long tail. Both land in the same
ExtractionResult shape.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from config.llm_config import UNSTRUCTURED_AUTO_ACCEPT
from ingestion.llm_extractor import (
    ExtractedRow,
    ExtractionResult,
    FieldMeta,
    SourcePayload,
)

_QTY_PRODUCT_RE = re.compile(
    r"(?:need|order|want|send|deliver(?:ed)?|add(?:ed)?|also)\s+"
    r"(\d+(?:\.\d+)?)\s*(cases?|kg|lbs?|units?|bunch(?:es)?|crates?)?\s+"
    r"(?:of\s+)?([a-z][a-z ]{2,40}?)(?=\s+(?:thursday|friday|monday|tuesday|"
    r"wednesday|saturday|sunday|tomorrow|today|next|by|on|for|also|and|$)|$)",
    re.IGNORECASE,
)
_SHORT_RE = re.compile(
    r"([a-z ]{3,40}?)\s+short\b.*?(?:only\s+had|had\s+only|just)\s+(\d+)",
    re.IGNORECASE,
)
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday")


def _next_weekday(name: str, today: date | None = None) -> str:
    t = today or date.today()
    target = _WEEKDAYS.index(name.lower())
    delta = (target - t.weekday()) % 7 or 7
    return (t + timedelta(days=delta)).isoformat()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def mock_extract_text(
    payload: SourcePayload,
    result: ExtractionResult,
    row_counter: int,
) -> int:
    """Parse message-style text into stg_buyer_orders rows (deterministic).

    Appends rows to ``result`` and returns the updated row counter. Every
    row defaults to requires_confirmation=True (unstructured floor): a
    message is a request, not a record, until the operator says so.
    """
    text = _strip_html(payload.raw_text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    mentioned_day: str | None = None
    for ln in lines:
        for wd in _WEEKDAYS:
            if wd in ln.lower():
                mentioned_day = _next_weekday(wd)
                break

        for m in _QTY_PRODUCT_RE.finditer(ln):
            qty, unit, product = m.group(1), (m.group(2) or "unit"), m.group(3)
            product = product.strip().rstrip(".,!")
            confidence = 0.80  # text is never auto-accept tier by default
            fields: dict[str, Any] = {
                "product_name": product.title(),
                "requested_quantity": float(qty),
                "delivery_date": mentioned_day,
                "buyer_name": None,
                "order_date": None,
            }
            meta = {
                "product_name": FieldMeta(
                    confidence=confidence,
                    inference_source=f"parsed from message: '{ln[:80]}'",
                    requires_confirmation=True,
                    flag_reason="extracted from free text — confirm "
                                "product and quantity"),
                "requested_quantity": FieldMeta(
                    confidence=confidence,
                    inference_source=f"parsed quantity '{qty} {unit}' from "
                                     f"message",
                    requires_confirmation=True,
                    flag_reason=f"unit '{unit}' from text — confirm the "
                                f"kg equivalent"),
            }
            result.extracted_rows.append(ExtractedRow(
                row_index=row_counter, table="stg_buyer_orders",
                fields=fields, field_metadata=meta,
                flags=[f"from unstructured text ({payload.filename})"],
                requires_confirmation=True,
            ))
            row_counter += 1

        sm = _SHORT_RE.search(ln)
        if sm:
            product, had = sm.group(1).strip(), float(sm.group(2))
            result.extracted_rows.append(ExtractedRow(
                row_index=row_counter, table="stg_buyer_orders",
                fields={"product_name": product.title(),
                        "fulfilled_quantity": had,
                        "requested_quantity": None},
                field_metadata={
                    "fulfilled_quantity": FieldMeta(
                        confidence=0.75,
                        inference_source=f"parsed shortfall from message: "
                                         f"'{ln[:80]}'",
                        requires_confirmation=True,
                        flag_reason="message reports a short fulfillment — "
                                    "match to the original order and "
                                    "confirm quantities"),
                },
                flags=[f"short fulfillment reported in text "
                       f"({payload.filename}) — needs matching to an order"],
                requires_confirmation=True,
            ))
            row_counter += 1

    if not result.extracted_rows:
        result.schema_gaps.append(
            f"{payload.filename}: no order-like statements found in the "
            f"text — nothing invented")

    return row_counter


def enforce_unstructured_floor(result: ExtractionResult) -> ExtractionResult:
    """Stricter policy for text-derived rows: requires_confirmation unless
    every field clears the 0.95 unstructured auto-accept bar."""
    for row in result.extracted_rows:
        if any("unstructured" in f or "from unstructured" in f
               for f in row.flags):
            clears = all(m.confidence >= UNSTRUCTURED_AUTO_ACCEPT
                         for m in row.field_metadata.values())
            if not clears:
                row.requires_confirmation = True
                for m in row.field_metadata.values():
                    m.requires_confirmation = True
    return result
