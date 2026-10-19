"""FreshRetailNet-50K (Dingdong-Inc, CC BY 4.0, arXiv 2505.16319) into a dedicated DuckDB file.

The two source Parquet files are reconciled against a fixed manifest (SHA-256, size, rows) before anything is read;
a file that differs is refused, never "mostly loaded". Two invariants the audit established on every row are
re-checked at load and fail the load when violated: `sale_amount == sum(hours_sale)`, and
`stock_hour6_22_cnt == sum(hours_stock_status[6..21])` (16 business hours, flag 1 = out of stock, as the official
baseline code treats it; the paper's prose inverts the sign). Quantities are the dataset's normalized units: not
pieces, not kilograms, not currency. Everything written here is OBSERVED; nothing is imputed.

Knowledge rule (declared, not in the data): a day's sales and stock flags become knowable at 23:59:59 UTC of that
calendar day. The source files carry dates only and no timezone; the rule is applied identically to every policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import duckdb

DATASET = "FreshRetailNet-50K"
LICENSE = "CC BY 4.0"
CITATION = "Wang et al., FreshRetailNet-50K: A Stockout-Annotated Censored Demand Dataset for Latent Demand Recovery and Forecasting in Fresh Retail, arXiv:2505.16319 (2025)"
KNOWLEDGE_RULE = "END_OF_DAY_UTC"         # observations of day d are knowable at d 23:59:59 UTC
BUSINESS_HOURS = range(6, 22)             # the 16 hours the stockout count covers (06:00..21:59)
OUT_OF_STOCK_FLAG = 1

#: the audited files; a file that does not match is refused
MANIFEST: dict[str, dict[str, Any]] = {
    "train.parquet": {"sha256": "6706832db892bbae4969c19d87e07975d2543d2ba7d7d4756360654785de5a3d", "bytes": 106436287, "rows": 4_500_000,
                      "first_day": "2024-03-28", "last_day": "2024-06-25", "days": 90},
    "eval.parquet": {"sha256": "1b118840664280c6b88bffc84c80ee1f54c05d911e354b7599e5da10995e960e", "bytes": 8440124, "rows": 350_000,
                     "first_day": "2024-06-26", "last_day": "2024-07-02", "days": 7},
}
SERIES = 50_000
DEFAULT_DB = Path("data/public/freshretailnet/frn.duckdb")


class DatasetMismatch(ValueError):
    """The supplied file is not the audited FreshRetailNet-50K release."""


@dataclass(frozen=True)
class Verified:
    name: str
    path: Path
    sha256: str
    bytes: int


def _one(conn: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> tuple[Any, ...]:
    row = conn.execute(sql, params or []).fetchone()
    if row is None:
        raise DatasetMismatch(f"query returned no row: {sql[:80]}")
    return row


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: str | Path, name: str) -> Verified:
    """Reconcile one source file against the manifest. Raises DatasetMismatch on any difference."""
    if name not in MANIFEST:
        raise DatasetMismatch(f"{name} is not a FreshRetailNet-50K file name (expected {sorted(MANIFEST)})")
    p = Path(path)
    if not p.is_file():
        raise DatasetMismatch(f"{name}: no file at {p}")
    size = p.stat().st_size
    if size != MANIFEST[name]["bytes"]:
        raise DatasetMismatch(f"{name}: {size} bytes, the audited release has {MANIFEST[name]['bytes']}")
    digest = sha256_of(p)
    if digest != MANIFEST[name]["sha256"]:
        raise DatasetMismatch(f"{name}: sha256 {digest} differs from the audited release {MANIFEST[name]['sha256']}")
    return Verified(name, p, digest, size)


def load(train: str | Path, eval_: str | Path, db: str | Path = DEFAULT_DB, *, replace: bool = False) -> Path:
    """Verify both files and load them into `db` as `frn_daily`, `frn_hourly` and `frn_manifest`.

    Idempotent: an existing database whose manifest matches is left alone unless `replace=True`. The database is
    a derived artefact of the two verified files and is never committed (`*.duckdb` is git-ignored)."""
    verified = [verify(train, "train.parquet"), verify(eval_, "eval.parquet")]
    db_path = Path(db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and not replace:
        with duckdb.connect(str(db_path), read_only=True) as conn:
            if _manifest_matches(conn):
                return db_path
        raise DatasetMismatch(f"{db_path} exists but its manifest does not match the audited release; load with replace=True")
    if db_path.exists():
        os.remove(db_path)
    conn = duckdb.connect(str(db_path))
    try:
        parts = []
        for v in verified:
            split = "train" if v.name.startswith("train") else "eval"
            parts.append(f"""SELECT '{split}' AS split, city_id, store_id, management_group_id, first_category_id, second_category_id,
                third_category_id, product_id, CAST(dt AS DATE) AS d, sale_amount, stock_hour6_22_cnt AS stock_hours_out, discount,
                holiday_flag, activity_flag, precpt, avg_temperature, avg_humidity, avg_wind_level, hours_sale, hours_stock_status
                FROM read_parquet('{v.path.as_posix()}')""")
        conn.execute("CREATE TABLE frn_daily AS " + " UNION ALL ".join(parts))
        _check_invariants(conn)
        conn.execute("""CREATE TABLE frn_hourly AS
            SELECT split, store_id, product_id, d, unnest(range(24)) AS hour, unnest(hours_sale) AS sale,
                   unnest(hours_stock_status) AS out_of_stock FROM frn_daily""")
        conn.execute("ALTER TABLE frn_daily DROP COLUMN hours_sale")
        conn.execute("ALTER TABLE frn_daily DROP COLUMN hours_stock_status")
        conn.execute("""CREATE TABLE frn_manifest (file VARCHAR, sha256 VARCHAR, bytes BIGINT, rows BIGINT, dataset VARCHAR, license VARCHAR,
                                                   knowledge_rule VARCHAR, evidence VARCHAR, loaded_at TIMESTAMP)""")
        for v in verified:
            rows = _one(conn, "SELECT count(*) FROM frn_daily WHERE split = ?", ["train" if v.name.startswith("train") else "eval"])[0]
            if rows != MANIFEST[v.name]["rows"]:
                raise DatasetMismatch(f"{v.name}: {rows} rows loaded, manifest says {MANIFEST[v.name]['rows']}")
            conn.execute("INSERT INTO frn_manifest VALUES (?, ?, ?, ?, ?, ?, ?, 'OBSERVED', ?)",
                         [v.name, v.sha256, v.bytes, rows, DATASET, LICENSE, KNOWLEDGE_RULE, datetime.now(timezone.utc).replace(tzinfo=None)])
        conn.execute("CREATE INDEX frn_daily_series ON frn_daily(store_id, product_id, d)")
    except Exception:
        conn.close()
        if db_path.exists():
            os.remove(db_path)
        raise
    conn.close()
    return db_path


def _manifest_matches(conn: duckdb.DuckDBPyConnection) -> bool:
    try:
        rows = conn.execute("SELECT file, sha256, bytes, rows FROM frn_manifest").fetchall()
    except duckdb.Error:
        return False
    found = {r[0]: (r[1], r[2], r[3]) for r in rows}
    return all(found.get(n) == (m["sha256"], m["bytes"], m["rows"]) for n, m in MANIFEST.items())


def _check_invariants(conn: duckdb.DuckDBPyConnection) -> None:
    """The structural facts the audit established; a violation means the file is not what was audited."""
    lo, hi = BUSINESS_HOURS.start + 1, BUSINESS_HOURS.stop          # DuckDB list slices are 1-based and inclusive
    bad = _one(conn, f"""SELECT
        count(*) FILTER (WHERE abs(list_sum(hours_sale) - sale_amount) > 1e-6),
        count(*) FILTER (WHERE list_sum(hours_stock_status[{lo}:{hi}]) <> stock_hours_out),
        count(*) FILTER (WHERE len(hours_sale) <> 24 OR len(hours_stock_status) <> 24),
        count(*) FILTER (WHERE sale_amount < 0 OR sale_amount IS NULL),
        count(*) FILTER (WHERE list_max(hours_stock_status) > 1 OR list_min(hours_stock_status) < 0),
        (SELECT count(*) FROM (SELECT store_id, product_id, d FROM frn_daily GROUP BY 1,2,3 HAVING count(*) > 1)),
        (SELECT count(DISTINCT (store_id, product_id)) FROM frn_daily)
        FROM frn_daily""")
    names = ("sum(hours_sale) != sale_amount", "stock_hours_out != sum(flags 6..21)", "list length != 24", "negative or null sales",
             "flag outside {0,1}", "duplicate (store, product, day) keys")
    problems = [f"{n}: {c} rows" for n, c in zip(names, bad[:6]) if c]
    if bad[6] != SERIES:
        problems.append(f"{bad[6]} series, the audited release has {SERIES}")
    if problems:
        raise DatasetMismatch("source files violate the audited invariants: " + "; ".join(problems))


def connect(db: str | Path = DEFAULT_DB, *, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    path = Path(db)
    if not path.exists():
        raise FileNotFoundError(f"{path} is not loaded; run zaad.public.freshretailnet.loader.load first")
    conn = duckdb.connect(str(path), read_only=read_only)
    if not _manifest_matches(conn):
        conn.close()
        raise DatasetMismatch(f"{path} does not carry the audited manifest")
    return conn


def manifest_record(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    rows = conn.execute("SELECT file, sha256, bytes, rows, dataset, license, knowledge_rule, evidence, loaded_at FROM frn_manifest ORDER BY file").fetchall()
    return {r[0]: {"sha256": r[1], "bytes": r[2], "rows": r[3], "dataset": r[4], "license": r[5], "knowledge_rule": r[6], "evidence": r[7],
                   "loaded_at": r[8].isoformat()} for r in rows}


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
