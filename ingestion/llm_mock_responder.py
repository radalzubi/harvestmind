"""Deterministic mock extraction — exercises the full pipeline, zero API.

This is what runs while USE_REAL_LLM is False (the default), and it is
the deterministic fallback when a real API call fails. Its "brain" is the
same alias knowledge the real prompt carries: exact schema names map at
0.98, known aliases at 0.95, close fuzzy matches at 0.75 (review tier),
weak fuzzy matches at 0.60 (uncertain tier — blanked for the operator).
Derivations (e.g. accepted = delivered − rejected) are tagged with their
arithmetic; ambiguous dates and lb→kg conversions are flagged. Given the
same input bytes it returns the same result, so tests are stable.

Every result carries mock_mode=True so no surface can mistake this for
real extraction.
"""

from __future__ import annotations

import difflib
import re
from typing import Any


from ingestion.llm_extractor import (
    ExtractedRow,
    ExtractionResult,
    FieldMapping,
    FieldMeta,
    SourcePayload,
    TARGET_SCHEMA,
)

# Aliases → (table, field). One alias may serve several tables; routing
# picks the table first, then the field within it.
ALIASES: dict[str, dict[str, str]] = {
    # stg_supplier_deliveries
    "supplier": {"stg_supplier_deliveries": "supplier_name",
                 "stg_inventory_lots": "supplier_id"},
    "supplier name": {"stg_supplier_deliveries": "supplier_name"},
    "vendor": {"stg_supplier_deliveries": "supplier_name"},
    "farm": {"stg_supplier_deliveries": "supplier_name"},
    "grower": {"stg_supplier_deliveries": "supplier_name"},
    "ordered": {"stg_supplier_deliveries": "ordered_quantity"},
    "qty ordered": {"stg_supplier_deliveries": "ordered_quantity"},
    "po qty": {"stg_supplier_deliveries": "ordered_quantity"},
    "units ordered": {"stg_supplier_deliveries": "ordered_quantity"},
    "delivered": {"stg_supplier_deliveries": "delivered_quantity"},
    "shipped": {"stg_supplier_deliveries": "delivered_quantity",
                "stg_buyer_orders": "fulfilled_quantity"},
    "received": {"stg_supplier_deliveries": "accepted_quantity"},
    "accepted": {"stg_supplier_deliveries": "accepted_quantity"},
    "good": {"stg_supplier_deliveries": "accepted_quantity"},
    "usable": {"stg_supplier_deliveries": "accepted_quantity"},
    "rejected": {"stg_supplier_deliveries": "rejected_quantity"},
    "returned": {"stg_supplier_deliveries": "rejected_quantity"},
    "refused": {"stg_supplier_deliveries": "rejected_quantity"},
    "damaged": {"stg_supplier_deliveries": "rejected_quantity"},
    "unit cost": {"stg_supplier_deliveries": "unit_cost"},
    "cost": {"stg_supplier_deliveries": "unit_cost"},
    "rate": {"stg_supplier_deliveries": "unit_cost"},
    "delivery date": {"stg_supplier_deliveries": "delivery_date",
                      "stg_buyer_orders": "delivery_date"},
    "ship date": {"stg_supplier_deliveries": "delivery_date"},
    "invoice date": {"stg_supplier_deliveries": "delivery_date"},
    "date sent": {"stg_supplier_deliveries": "delivery_date"},
    "lot": {"stg_supplier_deliveries": "lot_id",
            "stg_inventory_lots": "lot_id",
            "stg_waste_adjustments": "lot_id"},
    "lot#": {"stg_supplier_deliveries": "lot_id",
             "stg_inventory_lots": "lot_id"},
    "batch": {"stg_supplier_deliveries": "lot_id",
              "stg_inventory_lots": "lot_id"},
    "batch#": {"stg_inventory_lots": "lot_id"},
    "trace id": {"stg_inventory_lots": "lot_id"},
    "grade": {"stg_supplier_deliveries": "quality_grade",
              "stg_buyer_orders": "required_quality_grade"},

    # stg_buyer_orders
    "buyer": {"stg_buyer_orders": "buyer_name"},
    "customer": {"stg_buyer_orders": "buyer_name"},
    "customer name": {"stg_buyer_orders": "buyer_name"},
    "account": {"stg_buyer_orders": "buyer_name"},
    "requested": {"stg_buyer_orders": "requested_quantity"},
    "qty requested": {"stg_buyer_orders": "requested_quantity"},
    "order qty": {"stg_buyer_orders": "requested_quantity"},
    "fulfilled": {"stg_buyer_orders": "fulfilled_quantity"},
    "qty delivered": {"stg_buyer_orders": "fulfilled_quantity"},
    "sent": {"stg_buyer_orders": "fulfilled_quantity"},
    "invoiced": {"stg_buyer_orders": "fulfilled_quantity"},
    "substituted": {"stg_buyer_orders": "substituted_quantity"},
    "subs": {"stg_buyer_orders": "substituted_quantity"},
    "price": {"stg_buyer_orders": "sales_price"},
    "unit price": {"stg_buyer_orders": "sales_price"},
    "each": {"stg_buyer_orders": "sales_price"},
    "sales price": {"stg_buyer_orders": "sales_price"},
    "order date": {"stg_buyer_orders": "order_date"},
    "po date": {"stg_buyer_orders": "order_date"},
    "request date": {"stg_buyer_orders": "order_date"},
    "order": {"stg_buyer_orders": "order_id"},
    "order #": {"stg_buyer_orders": "order_id"},
    "order number": {"stg_buyer_orders": "order_id"},

    # stg_inventory_lots
    "on hand": {"stg_inventory_lots": "quantity_on_hand"},
    "in stock": {"stg_inventory_lots": "quantity_on_hand"},
    "available": {"stg_inventory_lots": "quantity_on_hand"},
    "qoh": {"stg_inventory_lots": "quantity_on_hand"},
    "qty on hand": {"stg_inventory_lots": "quantity_on_hand"},
    "expiry": {"stg_inventory_lots": "expiration_date"},
    "best by": {"stg_inventory_lots": "expiration_date"},
    "use by": {"stg_inventory_lots": "expiration_date"},
    "bb date": {"stg_inventory_lots": "expiration_date"},
    "sell by": {"stg_inventory_lots": "expiration_date"},
    "expiration": {"stg_inventory_lots": "expiration_date"},
    "arrival": {"stg_inventory_lots": "arrival_date"},
    "arrival date": {"stg_inventory_lots": "arrival_date"},
    "received date": {"stg_inventory_lots": "arrival_date"},
    "location": {"stg_inventory_lots": "warehouse_location"},
    "warehouse": {"stg_inventory_lots": "warehouse_location"},
    "committed": {"stg_inventory_lots": "committed_quantity"},
    "reserved": {"stg_inventory_lots": "committed_quantity"},

    # stg_waste_adjustments
    "wasted": {"stg_waste_adjustments": "quantity_lost"},
    "waste": {"stg_waste_adjustments": "quantity_lost"},
    "spoiled": {"stg_waste_adjustments": "quantity_lost"},
    "dumped": {"stg_waste_adjustments": "quantity_lost"},
    "shrink": {"stg_waste_adjustments": "quantity_lost"},
    "culled": {"stg_waste_adjustments": "quantity_lost"},
    "loss qty": {"stg_waste_adjustments": "quantity_lost"},
    "reason": {"stg_waste_adjustments": "reason"},
    "reason code": {"stg_waste_adjustments": "reason"},
    "value lost": {"stg_waste_adjustments": "estimated_value_lost"},
    "est value": {"stg_waste_adjustments": "estimated_value_lost"},

    # stg_products
    "category": {"stg_products": "category"},
    "shelf life": {"stg_products": "default_shelf_life_days"},
    "ftl": {"stg_products": "traceability_required"},

    # shared
    "product": {t: "product_name" for t in TARGET_SCHEMA},
    "product name": {t: "product_name" for t in TARGET_SCHEMA},
    "item": {t: "product_name" for t in TARGET_SCHEMA},
    "crop": {t: "product_name" for t in TARGET_SCHEMA},
    "sku": {t: "product_id" for t in TARGET_SCHEMA},
    "unit": {"stg_inventory_lots": "unit", "stg_products": "unit"},
    "date": {"stg_waste_adjustments": "date",
             "stg_supplier_deliveries": "delivery_date",
             "stg_buyer_orders": "order_date"},
    "notes": {},  # recognized but has no staging home — schema gap
}

# Commercial-goods aliases live in their own table and are MERGED into the
# produce aliases below, so a header that means something in both families
# (order date, on hand, warehouse) routes to whichever table the rest of
# the header row favours.
_FMCG_ALIASES: dict[str, dict[str, str]] = {
    "sku": {"stg_fmcg_skus": "sku", "stg_fmcg_orders": "sku", "stg_fmcg_purchase_orders": "sku",
            "stg_fmcg_receipts": "sku", "stg_fmcg_inventory": "sku"},
    "item code": {"stg_fmcg_skus": "sku", "stg_fmcg_orders": "sku", "stg_fmcg_purchase_orders": "sku",
                  "stg_fmcg_receipts": "sku", "stg_fmcg_inventory": "sku"},
    "item": {"stg_fmcg_skus": "sku", "stg_fmcg_orders": "sku", "stg_fmcg_purchase_orders": "sku",
             "stg_fmcg_receipts": "sku", "stg_fmcg_inventory": "sku"},
    "item no": {"stg_fmcg_skus": "sku", "stg_fmcg_purchase_orders": "sku", "stg_fmcg_inventory": "sku"},
    "article": {"stg_fmcg_skus": "sku", "stg_fmcg_orders": "sku"},
    "item name": {"stg_fmcg_skus": "sku_name"},
    "description": {"stg_fmcg_skus": "sku_name"},
    "po": {"stg_fmcg_purchase_orders": "po_id", "stg_fmcg_receipts": "po_id"},
    "po number": {"stg_fmcg_purchase_orders": "po_id", "stg_fmcg_receipts": "po_id"},
    "po no": {"stg_fmcg_purchase_orders": "po_id", "stg_fmcg_receipts": "po_id"},
    "purchase order": {"stg_fmcg_purchase_orders": "po_id", "stg_fmcg_receipts": "po_id"},
    "po date": {"stg_fmcg_purchase_orders": "po_date"},
    "order date": {"stg_fmcg_orders": "order_date", "stg_fmcg_purchase_orders": "po_date", "stg_buyer_orders": "order_date"},
    "expected date": {"stg_fmcg_purchase_orders": "expected_delivery_date"},
    "promised date": {"stg_fmcg_purchase_orders": "expected_delivery_date"},
    "eta": {"stg_fmcg_purchase_orders": "expected_delivery_date"},
    "receipt date": {"stg_fmcg_receipts": "receipt_date"},
    "date received": {"stg_fmcg_receipts": "receipt_date"},
    "grn date": {"stg_fmcg_receipts": "receipt_date"},
    "grn": {"stg_fmcg_receipts": "receipt_id"},
    "qty received": {"stg_fmcg_receipts": "qty_received"},
    "received qty": {"stg_fmcg_receipts": "qty_received"},
    "qty rejected": {"stg_fmcg_receipts": "qty_rejected"},
    "qty ordered": {"stg_fmcg_orders": "qty_ordered", "stg_fmcg_purchase_orders": "qty_ordered",
                    "stg_supplier_deliveries": "ordered_quantity"},
    "quantity": {"stg_fmcg_orders": "qty_ordered", "stg_fmcg_purchase_orders": "qty_ordered"},
    "qty": {"stg_fmcg_orders": "qty_ordered", "stg_fmcg_purchase_orders": "qty_ordered"},
    "qty shipped": {"stg_fmcg_orders": "qty_shipped"},
    "shipped qty": {"stg_fmcg_orders": "qty_shipped"},
    "customer id": {"stg_fmcg_orders": "customer_id"},
    "customer code": {"stg_fmcg_orders": "customer_id"},
    "sales order": {"stg_fmcg_orders": "order_id"},
    "so number": {"stg_fmcg_orders": "order_id"},
    "channel": {"stg_fmcg_orders": "channel"},
    "on hand": {"stg_fmcg_inventory": "on_hand", "stg_inventory_lots": "quantity_on_hand"},
    "stock on hand": {"stg_fmcg_inventory": "on_hand"},
    "qty on hand": {"stg_fmcg_inventory": "on_hand", "stg_inventory_lots": "quantity_on_hand"},
    "soh": {"stg_fmcg_inventory": "on_hand"},
    "in transit": {"stg_fmcg_inventory": "in_transit"},
    "on order": {"stg_fmcg_inventory": "in_transit"},
    "count date": {"stg_fmcg_inventory": "snapshot_date"},
    "snapshot date": {"stg_fmcg_inventory": "snapshot_date"},
    "stock date": {"stg_fmcg_inventory": "snapshot_date"},
    "warehouse": {"stg_fmcg_inventory": "location_id", "stg_inventory_lots": "warehouse_location"},
    "location": {"stg_fmcg_inventory": "location_id", "stg_inventory_lots": "warehouse_location"},
    "units per case": {"stg_fmcg_skus": "units_per_case"},
    "case pack": {"stg_fmcg_skus": "units_per_case"},
    "pack size": {"stg_fmcg_skus": "units_per_case"},
    "pcs per case": {"stg_fmcg_skus": "units_per_case"},
    "moq": {"stg_fmcg_skus": "moq_units"},
    "min order": {"stg_fmcg_skus": "moq_units"},
    "unit price": {"stg_fmcg_skus": "unit_price"},
    "selling price": {"stg_fmcg_skus": "unit_price"},
    "sell price": {"stg_fmcg_skus": "unit_price"},
    "cost price": {"stg_fmcg_skus": "unit_cost", "stg_fmcg_purchase_orders": "unit_cost"},
    "purchase price": {"stg_fmcg_skus": "unit_cost", "stg_fmcg_purchase_orders": "unit_cost"},
    "landed cost": {"stg_fmcg_skus": "unit_cost"},
    "category": {"stg_fmcg_skus": "category", "stg_products": "category"},
    "abc": {"stg_fmcg_skus": "abc_class"},
    "shelf life": {"stg_fmcg_skus": "shelf_life_days", "stg_products": "default_shelf_life_days"},
    "supplier id": {"stg_fmcg_skus": "supplier_id", "stg_fmcg_purchase_orders": "supplier_id", "stg_fmcg_suppliers": "supplier_id"},
    "supplier code": {"stg_fmcg_skus": "supplier_id", "stg_fmcg_purchase_orders": "supplier_id", "stg_fmcg_suppliers": "supplier_id"},
    "vendor id": {"stg_fmcg_purchase_orders": "supplier_id", "stg_fmcg_suppliers": "supplier_id"},
    "vendor code": {"stg_fmcg_purchase_orders": "supplier_id", "stg_fmcg_suppliers": "supplier_id"},
    "route": {"stg_fmcg_suppliers": "route"},
    "port": {"stg_fmcg_suppliers": "route"},
    "lane": {"stg_fmcg_suppliers": "route"},
    "origin": {"stg_fmcg_suppliers": "origin_iso3"},
    "country of origin": {"stg_fmcg_suppliers": "origin_iso3"},
    "country": {"stg_fmcg_suppliers": "origin_iso3"},
    "lead time": {"stg_fmcg_suppliers": "lead_time_promised_weeks"},
    "lead time weeks": {"stg_fmcg_suppliers": "lead_time_promised_weeks"},

}
for _k, _v in _FMCG_ALIASES.items():
    ALIASES.setdefault(_k, {}).update(_v)

# Columns that signal supplier-master data (no staging home — S/gap).
SUPPLIER_MASTER_HINTS = ("contact", "email", "phone", "payment terms",
                         "terms", "address")

_LB_RE = re.compile(r"\((?:lbs?|pounds?)\)|\b(?:lbs?|pounds?)\b")
_AMBIG_DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$")
_LB_TO_KG = 0.453592


def _norm(col: str) -> str:
    s = col.strip().lower()
    s = _LB_RE.sub("", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _slug(name: Any, prefix: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower()).strip("-")
    return f"{prefix}-{s[:24]}" if s else f"{prefix}-unknown"


def _route_table(headers: list[str]) -> str | None:
    """Pick the staging table whose signals best match the headers."""
    scores = {t: 0.0 for t in TARGET_SCHEMA}
    for h in headers:
        n = _norm(h)
        hit = ALIASES.get(n)
        if hit:
            for t in hit:
                scores[t] += 1.0
            continue
        for t, cols in TARGET_SCHEMA.items():
            if n.replace(" ", "_") in cols:
                scores[t] += 1.5
    best = max(scores, key=lambda t: scores[t])
    return best if scores[best] >= 2 else None


def _map_column(header: str, table: str) -> tuple[str | None, float, str, str | None]:
    """(target_field, confidence, reasoning, alternative) for one header."""
    n = _norm(header)
    schema_cols = TARGET_SCHEMA[table]

    snake = n.replace(" ", "_")
    if snake in schema_cols:
        return snake, 0.98, "exact schema name", None

    hit = ALIASES.get(n)
    if hit is not None:
        if table in hit:
            alts = [f"{t}.{f}" for t, f in hit.items() if t != table]
            return (hit[table], 0.95, f"known alias '{n}'",
                    alts[0] if alts else None)
        if not hit:
            return None, 0.0, "recognized but no staging home", None

    close = difflib.get_close_matches(snake, schema_cols, n=2, cutoff=0.62)
    if close:
        ratio = difflib.SequenceMatcher(None, snake, close[0]).ratio()
        alt = close[1] if len(close) > 1 else None
        if ratio >= 0.80:
            return close[0], 0.75, f"fuzzy match ({ratio:.2f})", alt
        return close[0], 0.60, f"weak fuzzy match ({ratio:.2f})", alt

    return None, 0.0, "no match", None


def mock_extract(
    payloads: list[SourcePayload],
    session_id: str,
) -> ExtractionResult:
    """Deterministic extraction over the payloads (tabular sources here;
    text sources route through the unstructured extractor)."""
    result = ExtractionResult(
        session_id=session_id,
        source_files=[p.filename for p in payloads],
        mock_mode=True,
    )
    result.summary.estimated_api_tokens = 0
    result.summary.estimated_api_cost_usd = 0.0

    row_counter = 0
    for payload in payloads:
        if payload.kind == "text":
            from ingestion.llm_unstructured import mock_extract_text
            row_counter = mock_extract_text(payload, result, row_counter)
            continue

        table = _route_table(payload.headers)
        if table is None:
            result.unmapped_columns.extend(payload.headers)
            result.schema_gaps.append(
                f"{payload.filename}: no staging table matches these "
                f"columns — file skipped, nothing invented")
            continue

        mapping: dict[str, tuple[str, FieldMapping]] = {}
        for h in payload.headers:
            n = _norm(h)
            if any(hint in n for hint in SUPPLIER_MASTER_HINTS):
                result.schema_gaps.append(
                    f"'{h}' looks like supplier master data (contacts/"
                    f"terms) — no staging table exists for it; column "
                    f"set aside, not loaded")
                result.unmapped_columns.append(h)
                continue
            target, conf, why, alt = _map_column(h, table)
            if target is None:
                result.unmapped_columns.append(h)
                continue
            fm = FieldMapping(source_column=h, target_field=target,
                              confidence=conf, reasoning=why,
                              alternative_mapping=alt)
            mapping[h] = (target, fm)
            result.column_mappings.append(fm)

        lb_columns = {h for h in payload.headers
                      if _LB_RE.search(h.strip().lower())}

        for raw in payload.rows:
            row = _build_row(raw, table, mapping, lb_columns, row_counter,
                             payload.filename)
            result.extracted_rows.append(row)
            row_counter += 1

    return result


def _build_row(
    raw: dict[str, Any],
    table: str,
    mapping: dict[str, tuple[str, "FieldMapping"]],
    lb_columns: set[str],
    row_index: int,
    filename: str,
) -> ExtractedRow:
    fields: dict[str, Any] = {}
    meta: dict[str, FieldMeta] = {}
    flags: list[str] = []

    for src, (target, fm) in mapping.items():
        val = raw.get(src)
        if isinstance(val, str) and not val.strip():
            val = None

        inference = f"mapped from '{src}'"
        flag_reason = None

        # lb → kg conversion, flagged per rule 6
        if src in lb_columns and val is not None:
            try:
                val = round(float(val) * _LB_TO_KG, 3)
                inference = f"mapped from '{src}'; converted lb → kg (×{_LB_TO_KG})"
                flags.append(f"{target}: converted lb → kg from '{src}'")
            except (TypeError, ValueError):
                pass

        # ambiguous date detection, rule 7
        if target.endswith("date") or target == "date":
            amb = _AMBIG_DATE_RE.match(str(val)) if val is not None else None
            if amb:
                m1, m2 = int(amb.group(1)), int(amb.group(2))
                if m1 <= 12 and m2 <= 12 and m1 != m2:
                    flag_reason = (
                        f"ambiguous date '{val}': could be "
                        f"{amb.group(3)}-{m1:02d}-{m2:02d} (US) or "
                        f"{amb.group(3)}-{m2:02d}-{m1:02d} (intl) — "
                        f"confirm the format")
                    flags.append(f"{target}: {flag_reason}")

        fields[target] = val
        meta[target] = FieldMeta(
            confidence=fm.confidence,
            inference_source=inference,
            requires_confirmation=flag_reason is not None,
            flag_reason=flag_reason,
        )

    # ID slugs (rule 2): generated, never guessed, flagged for confirmation
    name_to_id = (("product_name", "product_id", "prod"),
                  ("supplier_name", "supplier_id", "sup"),
                  ("buyer_name", "buyer_id", "buy"))
    for name_f, id_f, prefix in name_to_id:
        if id_f in TARGET_SCHEMA[table] and fields.get(name_f) \
                and not fields.get(id_f):
            fields[id_f] = _slug(fields[name_f], prefix)
            meta[id_f] = FieldMeta(
                confidence=0.85,
                inference_source=f"derived: slug of {name_f}",
                requires_confirmation=True,
                flag_reason="generated id — confirm or replace with your "
                            "own identifier",
            )

    # Derivations (rule 5) — tagged with their exact arithmetic
    if table == "stg_supplier_deliveries":
        o, d = fields.get("ordered_quantity"), fields.get("delivered_quantity")
        if fields.get("accepted_quantity") is None and d is not None:
            rej = fields.get("rejected_quantity") or 0
            try:
                fields["accepted_quantity"] = float(d) - float(rej)
                meta["accepted_quantity"] = FieldMeta(
                    confidence=0.85,
                    inference_source="derived: delivered_quantity − "
                                     "rejected_quantity",
                    requires_confirmation=True,
                    flag_reason="accepted quantity not in source — derived",
                )
            except (TypeError, ValueError):
                pass
        if o is not None and d is not None:
            try:
                short = float(o) - float(d)
                if short > 0:
                    flags.append(
                        f"short delivery inferred: {short:g} "
                        f"(ordered − delivered)")
                    meta["_short_inferred"] = FieldMeta(
                        confidence=0.9,
                        inference_source="derived: ordered_quantity − "
                                         "delivered_quantity",
                        requires_confirmation=False,
                        flag_reason=None)
            except (TypeError, ValueError):
                pass

    if table == "stg_buyer_orders":
        r, f = fields.get("requested_quantity"), fields.get("fulfilled_quantity")
        if fields.get("substituted_quantity") is None and f is not None:
            fields["substituted_quantity"] = 0
            meta["substituted_quantity"] = FieldMeta(
                confidence=0.9,
                inference_source="derived: no substitution column in "
                                 "source → 0",
                requires_confirmation=False, flag_reason=None)
        if r is not None and f is not None:
            try:
                missed = float(r) - float(f) - float(
                    fields.get("substituted_quantity") or 0)
                if missed > 0:
                    flags.append(
                        f"missed fulfillment inferred: {missed:g} "
                        f"(requested − fulfilled − substituted)")
                    meta["_missed_inferred"] = FieldMeta(
                        confidence=0.9,
                        inference_source="derived: requested_quantity − "
                                         "fulfilled_quantity − "
                                         "substituted_quantity",
                        requires_confirmation=False, flag_reason=None)
            except (TypeError, ValueError):
                pass

    return ExtractedRow(
        row_index=row_index,
        table=table,
        fields=fields,
        field_metadata=meta,
        flags=flags,
        requires_confirmation=any(m.requires_confirmation
                                  for m in meta.values()),
    )
