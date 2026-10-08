"""Canonical request fingerprint and causal attestation (HARDENING V1, H0).

Instrumentation only. Nothing here is called by the planner, the replay, the workspace adapter or the
API; importing this module changes no recommendation.

TIME

    event_at          when the event physically / commercially happens
    source_known_at   when the operator could have known it
    ingested_at       when ZAAD received the record

A fact may reach a decision taken at T only if `source_known_at < T`. That is not a statement about
`event_at`: a delivery promised for next Thursday is a future event the buyer already knows. And it is
never a statement about `ingested_at`. This module therefore fixes no knowledge rule. Whoever builds a
perturbation family passes an `Availability` predicate, `is_available_at(fact, decision_at) -> bool`,
and the family asks it which facts were knowable.

The vault has no `source_known_at` column for receipts. The one predicate shipped here,
`legacy_date_only_receipt_availability`, treats a receipt as known from its own date. It is a stated
test assumption for date-only receipt rows, sufficient to exhibit the receipt defect of commit 6704926,
and not the production knowledge rule (that belongs to H1b and the onboarding contract).

THE PROJECTION (`PROJECTION_VERSION`)

The causal identity of a request is the whole frozen contract `zaad.full.contracts.Request`. Every field
is included unless `EXCLUDED_PATHS` names it, and `EXCLUDED_PATHS` is empty: the contract forbids extra
fields and carries no build, run, session or import metadata, and every field it does carry is read by
`plan()`, `settle()`, a comparator, the economic scoring or the readiness labels. What is outside the
projection is everything that is not the request: the adapter's build report, vault columns the adapter
does not read (`imported_at`, `_upload_session_id`, `_uploaded_at`, `_source_file`), wall-clock time.

IDENTITY RULE AND ORDER

Two requests that can produce different planning, settlement, comparator, readiness or economic
behaviour must not share a fingerprint. A spurious difference is acceptable; a spurious equality is not.

Order is therefore part of the identity everywhere it has not been shown to be irrelevant:

- every sequence keeps its order, including all 22 top-level row collections (skus, locations,
  calendars, terms, resources, sources, stock, transfers, substitutions, customers, services, history,
  order_lines, events, shipment_history, signals, pipeline, inbound_transfers, incumbent_orders,
  incumbent_transfers, supplier_terms, sku_physics). Consumers are known to depend on it: `worlds.draw`
  consumes one random stream service by service and order by order, the model creates variables in
  collection order (solver ties), and `uncertainty.py` breaks `known_at` ties by position;
- a free mapping (`dict`) keeps its insertion order, unless it is listed in `ORDER_FREE_MAPPINGS`;
- `ORDER_FREE_MAPPINGS` holds `economics_provenance` only: its consumers look labels up by key
  (`economics.provenance`, `sourcing/explain.py`), and a behavioural permutation test pins that;
- the fields of a contract model are written in name order: a model's field order is fixed by its
  class and cannot differ between two requests.

CANONICAL FORM

- no whitespace; ASCII; model fields in name order;
- timestamps: timezone-aware only, converted to UTC, microsecond ISO-8601 (a naive datetime is refused);
- numbers: exact. Integers as integers; floats by their shortest round-trip representation, so two
  different doubles never serialise alike. No rounding. The only normalisation is `-0.0` to `0.0`,
  which are the same quantity;
- the digest covers the projection version and the contract's schema version.

A value of a type this module does not know is refused rather than stringified.

CAUSAL STATUS (what a report may be used for; distinct from solver evidence classes)

    PASS      eligible to be called causally attested, subject to the other evidence gates
    FAIL      the historical / replay result is not valid for causal evidence claims
    NOT_RUN   usable for internal debugging and development only; it may not be described as causally
              attested and may not support a validated historical savings claim

Nothing customer-visible reads these yet.
"""
from __future__ import annotations

import hashlib
import json
import math
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from numbers import Integral, Real
from typing import Any, Callable, ContextManager, Iterable, Iterator, Literal, Mapping

from pydantic import BaseModel

from zaad.full.contracts import Request

PROJECTION_VERSION = "zaad.causal.request.v1"

# path -> why it cannot affect plan(), settle(), candidate evaluation, a comparator, the economic scoring
# or decision readiness. Empty on purpose (see the module docstring); an entry needs that justification.
EXCLUDED_PATHS: dict[str, str] = {}

# top-level mapping -> the evidence that its key order cannot matter. Everything else keeps its order.
ORDER_FREE_MAPPINGS: dict[str, str] = {
    "economics_provenance": "labels looked up by key only (economics.provenance, sourcing/explain.py); "
                            "tests/unit/test_zaad_causal_fingerprint.py::test_the_one_order_free_mapping_is_order_free_in_behaviour"}

# what names a row when reporting a difference (the hash never depends on this)
IDENTITY_KEYS: dict[str, tuple[str, ...]] = {"history": ("service", "period"), "incumbent_orders": ("source", "period"),
                                             "incumbent_transfers": ("transfer", "period", "expiry")}
_ORDERED_MAP = "$ordered_map"


class CanonicalizationError(TypeError):
    """A value the canonical form has no exact, deterministic representation for."""


def _canon(value: Any, path: str) -> Any:
    if isinstance(value, BaseModel):
        out = {}
        for name in sorted(type(value).model_fields):
            here = f"{path}.{name}" if path else name
            if here not in EXCLUDED_PATHS:
                out[name] = _canon(getattr(value, name), here)
        return out
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, Enum):
        return _canon(value.value, path)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise CanonicalizationError(f"{path}: a timestamp without a timezone has no instant")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise CanonicalizationError(f"{path}: a non-finite number has no canonical form")
        return 0.0 if number == 0 else number
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise CanonicalizationError(f"{path}: a mapping key that is not text")
        if path in ORDER_FREE_MAPPINGS:
            return {key: _canon(value[key], f"{path}.{key}") for key in sorted(value)}
        return {_ORDERED_MAP: [[key, _canon(item, f"{path}.{key}" if path else key)] for key, item in value.items()]}
    if isinstance(value, (list, tuple)):
        return [_canon(item, f"{path}[{i}]") for i, item in enumerate(value)]
    raise CanonicalizationError(f"{path}: {type(value).__name__} has no canonical form")


def _bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def canonical_projection(req: Request) -> dict:
    """The decision-relevant content of a request in canonical form (see the module docstring)."""
    body = _canon(req, "")
    return {"projection_version": PROJECTION_VERSION, "schema_version": body.get("schema_version"), "request": body}


@dataclass(frozen=True)
class RequestFingerprint:
    hash: str
    projection_version: str
    schema_version: str | None

    def as_dict(self) -> dict:
        return {"hash": self.hash, "projection_version": self.projection_version, "schema_version": self.schema_version}


def fingerprint(req: Request) -> RequestFingerprint:
    """SHA-256 over the canonical projection, with the projection version it was computed under."""
    projection = canonical_projection(req)
    return RequestFingerprint(hashlib.sha256(_bytes(projection)).hexdigest(), projection["projection_version"], projection["schema_version"])


# ── first differing field ────────────────────────────────────────────────────
def _show(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        text = _bytes(value).decode("ascii")
        return text if len(text) <= 240 else text[:237] + "..."
    return value


def _row_key(collection: str, row: Any) -> str | None:
    keys = IDENTITY_KEYS.get(collection, ("id",))
    if isinstance(row, dict) and all(k in row for k in keys):
        return ",".join(f"{k}={row[k]}" for k in keys)
    return None


def _diff(a: Any, b: Any, path: str) -> dict | None:
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) == set(b) == {_ORDERED_MAP}:
            return _diff_rows(a[_ORDERED_MAP], b[_ORDERED_MAP], path, [r[0] for r in a[_ORDERED_MAP]], [r[0] for r in b[_ORDERED_MAP]])
        for key in sorted(set(a) | set(b)):
            here = f"{path}.{key}" if path else key
            if key not in a or key not in b:
                return {"path": here, "base": _show(a.get(key, "<absent>")), "variant": _show(b.get(key, "<absent>"))}
            x, y = a[key], b[key]
            if not path and isinstance(x, list) and isinstance(y, list):
                found = _diff_rows(x, y, here, [_row_key(key, r) for r in x], [_row_key(key, r) for r in y])
            else:
                found = _diff(x, y, here)
            if found:
                return found
        return None
    if isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b)):
            found = _diff(x, y, f"{path}[{i}]")
            if found:
                return found
        if len(a) != len(b):
            return {"path": f"{path}[{min(len(a), len(b))}]", "base": f"{len(a)} item(s)", "variant": f"{len(b)} item(s)"}
        return None
    if type(a) is not type(b) or a != b:
        return {"path": path, "base": _show(a), "variant": _show(b)}
    return None


def _diff_rows(a: list, b: list, path: str, keys_a: list, keys_b: list) -> dict | None:
    """Rows that can be named are compared by name, so a row that appeared or vanished is reported as that
    row and not as a shift of everything after it; the same rows in another order are reported as order."""
    named = all(k is not None for k in keys_a + keys_b) and len(set(keys_a)) == len(keys_a) and len(set(keys_b)) == len(keys_b)
    if not named:
        return _diff(a, b, path)
    rows_a, rows_b = dict(zip(keys_a, a)), dict(zip(keys_b, b))
    for key in sorted(set(rows_a) | set(rows_b)):
        here = f"{path}[{key}]"
        if key not in rows_a:
            return {"path": here, "base": "<absent>", "variant": _show(rows_b[key])}
        if key not in rows_b:
            return {"path": here, "base": _show(rows_a[key]), "variant": "<absent>"}
        found = _diff(rows_a[key], rows_b[key], here)
        if found:
            return found
    if keys_a != keys_b:
        at = next(i for i, (x, y) in enumerate(zip(keys_a, keys_b)) if x != y)
        return {"path": f"{path}<order>[{at}]", "base": keys_a[at], "variant": keys_b[at]}
    return None


def first_difference(base: Request, variant: Request) -> dict | None:
    """The first field path at which two requests differ, or None when their fingerprints are equal."""
    return _diff(canonical_projection(base)["request"], canonical_projection(variant)["request"], "")


# ── availability ─────────────────────────────────────────────────────────────
# is_available_at(fact, decision_at): could the operator have known this fact before the decision time?
Availability = Callable[[Mapping[str, Any], datetime], bool]

LEGACY_DATE_ONLY = "LEGACY_DATE_ONLY_TEST_ASSUMPTION: a receipt row is taken to be known from its own receipt_date"


def legacy_date_only_receipt_availability(fact: Mapping[str, Any], decision_at: datetime) -> bool:
    """LEGACY / DATE-ONLY TEST ASSUMPTION, for receipt rows that carry a date and no knowledge time: the
    receipt is treated as known from its receipt date, so it is available at T when `receipt_date < T`.
    Not the production rule and not true of facts in general (a future event can already be known)."""
    return fact["receipt_date"] < decision_at.astimezone(timezone.utc).date()


legacy_date_only_receipt_availability.label = LEGACY_DATE_ONLY     # type: ignore[attr-defined]

CANONICAL = "CANONICAL: source_known_at < decision_at; date-only fallback (known from the start of the event date) for rows without one"


def canonical_receipt_availability(fact: Mapping[str, Any], decision_at: datetime) -> bool:
    """The H1b rule for a receipt row: the fact is available at the decision when the operator could have
    known it before — `source_known_at < decision_at` when the row carries a knowledge time, else the
    date-only fallback (known from the start of `receipt_date`). Import time plays no part."""
    cutoff = decision_at.astimezone(timezone.utc).replace(tzinfo=None)
    known = fact.get("source_known_at")
    if known is None or (isinstance(known, float) and known != known):
        when = fact["receipt_date"]
        known = datetime(when.year, when.month, when.day)
    elif getattr(known, "tzinfo", None) is not None:
        known = known.astimezone(timezone.utc).replace(tzinfo=None)
    return known < cutoff


canonical_receipt_availability.label = CANONICAL     # type: ignore[attr-defined]


# ── causal perturbation harness ──────────────────────────────────────────────
Control = Literal["negative", "positive"]
PASS, FAIL, NOT_RUN_STATUS = "PASS", "FAIL", "NOT_RUN"

CAUSAL_STATUS_MEANING: dict[str, str] = {
    PASS: "eligible to be called causally attested, subject to the other evidence gates",
    FAIL: "the historical / replay result is not valid for causal evidence claims",
    NOT_RUN_STATUS: "internal debugging and development only: not causally attested, and no support for a validated historical savings claim"}


@dataclass(frozen=True)
class Perturbation:
    """One controlled change of the source data.

    `variant(source)` is a context manager that yields `(perturbed_source, changed)`, where `changed` is how
    many source facts the change touched, and restores the source on exit. A perturbation that touched
    nothing proves nothing and is reported as vacuous, never as a pass.

    control "negative": the changed facts were not available at the decision time; the request must not change.
    control "positive": the changed facts were available at the decision time; the request must change.

    Which facts are available is decided by the family's `Availability` predicate, never by this class;
    `availability` names the rule that was used so that every report states it."""
    name: str
    family: str
    control: Control
    variant: Callable[[Any], ContextManager[tuple[Any, int]]]
    availability: str = "declared by the perturbation's author"


def pure(change: Callable[[Any], tuple[Any, int]]) -> Callable[[Any], ContextManager[tuple[Any, int]]]:
    """A variant for sources that are plain values: `change(source)` returns `(new_source, changed)`."""
    @contextmanager
    def variant(source: Any) -> Iterator[tuple[Any, int]]:
        yield change(source)
    return variant


def in_transaction(change: Callable[[Any], int]) -> Callable[[Any], ContextManager[tuple[Any, int]]]:
    """A variant for a DuckDB vault: `change(conn)` edits rows and returns how many; everything is rolled
    back on exit, so the vault is never left perturbed."""
    @contextmanager
    def variant(conn: Any) -> Iterator[tuple[Any, int]]:
        conn.execute("BEGIN TRANSACTION")
        try:
            yield conn, int(change(conn))
        finally:
            conn.execute("ROLLBACK")
    return variant


def not_run() -> dict:
    """The report of causal checks that did not run."""
    return {"status": NOT_RUN_STATUS, "all_clean": False, "meaning": CAUSAL_STATUS_MEANING[NOT_RUN_STATUS], "decision_at": None,
            "projection_version": PROJECTION_VERSION, "base_request_hash": None, "variants_checked": 0, "vacuous": 0, "families": [], "failures": []}


def run_causal_checks(build: Callable[[Any], Request], source: Any, perturbations: Iterable[Perturbation]) -> dict:
    """Build the request, rebuild it under every perturbation and compare canonical hashes.

    status PASS      at least one perturbation touched the source and every one behaved as its control says
           FAIL      a negative control changed the request, or a positive control did not
           NOT_RUN   no perturbation touched the source
    `all_clean` is true only for PASS: nothing is called clean because it was not checked."""
    base = build(source)
    base_print = fingerprint(base)
    families: dict[tuple[str, str], dict] = {}
    failures: list[dict] = []
    checked = vacuous = 0
    for p in perturbations:
        group = families.setdefault((p.family, p.control), {"family": p.family, "control": p.control, "availability_rules": [],
                                                           "variants_checked": 0, "vacuous": 0, "failures": 0})
        if p.availability not in group["availability_rules"]:
            group["availability_rules"].append(p.availability)
        with p.variant(source) as (perturbed, changed):
            if changed <= 0:
                vacuous += 1
                group["vacuous"] += 1
                continue
            rebuilt = build(perturbed)
        checked += 1
        group["variants_checked"] += 1
        rebuilt_print = fingerprint(rebuilt)
        same = rebuilt_print.hash == base_print.hash
        if same == (p.control == "negative"):
            continue
        group["failures"] += 1
        failures.append({"perturbation": p.name, "family": p.family, "control": p.control, "availability": p.availability,
                         "source_facts_changed": changed,
                         "expected": "request unchanged" if p.control == "negative" else "request changed",
                         "observed": "request unchanged" if same else "request changed",
                         "variant_request_hash": rebuilt_print.hash,
                         "first_difference": None if same else first_difference(base, rebuilt)})
    status = FAIL if failures else (PASS if checked else NOT_RUN_STATUS)
    return {"status": status, "all_clean": status == PASS, "meaning": CAUSAL_STATUS_MEANING[status],
            "decision_at": base.as_of.astimezone(timezone.utc).isoformat(),
            "projection_version": base_print.projection_version, "base_request_hash": base_print.hash,
            "variants_checked": checked, "vacuous": vacuous, "families": list(families.values()), "failures": failures}


def composite_attestation(legacy: dict, causal: dict | None = None) -> dict:
    """The field checks of `historical.attest` and the causal checks as one attestation.

        legacy_all_clean   what `attest` alone concluded
        causal_status      PASS / FAIL / NOT_RUN
        causal_all_clean   the causal checks ran and passed
        all_clean          legacy_all_clean AND causal_status == PASS AND causal_all_clean

    `all_clean` here is the composite: a snapshot whose causal checks failed or did not run is never
    `all_clean`, whatever the field checks say, so a reader of the old key cannot take field checks alone
    for a complete attestation."""
    report = not_run() if causal is None else causal
    legacy_clean = legacy.get("all_clean") is True
    status = report.get("status")
    causal_clean = status == PASS and report.get("all_clean") is True
    return {**legacy, "legacy_all_clean": legacy_clean, "causal": report, "causal_status": status, "causal_all_clean": causal_clean,
            "all_clean": legacy_clean and causal_clean}


# ── perturbation family: receipts on purchase orders placed before the decision time ──
FUTURE_RECEIPTS = "future_receipts"

# fixed statements: row ids (and the day shift) are bound parameters, never part of the SQL text
_DELETE_RECEIPTS = "DELETE FROM stg_fmcg_receipts WHERE rowid IN (SELECT UNNEST(?))"
_HALVE_RECEIPTS = "UPDATE stg_fmcg_receipts SET qty_received = qty_received * 0.5 WHERE rowid IN (SELECT UNNEST(?))"
_MOVE_RECEIPTS = "UPDATE stg_fmcg_receipts SET receipt_date = CAST(receipt_date + to_days(CAST(? AS INTEGER)) AS DATE) WHERE rowid IN (SELECT UNNEST(?))"


def receipt_perturbations(decision_at: datetime, *, is_available_at: Availability, shift_days: int = 7,
                          positive_window_days: int = 56) -> list[Perturbation]:
    """The confirmed case (audit 1.1) against a vault (`stg_fmcg_purchase_orders`, `stg_fmcg_receipts`): a
    receipt that was not available at T, on a purchase order placed before T. Such receipts are deleted,
    re-quantified and re-dated, and one is added; one positive control changes receipts that were available.

    `is_available_at(fact, decision_at)` decides availability and has no default: the caller states the
    rule. A fact is the receipt row as a mapping (`po_id`, `receipt_date`, `sku`, `qty_received`,
    `po_date`). A receipt that the rule says was available is never used as a negative control, whatever
    its date. `decision_at` must be the request's own `as_of` (the adapter plans from the Monday of the week)."""
    if decision_at.tzinfo is None:
        raise ValueError("decision_at needs a timezone")
    day = decision_at.astimezone(timezone.utc).date()
    label, name = getattr(is_available_at, "label", None), getattr(is_available_at, "__name__", None)
    rule: str = label if isinstance(label, str) and label else name if isinstance(name, str) and name else "unnamed availability rule"
    def facts(conn: Any) -> list[dict]:
        present = {row[1] for row in conn.execute("PRAGMA table_info('stg_fmcg_receipts')").fetchall()}
        extra = [c for c in ("event_at", "source_known_at") if c in present]      # the H1b columns, when the vault has them
        columns = ("rowid", "po_id", "receipt_date", "sku", "qty_received", "po_date", *extra)
        select = ", ".join(["r.rowid", "r.po_id", "r.receipt_date", "r.sku", "r.qty_received", "p.po_date", *(f"r.{c}" for c in extra)])
        rows = conn.execute(f"SELECT {select} FROM stg_fmcg_receipts r JOIN stg_fmcg_purchase_orders p ON p.po_id = r.po_id WHERE p.po_date < ?", [day]).fetchall()  # nosec B608 - identifiers are this module's literals
        return [dict(zip(columns, row)) for row in rows]

    def unavailable(conn: Any) -> list[int]:
        return [f["rowid"] for f in facts(conn) if not is_available_at(f, decision_at)]

    def edit(conn: Any, statement: str, rowids: list[int], *leading: Any) -> int:
        # `statement` is one of the module's fixed strings; the row ids travel as one bound list parameter
        if rowids:
            conn.execute(statement, [*leading, rowids])
        return len(rowids)

    def delete(conn: Any) -> int:
        return edit(conn, _DELETE_RECEIPTS, unavailable(conn))

    def requantify(conn: Any) -> int:
        return edit(conn, _HALVE_RECEIPTS, unavailable(conn))

    def redate(conn: Any) -> int:
        # only receipts that stay unavailable after the move: the control must remain a negative one
        later = [f["rowid"] for f in facts(conn) if not is_available_at(f, decision_at)
                 and not is_available_at({**f, "receipt_date": f["receipt_date"] + timedelta(days=shift_days)}, decision_at)]
        return edit(conn, _MOVE_RECEIPTS, later, int(shift_days))

    def add(conn: Any) -> int:
        received = {f["po_id"] for f in facts(conn) if is_available_at(f, decision_at)}
        orders = conn.execute("SELECT po_id, sku, qty_ordered, po_date FROM stg_fmcg_purchase_orders WHERE po_date < ?", [day]).fetchall()
        when, added = day + timedelta(days=3), 0
        for po_id, sku, quantity, po_date in orders:
            new = {"po_id": po_id, "receipt_date": when, "sku": sku, "qty_received": quantity, "po_date": po_date}
            if po_id in received or is_available_at(new, decision_at):
                continue
            conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES (?, ?, ?, ?)", [po_id, when, sku, quantity])
            added += 1
        return added

    def past(conn: Any) -> int:
        since = day - timedelta(days=positive_window_days)
        known = [f["rowid"] for f in facts(conn) if is_available_at(f, decision_at) and f["receipt_date"] >= since]
        return edit(conn, _HALVE_RECEIPTS, known)

    def make(name: str, family: str, control: Control, change: Callable[[Any], int]) -> Perturbation:
        return Perturbation(name, family, control, in_transaction(change), availability=rule)
    return [make("delete receipts not available at T on orders placed before T", FUTURE_RECEIPTS, "negative", delete),
            make("halve the quantity of receipts not available at T on orders placed before T", FUTURE_RECEIPTS, "negative", requantify),
            make(f"move receipts not available at T {shift_days} days later", FUTURE_RECEIPTS, "negative", redate),
            make("add a receipt not available at T to every order placed before T with no available receipt", FUTURE_RECEIPTS, "negative", add),
            make(f"halve the quantity of available receipts of the last {positive_window_days} days", "past_receipts", "positive", past)]
