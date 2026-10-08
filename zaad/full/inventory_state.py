"""Opening inventory as a reconstructable, explicitly proven physical state (HARDENING V1, H2).

Inventory is physical state. A request uses an inventory state only when its effective state at the
decision origin is causally available and reconstructable; otherwise the cell is NOT READY and the build
says why. Nothing here falls back to zero, to a stale count, to one of several locations or to the last
physical row.

THE CELL. The physical unit is `(sku, location)`; a cell may carry several expiry cohorts (rows of the
same instant with different `expiry_date`), each a distinct `Stock` record.

TIMING. A snapshot row describes the state at one instant, `effective_at`:
    snapshot_at (exact)                       the instant itself (POINT_IN_TIME)
    date + basis END_OF_DAY                   the state that closes the day = opens the next: date + 1 day 00:00
    date + basis START_OF_DAY                 the state before that day's movements: date 00:00
    date, no basis                            AMBIGUOUS: some instant within [date, date + 1 day)
The basis comes from the row (`snapshot_basis`), else from the workspace declaration
(`inventory_snapshot_basis`). A date-only row's instant is never guessed.

KNOWLEDGE. An explicit `source_known_at` must precede the decision (`< decision_at`, H1b). Without one, a
count is taken to be known when it is effective, so a closing count may serve a decision taken at the
instant it opens (`effective_at <= decision_at`). ZAAD's import time is never knowledge.

READINESS of a cell at the decision origin T (`decision_at == period_origin`, H1b):
    READY_DIRECT                     the latest usable state is exactly the state at T (effective_at == T);
                                     an explicit zero is READY with quantity 0 (zero is a fact, not a default)
    NOT_READY_NO_SNAPSHOT            no usable state at all for the cell
    NOT_READY_AMBIGUOUS_TIMING       the latest usable rows are date-only with no declared basis
    NOT_READY_AMBIGUOUS              conflicting rows for one logical state (same cell, instant and cohort,
                                     different quantities), or cohorts that cannot be told from a total
    NOT_READY_INCOMPLETE_MOVEMENTS   the latest state is earlier than T and the movements from it to T are
                                     not provably complete, so it cannot be rolled forward (see ROLL-FORWARD)
    NOT_READY_LOCATION_AMBIGUITY     a single-site build met several real locations and no aggregation
                                     contract says how to read them together
"Stale" is not an age: a 30-day-old state would be READY if the movements since it were complete and
reconciled; a one-day-old one is not if they are not. Age is reported as metadata.

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
summed into the single site (an explicit contract, not an inference).

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
NOT_READY_AMBIGUOUS_TIMING = "NOT_READY_AMBIGUOUS_TIMING"
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


@dataclass
class Cohort:
    expiry_date: date | None
    quantity: float
    in_transit: float
    rows: int


@dataclass
class CellState:
    sku: str
    location: str
    status: str
    reason: str
    effective_at: datetime | None = None
    source_known_at: datetime | None = None
    basis: str | None = None
    quantity: float | None = None
    cohorts: list[Cohort] = field(default_factory=list)
    age_days: float | None = None
    rows_considered: int = 0
    rows_excluded_not_known: int = 0

    @property
    def ready(self) -> bool:
        return self.status in READY

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reason": self.reason,
                "snapshot_effective_at": None if self.effective_at is None else self.effective_at.isoformat(),
                "source_known_at": None if self.source_known_at is None else self.source_known_at.isoformat(),
                "basis": self.basis, "quantity_at_snapshot": self.quantity, "quantity_at_origin": self.quantity if self.ready else None,
                "roll_forward": None, "cohorts": [{"expiry_date": None if c.expiry_date is None else str(c.expiry_date), "quantity": c.quantity, "rows": c.rows} for c in self.cohorts],
                "in_transit_declared": sum(c.in_transit for c in self.cohorts) if self.cohorts else None,
                "age_days": self.age_days, "rows_considered": self.rows_considered, "rows_excluded_not_known": self.rows_excluded_not_known}


def _text(value: Any) -> str:
    return "" if value is None or (isinstance(value, float) and value != value) else str(value).strip()


def timed_rows(inventory: pd.DataFrame, *, decision_at: pd.Timestamp, default_basis: str | None) -> pd.DataFrame:
    """Every row with its effective instant, basis, knowledge time and availability at the decision."""
    rows = inventory.copy()
    if not len(rows):
        return rows
    cutoff = temporal.as_utc(decision_at)
    day = temporal.start_of_day(rows["snapshot_date"])
    basis = rows["snapshot_basis"].map(_text).str.upper() if "snapshot_basis" in rows.columns else pd.Series("", index=rows.index)
    basis = basis.where(basis != "", (default_basis or "").upper())
    exact = pd.to_datetime(rows["snapshot_at"], errors="coerce") if "snapshot_at" in rows.columns else pd.Series(pd.NaT, index=rows.index)
    if getattr(exact.dt, "tz", None) is not None:
        exact = exact.dt.tz_convert("UTC").dt.tz_localize(None)
    effective = pd.Series(pd.NaT, index=rows.index, dtype="datetime64[ns]")
    effective[exact.notna()] = exact[exact.notna()]
    basis = basis.where(exact.isna(), "POINT_IN_TIME")
    eod, sod = (basis == "END_OF_DAY") & effective.isna(), (basis == "START_OF_DAY") & effective.isna()
    effective[eod] = day[eod] + pd.Timedelta(days=1)
    effective[sod] = day[sod]
    ambiguous = effective.isna()
    window_end = day + pd.Timedelta(days=1)                       # an ambiguous row's state lies before this instant
    known = pd.to_datetime(rows["source_known_at"], errors="coerce") if "source_known_at" in rows.columns else pd.Series(pd.NaT, index=rows.index)
    if getattr(known.dt, "tz", None) is not None:
        known = known.dt.tz_convert("UTC").dt.tz_localize(None)
    explicit_known = known.notna()
    known_fallback = effective.where(~ambiguous, window_end)
    known = known.where(explicit_known, known_fallback)
    available = (explicit_known & (known < cutoff)) | (~explicit_known & (known <= cutoff))
    rows["effective_at"] = effective
    rows["timing_ambiguous"] = ambiguous
    rows["sort_instant"] = effective.where(~ambiguous, window_end)
    rows["basis_used"] = basis.where(~ambiguous, "AMBIGUOUS").where(basis != "", "AMBIGUOUS")
    rows["known_at_used"] = known
    rows["known_explicit"] = explicit_known
    rows["available"] = available & (rows["sort_instant"] <= cutoff)
    rows["location_norm"] = rows["location_id"].map(_text) if "location_id" in rows.columns else ""
    rows["location_norm"] = rows["location_norm"].where(~rows["location_norm"].isin(DEFAULT_LOCATION_IDS), "")
    rows["expiry_key"] = pd.to_datetime(rows["expiry_date"], errors="coerce").dt.date if "expiry_date" in rows.columns else None
    return rows


def resolve_cell(rows: pd.DataFrame, *, sku: str, location: str, decision_at: pd.Timestamp) -> CellState:
    """The latest usable state of one `(sku, location)` cell, from its timed rows."""
    cutoff = temporal.as_utc(decision_at)
    mine = rows[(rows["sku"].astype(str) == sku) & (rows["location_norm"] == location)]
    excluded = int((~mine["available"]).sum()) if len(mine) else 0
    usable = mine[mine["available"]] if len(mine) else mine

    def state(status: str, reason: str, **fields: Any) -> CellState:
        return CellState(sku=sku, location=location, status=status, reason=reason, rows_considered=int(len(mine)), rows_excluded_not_known=excluded, **fields)
    if not len(usable):
        return state(status=NOT_READY_NO_SNAPSHOT, reason="no inventory row for this cell is known at the decision" if len(mine) else "no inventory row for this cell")
    latest_instant = usable["sort_instant"].max()
    latest = usable[usable["sort_instant"] == latest_instant]
    if bool(latest["timing_ambiguous"].any()):
        return state(status=NOT_READY_AMBIGUOUS_TIMING, reason="the latest count is date-only with no declared basis (START_OF_DAY / END_OF_DAY); the instant it describes is unknown",
                         basis="AMBIGUOUS", age_days=float((cutoff - latest_instant).total_seconds() / 86400.), quantity=None)
    effective = latest_instant
    basis = str(latest["basis_used"].iloc[0])
    known = latest["known_at_used"].max()
    cohorts: list[Cohort] = []
    conflict = None
    for expiry_key, group in latest.groupby(latest["expiry_key"].astype(object).where(latest["expiry_key"].notna(), None), dropna=False):
        quantities = sorted(set(float(q) for q in group["on_hand"]))
        if len(quantities) > 1:
            conflict = f"{len(group)} rows for the same cell, instant and expiry cohort carry different quantities {quantities}"
            break
        cohorts.append(Cohort(expiry_date=None if expiry_key is None or pd.isna(expiry_key) else expiry_key, quantity=quantities[0],
                              in_transit=float(group["in_transit"].fillna(0.).sum()) if "in_transit" in group.columns else 0., rows=int(len(group))))
    if conflict:
        return state(status=NOT_READY_AMBIGUOUS, reason=conflict + "; no precedence or lot contract says which is the state",
                         effective_at=effective.to_pydatetime(), basis=basis)
    if len(cohorts) > 1 and any(c.expiry_date is None for c in cohorts):
        return state(status=NOT_READY_AMBIGUOUS, reason="rows with and without an expiry date at the same instant: a cohort cannot be told from a total",
                         effective_at=effective.to_pydatetime(), basis=basis)
    cohorts.sort(key=lambda c: (c.expiry_date is None, c.expiry_date or date.max))
    quantity = float(sum(c.quantity for c in cohorts))
    age = float((cutoff - effective).total_seconds() / 86400.)
    if effective == cutoff:
        return state(status=READY_DIRECT, reason="the count is the state at the decision origin" + (" (explicit zero)" if quantity == 0 else ""),
                         effective_at=effective.to_pydatetime(), source_known_at=known.to_pydatetime(), basis=basis, quantity=quantity, cohorts=cohorts, age_days=age)
    missing = [c for c in MOVEMENT_CLASSES_REQUIRED if c not in MOVEMENT_CLASSES_IN_CONTRACT]
    return state(status=NOT_READY_INCOMPLETE_MOVEMENTS,
                     reason=f"the latest count is {age:.1f} day(s) before the decision origin and cannot be rolled forward: the data contract carries no "
                            f"{', '.join(missing)} feed and no declaration that the recorded movements are complete",
                     effective_at=effective.to_pydatetime(), source_known_at=known.to_pydatetime(), basis=basis, quantity=quantity, cohorts=cohorts, age_days=age)


def resolve(inventory: pd.DataFrame, *, decision_at: pd.Timestamp, skus: list[str], locations: list[str] | None,
            single_location: str | None = None, default_basis: str | None = None, aggregation: str | None = None) -> dict[str, Any]:
    """The opening inventory state of every required cell and the readiness report.

    Network mode (`locations` given): one cell per sku x location, resolved on its own.
    Single-site mode (`single_location` given): the rows' real locations are read; one (or none) maps to the
    single site; several need `aggregation == "SUM"` (every location READY, quantities summed) or the
    build is NOT_READY_LOCATION_AMBIGUITY.

    Returns {"status", "cells": {"SKU|LOCATION": ...}, "stock": [...], "report": {...}} where `stock` holds one
    entry per READY cohort with a positive quantity: (sku, location, quantity, expiry_date, cohort_suffix); the
    caller composes the business-derived stock id from the cell and the cohort suffix."""
    cutoff = temporal.as_utc(decision_at)
    rows = timed_rows(inventory, decision_at=cutoff, default_basis=default_basis) if len(inventory) else inventory
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
            real = sorted(set(mine.loc[mine["available"], "location_norm"]) - {""}) if len(mine) else []
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
                    summed = CellState(sku, site, READY_DIRECT, f"declared SUM of {len(parts)} locations {real}", effective_at=parts[0].effective_at,
                                       source_known_at=max(p.source_known_at for p in parts if p.source_known_at), basis=parts[0].basis,
                                       quantity=float(sum(p.quantity or 0. for p in parts)), cohorts=_merge_cohorts(parts), age_days=parts[0].age_days,
                                       rows_considered=sum(p.rows_considered for p in parts), rows_excluded_not_known=sum(p.rows_excluded_not_known for p in parts))
                    cells[f"{sku}|{site}"] = summed
                    stock += _stock_entries(summed, site)
                else:
                    worst = next(p for p in parts if not p.ready)
                    cells[f"{sku}|{site}"] = CellState(sku, site, worst.status, f"location {worst.location!r}: {worst.reason}",
                                                       rows_considered=sum(p.rows_considered for p in parts), rows_excluded_not_known=sum(p.rows_excluded_not_known for p in parts))
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
              "movement_coverage": {"classes_in_contract": list(MOVEMENT_CLASSES_IN_CONTRACT), "classes_required": list(MOVEMENT_CLASSES_REQUIRED),
                                    "completeness_declared": False, "roll_forward_performed": False},
              "basis_default": default_basis, "aggregation": aggregation,
              "cells": {key: cell.as_dict() for key, cell in cells.items()}}
    return {"status": overall, "cells": cells, "stock": stock, "report": report}


def _stock_entries(state: CellState, location: str) -> list[dict[str, Any]]:
    if not state.ready:
        return []
    out = []
    for cohort in state.cohorts:
        if cohort.quantity <= 0:
            continue
        suffix = "" if cohort.expiry_date is None else f"#{cohort.expiry_date.isoformat()}"
        out.append({"sku": state.sku, "location": location, "quantity": cohort.quantity, "expiry_date": cohort.expiry_date, "cohort_suffix": suffix})
    return out


def _merge_cohorts(parts: list[CellState]) -> list[Cohort]:
    merged: dict[date | None, Cohort] = {}
    for part in parts:
        for cohort in part.cohorts:
            if cohort.expiry_date in merged:
                merged[cohort.expiry_date].quantity += cohort.quantity
                merged[cohort.expiry_date].in_transit += cohort.in_transit
                merged[cohort.expiry_date].rows += cohort.rows
            else:
                merged[cohort.expiry_date] = Cohort(cohort.expiry_date, cohort.quantity, cohort.in_transit, cohort.rows)
    return sorted(merged.values(), key=lambda c: (c.expiry_date is None, c.expiry_date or date.max))


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
