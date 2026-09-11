"""Sector-language explanations and the `physics` report block.

Reads the request's resolved physics, the final plan and its confirmation rows (settlements on the
selection worlds) and states, per SKU and location, physical against sellable stock at the review
and what the physics did to the executed actions. Ownership labels stay P0 / P1 / P2; the block only
adds the physical reason. No solver vocabulary."""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

from zaad.sectors.contracts import resolve

SECTOR_PRINCIPLE = {
    "COMMERCIAL": "Economic replenishment under real purchasing and import constraints.",
    "PRODUCE": "The right amount of product, with enough life left to sell it.",
    "MEAT_SEAFOOD": "Protect service without turning uncertainty into unnecessary aging, expiry and working capital.",
}


def _periods(n: int | float) -> str:
    n = int(n)
    return f"{n} period" if n == 1 else f"{n} periods"


def _stock_view(req, physics) -> list[dict[str, Any]]:
    """Physical and sellable units on hand at period zero, per SKU and location."""
    rows: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"physical_on_hand": 0., "sellable_on_hand": 0., "shortest_remaining_life": math.inf})
    for lot in req.stock:
        row = rows[lot.sku, lot.location]
        row["physical_on_hand"] += lot.usable
        if physics.sellable(lot.sku, lot.expires_in, 0):
            row["sellable_on_hand"] += lot.usable
        if lot.usable > 0:
            row["shortest_remaining_life"] = min(row["shortest_remaining_life"], lot.expires_in)
    out = []
    for (sku, location), row in sorted(rows.items()):
        p = physics.sku[sku]
        out.append({"sku": sku, "location": location, "sector": p.sector, "storage_state": p.storage_state,
                    "physical_on_hand": round(row["physical_on_hand"], 3), "sellable_on_hand": round(row["sellable_on_hand"], 3),
                    "unsellable_on_hand": round(row["physical_on_hand"] - row["sellable_on_hand"], 3),
                    "shortest_remaining_life_periods": None if row["shortest_remaining_life"] == math.inf else int(row["shortest_remaining_life"]),
                    "minimum_remaining_life_at_sale": p.minimum_remaining_life_at_sale})
    return out


def _action_sentences(req, physics, final) -> list[str]:
    sentences: list[str] = []
    if final is None:
        return sentences
    skus = {s.id: s for s in req.skus}
    sources = {s.id: s for s in req.sources}
    lanes = {a.id: a for a in req.transfers}
    for (source_id, t), q in sorted(final.purchases.items()):
        if t != 0 or q <= 1e-9:
            continue
        src = sources[source_id]
        p = physics.sku[src.sku]
        life = physics.receipt_life(src.sku, source_id)
        if p.sector == "COMMERCIAL":
            packs = [m for m in (src.case_multiple, src.pallet_multiple, src.transport_multiple, src.multiple) if m > 0]
            if packs:
                unit = max(packs)
                sentences.append(f"{src.sku}: {q:.0f} units from {src.supplier} is {q / unit:.0f} x {unit:.0f}-unit packs; the supplier ships whole packs.")
        elif physics.age_at_receipt(src.sku, source_id) > 0:
            sentences.append(f"{src.sku}: {q:.0f} units from {src.supplier} arrive with {life} of {skus[src.sku].shelf_life} periods of life "
                             f"(age at receipt {_periods(physics.age_at_receipt(src.sku, source_id))}); they are sellable for {_periods(max(0, life - p.minimum_remaining_life_at_sale))}.")
    for (lane_id, expiry, t), q in sorted(final.transfers.items()):
        if t != 0 or q <= 1e-9:
            continue
        arc = lanes[lane_id]
        p = physics.sku[arc.sku]
        remaining = expiry - arc.lead_periods
        if p.sector != "COMMERCIAL":
            sentences.append(f"{arc.sku}: {q:.0f} units {arc.origin} -> {arc.destination} on {lane_id} ({p.storage_state.lower()}) arrive with "
                             f"{_periods(remaining)} of life, {max(0, remaining - p.minimum_remaining_life_at_sale)} of them sellable.")
    # what the physics ruled out
    for arc in req.transfers:
        if not physics.lane_ok(arc.sku, arc.id):
            sentences.append(f"{arc.sku}: lane {arc.id} cannot carry {physics.state(arc.sku).lower()} goods; it is not used.")
        elif not physics.location_ok(arc.sku, arc.destination):
            sentences.append(f"{arc.sku}: {arc.destination} cannot store {physics.state(arc.sku).lower()} goods; no transfer or receipt goes there.")
    for src in req.sources:
        if src.approved and physics.receipt_life(src.sku, src.id) <= physics.min_receipt(src.sku):
            sentences.append(f"{src.sku}: purchases from {src.supplier} would arrive with {_periods(physics.receipt_life(src.sku, src.id))} of life, "
                             f"below the {_periods(physics.min_receipt(src.sku))} required at receipt; the source is not used.")
    for lot in req.stock:
        if lot.usable > 0 and physics.location_ok(lot.sku, lot.location):
            for arc in req.transfers:
                if arc.sku == lot.sku and arc.origin == lot.location and physics.lane_ok(arc.sku, arc.id) and physics.location_ok(arc.sku, arc.destination) \
                        and not physics.receivable(arc.sku, lot.expires_in, arc.lead_periods) and lot.expires_in > arc.lead_periods:
                    sentences.append(f"{lot.sku}: the {lot.usable:.0f}-unit lot at {lot.location} (expires in {_periods(lot.expires_in)}) would reach {arc.destination} with "
                                     f"{_periods(lot.expires_in - arc.lead_periods)} of life, below the {_periods(physics.min_receipt(lot.sku))} required at receipt; it stays where it can still be sold.")
    return sentences


def physics_block(req, final, final_rows, incumbent, incumbent_rows, fits) -> dict[str, Any]:
    physics = resolve(req)
    if physics is None:
        return {}
    expired = None
    if final_rows and all(r.get("usable") for r in final_rows):
        expired = sum(r.get("trace", [{}])[-1].get("expired_units", 0.) * r.get("weight", 1.) for r in final_rows if r.get("trace"))
    profiles = []
    for sku in sorted(physics.sku):
        p = physics.sku[sku]
        profiles.append({"sku": sku, "sector": p.sector, "declared": sku in physics.declared, "storage_state": p.storage_state,
                         "shelf_life_periods": physics.shelf_life[sku], "age_at_receipt_periods": p.age_at_receipt_periods,
                         "age_at_receipt_by_source": dict(p.age_at_receipt_by_source),
                         "minimum_remaining_life_at_receipt": p.minimum_remaining_life_at_receipt,
                         "minimum_remaining_life_at_sale": p.minimum_remaining_life_at_sale,
                         "weight_per_unit": p.weight_per_unit, "provenance": dict(p.provenance)})
    return {"version": "zaad.sectors.1.0", "sector_default": physics.sector_default,
            "principles": {m: SECTOR_PRINCIPLE[m] for m in sorted({p.sector for p in physics.sku.values()})},
            "profiles": profiles,
            "storage": {"locations": {k: sorted(v) for k, v in physics.location_states.items() if v}, "lanes": {k: sorted(v) for k, v in physics.lane_states.items() if v}},
            "stock": _stock_view(req, physics),
            "expected_expired_units_over_plan": expired,
            "explanations": _action_sentences(req, physics, final),
            "scope": "physics changes which units can be received, held, moved and sold and what a residual unit is worth; the frozen P0 / P1 / P2 engine still chooses the action",
            "metric_note": "sellable_on_hand counts units with more remaining life than the minimum at sale; service is measured on units served, which are sellable by construction"}
