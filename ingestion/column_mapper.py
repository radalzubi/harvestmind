"""Auto-map real-world export columns to HarvestMind schema names.

Real partner exports never match the schema. Local Line uses "Order Number",
QuickBooks uses "Num", a hub on a spreadsheet might use "PO #" or "Customer".
This module maps each via a 4-step strategy:
  1. Exact, case-insensitive, whitespace-stripped
  2. COLUMN_ALIASES lookup
  3. difflib.get_close_matches against the schema columns
  4. Drop with a warning (unmapped columns are not silently kept)

It also handles unit conversion (lbs → kg) and infers missing required columns
where reasonable (week_start from order_date, deterministic ID from row hash).
"""

from __future__ import annotations

import difflib
import hashlib
from typing import Iterable

import pandas as pd


# ── Aliases ──────────────────────────────────────────────────────────────────

COLUMN_ALIASES: dict[str, str] = {
    # Local Line ───────────────────────────────────────────────────────────
    "order number":      "order_id",
    "order #":           "order_id",
    "customer":          "buyer_id",
    "customer name":     "buyer_id",
    "hub":               "buyer_id",
    "order date":        "order_date",
    "fulfillment date":  "delivery_date",
    "item":              "product_id",
    "product name":      "product_id",
    "quantity":          "qty_ordered_kg",
    "qty":               "qty_ordered_kg",
    "qty ordered":       "qty_ordered_kg",
    "qty delivered":     "qty_delivered_kg",
    "unit price":        "price_per_kg",
    "price":             "price_per_kg",
    "vendor":            "supplier_id",
    "farm":              "supplier_id",
    "producer":          "supplier_id",

    # QuickBooks ──────────────────────────────────────────────────────────
    "num":               "order_id",
    "invoice #":         "order_id",
    "name":              "buyer_id",
    "date":              "order_date",
    "due date":          "delivery_date",
    "description":       "product_id",
    "amount":            "price_per_kg",
    "balance":           "price_per_kg",
    "type":              "status",

    # Generic spreadsheet ─────────────────────────────────────────────────
    "order id":          "order_id",
    "po number":         "po_id",
    "po #":              "po_id",
    "buyer":             "buyer_id",
    "supplier":          "supplier_id",
    "grower":            "supplier_id",
    "crop":              "product_id",
    "product":           "product_id",
    "week":              "week_start",
    "week of":           "week_start",
    "delivered":         "qty_delivered_kg",
    "received":          "qty_received_kg",
    "qty received":      "qty_received_kg",
    "rejected":          "qty_rejected_kg",
    "qty rejected":      "qty_rejected_kg",
    "returns":           "qty_rejected_kg",
    "rejection reason":  "rejection_reason",
    "reason":            "rejection_reason",
    "waste":             "qty_wasted_kg",
    "loss":              "qty_wasted_kg",
    "wasted":            "qty_wasted_kg",
    "value":             "estimated_value_usd",
    "cost":              "estimated_value_usd",
    "committed":         "qty_committed_kg",
    "spot":              "is_spot_purchase",
    "emergency":         "is_spot_purchase",
    "temp":              "temp_on_arrival_c",
    "temperature":       "temp_on_arrival_c",
    "arrival temp":      "temp_on_arrival_c",
}


SCHEMA_COLS: dict[str, list[str]] = {
    "orders": [
        "order_id", "buyer_id", "order_date", "week_start", "status", "notes",
    ],
    "order_lines": [
        "line_id", "order_id", "product_id", "qty_ordered_kg",
        "qty_delivered_kg", "price_per_kg", "lost_sale_flag",
    ],
    "deliveries": [
        "delivery_id", "supplier_id", "product_id", "delivery_date",
        "qty_received_kg", "qty_rejected_kg", "rejection_reason",
        "temp_on_arrival_c",
    ],
    "purchase_orders": [
        "po_id", "supplier_id", "product_id", "po_date", "week_start",
        "qty_committed_kg", "price_per_kg", "is_spot_purchase", "status",
    ],
    "waste_events": [
        "waste_id", "event_date", "product_id", "qty_wasted_kg",
        "reason_code", "estimated_value_usd", "waste_stage",
    ],
}


# ── Mapping ──────────────────────────────────────────────────────────────────

def _normalize(col: str) -> str:
    return col.strip().lower()


_UNIT_SUFFIXES = ("(lbs)", "(lb)", "(pounds)", "(pound)",
                  "(tons)", "(ton)", "(kg)", "(g)", "(usd)", "($)")


def _strip_unit_suffix(norm: str) -> str:
    """Drop trailing unit hints so 'qty received (lbs)' → 'qty received'."""
    s = norm
    for suf in _UNIT_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    # Also strip standalone trailing tokens.
    for tok in (" lbs", " lb", " pounds", " pound", " kg", " tons", " ton"):
        if s.endswith(tok):
            s = s[: -len(tok)].strip()
    return s


def auto_map_columns(
    df: pd.DataFrame,
    target_schema: str,
) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    """Map df columns to schema names. Returns (renamed_df, mapping, warnings).

    Strategy (in order):
      1. Exact match, case-insensitive, whitespace-stripped
      2. COLUMN_ALIASES lookup
      3. difflib.get_close_matches against the schema's column list
      4. Unmatched → warning + drop from df

    The mapping dict only includes columns we actually renamed
    ({original: schema}). Warnings list every unmapped column with a hint.
    """
    if target_schema not in SCHEMA_COLS:
        raise ValueError(
            f"Unknown target_schema {target_schema!r}. "
            f"Allowed: {sorted(SCHEMA_COLS)}"
        )

    schema_cols = SCHEMA_COLS[target_schema]
    mapping: dict[str, str] = {}
    warnings: list[str] = []
    seen_targets: set[str] = set()

    for col in list(df.columns):
        norm = _normalize(col)
        stripped = _strip_unit_suffix(norm)

        # 1. Exact match against schema names
        for sc in schema_cols:
            if norm == sc.lower() or stripped == sc.lower():
                mapping[col] = sc
                seen_targets.add(sc)
                break
        if col in mapping:
            continue

        # 2. Alias lookup (try the unit-stripped form too)
        for key in (norm, stripped):
            if key in COLUMN_ALIASES:
                tgt = COLUMN_ALIASES[key]
                if tgt in schema_cols:
                    mapping[col] = tgt
                    seen_targets.add(tgt)
                    break
        if col in mapping:
            continue

        # 3. Fuzzy match against schema columns (use stripped form for accuracy)
        candidates = difflib.get_close_matches(
            stripped, [c.lower() for c in schema_cols], n=1, cutoff=0.72,
        )
        if candidates:
            tgt = next(sc for sc in schema_cols if sc.lower() == candidates[0])
            if tgt in seen_targets:
                warnings.append(
                    f"Column '{col}' fuzzy-matches '{tgt}' but that target is "
                    f"already mapped — dropping. Rename your column to disambiguate."
                )
                continue
            mapping[col] = tgt
            seen_targets.add(tgt)
            continue

        # 4. Unmapped
        warnings.append(f"Column '{col}' could not be mapped to {target_schema} schema — dropped.")

    # Build renamed df, dropping unmapped columns
    keep = [c for c in df.columns if c in mapping]
    renamed = df[keep].rename(columns=mapping).copy()

    return renamed, mapping, warnings


# ── Unit conversion ──────────────────────────────────────────────────────────

# Tokens that signal a non-kg unit. Order matters: check 'metric ton' before 'ton'.
_LB_TOKENS = ("lbs", "lb", "pounds", "pound")
_TON_TOKENS = ("tons", "ton")

# Conversion factors → kg
_LB_TO_KG = 0.453592
_TON_TO_KG = 907.185  # US (short) ton; metric tonne is 1000 kg


def detect_and_convert_units(
    df: pd.DataFrame,
    original_columns: Iterable[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Detect lb/ton columns by ORIGINAL header name and convert to kg.

    The mapping has already turned 'Qty (lbs)' into 'qty_ordered_kg', so we
    use the original (pre-rename) header to detect the unit. Caller passes
    the original column names list.

    Returns (df_with_converted_cols, list_of_human_readable_conversions).
    """
    df = df.copy()
    conversions: list[str] = []

    # Build a {schema_col: original_col} reverse map from columns currently
    # in the df (post-rename) and the originals provided.
    # Simpler: iterate originals; for each, infer factor from header, then
    # find which schema column it would have been mapped to and apply.
    # We rely on the lowercased original to detect units.

    for orig in original_columns:
        norm = _normalize(orig)
        factor: float | None = None
        unit_label = ""

        # 'metric ton' is left alone — it's already 1000 kg, but rare in food
        # hub exports; add explicit handling later if needed.
        if "metric ton" in norm:
            continue

        if any(tok in norm.split() or norm.endswith(tok) or f"({tok})" in norm or f" {tok}" in norm
               for tok in _LB_TOKENS):
            factor = _LB_TO_KG
            unit_label = "lbs → kg"
        elif any(tok in norm.split() or norm.endswith(tok) or f"({tok})" in norm or f" {tok}" in norm
                 for tok in _TON_TOKENS):
            factor = _TON_TO_KG
            unit_label = "tons → kg"

        if factor is None:
            continue

        # Resolve the schema column this original mapped to.
        if norm in COLUMN_ALIASES:
            target = COLUMN_ALIASES[norm]
        else:
            # Strip parenthetical units to match the alias key.
            stripped = norm
            for tok in _LB_TOKENS + _TON_TOKENS:
                stripped = stripped.replace(f"({tok})", "").replace(f" {tok}", "").strip()
            target = COLUMN_ALIASES.get(stripped)

        if target and target in df.columns:
            df[target] = pd.to_numeric(df[target], errors="coerce") * factor
            conversions.append(f"Converted '{orig}' → kg ({unit_label}, ×{factor})")

    return df, conversions


# ── Inference ────────────────────────────────────────────────────────────────

def _row_hash(row: pd.Series, prefix: str) -> str:
    """Stable short hash of all row values — used for deterministic synthetic IDs."""
    payload = "|".join(str(v) for v in row.to_list())
    return f"{prefix}-{hashlib.md5(payload.encode('utf-8')).hexdigest()[:8].upper()}"


_INSERT_IDENT_RE = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def insert_from_df(
    conn,
    table_name: str,
    df: pd.DataFrame,
    on_conflict: str = "ignore",
) -> int:
    """Insert df rows into a DuckDB table with an explicit column list.

    Unlike `INSERT … SELECT *`, this only supplies the columns actually
    present in df; columns with DEFAULT values fall back to their defaults
    instead of receiving NULL. Required for partial-CSV ingestion where the
    partner sends 4 columns of a 7-column table.

    Both table_name and every df column name must match `_INSERT_IDENT_RE` —
    callers are expected to allowlist `table_name` separately.
    """
    if not _INSERT_IDENT_RE.match(table_name):
        raise ValueError(f"table_name {table_name!r} is not a valid SQL identifier")
    for c in df.columns:
        if not _INSERT_IDENT_RE.match(str(c)):
            raise ValueError(f"column name {c!r} is not a valid SQL identifier")

    if df.empty:
        return 0

    cols_sql = ", ".join(df.columns)
    conflict_sql = " ON CONFLICT DO NOTHING" if on_conflict == "ignore" else ""

    before = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    conn.register("hm_insert_df", df)
    try:
        conn.execute(
            f"INSERT INTO {table_name} ({cols_sql}) "
            f"SELECT {cols_sql} FROM hm_insert_df{conflict_sql}"
        )
    finally:
        conn.unregister("hm_insert_df")
    after = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    return int(after - before)


def align_to_table_schema(conn, table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Pad df with NULL columns and reorder to match a DuckDB table's schema.

    DuckDB's INSERT OR IGNORE … SELECT * matches columns by position, so the
    df must have exactly the table's columns in the table's order. Real-world
    partner CSVs only carry a subset; we pad the rest with NULL.
    """
    # PRAGMA table_info returns (cid, name, type, notnull, default, pk).
    table_cols = [
        r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]
    if not table_cols:
        return df
    out = df.copy()
    for col in table_cols:
        if col not in out.columns:
            out[col] = None
    return out[table_cols]


def infer_missing_columns(
    df: pd.DataFrame,
    target_schema: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Fill in required columns that can be derived from other fields.

    Rules:
      - week_start missing + order_date present:
          week_start = order_date floored to Monday
      - {entity}_id missing:
          stable md5 of row values, prefixed by entity
            order_id    → "ORD-..."
            delivery_id → "DEL-..."
            waste_id    → "WST-..."
            line_id     → "LIN-..."
            po_id       → "PO-..."

    Returns (df, list_of_human_readable_inferences).
    """
    df = df.copy()
    inferences: list[str] = []

    # week_start ← order_date / event_date / po_date
    if "week_start" not in df.columns:
        date_source = next(
            (c for c in ("order_date", "event_date", "po_date", "delivery_date")
             if c in df.columns),
            None,
        )
        if date_source and len(df) > 0:
            ds = pd.to_datetime(df[date_source], errors="coerce")
            offsets = pd.to_timedelta(
                ds.dt.weekday.fillna(0).astype(int), unit="D"
            )
            df["week_start"] = (ds - offsets).dt.date
            inferences.append(f"Inferred week_start from {date_source}")

    # IDs derived from row hash where missing
    id_prefixes = {
        "order_id":    "ORD",
        "delivery_id": "DEL",
        "waste_id":    "WST",
        "line_id":     "LIN",
        "po_id":       "PO",
    }
    for id_col, prefix in id_prefixes.items():
        if id_col in SCHEMA_COLS.get(target_schema, []) and id_col not in df.columns:
            df[id_col] = df.apply(lambda r, p=prefix: _row_hash(r, p), axis=1)
            inferences.append(f"Generated {id_col} from row hash (prefix {prefix})")

    return df, inferences
