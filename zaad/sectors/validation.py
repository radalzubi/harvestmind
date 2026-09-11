"""Validation of declared sector physics against the request it is attached to.

Runs inside the frozen request's own validator, so a malformed combination is refused at the
contract (HTTP 422 on the API) before any model is built. A legacy request (no sector mode, no
profile) is not inspected beyond the enum checks pydantic already performs.
"""
from __future__ import annotations

from zaad.sectors.contracts import SECTOR_MODES, STORAGE_STATES, resolve

MAX_PROFILES = 5000   # the frozen SKU cap; a profile per SKU at most


def validate_request(req) -> None:
    mode = getattr(req, "sector_mode", None)
    profiles = tuple(getattr(req, "sku_physics", ()) or ())
    if mode is not None and mode not in SECTOR_MODES:
        raise ValueError(f"unknown sector mode {mode!r}; expected one of {SECTOR_MODES}")
    for loc in req.locations:
        for s in getattr(loc, "storage_states", ()) or ():
            if s not in STORAGE_STATES:
                raise ValueError(f"location {loc.id}: unknown storage state {s!r}")
    for arc in req.transfers:
        for s in getattr(arc, "storage_states", ()) or ():
            if s not in STORAGE_STATES:
                raise ValueError(f"lane {arc.id}: unknown storage state {s!r}")
    physics = resolve(req)
    if physics is None:
        return
    if len(profiles) > MAX_PROFILES:
        raise ValueError(f"at most {MAX_PROFILES} sku physics profiles")
    skus = {s.id: s for s in req.skus}
    seen: set[str] = set()
    for p in profiles:
        if p.sku not in skus:
            raise ValueError(f"sku physics for unknown SKU {p.sku!r}")
        if p.sku in seen:
            raise ValueError(f"duplicate sku physics for {p.sku!r}")
        seen.add(p.sku)
        life = int(skus[p.sku].shelf_life)
        ages = [p.age_at_receipt_periods, *p.age_at_receipt_by_source.values()]
        if max(ages) >= life:
            raise ValueError(f"sku physics {p.sku}: age at receipt ({max(ages)}) must be below the shelf life ({life})")
        if p.minimum_remaining_life_at_receipt >= life:
            raise ValueError(f"sku physics {p.sku}: minimum remaining life at receipt ({p.minimum_remaining_life_at_receipt}) must be below the shelf life ({life})")
        if p.minimum_remaining_life_at_sale >= life:
            raise ValueError(f"sku physics {p.sku}: minimum remaining life at sale ({p.minimum_remaining_life_at_sale}) must be below the shelf life ({life})")
        if p.minimum_remaining_life_at_receipt + max(ages) >= life:
            raise ValueError(f"sku physics {p.sku}: no purchase can arrive with the minimum remaining life at receipt (age {max(ages)} + minimum {p.minimum_remaining_life_at_receipt} >= shelf life {life})")
        sources = {s.id for s in req.sources}
        for source in p.age_at_receipt_by_source:
            if source not in sources:
                raise ValueError(f"sku physics {p.sku}: age at receipt for unknown source {source!r}")
        state = p.storage_state
        holders = [loc.id for loc in req.locations if physics.location_ok(p.sku, loc.id)]
        if not holders:
            raise ValueError(f"sku physics {p.sku}: no location can hold storage state {state}")
    for lot in req.stock:
        if lot.usable > 0 and lot.sku in physics.sku and not physics.location_ok(lot.sku, lot.location):
            raise ValueError(f"stock {lot.id}: {lot.sku} ({physics.state(lot.sku)}) is held at {lot.location}, which cannot store that state")
    for inbound in req.inbound_transfers:
        if inbound.sku in physics.sku and not physics.location_ok(inbound.sku, inbound.destination):
            raise ValueError(f"inbound transfer {inbound.id}: destination {inbound.destination} cannot store {physics.state(inbound.sku)}")
    for st in getattr(req, "supplier_terms", ()) or ():
        cap = getattr(st, "max_shipment_weight", None)
        if cap is not None:
            lines = [s for s in req.sources if s.supplier == st.supplier]
            missing = [s.sku for s in lines if physics.weight(s.sku) is None]
            if missing:
                raise ValueError(f"supplier {st.supplier}: max_shipment_weight declared but SKUs {sorted(set(missing))} have no weight_per_unit")
