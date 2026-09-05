"""Anonymise an operator export BEFORE it is stored.

The engine needs identities only to join tables (a PO to its receipts, a
SKU to its supplier), never to know what they are. This module replaces
every identifier column with a keyed hash (HMAC-SHA256, per-operator
secret, truncated), drops free-text name, address and contact columns,
and leaves quantities, prices and dates untouched. The same secret gives
the same hash in every table, so joins survive; without the secret the
hashes cannot be reversed or linked back to the operator's real codes.

Two ways to use it:

  * server side: ``POST /intake/upload/{table}?anonymize=true`` (the
    default for pilot operators) applies it before the raw file reaches
    the vault, with a secret held in the operator registry, never in the
    database;
  * client side: ``python scripts/anonymize_export.py --secret ... file.csv``
    lets the operator anonymise on their own machine so real codes never
    leave it. The operator keeps the secret; the report they get back maps
    only hashed ids, which they can resolve locally.
"""

from __future__ import annotations

import hashlib
import hmac
import io
from dataclasses import dataclass, field

import pandas as pd

# Identifier columns: hashed consistently across tables. Names that act as
# keys in the agriculture schema (product_name, supplier_name, buyer_name)
# are hashed, not dropped, so joins survive and the name itself never lands.
ID_COLUMNS = {
    "sku", "product_id", "supplier_id", "customer_id", "po_id", "order_id", "receipt_id",
    "lot_id", "location_id", "warehouse_id", "manufacturer", "carrier", "buyer_id", "vendor_id",
    "item_code", "material", "batch", "batch_id", "invoice_id",
    "product_name", "supplier_name", "vendor_name", "customer_name", "buyer_name", "name",
    "company", "company_name", "brand", "brand_name",
}
# Free text that can identify people: dropped, never stored.
DROP_COLUMNS = {
    "description", "contact", "contact_name", "email", "phone", "address", "address1", "address2",
    "city", "notes", "comment", "comments", "remarks",
}
HASH_CHARS = 16


@dataclass
class AnonymizationReport:
    hashed_columns: list = field(default_factory=list)
    dropped_columns: list = field(default_factory=list)
    rows: int = 0
    untouched_columns: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def hash_id(value: object, secret: bytes | str) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return ""
    key = secret.encode() if isinstance(secret, str) else secret
    digest = hmac.new(key, str(value).strip().encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:HASH_CHARS]


def anonymize_frame(df: pd.DataFrame, secret: bytes | str, *, extra_id_columns: tuple = (),
                    extra_drop_columns: tuple = ()) -> tuple[pd.DataFrame, AnonymizationReport]:
    if not secret:
        raise ValueError("an anonymisation secret is required")
    ids = ID_COLUMNS | {c.lower() for c in extra_id_columns}
    drops = DROP_COLUMNS | {c.lower() for c in extra_drop_columns}
    out = df.copy()
    rep = AnonymizationReport(rows=len(df))
    for col in list(out.columns):
        low = str(col).strip().lower()
        if low in drops:
            out = out.drop(columns=[col])
            rep.dropped_columns.append(str(col))
        elif low in ids or low.endswith("_id") and low not in ("operator_id",):
            out[col] = out[col].map(lambda v: hash_id(v, secret))
            rep.hashed_columns.append(str(col))
        else:
            rep.untouched_columns.append(str(col))
    return out, rep


def anonymize_csv_bytes(contents: bytes, secret: bytes | str, **kw) -> tuple[bytes, AnonymizationReport]:
    df = pd.read_csv(io.BytesIO(contents))
    out, rep = anonymize_frame(df, secret, **kw)
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8"), rep


def looks_anonymized(df: pd.DataFrame) -> bool:
    """Heuristic: every id column is a 16-hex-char hash and no drop column remains."""
    cols = {str(c).strip().lower() for c in df.columns}
    if cols & DROP_COLUMNS:
        return False
    for col in df.columns:
        low = str(col).strip().lower()
        if low in ID_COLUMNS or (low.endswith("_id") and low != "operator_id"):
            vals = df[col].dropna().astype(str).head(50)
            if len(vals) and not all(len(v) == HASH_CHARS and all(ch in "0123456789abcdef" for ch in v) for v in vals):
                return False
    return True
