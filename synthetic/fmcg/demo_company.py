"""One complete, deterministic DEMO company for the ZAAD operating product.

**DEMO / SYNTHETIC DATA. Not a customer. Never presented as one.** Every identifier begins with
``DEMO-``; the company name is invented; the dates end on the ``as_of`` you pass.

*Al-Bahr Trading* is a fictional Amman import distributor with two years of history that connects
across every record family the product reads:

    customers -> customer orders (with what was shipped) -> inventory snapshots by site
    -> SKUs -> suppliers on declared corridors -> purchase orders (promised dates) -> receipts
    -> lanes and transfers between sites -> declared alternative sources (P3)
    -> amendment rights on open orders (P4B) -> service classes and open customer orders (P5)

and it carries signal, not noise. The scenarios below are built in, and each reconciles with
its own source rows (``tests/integration/test_demo_company.py`` checks the arithmetic):

* a stable customer, a growing one, a declining one, a seasonal one (summer peak), and a
  small e-commerce account that grows from nothing;
* one visible demand spike five weeks before ``as_of``: the growing customer orders four times
  its usual quantity of three beverage products in one week;
* one supplier that deteriorates gradually (lateness rises through the second year), one that
  is reliable, one with a short-fill problem, one whose orders sometimes carry no promised date
  (so lateness is measurable on part of its orders, honestly);
* one product in excess (bought at 1.8x demand for six months), one exposed to shortage (its
  supplier short-fills and stock runs thin, so shipments fall short of orders), one site
  imbalance (Aqaba over-stocked, Irbid under-stocked on the same product);
* open purchase orders with declared amendment rights: one the engine is likely to defer (on the
  excess product), one it is likely to expedite (on the shortage product), one it is likely to
  keep; partial receipts; short fills; late, on-time and early deliveries.

Nothing here decides anything. The recommendations a demo shows come from the released engine
run over these rows; ``scripts/zaad_demo_workspace.py`` drives that loop through the public API.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

COMPANY = "Al-Bahr Trading (DEMO)"
CLASSIFICATION = "DEMO / SYNTHETIC DATA"
CURRENCY = "JOD"

LOCATIONS = [("DEMO-DC-AMMAN", "central_dc"), ("DEMO-BR-IRBID", "branch"), ("DEMO-BR-AQABA", "branch")]
LANES = [("DEMO-DC-AMMAN", "DEMO-BR-IRBID", 2, 0.09), ("DEMO-DC-AMMAN", "DEMO-BR-AQABA", 4, 0.17)]

#: supplier id, name, origin ISO3, route tag (a corridor the Network Twin already draws),
#: promised days, behaviour
SUPPLIERS = [
    ("DEMO-SUP-01", "Rhine Foods GmbH", "DEU", "aqaba", 28, "reliable"),
    ("DEMO-SUP-02", "Jiangnan Consumer Co.", "CHN", "aqaba", 36, "deteriorating"),
    ("DEMO-SUP-03", "Jeddah Distributors", "SAU", "jeddah", 12, "short_fill"),
    ("DEMO-SUP-04", "Gulf Paper Mills", "ARE", "road_saudi", 15, "partial_no_promise"),
    ("DEMO-SUP-05", "Anatolia Goods", "TUR", "iraq_overland", 20, "alternative"),
    ("DEMO-SUP-06", "Basra Beverages", "IRQ", "umm_qasr", 22, "reliable"),
]
CATEGORIES = {
    "Beverages": ("DEMO-SUP-06", "Sawa"), "Household": ("DEMO-SUP-02", "Nour"),
    "Personal care": ("DEMO-SUP-01", "Reem"), "Ambient food": ("DEMO-SUP-03", "Dalia"),
    "Paper": ("DEMO-SUP-04", "Qamar"), "Snacks": ("DEMO-SUP-01", "Tamr"),
}
#: customer id, name, service class, base share of demand, behaviour
CUSTOMERS = [
    ("DEMO-CUST-RETAIL-A", "Amman Retail Group", "CONTRACT", 0.26, "stable"),
    ("DEMO-CUST-GROW", "Sahara Supermarkets", "STRATEGIC", 0.16, "growing"),
    ("DEMO-CUST-DECLINE", "Old Souk Traders", "STANDARD", 0.14, "declining"),
    ("DEMO-CUST-HORECA", "Dead Sea Hotels", "CONTRACT", 0.12, "seasonal"),
    ("DEMO-CUST-WHOLESALE-B", "Zarqa Wholesale", "STANDARD", 0.15, "stable"),
    ("DEMO-CUST-ECOM", "Basket Online", "STANDARD", 0.05, "new_growing"),
    ("DEMO-CUST-PHARMA", "Petra Pharmacies", "CONTRACT", 0.06, "stable"),
    ("DEMO-CUST-EXPORT", "Baghdad Trading House", "STANDARD", 0.06, "lumpy"),
]
# Categories cycle through the catalogue (index 1 Beverages, 2 Household, 3 Personal care, 4 Ambient
# food, 5 Paper, 6 Snacks, 7 Beverages, ...), so each scenario product below sits in the category —
# and with the supplier — its story needs.
EXCESS_SKU = "DEMO-0008"       # Household (Jiangnan), bought at 1.8x demand for six months
SHORTAGE_SKU = "DEMO-0010"     # Ambient food (Jeddah, the short-filling supplier), thin cover
IMBALANCE_SKU = "DEMO-0021"    # Personal care: Aqaba over-stocked, Irbid under-stocked
SPIKE_SKUS = ("DEMO-0001", "DEMO-0007", "DEMO-0013")   # beverages, the growing customer's spike
SPIKE_WEEKS_BEFORE_END = 5
HISTORY_WEEKS = 104


@dataclass
class DemoCompany:
    as_of: date
    seed: int
    skus: list[dict[str, Any]] = field(default_factory=list)
    suppliers: list[dict[str, Any]] = field(default_factory=list)
    customers: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)
    lanes: list[dict[str, Any]] = field(default_factory=list)
    transfers: list[dict[str, Any]] = field(default_factory=list)
    orders: list[dict[str, Any]] = field(default_factory=list)
    purchase_orders: list[dict[str, Any]] = field(default_factory=list)
    receipts: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    commitments: list[dict[str, Any]] = field(default_factory=list)
    options: list[dict[str, Any]] = field(default_factory=list)
    service_classes: list[dict[str, Any]] = field(default_factory=list)
    atp_orders: list[dict[str, Any]] = field(default_factory=list)
    economics: list[dict[str, Any]] = field(default_factory=list)
    scenarios: dict[str, Any] = field(default_factory=dict)

    def counts(self) -> dict[str, int]:
        return {name: len(getattr(self, name)) for name in (
            "skus", "suppliers", "customers", "locations", "lanes", "transfers", "orders", "purchase_orders",
            "receipts", "inventory", "sources", "commitments", "options", "service_classes", "atp_orders", "economics")}


def _weeks(end: date, count: int) -> list[date]:
    """`count` Mondays whose weeks close (Sunday) on or before `end`."""
    last = end - timedelta(days=end.weekday())   # the Monday of `end`'s week
    if last + timedelta(days=6) > end:
        last -= timedelta(days=7)               # that week has not closed yet: use the one before
    return [last - timedelta(weeks=count - 1 - i) for i in range(count)]


def build_demo_company(as_of: date | None = None, seed: int = 7) -> DemoCompany:
    rng = random.Random(seed)
    today = as_of or date.today()
    weeks = _weeks(today - timedelta(days=1), HISTORY_WEEKS)
    n = len(weeks)
    c = DemoCompany(as_of=today, seed=seed)

    # ── masters ──
    for sid, name, origin, route, promised_days, behaviour in SUPPLIERS:
        c.suppliers.append({"supplier_id": sid, "supplier_name": name, "origin_iso3": origin, "route": route,
                            "capacity_per_week": 60_000 if behaviour != "short_fill" else 18_000,
                            "lead_time_promised_weeks": round(promised_days / 7, 1), "behaviour": behaviour,
                            "promised_days": promised_days,
                            "risk_group": f"port_{route}" if route in ("aqaba", "jeddah", "umm_qasr") else None,
                            "risk_group_kind": "PORT" if route in ("aqaba", "jeddah", "umm_qasr") else None})
    supplier_of = {s["supplier_id"]: s for s in c.suppliers}
    for lid, kind in LOCATIONS:
        c.locations.append({"location_id": lid, "kind": kind, "holding_annual": 0.12 if kind == "central_dc" else 0.16,
                            "capacity_units": 600_000 if kind == "central_dc" else 120_000})
    for origin, destination, lead, cost in LANES:
        c.lanes.append({"lane_id": f"{origin}->{destination}", "origin_id": origin, "destination_id": destination,
                        "lead_days": lead, "cost_per_unit": cost, "capacity_per_week": 40_000, "approved": True})
    categories = list(CATEGORIES)
    for index in range(1, 37):
        category = categories[(index - 1) % len(categories)]
        sid, brand = CATEGORIES[category]
        pack = [6, 12, 24, 48][index % 4]
        cost = round(rng.uniform(0.6, 9.5), 2)
        weekly = rng.randint(400, 2400)
        c.skus.append({"sku": f"DEMO-{index:04d}", "sku_name": f"{brand} {category.split()[0]} {['1L', '500ml', '2kg', '750g', '12s', '24s'][index % 6]} #{index}",
                       "brand": brand, "category": category, "sub_category": f"{category} — line {index % 3 + 1}",
                       "supplier_id": sid, "unit_cost": cost, "unit_price": round(cost * rng.uniform(1.2, 1.5), 2),
                       "units_per_case": pack, "cases_per_layer": 8, "layers_per_pallet": 6, "order_multiple": "case",
                       "moq_units": pack * rng.choice([10, 20, 40]), "shelf_life_days": rng.choice([180, 365, 540, 730]),
                       "abc_class": "A" if index % 4 == 0 else "B" if index % 3 else "C", "weekly": weekly})
    sku_of = {s["sku"]: s for s in c.skus}
    for cid, name, klass, share, behaviour in CUSTOMERS:
        c.customers.append({"customer_id": cid, "customer_name": name, "service_class": klass, "share": share, "behaviour": behaviour})

    # ── customer orders: who ordered what, week by week, and what was shipped ──
    spike_week = weeks[n - 1 - SPIKE_WEEKS_BEFORE_END]

    def customer_factor(behaviour: str, week_index: int, week: date) -> float:
        t = week_index / max(1, n - 1)
        if behaviour == "growing":
            return 0.5 + 1.0 * t
        if behaviour == "declining":
            return 1.4 - 0.8 * t
        if behaviour == "seasonal":
            return 1.0 + 0.6 * max(0., math.sin((week.timetuple().tm_yday - 100) / 365 * 2 * math.pi))
        if behaviour == "new_growing":
            return 0. if t < 0.4 else (t - 0.4) / 0.6 * 1.6
        if behaviour == "lumpy":
            return 3.0 if week_index % 4 == 0 else 0.
        return 1.0

    def category_factor(category: str, week: date) -> float:
        if category == "Beverages":   # summer peak
            return 1.0 + 0.45 * max(0., math.sin((week.timetuple().tm_yday - 120) / 365 * 2 * math.pi))
        return 1.0

    demand_plan: dict[tuple[str, int, str], list[tuple[str, int]]] = {}   # (sku, week_index, location) -> [(customer, qty)]
    site_of_customer = {cid: LOCATIONS[i % 3][0] for i, (cid, *_rest) in enumerate(CUSTOMERS)}
    for s in c.skus:
        for wi, week in enumerate(weeks):
            base = s["weekly"] * category_factor(s["category"], week)
            for cid, _name, _klass, share, behaviour in CUSTOMERS:
                spike_line = week == spike_week and cid == "DEMO-CUST-GROW" and s["sku"] in SPIKE_SKUS
                if rng.random() < 0.18 and behaviour != "lumpy" and not spike_line:
                    continue   # not every customer orders every product every week
                qty = base * share * customer_factor(behaviour, wi, week) * rng.uniform(0.75, 1.25)
                if spike_line:
                    qty *= 4.0
                qty = int(round(qty / s["units_per_case"])) * s["units_per_case"]
                if qty <= 0:
                    continue
                demand_plan.setdefault((s["sku"], wi, site_of_customer[cid]), []).append((cid, qty))

    # what each product's customers actually order each week, so purchasing can track it
    weekly_orders: dict[tuple[str, int], int] = {}
    for (sku, wi, _site), rows in demand_plan.items():
        weekly_orders[(sku, wi)] = weekly_orders.get((sku, wi), 0) + sum(q for _cid, q in rows)

    # ── purchase orders and receipts (the supply side), then the stock balance that shipments obey ──
    po_seq = 0
    receipts_by_week: dict[tuple[str, int], int] = {}   # (sku, week_index at the DC) -> units received
    for s in c.skus:
        sup = supplier_of[s["supplier_id"]]
        behaviour = sup["behaviour"]
        for wi, week in enumerate(weeks):
            if wi % 2:
                continue
            po_seq += 1
            po_id = f"DEMO-PO-{po_seq:05d}"
            # buy for the fortnight the order will land in (about four weeks out), from what customers order
            ahead = [weekly_orders.get((s["sku"], w), 0) for w in (wi + 4, wi + 5) if w < n]
            fortnight_demand = sum(ahead) if ahead else 2 * s["weekly"] * 0.8 * category_factor(s["category"], week)
            if len(ahead) == 1:
                fortnight_demand *= 2
            multiplier = 1.0
            if s["sku"] == EXCESS_SKU and wi >= n - 26:
                multiplier = 1.8
            if s["sku"] == SHORTAGE_SKU:
                multiplier = 0.85
            qty = max(s["units_per_case"], int(round(fortnight_demand * multiplier * rng.uniform(0.9, 1.1) / s["units_per_case"])) * s["units_per_case"])
            promised: date | None = week + timedelta(days=sup["promised_days"])
            if behaviour == "partial_no_promise" and (po_seq % 2 == 0):
                promised = None
            c.purchase_orders.append({"po_id": po_id, "po_date": week, "supplier_id": sup["supplier_id"], "sku": s["sku"],
                                      "qty_ordered": qty, "unit_cost": s["unit_cost"], "expected_delivery_date": promised,
                                      "destination_id": LOCATIONS[0][0]})
            # arrival behaviour
            t = wi / max(1, n - 1)
            if behaviour == "deteriorating":
                late_share, late_days = 0.05 + 0.40 * max(0., t - 0.4) / 0.6, int(2 + 14 * max(0., t - 0.4) / 0.6)
            elif behaviour == "short_fill":
                late_share, late_days = 0.15, 4
            elif behaviour == "reliable":
                late_share, late_days = 0.05, 2
            else:
                late_share, late_days = 0.12, 5
            nominal = week + timedelta(days=sup["promised_days"])
            arrives = nominal + timedelta(days=(rng.randint(1, max(1, late_days) + 3) if rng.random() < late_share else -rng.randint(0, 3)))
            if arrives >= today - timedelta(days=3) or wi >= n - 4:
                continue   # still open: not yet arrived, or placed within the last four weeks and in flight
            fill = 1.0
            if behaviour == "short_fill":
                fill = min(1.0, rng.gauss(0.82, 0.08))
            elif rng.random() < 0.06:
                fill = rng.uniform(0.9, 0.99)
            received_total = max(0, int(qty * fill / s["units_per_case"]) * s["units_per_case"])
            parts = [(arrives, received_total)]
            if behaviour == "partial_no_promise" and received_total >= 4 * s["units_per_case"] and rng.random() < 0.5:
                first = int(received_total * 0.6 / s["units_per_case"]) * s["units_per_case"]
                parts = [(arrives, first), (arrives + timedelta(days=7), received_total - first)]
            for pi, (when, units) in enumerate(parts, start=1):
                if units <= 0:
                    continue
                c.receipts.append({"receipt_id": f"DEMO-RCPT-{po_id}-{pi}", "po_id": po_id, "receipt_date": when,
                                   "sku": s["sku"], "qty_received": units, "qty_rejected": 0})
                arrival_week = min(n - 1, max(0, (when - weeks[0]).days // 7))
                receipts_by_week[(s["sku"], arrival_week)] = receipts_by_week.get((s["sku"], arrival_week), 0) + units

    # stock balance per site, weekly: DC receives, ships to branches by lane, every site ships to its customers
    order_seq = 0
    branch_share = {"DEMO-BR-IRBID": 0.28, "DEMO-BR-AQABA": 0.22}
    for s in c.skus:
        stock = {LOCATIONS[0][0]: 8 * s["weekly"], "DEMO-BR-IRBID": 3 * s["weekly"], "DEMO-BR-AQABA": 3 * s["weekly"]}
        if s["sku"] == SHORTAGE_SKU:
            stock = {k: int(v * 0.35) for k, v in stock.items()}
        for wi, week in enumerate(weeks):
            stock[LOCATIONS[0][0]] += receipts_by_week.get((s["sku"], wi), 0)
            # transfers: top the branches up towards a few weeks of their demand
            for branch, share in branch_share.items():
                target = 3 * s["weekly"] * share
                if s["sku"] == IMBALANCE_SKU and wi >= n - 30:
                    target = target * (2.4 if branch == "DEMO-BR-AQABA" else 0.35)
                need = int(max(0., target - stock[branch]) / s["units_per_case"]) * s["units_per_case"]
                move = min(need, int(stock[LOCATIONS[0][0]] * 0.5 / s["units_per_case"]) * s["units_per_case"])
                if move > 0:
                    lead = next(lane[2] for lane in LANES if lane[1] == branch)
                    c.transfers.append({"transfer_id": f"DEMO-TR-{s['sku']}-{wi:03d}-{branch[-5:]}", "lane_id": f"{LOCATIONS[0][0]}->{branch}",
                                        "origin_id": LOCATIONS[0][0], "destination_id": branch, "sku": s["sku"], "qty": move,
                                        "dispatch_date": week, "expected_arrival_date": week + timedelta(days=lead),
                                        "received_date": week + timedelta(days=lead + (1 if wi % 7 == 0 else 0))})
                    stock[LOCATIONS[0][0]] -= move
                    stock[branch] += move
            # shipments: each site serves its customers from its own stock; a shortfall is recorded, never invented
            for site in stock:
                for cid, qty in demand_plan.get((s["sku"], wi, site), []):
                    order_seq += 1
                    shipped = min(qty, stock[site])
                    stock[site] -= shipped
                    c.orders.append({"order_id": f"DEMO-SO-{order_seq:06d}", "customer_id": cid, "order_date": week + timedelta(days=rng.randint(0, 4)),
                                     "requested_delivery_date": week + timedelta(days=rng.randint(3, 7)), "sku": s["sku"],
                                     "qty_ordered": qty, "qty_shipped": shipped, "channel": "wholesale", "location_id": site})
            # the weekly snapshot, taken on the Sunday closing the week
            snapshot = week + timedelta(days=6)
            for site, units in stock.items():
                c.inventory.append({"snapshot_date": snapshot, "sku": s["sku"], "location_id": site, "on_hand": units,
                                    "in_transit": 0, "expiry_date": None})

    # ── declared alternative sources (P3) on a third of the catalogue, from the Turkish corridor ──
    for s in c.skus[::3]:
        if s["supplier_id"] == "DEMO-SUP-05":
            continue
        c.sources.append({"sku": s["sku"], "supplier_id": "DEMO-SUP-05", "approved": True, "compliance": "cleared",
                          "unit_cost": round(s["unit_cost"] * 1.06, 2), "freight_per_unit": 0.05, "handling_per_unit": 0.01,
                          "capacity_per_week": 12_000, "lead_time_promised_weeks": 3.0, "moq_units": s["units_per_case"] * 10,
                          "units_per_case": s["units_per_case"], "incumbent_share": 0.0, "switching_cost": round(s["unit_cost"] * 40, 2),
                          "provenance": "OPERATOR_DECLARED"})

    # ── amendment rights (P4B) on three open orders: excess (defer), shortage (expedite), stable (keep) ──
    received_ids = {r["po_id"] for r in c.receipts}
    open_pos = [p for p in c.purchase_orders if p["po_id"] not in received_ids and p["po_date"] < today]

    def latest_open(sku: str) -> dict[str, Any] | None:
        rows = [p for p in open_pos if p["sku"] == sku]
        return max(rows, key=lambda p: p["po_date"]) if rows else None

    rights = {"defer": latest_open(EXCESS_SKU), "expedite": latest_open(SHORTAGE_SKU), "keep": latest_open("DEMO-0025")}
    for role, po in rights.items():
        if po is None:
            continue
        c.commitments.append({"po_id": po["po_id"], "stage": "ordered", "allow_split_amendments": True,
                              "minimum_remaining_quantity": 0, "prepaid_per_remaining_unit": 0.40,
                              "deposit_refundable_fraction": 0.5, "cancellation_status": "none", "role": role})
        c.options.append({"po_id": po["po_id"], "option_id": f"{po['po_id']}-defer", "action": "reschedule", "due_offset_periods": 6,
                          "fee_per_unit": 0.05, "credit_per_unit": 0, "max_quantity": 100000, "deadline": today + timedelta(days=30),
                          "allowed_stages": '["ordered"]', "contract_reference": f"Contract {po['po_id']}", "provenance": "CONTRACT"})
        c.options.append({"po_id": po["po_id"], "option_id": f"{po['po_id']}-expedite", "action": "expedite", "due_offset_periods": 1,
                          "fee_per_unit": 0.18, "credit_per_unit": 0, "max_quantity": 100000, "deadline": today + timedelta(days=14),
                          "allowed_stages": '["ordered"]', "contract_reference": f"Contract {po['po_id']}", "provenance": "CONTRACT"})
        c.options.append({"po_id": po["po_id"], "option_id": f"{po['po_id']}-cancel", "action": "cancel", "due_offset_periods": 0,
                          "fee_per_unit": 0.10, "credit_per_unit": 0.20, "max_quantity": 100000, "deadline": today + timedelta(days=14),
                          "allowed_stages": '["ordered"]', "contract_reference": f"Contract {po['po_id']}", "provenance": "CONTRACT"})

    # ── service classes and open customer orders (P5) on the shortage product ──
    for klass, floor, penalty, strategic in (("STRATEGIC", 0.98, 1.8, True), ("CONTRACT", 0.95, 1.2, False), ("STANDARD", 0.90, 0.6, False)):
        c.service_classes.append({"class_id": klass, "provenance": "OPERATOR_DECLARED", "reference": f"Service policy {klass}",
                                  "contractual_service_floor": floor, "shortage_penalty_per_unit": penalty,
                                  "late_penalty_per_unit_period": 0.1, "refusal_cost_per_unit": 0.3, "lost_margin_per_unit": None,
                                  "strategic": strategic, "tier": klass.lower()})
    # The released planning contract carries one aggregate customer ("customers") per workspace and
    # distinguishes open orders by their declared service class, so the P5 declarations name that
    # aggregate — a named customer would be refused by the contract. Which customer placed each order
    # is kept in `reference` for people, not for the engine.
    for i, (cid, _name, klass, _share, _b) in enumerate(CUSTOMERS[:6]):
        c.atp_orders.append({"order_id": f"DEMO-ATP-{i + 1:03d}", "line_id": f"DEMO-ATP-{i + 1:03d}-1", "customer_id": "customers", "service_class": klass,
                             "placed_by": cid,
                             "sku": SHORTAGE_SKU, "quantity": sku_of[SHORTAGE_SKU]["units_per_case"] * (6 + 2 * i),
                             "minimum_ship_quantity": sku_of[SHORTAGE_SKU]["units_per_case"], "order_period": 0, "requested_period": 1 + i % 3,
                             "ship_from": None, "unit_margin": round(sku_of[SHORTAGE_SKU]["unit_price"] - sku_of[SHORTAGE_SKU]["unit_cost"], 2),
                             "partial_fulfillment_allowed": True, "backorder_allowed": True, "max_backorder_periods": 2,
                             "substitution_allowed": False, "late_semantics": "ACCEPT_LATE", "priority_provenance": "OPERATOR_DECLARED"})

    c.economics = [{"key": "currency", "value": CURRENCY, "provenance": "OPERATOR_DECLARED"},
                   {"key": "cost_of_capital_annual", "value": "0.11", "provenance": "OPERATOR_DECLARED"},
                   {"key": "storage_handling_annual", "value": "0.06", "provenance": "OPERATOR_DECLARED"}]
    c.scenarios = {
        "company": COMPANY, "classification": CLASSIFICATION, "as_of": today.isoformat(), "seed": seed,
        "history_weeks": HISTORY_WEEKS, "spike": {"week": spike_week.isoformat(), "customer": "DEMO-CUST-GROW", "skus": list(SPIKE_SKUS), "multiplier": 4.0},
        "excess_sku": EXCESS_SKU, "shortage_sku": SHORTAGE_SKU, "imbalance_sku": IMBALANCE_SKU,
        "amendment_rights": {role: (po["po_id"] if po else None) for role, po in rights.items()},
        "suppliers": {s["supplier_id"]: s["behaviour"] for s in c.suppliers},
        "customers": {cu["customer_id"]: cu["behaviour"] for cu in c.customers},
    }
    return c


def load_demo_company_into(conn: Any, operator: str, as_of: date | None = None, seed: int = 7) -> dict[str, Any]:
    """Replace the vault's FMCG staging data with the demo company. Returns what was loaded."""
    c = build_demo_company(as_of=as_of, seed=seed)
    tables = ["stg_fmcg_skus", "stg_fmcg_suppliers", "stg_fmcg_orders", "stg_fmcg_purchase_orders", "stg_fmcg_receipts",
              "stg_fmcg_inventory", "stg_fmcg_locations", "stg_fmcg_lanes", "stg_fmcg_transfers", "stg_fmcg_sources",
              "stg_fmcg_economics", "stg_fmcg_promotions"]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")  # nosec B608 - table names are literals above
    for table in ("stg_po_commitments", "stg_po_options", "stg_atp_service_classes", "stg_atp_customer_orders", "stg_atp_policy"):
        conn.execute(f"DELETE FROM {table} WHERE operator_id = ?", [operator])  # nosec B608 - literals; the operator binds

    def insert(table: str, rows: list[dict[str, Any]], columns: list[str], extra: dict[str, Any] | None = None) -> None:
        if not rows:
            return
        cols = list(columns) + list((extra or {}).keys())
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"  # nosec B608 - literals
        conn.executemany(sql, [[row.get(col) for col in columns] + list((extra or {}).values()) for row in rows])

    insert("stg_fmcg_skus", c.skus, ["sku", "sku_name", "brand", "category", "sub_category", "supplier_id", "unit_cost", "unit_price",
                                     "units_per_case", "cases_per_layer", "layers_per_pallet", "order_multiple", "moq_units", "shelf_life_days", "abc_class"])
    insert("stg_fmcg_suppliers", c.suppliers, ["supplier_id", "supplier_name", "origin_iso3", "route", "capacity_per_week",
                                               "lead_time_promised_weeks", "risk_group", "risk_group_kind"])
    insert("stg_fmcg_locations", c.locations, ["location_id", "kind", "holding_annual", "capacity_units"])
    insert("stg_fmcg_lanes", c.lanes, ["lane_id", "origin_id", "destination_id", "lead_days", "cost_per_unit", "capacity_per_week", "approved"])
    insert("stg_fmcg_transfers", c.transfers, ["transfer_id", "lane_id", "origin_id", "destination_id", "sku", "qty", "dispatch_date",
                                               "expected_arrival_date", "received_date"])
    insert("stg_fmcg_orders", c.orders, ["order_id", "customer_id", "order_date", "requested_delivery_date", "sku", "qty_ordered",
                                         "qty_shipped", "channel", "location_id"])
    insert("stg_fmcg_purchase_orders", c.purchase_orders, ["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost",
                                                           "expected_delivery_date", "destination_id"])
    insert("stg_fmcg_receipts", c.receipts, ["receipt_id", "po_id", "receipt_date", "sku", "qty_received", "qty_rejected"])
    insert("stg_fmcg_inventory", c.inventory, ["snapshot_date", "sku", "location_id", "on_hand", "in_transit", "expiry_date"])
    insert("stg_fmcg_sources", c.sources, ["sku", "supplier_id", "approved", "compliance", "unit_cost", "freight_per_unit", "handling_per_unit",
                                           "capacity_per_week", "lead_time_promised_weeks", "moq_units", "units_per_case", "incumbent_share",
                                           "switching_cost", "provenance"])
    insert("stg_fmcg_economics", c.economics, ["key", "value", "provenance"])
    insert("stg_po_commitments", c.commitments, ["po_id", "stage", "allow_split_amendments", "minimum_remaining_quantity",
                                                 "prepaid_per_remaining_unit", "deposit_refundable_fraction", "cancellation_status"],
           {"operator_id": operator})
    insert("stg_po_options", c.options, ["po_id", "option_id", "action", "due_offset_periods", "fee_per_unit", "credit_per_unit",
                                         "max_quantity", "deadline", "allowed_stages", "contract_reference", "provenance"],
           {"operator_id": operator})
    insert("stg_atp_service_classes", c.service_classes, ["class_id", "provenance", "reference", "contractual_service_floor",
                                                          "shortage_penalty_per_unit", "late_penalty_per_unit_period", "refusal_cost_per_unit",
                                                          "lost_margin_per_unit", "strategic", "tier"], {"operator_id": operator})
    insert("stg_atp_customer_orders", c.atp_orders, ["order_id", "line_id", "customer_id", "service_class", "sku", "quantity",
                                                     "minimum_ship_quantity", "order_period", "requested_period", "ship_from", "unit_margin",
                                                     "partial_fulfillment_allowed", "backorder_allowed", "max_backorder_periods",
                                                     "substitution_allowed", "late_semantics", "priority_provenance"], {"operator_id": operator})
    conn.execute("INSERT INTO stg_atp_policy (operator_id, incumbent_policy, fairness, include_inbound, inbound_confidence, "
                 "promise_horizon, cross_location, provenance) VALUES (?, 'FIFO_PROMISE', 'NONE', TRUE, 1.0, 4, FALSE, 'OPERATOR_DECLARED')",
                 [operator])
    return {"company": COMPANY, "classification": CLASSIFICATION, "tables": c.counts(),
            "total_rows": sum(c.counts().values()), "scenarios": c.scenarios,
            "note": "A made-up import distributor with two years of connected history; replaces existing FMCG data. Never a real customer."}


def scenario_manifest(as_of: date | None = None, seed: int = 7) -> str:
    return json.dumps(build_demo_company(as_of=as_of, seed=seed).scenarios, indent=2, default=str)
