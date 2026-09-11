"""The operator's incumbent source mix in the frozen rule projections (P3).

The frozen purchasing rules (`zaad.full.policies.baseline_plan`, `zaad.meio.baselines.network_rule_plan`)
buy each period's quantity from the cheapest landed source of the pair. When the request declares
`incumbent_shares` for the pair, the same quantity is split across the declared sources in those shares,
each line lot-rounded and capped by its own source, so the incumbent ZAAD is compared against is the mix
the operator actually runs. Without declared shares (or without a sourcing block) the split is the
frozen single line, unchanged."""
from __future__ import annotations

import math

from zaad.full.contracts import Source
from zaad.full.economics import round_up


def _round_down(q: float, pack: float) -> float:
    return q if pack <= 0 else math.floor(q / pack + 1e-9) * pack


def lot_fit(source: Source, q: float, t: int) -> float:
    """Lift to the MOQ and packs, cap by the source's maximum and dated capacity, then bring an illegal
    cap back to the pack below it (the projection is always physically legal)."""
    if q <= 0:
        return 0.
    q = max(q, source.minimum)
    for m in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple):
        q = round_up(q, m)
    q = min(q, source.maximum, source.capacity_by_period[t])
    for pack in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple):
        if pack > 0:
            q = _round_down(q, pack)
    return q if q >= source.minimum - 1e-9 else 0.


def split_projection(sourcing, sku: str, location: str, options: list[Source], primary: Source, q: float, t: int) -> list[tuple[Source, float]]:
    """[(source, quantity)] for a rule's period quantity `q`: the declared incumbent mix when one exists
    for the pair (restricted to the eligible `options`), otherwise the frozen single line."""
    mix = sourcing.incumbent_mix.get((sku, location)) if sourcing is not None else None
    if not mix:
        return [(primary, q)]
    by_id = {s.id: s for s in options}
    rows = [(by_id[sid], share) for sid, share in mix.items() if sid in by_id]
    if not rows:
        return [(primary, q)]
    total_share = sum(share for _, share in rows)
    out: list[tuple[Source, float]] = []
    remaining = q
    for i, (source, share) in enumerate(rows):
        want = remaining if i == len(rows) - 1 else q * share / total_share
        line = lot_fit(source, min(want, remaining), t)
        if line > 0:
            out.append((source, line))
            remaining = max(0., remaining - line)
    return out


def apply_resource_cap(req, purchases: dict[tuple[str, int], float]) -> dict[str, float]:
    """Keep every projected supplier order inside the shared resource capacity it draws on (P3): when
    the lines on one resource in one period exceed its dated capacity, they are scaled down
    proportionally and pack-rounded down, and a line that falls below its MOQ is dropped. A buyer whose
    supplier allocates a shared capacity does exactly this; the frozen rule projections buy per SKU
    and never see a resource shared across SKUs. Returns the units removed per resource."""
    sources = {s.id: s for s in req.sources}
    volume = {s.id: next(k.volume for k in req.skus if k.id == s.id) for s in req.skus}
    removed: dict[str, float] = {}
    for resource in req.resources:
        for t in range(req.horizon):
            lines = [(sid, q) for (sid, k), q in purchases.items() if k == t and q > 0 and resource.id in sources[sid].resources]
            used = sum(q * volume[sources[sid].sku] for sid, q in lines)
            cap = resource.capacity_by_period[t]
            if used <= cap + 1e-9 or not lines:
                continue
            scale = cap / used
            for sid, q in lines:
                src = sources[sid]
                capped = q * scale
                for pack in (src.multiple, src.case_multiple, src.pallet_multiple, src.transport_multiple):
                    if pack > 0:
                        capped = _round_down(capped, pack)
                if capped < src.minimum - 1e-9:
                    capped = 0.
                removed[resource.id] = removed.get(resource.id, 0.) + (q - capped)
                if capped > 0:
                    purchases[sid, t] = capped
                else:
                    purchases.pop((sid, t), None)
    return removed


def fit_resources(req, used: dict[tuple[str, int], float], source: Source, q: float, t: int) -> float:
    """Cap a projected line by the room left on every shared resource it draws on in period `t`
    (pack-rounded down; below the MOQ the line is dropped) and book its usage. `used` accumulates
    volume per (resource, period) across SKUs, so a rule projected SKU by SKU never exceeds a
    capacity two SKUs share."""
    resources = {r.id: r for r in req.resources}
    volume = next(k.volume for k in req.skus if k.id == source.sku)
    room = q
    for rid in source.resources:
        left = (resources[rid].capacity_by_period[t] - used.get((rid, t), 0.)) / volume
        room = min(room, max(0., left))
    if room < q - 1e-9:
        for pack in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple):
            if pack > 0:
                room = _round_down(room, pack)
        if room < source.minimum - 1e-9:
            room = 0.
    for rid in source.resources:
        used[rid, t] = used.get((rid, t), 0.) + room * volume
    return room
