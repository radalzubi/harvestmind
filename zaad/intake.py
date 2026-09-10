"""CSV bundle -> canonical as-of snapshot, with no shared/training database writes."""
from __future__ import annotations

import csv
import io
import json

from zaad.contracts import PlanningRequest

TABLES = frozenset({"items", "nodes", "edges", "routes", "demand", "deliveries", "inventory", "pipeline"})
JSON_COLUMNS = {"edges", "failure_domains"}
BOOL_COLUMNS = {"approved", "available", "cancelable"}


def load_csv_bundle(metadata: dict, tables: dict[str, str]) -> PlanningRequest:
    """Each table is UTF-8 CSV text; list cells use JSON, booleans true/false.

    The caller must resolve source PO revisions and units explicitly. Unknown
    columns, ambiguous dates, future records and incomplete references fail
    validation. Empty history periods must be explicit zeros, never fabricated.
    """
    if set(tables)-TABLES or set(metadata).intersection(TABLES):
        raise ValueError("unknown or duplicated CSV table")
    if sum(len(t.encode("utf-8")) for t in tables.values()) > 2*1024*1024:
        raise ValueError("CSV bundle exceeds 2 MiB")
    payload = dict(metadata)
    for table, contents in tables.items():
        reader = csv.DictReader(io.StringIO(contents))
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("missing or duplicate CSV columns")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError("CSV row has extra columns")
            record: dict = {k:v for k,v in row.items() if v not in ("", None)}
            for field in JSON_COLUMNS.intersection(record):
                record[field] = json.loads(record[field])
            for field in BOOL_COLUMNS.intersection(record):
                if record[field] not in ("true", "false"):
                    raise ValueError("CSV boolean must be true or false")
                record[field] = record[field] == "true"
            rows.append(record)
            if len(rows) > 12480:
                raise ValueError("CSV exceeds row bound")
        payload[table] = rows
    return PlanningRequest.model_validate(payload)


def export_csv_bundle(request: PlanningRequest) -> tuple[dict, dict[str, str]]:
    payload = request.model_dump(mode="json")
    tables = {}
    for name in sorted(TABLES):
        rows = payload.pop(name)
        if not rows:
            # Empty optional tables can be omitted, not represented by fake rows.
            continue
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v) if isinstance(v,(list,bool)) else v for k,v in row.items()})
        tables[name] = stream.getvalue()
    return payload, tables
