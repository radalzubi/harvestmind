"""Signals with provenance, freshness and quality; logistics adapters.

A signal that is not current is not a signal. The store answers "what do
we know, from where, how old, how good" and refuses to let a stale or
absent feed read as "conditions are normal". Absence is reported as
UNAVAILABLE and the state estimator treats it as missing evidence, which
widens uncertainty rather than narrowing it.
"""

from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROVENANCE = ("REAL_OPERATOR", "REAL_PUBLIC", "INFERRED", "ASSUMED", "SYNTHETIC_CALIBRATED")


@dataclass(frozen=True)
class Signal:
    timestamp: datetime            # when the observation is FOR
    entity_type: str               # port | route | supplier | sku | carrier | region | operator
    entity_id: str
    metric: str                    # throughput_index | fill | lead_weeks | demand_index | disruption_flag ...
    value: float
    provenance: str
    quality: float = 1.0           # 0..1, source's own confidence
    refreshed_at: datetime | None = None
    transform: str = ""            # how it was derived, for the audit

    def __post_init__(self) -> None:
        if self.provenance not in PROVENANCE:
            raise ValueError(f"provenance must be one of {PROVENANCE}, got {self.provenance!r}")
        if not 0.0 <= self.quality <= 1.0:
            raise ValueError("quality must be in [0, 1]")


@dataclass
class SignalStatus:
    available: bool
    age_days: float | None
    stale: bool
    n: int
    provenance: str | None
    quality: float | None
    reason: str


@dataclass
class SignalStore:
    max_age_days: float = 45.0
    _by_key: dict = field(default_factory=lambda: defaultdict(list))

    def add(self, s: Signal) -> None:
        self._by_key[(s.entity_type, s.entity_id, s.metric)].append(s)

    def series(self, entity_type: str, entity_id: str, metric: str, as_of: datetime | None = None) -> list:
        """Signals at or before ``as_of`` (leakage-free by construction)."""
        xs = sorted(self._by_key.get((entity_type, entity_id, metric), []), key=lambda s: s.timestamp)
        if as_of is not None:
            xs = [s for s in xs if s.timestamp <= as_of]
        return xs

    def status(self, entity_type: str, entity_id: str, metric: str, as_of: datetime | None = None) -> SignalStatus:
        xs = self.series(entity_type, entity_id, metric, as_of)
        now = as_of or datetime.now(timezone.utc)
        if not xs:
            return SignalStatus(False, None, True, 0, None, None, "no observations; treated as UNAVAILABLE, not normal")
        last = xs[-1]
        age = (now - last.timestamp).total_seconds() / 86400.0
        stale = age > self.max_age_days
        return SignalStatus(True, age, stale, len(xs), last.provenance, last.quality,
                            "stale beyond max_age; evidence weight reduced" if stale else "current")

    def latest(self, entity_type: str, entity_id: str, metric: str, as_of: datetime | None = None) -> Signal | None:
        xs = self.series(entity_type, entity_id, metric, as_of)
        return xs[-1] if xs else None

    def availability(self, as_of: datetime | None = None) -> dict:
        return {f"{et}:{eid}:{m}": self.status(et, eid, m, as_of=as_of).__dict__ for (et, eid, m) in self._by_key}


# ── PortWatch adapter (REAL PUBLIC) ─────────────────────────────────────────
def load_portwatch_signals(store: SignalStore, csv_path: str | Path, ports: tuple = ("Aqaba",),
                           trailing_months: int = 12) -> int:
    """Monthly import tonnage as an index against its own trailing median.
    Value 1.0 = at trailing norm; 0.7 = arrivals at 70% of the norm.
    The observation is stamped with the month it describes; refreshed_at
    is the file's modification time, so freshness is honest."""
    p = Path(csv_path)
    if not p.exists():
        return 0
    refreshed = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    monthly: dict = defaultdict(float)
    with p.open() as fh:
        for row in csv.DictReader(fh):
            if row.get("portname") in ports:
                monthly[(row["portname"], row["date"][:7])] += float(row.get("import") or 0.0)
    n = 0
    for port in ports:
        months = sorted(m for (pt, m) in monthly if pt == port)[:-1]   # last month is partial
        for k, m in enumerate(months):
            if k < trailing_months:
                continue
            prior = [monthly[(port, months[j])] for j in range(k - trailing_months, k)]
            med = st.median(prior)
            if med <= 0:
                continue
            y, mo = int(m[:4]), int(m[5:7])
            ts = datetime(y, mo, 28, tzinfo=timezone.utc)
            store.add(Signal(timestamp=ts, entity_type="port", entity_id=port.upper(),
                             metric="throughput_index", value=min(monthly[(port, m)] / med, 3.0),
                             provenance="REAL_PUBLIC", quality=0.8, refreshed_at=refreshed,
                             transform=f"monthly import tonnage / trailing {trailing_months}-month median"))
            n += 1
    return n


def operator_disruption_flag(store: SignalStore, entity_type: str, entity_id: str, when: date,
                             severity: float, note: str = "") -> None:
    """An operator-entered flag (e.g. 'port strike'), severity in [0, 1]."""
    store.add(Signal(timestamp=datetime(when.year, when.month, when.day, tzinfo=timezone.utc),
                     entity_type=entity_type, entity_id=entity_id, metric="disruption_flag",
                     value=float(min(max(severity, 0.0), 1.0)), provenance="REAL_OPERATOR",
                     quality=0.9, refreshed_at=datetime.now(timezone.utc), transform=note))


def weeks_ago(as_of: datetime, n: int) -> datetime:
    return as_of - timedelta(weeks=n)
