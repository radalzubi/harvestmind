# Data request: commercial / FMCG distributor diagnostic

What we need from you, exactly, to return three things within one week: your current ordering policy as inferred from your own purchase history, a backtested number for what a safe optimizer would have done on that history, and the current risk on your supply lanes. Everything is a plain CSV export from your ERP. Twelve months is ideal; twenty-six weeks is the minimum.

## At a glance

- 5 required files, 3 optional files, one 10-minute conversation.
- Customer names, contact details and addresses are never needed.
- Run our anonymiser on your machine before sending, so your real codes never leave your building.

## Required files

### 1. `skus.csv` — product master
| column | type | need | meaning |
|---|---|---|---|
| `sku` | text | required | your item code |
| `unit_cost` | number | required | landed cost per each |
| `supplier_id` | text | required | who you buy it from |
| `unit_price` or `contribution_margin` | number | required | sell price per each, or margin per each; without one the plan cannot price a lost sale |
| `units_per_case` | integer | required | eaches per case |
| `moq_units` | number | preferred | minimum order in eaches |
| `cases_per_layer`, `layers_per_pallet` | integer | preferred | pallet build |
| `order_multiple` | text | preferred | `each`, `case`, `layer` or `pallet` |
| `category`, `abc_class`, `shelf_life_days` | text / int | preferred | classification and shelf life |
| `service_class` | text | preferred | e.g. `A_CRITICAL`, `B`, `C` |
| `supplier_capacity_per_week` | number | preferred | if a supplier caps your weekly volume |
| `sku_name`, `manufacturer` | text | optional | descriptive only |

### 2. `orders.csv` — customer order lines (sales)
| column | type | need | meaning |
|---|---|---|---|
| `order_date` | date | required | when the customer ordered |
| `sku` | text | required | |
| `qty_ordered` | number | required | eaches requested |
| `qty_shipped` | number | preferred | eaches actually shipped; a gap is a recorded stock-out |
| `order_id`, `customer_id` | text | preferred | for de-duplication; hashed, never stored raw |
| `requested_delivery_date`, `channel` | date / text | optional | |

### 3. `purchase_orders.csv` — what you ordered from suppliers
| column | type | need | meaning |
|---|---|---|---|
| `po_id` | text | required | |
| `po_date` | date | required | |
| `sku` | text | required | |
| `qty_ordered` | number | required | eaches |
| `supplier_id` | text | required | |
| `unit_cost` | number | preferred | |
| `expected_delivery_date` | date | preferred | promised date, for on-time measurement |

### 4. `receipts.csv` — what arrived against those POs
| column | type | need | meaning |
|---|---|---|---|
| `po_id` | text | required | links to the PO |
| `receipt_date` | date | required | |
| `qty_received` | number | required | eaches; partial deliveries as separate rows |
| `sku` | text | preferred | |
| `qty_rejected` | number | preferred | |
| `receipt_id` | text | optional | |

### 5. `inventory.csv` — stock snapshots
| column | type | need | meaning |
|---|---|---|---|
| `snapshot_date` | date | required | weekly or month-end |
| `sku` | text | required | |
| `on_hand` | number | required | eaches |
| `in_transit` | number | preferred | eaches on order not yet received |
| `location_id` | text | preferred | if more than one warehouse |

## Optional files (each one protects a conclusion)

### 6. `suppliers.csv`
| column | meaning |
|---|---|
| `supplier_id` | |
| `route` | the lane it ships on: e.g. `aqaba`, `red_sea`, `hormuz`, `road_turkey`, `air`; suppliers on one lane share risk |
| `origin_iso3` | country of origin (`TUR`, `EGY`, `CHN`, `DEU`, …); drives the lead-time prior until your receipts measure it |
| `lead_time_promised_weeks` | quoted lead time |
| `capacity_per_week` | units per week if capped |
| `manufacturer` | shared upstream source |

### 7. `economics.csv` — your carrying-cost inputs (key, value)
`cost_of_capital_annual` (e.g. `0.12`), `storage_handling_annual` (warehouse rent and handling as a share of stock value, or per pallet), `insurance_annual`, `obsolescence_annual`, `fixed_po_cost`, `currency`. Without these a public benchmark is used and every plan reports the sensitivity to it.

### 8. `promotions.csv` — planned promotions
`sku`, `week_start`, `uplift` (multiplier, e.g. `1.6`). Promotions become planned inputs instead of surprises in the history.

## The conversation (10 minutes)

Who decides orders, on what rule, how often, and what they override. That is your real policy; the PO log only approximates it.

## How to prepare and send

1. Export each table as CSV from your ERP (SAP Business One, Odoo, Dynamics and NetSuite all export these views directly). Extra columns are fine; they are ignored with a note.
2. Anonymise on your own machine: `python scripts/anonymize_export.py --secret "<a passphrase you keep>" *.csv`. Identifiers become keyed hashes, names and contacts are dropped, quantities and dates are untouched. Keep the passphrase; only you can map the hashes back.
3. Send the `.anon.csv` files. You get back a readiness score immediately (`GET /fmcg/readiness` tells you what is missing and what it weakens), and the three results within a week.

## What you get back

- Your inferred current policy (cover weeks, review cadence, how consistently it is followed).
- The backtested number: what a safe optimizer would have done on your own last twelve months versus what you did, with a conservative lower bound, including "no material improvement" if that is the honest answer.
- Your supply-lane risk today from public shipping data, and which SKUs it touches.
