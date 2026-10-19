"""Walmart M5 (Kaggle "M5 Forecasting - Accuracy", data provider Walmart, organised by the M Open Forecasting Center,
University of Nicosia) into a dedicated DuckDB file.

Access and terms. The archive was downloaded by the repository owner from the Kaggle competition page, which requires a
Kaggle account and acceptance of the competition rules; those rules govern use of the data and were not retrievable
without a login from this environment. The raw files are therefore never committed, never redistributed from this
repository, and used here only for internal research validation; any use beyond the competition's research terms needs
the owner's confirmation against the rules text. The four source files are reconciled against a fixed manifest
(SHA-256, size) before anything is read; a file that differs is refused.

Content. `sales_train_evaluation.csv` holds unit sales for 30,490 store-item series over 1,941 days (d_1 = 2011-01-29
to d_1941 = 2016-05-22; the calendar file runs 28 days further, to 2016-06-19, for the competition's forecast period); `sales_train_validation.csv` is the same series truncated at d_1913 (the audit checks the two
agree on d_1..d_1913, so only the evaluation file is loaded). `calendar.csv` maps d_n to dates, Walmart weeks
(`wm_yr_wk`, Saturday to Friday), events and SNAP days; `sell_prices.csv` gives the weekly shelf price per store-item.
Sales are OBSERVED unit sales, not demand: stockouts are not annotated, so censoring cannot be measured on this
dataset. Days before an item's first price row are days the item was not listed, not zero demand.

Knowledge rule (declared): a day's sales become knowable at 23:59:59 UTC of that day; a week's price is knowable at
the start of its Walmart week (prices are set ahead of the week).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any

import duckdb

DATASET = "M5 Forecasting - Accuracy (Walmart)"
TERMS = "Kaggle competition rules (login required to view); internal research validation only; raw files never committed"
KNOWLEDGE_RULE = "END_OF_DAY_UTC for sales; START_OF_WALMART_WEEK for prices"
FIRST_DAY = date(2011, 1, 29)
DAYS = 1941
SERIES = 30_490

MANIFEST: dict[str, dict[str, Any]] = {
    "calendar.csv": {"sha256": "d12b5914ef03e66649adf5dd9e996e6602251c22b7a6af8f1f7e3aa12f8860f5", "bytes": 103469},
    "sales_train_validation.csv": {"sha256": "f368e66ed1dbecb48b2cc8fc589bf68b3deddbbb36bf5c88b4d6d0a09b9b6724", "bytes": 120007726},
    "sales_train_evaluation.csv": {"sha256": "4b4a47c44c38380d2a9168216fea8c9ff2f31b1ddb772f8a0995952a038b8aa0", "bytes": 121736518},
    "sell_prices.csv": {"sha256": "9da3ad1f8b8ccacdbdc70612191dd375ec24a4ac6625c24b75b3bc60b0bed2ef", "bytes": 203395785},
}
DEFAULT_RAW = Path("data/public/m5/raw")
DEFAULT_DB = Path("data/public/m5/m5.duckdb")


class DatasetMismatch(ValueError):
    """The supplied file is not the audited M5 release."""


@dataclass(frozen=True)
class Verified:
    name: str
    path: Path
    sha256: str
    bytes: int


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: str | Path, name: str) -> Verified:
    if name not in MANIFEST:
        raise DatasetMismatch(f"{name} is not an M5 file name (expected {sorted(MANIFEST)})")
    p = Path(path)
    if not p.is_file():
        raise DatasetMismatch(f"{name}: no file at {p}")
    size = p.stat().st_size
    if size != MANIFEST[name]["bytes"]:
        raise DatasetMismatch(f"{name}: {size} bytes, the audited release has {MANIFEST[name]['bytes']}")
    digest = sha256_of(p)
    if digest != MANIFEST[name]["sha256"]:
        raise DatasetMismatch(f"{name}: sha256 {digest} differs from the audited release")
    return Verified(name, p, digest, size)


def _one(conn: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> tuple[Any, ...]:
    row = conn.execute(sql, params or []).fetchone()
    if row is None:
        raise DatasetMismatch(f"query returned no row: {sql[:80]}")
    return row


def load(raw: str | Path = DEFAULT_RAW, db: str | Path = DEFAULT_DB, *, replace: bool = False) -> Path:
    """Verify the four files and load `m5_daily`, `m5_calendar`, `m5_prices` and `m5_manifest` into `db`."""
    raw_dir = Path(raw)
    verified = [verify(raw_dir / name, name) for name in MANIFEST]
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
        conn.execute("CREATE TABLE m5_calendar AS SELECT CAST(date AS DATE) AS d, wm_yr_wk, weekday, wday, month, year, d AS dkey, "
                     "CAST(substr(d, 3) AS INTEGER) AS dnum, event_name_1, event_type_1, event_name_2, event_type_2, snap_CA, snap_TX, snap_WI "
                     "FROM read_csv(?, header=true)", [str(raw_dir / "calendar.csv")])
        conn.execute("CREATE TABLE m5_prices AS SELECT store_id, item_id, wm_yr_wk, sell_price FROM read_csv(?, header=true)", [str(raw_dir / "sell_prices.csv")])
        day_cols = [r[0] for r in conn.execute("SELECT column_name FROM (DESCRIBE SELECT * FROM read_csv(?, header=true)) WHERE regexp_matches(column_name, '^d_[0-9]+$')",
                                               [str(raw_dir / "sales_train_evaluation.csv")]).fetchall()]
        if len(day_cols) != DAYS:
            raise DatasetMismatch(f"{len(day_cols)} day columns in sales_train_evaluation.csv, expected {DAYS}")
        conn.execute("CREATE TEMP TABLE wide AS SELECT * FROM read_csv(?, header=true)", [str(raw_dir / "sales_train_evaluation.csv")])
        cols = ", ".join(day_cols)
        conn.execute(f"""CREATE TABLE m5_daily AS
            SELECT u.id, u.item_id, u.dept_id, u.cat_id, u.store_id, u.state_id, c.d, CAST(substr(u.dkey, 3) AS INTEGER) AS dnum, CAST(u.qty AS DOUBLE) AS qty
            FROM (UNPIVOT wide ON {cols} INTO NAME dkey VALUE qty) u JOIN m5_calendar c ON c.dkey = u.dkey""")  # noqa: S608  # nosec B608 - column names come from DESCRIBE, matched ^d_[0-9]+$
        conn.execute("DROP TABLE wide")
        _check_invariants(conn, raw_dir)
        conn.execute("CREATE INDEX m5_daily_series ON m5_daily(store_id, item_id, d)")
        conn.execute("CREATE INDEX m5_prices_key ON m5_prices(store_id, item_id, wm_yr_wk)")
        conn.execute("CREATE TABLE m5_manifest (file VARCHAR, sha256 VARCHAR, bytes BIGINT, dataset VARCHAR, terms VARCHAR, knowledge_rule VARCHAR, evidence VARCHAR, loaded_at TIMESTAMP)")
        for v in verified:
            conn.execute("INSERT INTO m5_manifest VALUES (?, ?, ?, ?, ?, ?, 'OBSERVED', ?)",
                         [v.name, v.sha256, v.bytes, DATASET, TERMS, KNOWLEDGE_RULE, datetime.now(timezone.utc).replace(tzinfo=None)])
    except Exception:
        conn.close()
        if db_path.exists():
            os.remove(db_path)
        raise
    conn.close()
    return db_path


def _check_invariants(conn: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    series, days, dmin, dmax, neg, nulls, dup = _one(conn, """SELECT count(DISTINCT id), count(DISTINCT dnum), min(dnum), max(dnum),
        count(*) FILTER (WHERE qty < 0), count(*) FILTER (WHERE qty IS NULL),
        (SELECT count(*) FROM (SELECT id, dnum FROM m5_daily GROUP BY 1, 2 HAVING count(*) > 1)) FROM m5_daily""")
    problems = []
    if series != SERIES:
        problems.append(f"{series} series, the audited release has {SERIES}")
    if (days, dmin, dmax) != (DAYS, 1, DAYS):
        problems.append(f"days {dmin}..{dmax} ({days} distinct), expected 1..{DAYS}")
    if neg or nulls or dup:
        problems.append(f"{neg} negative, {nulls} null, {dup} duplicate quantities")
    first = _one(conn, "SELECT min(d) FROM m5_daily WHERE dnum = 1")[0]
    if first != FIRST_DAY:
        problems.append(f"d_1 maps to {first}, expected {FIRST_DAY}")
    # the validation file is the evaluation file truncated at d_1913 (so only one file carries sales)
    agree = _one(conn, """SELECT sum(CASE WHEN v.d_1913 = e.qty THEN 1 ELSE 0 END), count(*) FROM read_csv(?, header=true) v
                           JOIN m5_daily e ON e.dnum = 1913 AND e.id = replace(v.id, '_validation', '_evaluation')""", [str(raw_dir / "sales_train_validation.csv")])
    if agree[0] != agree[1] or agree[1] != SERIES:
        problems.append(f"validation file disagrees with evaluation file on d_1913 ({agree[0]} of {agree[1]} rows agree)")
    if problems:
        raise DatasetMismatch("source files violate the audited invariants: " + "; ".join(problems))


def _manifest_matches(conn: duckdb.DuckDBPyConnection) -> bool:
    try:
        rows = conn.execute("SELECT file, sha256, bytes FROM m5_manifest").fetchall()
    except duckdb.Error:
        return False
    found = {r[0]: (r[1], r[2]) for r in rows}
    return all(found.get(n) == (m["sha256"], m["bytes"]) for n, m in MANIFEST.items())


def connect(db: str | Path = DEFAULT_DB, *, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    path = Path(db)
    if not path.exists():
        raise FileNotFoundError(f"{path} is not loaded; run zaad.public.m5.loader.load first")
    conn = duckdb.connect(str(path), read_only=read_only)
    conn.execute("SET enable_progress_bar = false")
    if not _manifest_matches(conn):
        conn.close()
        raise DatasetMismatch(f"{path} does not carry the audited manifest")
    return conn


def manifest_record(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    rows = conn.execute("SELECT file, sha256, bytes, dataset, terms, knowledge_rule, evidence, loaded_at FROM m5_manifest ORDER BY file").fetchall()
    return {r[0]: {"sha256": r[1], "bytes": r[2], "dataset": r[3], "terms": r[4], "knowledge_rule": r[5], "evidence": r[6], "loaded_at": r[7].isoformat()} for r in rows}
