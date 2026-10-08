"""Opening inventory as a reconstructable, explicitly proven physical state (HARDENING V1, H2).

Inventory is physical state. A request uses an inventory state only when its effective state at the
decision origin is causally available and reconstructable; otherwise the cell is NOT READY and the build
says why. Nothing here falls back to zero, to a stale count, to one of several locations or to the last
physical row.

THE CELL. The physical unit is `(sku, location)`; a cell may carry several cohorts (rows of the same
instant with a different `expiry_date` and/or `lot_id`), each a distinct `Stock` record.

PHYSICAL TIMING. A snapshot row describes the state at one instant, `effective_at`:
    snapshot_at (exact)                       the instant itself (POINT_IN_TIME)
    date + basis END_OF_DAY                   the state that closes the day = opens the next: date + 1 day 00:00
    date + basis START_OF_DAY                 the state before that day's movements: date 00:00
    date, no basis                            AMBIGUOUS: some instant within [date, date + 1 day)
The basis comes from the row (`snapshot_basis`), else from the workspace declaration
(`inventory_snapshot_basis`). A date-only row's instant is never guessed. The basis says WHAT state the
quantity is; it says nothing about WHEN the operator learned it.

KNOWLEDGE TIMING (the H1b rule, unchanged for inventory): a count enters a decision only if
    source_known_at < decision_at            (strict)
`source_known_at` is the row's own declaration. A row without one has no knowledge time, and no inventory
fact is admitted on an implicit one: not its effective instant, not its date, not ZAAD's import time, not
"the decision minus a second". The only other admissible knowledge time is a workspace-level declared
rule in the economics table, `inventory_source_known_rule = CLOSE_OF_SNAPSHOT_DAY` (the count is known at
the last second of its snapshot day), which the operator or a synthetic loader declares explicitly and the
report records as `knowledge_basis = DECLARED_RULE`. Without a knowledge time a cell is
NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE.

READINESS of a cell at the decision origin T (`decision_at == period_origin`, H1b):
    READY_DIRECT                           the latest known state is exactly the state at T (effective_at == T);
                                           an explicit zero is READY with quantity 0 (zero is a fact, not a default)
    NOT_READY_NO_SNAPSHOT                  no row at all for the cell at or before T, or none of the latest state known before T
    NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE   rows of the latest state carry no knowledge time and no declared rule covers them
    NOT_READY_INCOMPLETE_STATE_KNOWLEDGE   only some rows of the latest physical state were knowable before T: a knowable
                                           subset is not a partial opening balance, the balance cannot be established
    NOT_READY_AMBIGUOUS_TIMING             the latest known rows are date-only with no declared basis
    NOT_READY_AMBIGUOUS                    more than one row for one logical cohort (same cell, instant,
                                           expiry and lot identity), whatever their quantities; or cohorts
                                           that cannot be told from a total
    NOT_READY_INCOMPLETE_MOVEMENTS         the latest state is earlier than T and the movements from it to T are
                                           not provably complete, so it cannot be rolled forward (see ROLL-FORWARD)
    NOT_READY_LOCATION_AMBIGUITY           a single-site build met several real locations and no aggregation
                                           contract says how to read them together
"Stale" is not an age: a 30-day-old state would be READY if the movements since it were complete and
reconciled; a one-day-old one is not if they are not. Age is reported as metadata.

STATE COMPLETENESS. The physical state is selected first (the cell's latest instant at or before T),
independently of knowledge; it is READY only if EVERY row defining it is known before T. The rows of a
state the operator knew only in part never reach the Request, not even the knowable ones: the evaluator
counts them only to conclude that the balance cannot be established. State strictly after T is not history
and creates no requirement.

LOTS. Two rows for one `(sku, location, effective_at, expiry_date)` are two records of one cohort or two
real lots; without a lot identity the data cannot say which, so equal quantities are not accepted as one
state and are not summed. An explicit `lot_id` (migration 030, optional) is an identity: within one cell and
physical state it names exactly one row, and a repeated `lot_id` blocks whatever else differs (expiry,
quantity, knowledge time or any attribute). Row order and upload metadata are never identity.

ROLL-FORWARD. state(T) = snapshot + accepted receipts + received inbound transfers - shipped customer
orders - dispatched outbound transfers +/- explicit adjustments between the snapshot instant and T, using
actual quantities only. This module does not perform it: the current data contract has no adjustments /
returns / shrink / cycle-count feed and no declaration that the recorded movement classes are complete,
and an absent feed is not proof that nothing happened. A snapshot earlier than T is therefore
NOT_READY_INCOMPLETE_MOVEMENTS with the missing classes named. `reconcile` offers the ex-post check that a
future contract would need (prior snapshot + recorded movements vs the next snapshot); it never feeds a
request.

LOCATIONS. Network builds resolve every `(sku, location)` the request declares. Single-site builds map one
real location (or none declared) to the request's location; several real locations are
NOT_READY_LOCATION_AMBIGUITY unless the workspace declares `inventory_single_site_aggregation = SUM`,
in which case each location is resolved on its own and, if every one is READY, their quantities are
summed into the single site (an explicit contract, not an inference). An aggregate is known only when all
of its components are known: its `source_known_at` is the latest of theirs.

`in_transit` on a snapshot row is an aggregate with no order, source or due identity. It never becomes
stock, a pipeline order or an inbound transfer; it is reported beside the request's own open inbound as
a reconciliation signal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from zaad.full import temporal

BASES = ("START_OF_DAY", "END_OF_DAY", "POINT_IN_TIME")
READY_DIRECT = "READY_DIRECT"
NOT_READY_NO_SNAPSHOT = "NOT_READY_NO_SNAPSHOT"
NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE = "NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE"
NOT_READY_AMBIGUOUS_TIMING = "NOT_READY_AMBIGUOUS_TIMING"
NOT_READY_INCOMPLETE_STATE_KNOWLEDGE = "NOT_READY_INCOMPLETE_STATE_KNOWLEDGE"
NOT_READY_AMBIGUOUS = "NOT_READY_AMBIGUOUS"
NOT_READY_INCOMPLETE_MOVEMENTS = "NOT_READY_INCOMPLETE_MOVEMENTS"
NOT_READY_LOCATION_AMBIGUITY = "NOT_READY_LOCATION_AMBIGUITY"
READY = (READY_DIRECT,)
DEFAULT_LOCATION_IDS = ("", "MAIN", "main", "None", "nan")       # what an undeclared location column says
MOVEMENT_CLASSES_REQUIRED = ("supplier_receipts", "customer_shipments", "transfers_in", "transfers_out",
                             "adjustments", "returns", "shrink_or_write_off", "cycle_count_corrections")
MOVEMENT_CLASSES_IN_CONTRACT = ("supplier_receipts", "customer_shipments", "transfers_in", "transfers_out")
BASIS_KEY = "inventory_snapshot_basis"
AGGREGATION_KEY = "inventory_single_site_aggregation"
KNOWN_RULE_KEY = "inventory_source_known_rule"
KNOWN_RULE_CLOSE_OF_DAY = "CLOSE_OF_SNAPSHOT_DAY"                 # known at snapshot_date 23:59:59 (the day's last second)
KNOWN_RULES = (KNOWN_RULE_CLOSE_OF_DAY,)
KNOWLEDGE_EXPLICIT = "EXPLICIT_SOURCE_KNOWN"
KNOWLEDGE_DECLARED_RULE = "DECLARED_RULE"
KNOWLEDGE_UNAVAILABLE = "KNOWLEDGE_TIME_UNAVAILABLE"


@dataclass
class Cohort:
    expiry_date: date | None
    lot_id: str | None
    quantity: float
    in_transit: float
    rows: int
    source_known_at: datetime | None = None
    knowledge_basis: str | None = None

    @property
    def suffix(self) -> str:
        """The deterministic, business-derived part of the Stock id this cohort adds to `open_{sku}[@loc]`."""
        return ("" if self.expiry_date is None else f"#{self.expiry_date.isoformat()}") + ("" if self.lot_id is None else f"~{self.lot_id}")


@dataclass
class CellState:
    sku: str
    location: str
    status: str
    reason: str
    effective_at: datetime | None = None
    source_known_at: datetime | None = None
    knowledge_basis: str | None = None
    basis: str | None = None
    quantity: float | None = None
    cohorts: list[Cohort] = field(default_factory=list)
    age_days: float | None = None
    rows_considered: int = 0
    rows_defining_state: int = 0
    rows_known_before_decision: int = 0
    rows_excluded_not_known: int = 0
    rows_without_knowledge_time: int = 0

    @property
    def ready(self) -> bool:
        return self.status in READY

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reason": self.reason,
                "snapshot_effective_at": None if self.effective_at is None else self.effective_at.isoformat(),
                "source_known_at": None if self.source_known_at is None else self.source_known_at.isoformat(),
                "knowledge_basis": self.knowledge_basis,
                "basis": self.basis, "quantity_at_snapshot": self.quantity, "quantity_at_origin": self.quantity if self.ready else None,
                "roll_forward": None,
                "cohorts": [{"expiry_date": None if c.expiry_date is None else str(c.expiry_date), "lot_id": c.lot_id, "quantity": c.quantity, "rows": c.rows,
                             "source_known_at": None if c.source_known_at is None else c.source_known_at.isoformat(), "knowledge_basis": c.knowledge_basis}
                            for c in self.cohorts],
                "in_transit_declared": sum(c.in_transit for c in self.cohorts) if self.cohorts else None,
                "age_days": self.age_days, "rows_considered": self.rows_considered,
                "state_knowledge": {"rows_defining_state": self.rows_defining_state, "rows_known_before_decision": self.rows_known_before_decision,
                                    "rows_excluded_by_causal_cutoff": self.rows_excluded_not_known, "rows_without_knowledge_time": self.rows_without_knowledge_time},
                "rows_excluded_not_known": self.rows_excluded_not_known, "rows_without_knowledge_time": self.rows_without_knowledge_time}


def _text(value: Any) -> str:
    return "" if value is None or (isinstance(value, float) and value != value) else str(value).strip()


def _naive_utc(series: pd.Series) -> pd.Series:
    stamps = pd.to_datetime(series, errors="coerce")
    if getattr(stamps.dt, "tz", None) is not None:
        stamps = stamps.dt.tz_convert("UTC").dt.tz_localize(None)
    return stamps


def timed_rows(inventory: pd.DataFrame, *, decision_at: pd.Timestamp, default_basis: str | None, known_rule: str | None = None) -> pd.DataFrame:
    """Every row with its effective instant, basis, knowledge time and availability at the decision.

    Physical timing and knowledge timing are separate columns: `effective_at` / `basis_used` say which state
    the quantity is; `known_at_used` / `knowledge_basis` say when it could be known, from the row's own
    `source_known_at` or from the declared workspace rule, never from the effective instant."""
    rows = inventory.copy()
    if not len(rows):
        return rows
    if known_rule is not None and known_rule.upper() not in KNOWN_RULES:
        raise ValueError(f"{KNOWN_RULE_KEY}: unsupported value {known_rule!r}; supported: {KNOWN_RULES}")
    cutoff = temporal.as_utc(decision_at)
    day = temporal.start_of_day(rows["snapshot_date"])
    basis = rows["snapshot_basis"].map(_text).str.upper() if "snapshot_basis" in rows.columns else pd.Series("", index=rows.index)
    basis = basis.where(basis != "", (default_basis or "").upper())
    exact = _naive_utc(rows["snapshot_at"]) if "snapshot_at" in rows.columns else pd.Series(pd.NaT, index=rows.index, dtype="datetime64[ns]")
    effective = pd.Series(pd.NaT, index=rows.index, dtype="datetime64[ns]")
    effective[exact.notna()] = exact[exact.notna()]
    basis = basis.where(exact.isna(), "POINT_IN_TIME")
    eod, sod = (basis == "END_OF_DAY") & effective.isna(), (basis == "START_OF_DAY") & effective.isna()
    effective[eod] = day[eod] + pd.Timedelta(days=1)
    effective[sod] = day[sod]
    ambiguous = effective.isna()
    window_end = day + pd.Timedelta(days=1)                       # an ambiguous row's state lies before this instant
    known = _naive_utc(rows["source_known_at"]) if "source_known_at" in rows.columns else pd.Series(pd.NaT, index=rows.index, dtype="datetime64[ns]")
    explicit_known = known.notna()
    knowledge_basis = pd.Series(KNOWLEDGE_UNAVAILABLE, index=rows.index, dtype=object).where(~explicit_known, KNOWLEDGE_EXPLICIT)
    if known_rule is not None:
        ruled = ~explicit_known
        known = known.where(explicit_known, day + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
        knowledge_basis = knowledge_basis.where(~ruled, f"{KNOWLEDGE_DECLARED_RULE}:{known_rule.upper()}")
    has_knowledge = known.notna()
    rows["effective_at"] = effective
    rows["timing_ambiguous"] = ambiguous
    rows["sort_instant"] = effective.where(~ambiguous, window_end)
    rows["basis_used"] = basis.where(~ambiguous, "AMBIGUOUS").where(basis != "", "AMBIGUOUS")
    rows["known_at_used"] = known
    rows["knowledge_basis"] = knowledge_basis
    rows["has_knowledge_time"] = has_knowledge
    rows["available"] = has_knowledge & (known < cutoff) & (rows["sort_instant"] <= cutoff)       # the H1b inequality, strict
    rows["location_norm"] = rows["location_id"].map(_text) if "location_id" in rows.columns else ""
    rows["location_norm"] = rows["location_norm"].where(~rows["location_norm"].isin(DEFAULT_LOCATION_IDS), "")
    rows["expiry_key"] = pd.to_datetime(rows["expiry_date"], errors="coerce").dt.date if "expiry_date" in rows.columns else None
    rows["lot_key"] = rows["lot_id"].map(_text) if "lot_id" in rows.columns else ""
    return rows


def resolve_cell(rows: pd.DataFrame, *, sku: str, location: str, decision_at: pd.Timestamp) -> CellState:
    """The latest physical state of one `(sku, location)` cell at or before the decision, and whether it is
    causally and completely known.

    The physical state is selected first, independently of knowledge: the latest instant at or before T
    among the cell's rows. Every row of that state must then be known before T (strict H1b rule); a state
    only some of whose rows were knowable is NOT a partial opening balance, it is an opening balance ZAAD
    cannot establish (NOT_READY_INCOMPLETE_STATE_KNOWLEDGE). Quantities of rows that were not knowable never
    reach the Request; the evaluator only counts them to conclude that the state is not reconstructable."""
    cutoff = temporal.as_utc(decision_at)
    mine = rows[(rows["sku"].astype(str) == sku) & (rows["location_norm"] == location)]
    relevant = mine[mine["sort_instant"] <= cutoff] if len(mine) else mine          # physical state at or before T; later state is not history

    def state(status: str, reason: str, **fields: Any) -> CellState:
        return CellState(sku=sku, location=location, status=status, reason=reason, rows_considered=int(len(mine)), **fields)

    if not len(relevant):
        return state(NOT_READY_NO_SNAPSHOT, "no inventory row for this cell describes a state at or before the decision" if len(mine) else "no inventory row for this cell")
    latest_instant = relevant["sort_instant"].max()
    latest = relevant[relevant["sort_instant"] == latest_instant]
    n_state = int(len(latest))
    n_known = int(latest["available"].sum())
    n_no_time = int((~latest["has_knowledge_time"]).sum())
    n_late = n_state - n_known - n_no_time
    counts = {"rows_defining_state": n_state, "rows_known_before_decision": n_known, "rows_excluded_not_known": n_late, "rows_without_knowledge_time": n_no_time}
    if bool(latest["timing_ambiguous"].any()):
        return state(NOT_READY_AMBIGUOUS_TIMING, "the latest count is date-only with no declared basis (START_OF_DAY / END_OF_DAY); the instant it describes is unknown",
                     basis="AMBIGUOUS", age_days=float((cutoff - latest_instant).total_seconds() / 86400.), **counts)
    effective = latest_instant
    basis = str(latest["basis_used"].iloc[0])
    common_blocked = {"effective_at": effective.to_pydatetime(), "basis": basis, **counts}
    if n_no_time:
        return state(NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE,
                     f"{n_no_time} of the {n_state} row(s) defining the opening count carry no source_known_at and no declared {KNOWN_RULE_KEY} covers them: "
                     "when the count could be known is not established, so it is not causally available", **common_blocked)
    if n_known == 0:
        return state(NOT_READY_NO_SNAPSHOT, f"no row of the latest physical state ({n_state} row(s)) is known before the decision", **common_blocked)
    if n_known < n_state:
        return state(NOT_READY_INCOMPLETE_STATE_KNOWLEDGE,
                     f"the opening count has {n_state} lot/cohort rows, but only {n_known} were knowable at the decision ({n_late} known at or after it), "
                     "so ZAAD cannot establish the full opening balance; a knowable subset is not a partial balance", **common_blocked)
    # explicit lot identities first: within one physical state a non-empty lot_id names exactly one row
    lots = latest[latest["lot_key"] != ""]
    repeated = lots.groupby("lot_key").size()
    repeated = repeated[repeated > 1]
    if len(repeated):
        lot = str(repeated.index[0])
        return state(NOT_READY_AMBIGUOUS,
                     f"lot {lot!r} appears {int(repeated.iloc[0])} times in the same cell and physical state; a lot identity names one lot state and no "
                     "revision or duplicate contract says which row is authoritative (quantity, expiry or any other attribute cannot decide it)", **common_blocked)
    cohorts: list[Cohort] = []
    expiry_keys = latest["expiry_key"].astype(object).where(latest["expiry_key"].notna(), None)
    for (expiry_key, lot_key), group in latest.groupby([expiry_keys, latest["lot_key"]], dropna=False):
        if len(group) > 1:                                                   # only rows without a lot identity can reach here
            quantities = sorted(set(float(q) for q in group["on_hand"]))
            return state(NOT_READY_AMBIGUOUS,
                         f"{len(group)} rows for the same cell, instant and cohort (expiry {expiry_key}, no lot identity) with quantities {quantities}: "
                         "one record repeated or two real lots cannot be told apart without a lot_id; no precedence rule chooses among them", **common_blocked)
        row = group.iloc[0]
        cohorts.append(Cohort(expiry_date=None if expiry_key is None or pd.isna(expiry_key) else expiry_key, lot_id=lot_key or None, quantity=float(row["on_hand"]),
                              in_transit=float(row["in_transit"]) if "in_transit" in group.columns and not pd.isna(row["in_transit"]) else 0., rows=1,
                              source_known_at=pd.Timestamp(row["known_at_used"]).to_pydatetime(), knowledge_basis=str(row["knowledge_basis"])))
    if len(cohorts) > 1 and any(c.expiry_date is None and c.lot_id is None for c in cohorts):
        return state(NOT_READY_AMBIGUOUS, "rows with and without a cohort identity (expiry date / lot) at the same instant: a cohort cannot be told from a total", **common_blocked)
    cohorts.sort(key=lambda c: (c.expiry_date is None, c.expiry_date or date.max, c.lot_id or ""))
    quantity = float(sum(c.quantity for c in cohorts))
    known = max(c.source_known_at for c in cohorts if c.source_known_at)
    knowledge = sorted({c.knowledge_basis for c in cohorts if c.knowledge_basis})
    age = float((cutoff - effective).total_seconds() / 86400.)
    common = {"effective_at": effective.to_pydatetime(), "source_known_at": known, "knowledge_basis": " | ".join(knowledge), "basis": basis,
              "quantity": quantity, "cohorts": cohorts, "age_days": age, **counts}
    if effective == cutoff:
        return state(READY_DIRECT, "the count is the state at the decision origin" + (" (explicit zero)" if quantity == 0 else ""), **common)
    missing = [c for c in MOVEMENT_CLASSES_REQUIRED if c not in MOVEMENT_CLASSES_IN_CONTRACT]
    return state(NOT_READY_INCOMPLETE_MOVEMENTS,
                 f"the latest count is {age:.1f} day(s) before the decision origin and cannot be rolled forward: the data contract carries no "
                 f"{', '.join(missing)} feed and no declaration that the recorded movements are complete", **common)


def resolve(inventory: pd.DataFrame, *, decision_at: pd.Timestamp, skus: list[str], locations: list[str] | None,
            single_location: str | None = None, default_basis: str | None = None, aggregation: str | None = None,
            known_rule: str | None = None) -> dict[str, Any]:
    """The opening inventory state of every required cell and the readiness report.

    Network mode (`locations` given): one cell per sku x location, resolved on its own.
    Single-site mode (`single_location` given): the rows' real locations are read; one (or none) maps to the
    single site; several need `aggregation == "SUM"` (every location READY, quantities summed) or the
    build is NOT_READY_LOCATION_AMBIGUITY.

    Returns {"status", "cells": {"SKU|LOCATION": ...}, "stock": [...], "report": {...}} where `stock` holds one
    entry per READY cohort with a positive quantity: (sku, location, quantity, expiry_date, lot_id,
    cohort_suffix, source_known_at); the caller composes the business-derived stock id from the cell and the
    cohort suffix and carries the cohort's own knowledge time."""
    cutoff = temporal.as_utc(decision_at)
    rows = timed_rows(inventory, decision_at=cutoff, default_basis=default_basis, known_rule=known_rule) if len(inventory) else inventory
    cells: dict[str, CellState] = {}
    stock: list[dict[str, Any]] = []
    if locations is not None:
        for sku in sorted(skus):
            for location in sorted(locations):
                state = resolve_cell(rows, sku=sku, location=location, decision_at=cutoff) if len(rows) else CellState(sku, location, NOT_READY_NO_SNAPSHOT, "no inventory rows uploaded")
                cells[f"{sku}|{location}"] = state
                stock += _stock_entries(state, location)
    else:
        site = single_location or "main"
        for sku in sorted(skus):
            if not len(rows):
                cells[f"{sku}|{site}"] = CellState(sku, site, NOT_READY_NO_SNAPSHOT, "no inventory rows uploaded")
                continue
            mine = rows[rows["sku"].astype(str) == sku]
            # the physical locations are those with state at or before T, whether or not that state was knowable:
            # a location whose count was not known does not vanish from the network, it blocks it
            real = sorted(set(mine.loc[mine["sort_instant"] <= cutoff, "location_norm"]) - {""}) if len(mine) else []
            if len(real) <= 1:
                location = real[0] if real else ""
                state = resolve_cell(rows, sku=sku, location=location, decision_at=cutoff)
                state.location = site
                if location:
                    state.reason += f" (location {location!r} read as the single site)"
                cells[f"{sku}|{site}"] = state
                stock += _stock_entries(state, site)
            elif (aggregation or "").upper() == "SUM":
                parts = [resolve_cell(rows, sku=sku, location=location, decision_at=cutoff) for location in real]
                if all(p.ready for p in parts):
                    merged = _merge_cohorts(parts)
                    summed = CellState(sku, site, READY_DIRECT, f"declared SUM of {len(parts)} locations {real}", effective_at=parts[0].effective_at,
                                       source_known_at=max(p.source_known_at for p in parts if p.source_known_at),
                                       knowledge_basis=" | ".join(sorted({p.knowledge_basis for p in parts if p.knowledge_basis})), basis=parts[0].basis,
                                       quantity=float(sum(p.quantity or 0. for p in parts)), cohorts=merged, age_days=parts[0].age_days,
                                       rows_considered=sum(p.rows_considered for p in parts), rows_defining_state=sum(p.rows_defining_state for p in parts),
                                       rows_known_before_decision=sum(p.rows_known_before_decision for p in parts),
                                       rows_excluded_not_known=sum(p.rows_excluded_not_known for p in parts),
                                       rows_without_knowledge_time=sum(p.rows_without_knowledge_time for p in parts))
                    cells[f"{sku}|{site}"] = summed
                    stock += _stock_entries(summed, site)
                else:
                    worst = next(p for p in parts if not p.ready)
                    cells[f"{sku}|{site}"] = CellState(sku, site, worst.status, f"location {worst.location!r}: {worst.reason}",
                                                       rows_considered=sum(p.rows_considered for p in parts), rows_defining_state=sum(p.rows_defining_state for p in parts),
                                                       rows_known_before_decision=sum(p.rows_known_before_decision for p in parts),
                                                       rows_excluded_not_known=sum(p.rows_excluded_not_known for p in parts),
                                                       rows_without_knowledge_time=sum(p.rows_without_knowledge_time for p in parts))
            else:
                cells[f"{sku}|{site}"] = CellState(sku, site, NOT_READY_LOCATION_AMBIGUITY,
                                                   f"stock counts exist for {len(real)} locations {real}; a single-site build cannot choose one "
                                                   f"(use the network workspace or declare {AGGREGATION_KEY} = SUM)",
                                                   rows_considered=int(len(mine)))
    statuses = [c.status for c in cells.values()]
    overall = "READY" if cells and all(s in READY for s in statuses) else ("NOT_READY" if cells else "NO_CELLS")
    report = {"status": overall, "decision_at": cutoff.isoformat(), "required_cells": len(cells),
              "ready_cells": sum(1 for s in statuses if s in READY), "direct_snapshot_cells": statuses.count(READY_DIRECT), "rolled_forward_cells": 0,
              "blocked_cells": sum(1 for s in statuses if s not in READY), "zero_cells": sum(1 for c in cells.values() if c.ready and c.quantity == 0),
              "latest_snapshot_age_days": max((c.age_days for c in cells.values() if c.age_days is not None), default=None),
              "rows_uploaded": int(len(inventory)),
              "knowledge_rule": "source_known_at < decision_at (strict); rows without a knowledge time are not available; "
                                "a physical state is READY only if every row defining it is known before the decision",
              "source_known_rule_declared": known_rule,
              "movement_coverage": {"classes_in_contract": list(MOVEMENT_CLASSES_IN_CONTRACT), "classes_required": list(MOVEMENT_CLASSES_REQUIRED),
                                    "completeness_declared": False, "roll_forward_performed": False},
              "basis_default": default_basis, "aggregation": aggregation,
              "cells": {key: cell.as_dict() for key, cell in cells.items()}}
    return {"status": overall, "cells": cells, "stock": stock, "report": report}


def _stock_entries(state: CellState, location: str) -> list[dict[str, Any]]:
    if not state.ready:
        return []
    return [{"sku": state.sku, "location": location, "quantity": cohort.quantity, "expiry_date": cohort.expiry_date, "lot_id": cohort.lot_id,
             "cohort_suffix": cohort.suffix, "source_known_at": cohort.source_known_at, "knowledge_basis": cohort.knowledge_basis}
            for cohort in state.cohorts if cohort.quantity > 0]


def _merge_cohorts(parts: list[CellState]) -> list[Cohort]:
    """Cohorts of several locations summed into one site: an aggregate is known only when every component is."""
    merged: dict[tuple[date | None, str | None], Cohort] = {}
    for part in parts:
        for cohort in part.cohorts:
            key = (cohort.expiry_date, cohort.lot_id)
            if key in merged:
                merged[key].quantity += cohort.quantity
                merged[key].in_transit += cohort.in_transit
                merged[key].rows += cohort.rows
                merged[key].source_known_at = max(t for t in (merged[key].source_known_at, cohort.source_known_at) if t)
                merged[key].knowledge_basis = " | ".join(sorted({b for b in (merged[key].knowledge_basis, cohort.knowledge_basis) if b}))
            else:
                merged[key] = Cohort(cohort.expiry_date, cohort.lot_id, cohort.quantity, cohort.in_transit, cohort.rows, cohort.source_known_at, cohort.knowledge_basis)
    return sorted(merged.values(), key=lambda c: (c.expiry_date is None, c.expiry_date or date.max, c.lot_id or ""))


def reconcile(prior_quantity: float, next_quantity: float, *, receipts: float = 0., shipments: float = 0., transfers_in: float = 0.,
              transfers_out: float = 0., adjustments: float = 0.) -> dict[str, Any]:
    """Ex-post check of the movement ledger between two observed counts: does prior + recorded movements
    reproduce the next count? Numerical tolerance only; any operational tolerance is the caller's and must
    be reported. Never a planning input."""
    expected = prior_quantity + receipts + shipments * -1 + transfers_in - transfers_out + adjustments
    difference = next_quantity - expected
    return {"expected": expected, "observed": next_quantity, "absolute_difference": difference,
            "relative_difference": (difference / next_quantity) if next_quantity else None,
            "reconciles": abs(difference) <= 1e-6 * max(1., abs(next_quantity)),
            "movement_classes_used": [k for k, v in (("supplier_receipts", receipts), ("customer_shipments", shipments), ("transfers_in", transfers_in),
                                                     ("transfers_out", transfers_out), ("adjustments", adjustments)) if v]}


def synthetic_rows_are_closing_counts(snapshot_dates: pd.Series) -> pd.Series:
    """Helper for synthetic loaders: the simulator writes each week's state after that week's arrivals,
    fulfilment and replenishment and labels it with the week start; the truthful row is the count that
    closes the week: `snapshot_date` = week start + 6 days, basis END_OF_DAY."""
    return pd.to_datetime(snapshot_dates) + timedelta(days=6)
