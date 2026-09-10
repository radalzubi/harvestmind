"""Strict CSV bundles and version reconciliation; no database/training writes."""
from __future__ import annotations

import csv
from datetime import datetime
import io
import json

from zaad.full.contracts import Request

TABLES = ("skus", "locations", "calendars", "terms", "resources", "sources", "stock",
          "transfers", "inbound_transfers", "substitutions", "customers", "services", "history",
          "shipment_history", "pipeline", "order_lines", "events", "incumbent_orders")


def export_bundle(req: Request) -> dict[str, str]:
    data = req.model_dump(mode="json")
    output = {}
    for table in TABLES:
        rows = data.pop(table)
        columns = list(rows[0]) if rows else []
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, allow_nan=False) for k, v in row.items()})
        output[table + ".csv"] = stream.getvalue()
    output["metadata.json"] = json.dumps(data, indent=2, allow_nan=False)
    output["schema.json"] = json.dumps(Request.model_json_schema(), indent=2)
    return output


def import_bundle(files: dict[str, str]) -> Request:
    allowed = {t + ".csv" for t in TABLES} | {"metadata.json", "schema.json"}
    if set(files) - allowed or "metadata.json" not in files:
        raise ValueError("unknown table or missing metadata.json")
    if sum(len(v.encode()) for v in files.values()) > 64 * 1024 * 1024:
        raise ValueError("CSV bundle exceeds 64 MiB offline bound")
    data = json.loads(files["metadata.json"])
    if any(t in data for t in TABLES):
        raise ValueError("tables must not appear in both metadata and CSV")
    for table in TABLES:
        if table + ".csv" not in files:
            raise ValueError(f"explicit table required, even if empty: {table}")
        reader = csv.DictReader(io.StringIO(files[table + ".csv"]))
        if reader.fieldnames and len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("duplicate CSV headers")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("ragged CSV row")
            rows.append({k: json.loads(v) for k, v in row.items()})
        data[table] = rows
    return Request.model_validate(data)


def resolve_po_revisions(rows: list[dict], as_of: datetime) -> list[dict]:
    if as_of.tzinfo is None:
        raise ValueError("aware as-of time required")
    seen: set[tuple] = set()
    latest: dict[str, dict] = {}
    for row in rows:
        known = datetime.fromisoformat(row["known_at"]) if isinstance(row["known_at"], str) else row["known_at"]
        if known.tzinfo is None:
            raise ValueError("aware revision clock required")
        key = row["id"], row["revision"]
        if key in seen:
            raise ValueError("duplicate PO revision")
        seen.add(key)
        if known <= as_of and (row["id"] not in latest or row["revision"] > latest[row["id"]]["revision"]):
            latest[row["id"]] = row
    return list(latest.values())
