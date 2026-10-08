"""The canonical temporal contract of a decision (HARDENING V1, H1b).

Three times are kept apart on every fact:

    event_at           when it physically / commercially happened, or becomes effective
    source_known_at    when the operator could have known it
    ingested_at        when ZAAD received the row (`imported_at`, upload session, file): never causality

A fact may reach a decision taken at `decision_at` only if

    source_known_at < decision_at

That is a statement about knowledge, not about the event: a promotion planned for next week that was
announced yesterday is available today; a receipt that happened yesterday but is posted tomorrow is not.

`decision_at` is the exact causal cutoff. It is distinct from the planning period origin (`Request.as_of`,
the Monday that anchors the weekly buckets). This module is general: `available` takes any exact cutoff.
The weekly workspace (`zaad.full.workspace.build_request`) reconstructs its physical state at the period
origin and therefore only builds decisions taken at that boundary (`decision_at == period_origin`); it
refuses any other cutoff rather than pairing one instant's state with another instant's knowledge.

DATE-ONLY FALLBACK. Most staging rows carry a date and no time. For a transactional fact with only a date
the fallback is `event_at = start of that date` and `source_known_at = event_at`, labelled
DATE_ONLY_FALLBACK. It is a declared assumption, not evidence. For a future-effective fact (a promotion)
there is no defensible knowledge time without `source_known_at`: that is KNOWLEDGE_TIME_UNAVAILABLE, and
the caller decides what that means (excluded from a historical decision; usable, and labelled, in a live
one).

All instants are handled as naive UTC timestamps, which is how DuckDB TIMESTAMP columns come back.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

EXPLICIT_SOURCE_KNOWN = "EXPLICIT_SOURCE_KNOWN"
DATE_ONLY_FALLBACK = "DATE_ONLY_FALLBACK"
KNOWLEDGE_TIME_UNAVAILABLE = "KNOWLEDGE_TIME_UNAVAILABLE"
KNOWN_AT = "source_known_at_utc"      # the knowledge time `available` attaches to each kept row (no leading underscore: itertuples keeps it)
BASIS = "knowledge_basis"             # and its basis label


def as_utc(value: Any) -> pd.Timestamp:
    """A naive UTC timestamp from an aware or naive datetime / timestamp (naive means UTC)."""
    stamp = pd.Timestamp(value)
    return stamp.tz_convert("UTC").tz_localize(None) if stamp.tzinfo is not None else stamp


def start_of_day(values: pd.Series) -> pd.Series:
    """The start (00:00 UTC) of each date: the date-only fallback for an event's instant."""
    stamps = pd.to_datetime(values)
    if getattr(stamps.dt, "tz", None) is not None:
        stamps = stamps.dt.tz_convert("UTC").dt.tz_localize(None)
    return stamps.dt.normalize()


def knowledge_time(frame: pd.DataFrame, *, date_col: str | None, known_col: str = "source_known_at",
                   fallback: bool = True) -> tuple[pd.Series, pd.Series]:
    """Per row: when the operator could have known the fact, and on what basis.

    Explicit `known_col` wins. Otherwise, with `fallback`, the start of `date_col` (DATE_ONLY_FALLBACK);
    without it, NaT (KNOWLEDGE_TIME_UNAVAILABLE)."""
    known = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
    basis = pd.Series(KNOWLEDGE_TIME_UNAVAILABLE, index=frame.index, dtype=object)
    if known_col in frame.columns:
        explicit = pd.to_datetime(frame[known_col], errors="coerce")
        if getattr(explicit.dt, "tz", None) is not None:
            explicit = explicit.dt.tz_convert("UTC").dt.tz_localize(None)
        has = explicit.notna()
        known[has] = explicit[has]
        basis[has] = EXPLICIT_SOURCE_KNOWN
    if fallback and date_col is not None and date_col in frame.columns:
        missing = known.isna()
        known[missing] = start_of_day(frame.loc[missing, date_col])
        basis[missing & known.notna()] = DATE_ONLY_FALLBACK
    return known, basis


def available(frame: pd.DataFrame, decision_at: datetime | pd.Timestamp, *, date_col: str | None,
              known_col: str = "source_known_at", fallback: bool = True) -> tuple[pd.DataFrame, dict[str, int]]:
    """The rows whose knowledge time precedes `decision_at`, with that time and basis attached, and the
    counts a reviewer needs: how many rest on exact evidence, how many on the date-only fallback, how
    many were excluded because they were not known (or their knowledge time is unavailable)."""
    counts = {"explicit_source_known": 0, "date_only_fallback": 0, "excluded_not_known": 0, "knowledge_time_unavailable": 0}
    if not len(frame):
        return frame.copy(), counts
    cutoff = as_utc(decision_at)
    known, basis = knowledge_time(frame, date_col=date_col, known_col=known_col, fallback=fallback)
    keep = known.notna() & (known < cutoff)
    counts["explicit_source_known"] = int((keep & (basis == EXPLICIT_SOURCE_KNOWN)).sum())
    counts["date_only_fallback"] = int((keep & (basis == DATE_ONLY_FALLBACK)).sum())
    counts["knowledge_time_unavailable"] = int(known.isna().sum())                   # no knowledge time at all
    counts["excluded_not_known"] = int((known.notna() & ~keep).sum())               # known, but only at or after the decision
    kept = frame.loc[keep].copy()
    kept[KNOWN_AT] = known[keep]
    kept[BASIS] = basis[keep]
    return kept, counts
