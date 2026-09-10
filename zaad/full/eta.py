"""Right-censored Kaplan-Meier ETA, conditional on remaining open at its age."""
from __future__ import annotations

from dataclasses import dataclass

from zaad.full.contracts import ShipmentObservation


@dataclass(frozen=True)
class ETA:
    p50: int | None
    p80: int | None
    p90: int | None
    support: tuple[tuple[int, float], ...]
    unresolved_mass: float
    records: int
    censored: int
    scope: str


def conditional_eta(records: tuple[ShipmentObservation, ...], source: str,
                    age_days: int, stage: str | None = None, carrier: str | None = None) -> ETA:
    if age_days < 0:
        raise ValueError("negative PO age")
    rows = [r for r in records if r.source == source]
    stratified = [r for r in rows if (stage is None or r.stage == stage)
                  and (carrier is None or r.carrier == carrier)]
    scope = "source"
    if len(stratified) >= 12 and sum(r.arrived for r in stratified) >= 6:
        rows, scope = stratified, "source_stage_carrier"
    if len(rows) < 6:
        return ETA(None, None, None, (), 1., len(rows), sum(not r.arrived for r in rows), "insufficient")
    survival, at_age = 1., 1.
    masses = []
    for t in sorted({r.elapsed_days for r in rows}):
        risk = sum(r.elapsed_days >= t for r in rows)
        deaths = sum(r.elapsed_days == t and r.arrived for r in rows)
        mass = survival * deaths / risk
        survival -= mass
        if t <= age_days:
            at_age = survival
        else:
            masses.append((t - age_days, mass))
    if at_age <= 1e-12:
        return ETA(None, None, None, (), 1., len(rows), sum(not r.arrived for r in rows), "outside_support")
    conditional = tuple((t, m / at_age) for t, m in masses if m > 0)
    def quantile(level):
        cumulative = 0.
        for t, mass in conditional:
            cumulative += mass
            if cumulative >= level - 1e-12:
                return t
        return None  # infinity represented as null, never fabricated finite tail
    return ETA(quantile(.5), quantile(.8), quantile(.9), conditional,
               max(0., 1 - sum(m for _, m in conditional)), len(rows),
               sum(not r.arrived for r in rows), scope)
