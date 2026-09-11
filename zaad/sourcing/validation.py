"""Validation of a declared sourcing portfolio against the request it is attached to. Runs inside
the frozen request validator (HTTP 422 on the API) before any model is built. A frozen request
(no portfolio) is not inspected."""
from __future__ import annotations

import math

from zaad.sourcing.contracts import MAX_SOURCES_PER_PAIR, resolve


def validate_request(req) -> None:
    portfolio = getattr(req, "sourcing", None)
    if portfolio is None:
        return
    sources = {s.id: s for s in req.sources}
    approved = {s.id for s in req.sources if s.approved and s.compliance == "cleared"}
    # every economic figure a sourcing decision compares must be finite (the frozen contract bounds
    # signs, not magnitudes; a non-finite price or capacity would poison the objective)
    for s in req.sources:
        for field in ("unit_price", "freight_per_unit", "handling_per_unit", "fixed_order_fee", "minimum", "maximum", "fill_mean", "fill_sd", "lead_sd_days"):
            if not math.isfinite(float(getattr(s, field))):
                raise ValueError(f"sourcing: source {s.id}: {field} is not finite")
        if any(not math.isfinite(float(c)) for c in s.capacity_by_period):
            raise ValueError(f"sourcing: source {s.id}: capacity is not finite")
    for st in getattr(req, "supplier_terms", ()) or ():
        for field in ("minimum_order_value", "fixed_order_cost", "receiving_fee_per_receipt", "receiving_per_pallet", "freight_per_pallet"):
            if not math.isfinite(float(getattr(st, field))):
                raise ValueError(f"sourcing: supplier terms {st.supplier}: {field} is not finite")
    pairs: dict[tuple[str, str], list[str]] = {}
    for s in req.sources:
        pairs.setdefault((s.sku, s.destination), []).append(s.id)
    for pair, ids in pairs.items():
        if len(ids) > MAX_SOURCES_PER_PAIR:
            raise ValueError(f"sourcing: {len(ids)} sources for {pair[0]} at {pair[1]}; at most {MAX_SOURCES_PER_PAIR}")
    # risk groups: known members, no duplicate ids, no duplicated member set, common share bounded
    seen_ids: set[str] = set()
    seen_sets: set[frozenset[str]] = set()
    common: dict[str, float] = {}
    for g in portfolio.risk_groups:
        if g.id in seen_ids:
            raise ValueError(f"sourcing: duplicate risk group id {g.id!r}")
        seen_ids.add(g.id)
        members = frozenset(g.members)
        if members in seen_sets:
            raise ValueError(f"sourcing: risk group {g.id} duplicates another group's members")
        seen_sets.add(members)
        for m in g.members:
            if m not in sources:
                raise ValueError(f"sourcing: risk group {g.id} names unknown source {m!r}")
            common[m] = common.get(m, 0.) + g.correlation
    for m, total in common.items():
        if total > 1. + 1e-9:
            raise ValueError(f"sourcing: source {m} has a total group correlation of {total:.3f} above 1; the shock cannot keep its marginal")
    # share constraints: one per source and scope, matching pair, qualified source, feasible sums
    seen_share: set[tuple[str, str]] = set()
    by_pair: dict[tuple[str, str, str], list] = {}
    for c in portfolio.share_constraints:
        if c.source not in sources:
            raise ValueError(f"sourcing: share constraint for unknown source {c.source!r}")
        s = sources[c.source]
        if (s.sku, s.destination) != (c.sku, c.destination):
            raise ValueError(f"sourcing: share constraint for {c.source} names {c.sku} at {c.destination}, but the source supplies {s.sku} to {s.destination}")
        if (c.source, c.scope) in seen_share:
            raise ValueError(f"sourcing: duplicate share constraint for {c.source} ({c.scope})")
        seen_share.add((c.source, c.scope))
        if (c.minimum_share > 0 or c.committed_units > 0) and c.source not in approved:
            raise ValueError(f"sourcing: source {c.source} is not qualified (approved and cleared) and cannot carry a minimum share or committed units")
        by_pair.setdefault((c.sku, c.destination, c.scope), []).append(c)
        if c.committed_units > 0:
            capacity = sum(min(s.maximum, cap) for cap in s.capacity_by_period[:req.horizon])
            if c.committed_units > capacity + 1e-9:
                raise ValueError(f"sourcing: committed units {c.committed_units:g} for {c.source} exceed its capacity over the horizon ({capacity:g})")
    for (sku, dest, scope), rows in by_pair.items():
        if sum(r.minimum_share for r in rows) > 1. + 1e-9:
            raise ValueError(f"sourcing: minimum shares for {sku} at {dest} sum above 100 %")
        ids = pairs.get((sku, dest), [])
        constrained = {r.source: r.maximum_share for r in rows}
        if sum(constrained.get(i, 1.) for i in ids if i in approved) < 1. - 1e-9:
            raise ValueError(f"sourcing: maximum shares for {sku} at {dest} sum below 100 %; no full commitment is possible")
    # switching costs and incumbent shares
    seen_switch: set[str] = set()
    for c in portfolio.switching_costs:
        if c.source not in sources:
            raise ValueError(f"sourcing: switching cost for unknown source {c.source!r}")
        if c.source in seen_switch:
            raise ValueError(f"sourcing: duplicate switching cost for {c.source}")
        seen_switch.add(c.source)
        if not math.isfinite(c.cost):
            raise ValueError(f"sourcing: switching cost for {c.source} is not finite")
    mix: dict[tuple[str, str], float] = {}
    seen_mix: set[str] = set()
    for row in portfolio.incumbent_shares:
        if row.source not in sources:
            raise ValueError(f"sourcing: incumbent share for unknown source {row.source!r}")
        s = sources[row.source]
        if (s.sku, s.destination) != (row.sku, row.destination):
            raise ValueError(f"sourcing: incumbent share for {row.source} names {row.sku} at {row.destination}, but the source supplies {s.sku} to {s.destination}")
        if row.source in seen_mix:
            raise ValueError(f"sourcing: duplicate incumbent share for {row.source}")
        seen_mix.add(row.source)
        mix[row.sku, row.destination] = mix.get((row.sku, row.destination), 0.) + row.share
    for pair, total in mix.items():
        if total > 1. + 1e-9:
            raise ValueError(f"sourcing: incumbent shares for {pair[0]} at {pair[1]} sum above 100 %")
    # A declared share limit is a contract the incumbent must already satisfy, so that ZAAD's constrained
    # candidates are compared against a contract-feasible incumbent: the pair needs declared incumbent
    # shares that meet every limit (dated incumbent orders are the operator's actual orders and are
    # reported against the limits instead).
    declared_mix = {(r.sku, r.destination, r.source): r.share for r in portfolio.incumbent_shares}
    for c in portfolio.share_constraints:
        if getattr(req, "incumbent_orders", ()):
            continue
        if (c.sku, c.destination) not in mix:
            raise ValueError(f"sourcing: {c.sku} at {c.destination} carries a share constraint but no declared incumbent shares; declare the current mix so the constraint can be compared")
        share = declared_mix.get((c.sku, c.destination, c.source), 0.)
        if share < c.minimum_share - 1e-9 or share > c.maximum_share + 1e-9:
            raise ValueError(f"sourcing: the declared incumbent share of {c.source} ({share:.0%}) does not meet its declared limits [{c.minimum_share:.0%}, {c.maximum_share:.0%}]")
    resolve(req)
