# Field Definitions

**HarvestMind CSV Column Specifications**

This document defines every accepted column name for each staging table.
Column names are case-insensitive and may include spaces — HarvestMind maps
common aliases automatically.

---

## stg_products

Product catalog. One row per product you handle.

| Schema Column | Accepted CSV Headers | Type | Notes |
|---|---|---|---|
| `product_id` | `Product ID` | text | Optional unique identifier |
| `product_name` | `Product Name` | text | **Required** |
| `category` | `Category` | text | e.g., Leafy Greens, Root Vegetables |
| `unit` | `Unit` | text | kg, lb, case, bunch, etc. |
| `default_shelf_life_days` | `Shelf Life (days)`, `Default Shelf Life Days` | integer | Days until expiry from arrival |
| `traceability_required` | `Traceability Required`, `FTL Item` | boolean | True/False or Y/N |

**Minimum viable**: `product_name` only.

---

## stg_supplier_deliveries

Inbound delivery history. One row per delivery line.

| Schema Column | Accepted CSV Headers | Type | Notes |
|---|---|---|---|
| `delivery_id` | `Delivery ID` | text | Optional internal reference |
| `supplier_id` | `Supplier ID` | text | Optional |
| `supplier_name` | `Supplier Name` | text | Recommended for readability |
| `product_id` | `Product ID` | text | Optional |
| `product_name` | `Product Name` | text | **Required** |
| `delivery_date` | `Delivery Date` | date | **Required** (YYYY-MM-DD or MM/DD/YYYY) |
| `ordered_quantity` | `Ordered Quantity` | decimal | Quantity you ordered |
| `delivered_quantity` | `Delivered Quantity` | decimal | Quantity the supplier sent |
| `accepted_quantity` | `Accepted Quantity` | decimal | Quantity you accepted into stock |
| `rejected_quantity` | `Rejected Quantity` | decimal | Quantity rejected at receiving |
| `unit_cost` | `Unit Cost` | decimal | Cost per unit in dollars |
| `quality_grade` | `Quality Grade` | text | A, B, C, Premium, Standard, etc. |
| `lot_id` | `Lot ID` | text | Links delivery to inventory lot |

**Fill rate** = `accepted_quantity / ordered_quantity`.
If `ordered_quantity` is missing, fill rate is calculated as `delivered_quantity / ordered_quantity`.
If `accepted_quantity` is missing, `delivered_quantity` is used as a proxy.

**Minimum viable**: `product_name`, `delivery_date`.

---

## stg_inventory_lots

Current on-hand inventory, one row per lot. This is the most important file.

| Schema Column | Accepted CSV Headers | Type | Notes |
|---|---|---|---|
| `lot_id` | `Lot ID` | text | Critical for FSMA-204. Missing = traceability failure |
| `product_id` | `Product ID` | text | Optional |
| `product_name` | `Product Name` | text | **Required** |
| `supplier_id` | `Supplier ID` | text | Optional |
| `quantity_on_hand` | `Quantity On Hand`, `Qty On Hand` | decimal | **Required** |
| `unit` | `Unit` | text | kg, lb, case, etc. |
| `arrival_date` | `Arrival Date` | date | When the lot arrived |
| `expiration_date` | `Expiration Date`, `Expiry Date` | date | **Strongly recommended**. Without this, near-expiry analysis is unavailable |
| `warehouse_location` | `Warehouse Location`, `Location` | text | Bin, zone, cool-room |
| `quality_grade` | `Quality Grade` | text | |
| `committed_quantity` | `Committed Quantity`, `Qty Committed` | decimal | Quantity reserved for pending orders |

**Near-expiry**: lots with `expiration_date` within 3 days of analysis date.

**ATP** = `quantity_on_hand − committed_quantity − expired_quantity − near_expiry_quantity`

**Minimum viable**: `product_name`, `quantity_on_hand`.

---

## stg_buyer_orders

Outbound order history. One row per order line.

| Schema Column | Accepted CSV Headers | Type | Notes |
|---|---|---|---|
| `order_id` | `Order ID` | text | Optional |
| `buyer_id` | `Buyer ID` | text | Optional |
| `buyer_name` | `Buyer Name` | text | Recommended |
| `product_id` | `Product ID` | text | Optional |
| `product_name` | `Product Name` | text | **Required** |
| `order_date` | `Order Date` | date | When the order was placed |
| `delivery_date` | `Delivery Date` | date | When the order was delivered |
| `requested_quantity` | `Requested Quantity`, `Qty Requested` | decimal | **Required** |
| `fulfilled_quantity` | `Fulfilled Quantity`, `Qty Fulfilled`, `Qty Delivered` | decimal | Actual quantity delivered |
| `substituted_quantity` | `Substituted Quantity` | decimal | Different product/grade sent |
| `sales_price` | `Sales Price`, `Price/kg` | decimal | Per-unit sales price. Required for shortage loss valuation |
| `required_quality_grade` | `Required Quality Grade`, `Grade` | text | Grade the buyer specified |

**Fulfillment rate** = `fulfilled_quantity / requested_quantity`.
Substituted quantity is counted as fulfilled.
**Missed** = `requested_quantity − fulfilled_quantity − substituted_quantity`.

**Minimum viable**: `product_name`, `requested_quantity`.

---

## stg_waste_adjustments

Waste and spoilage log. One row per waste event or inventory write-down.

| Schema Column | Accepted CSV Headers | Type | Notes |
|---|---|---|---|
| `adjustment_id` | `Adjustment ID` | text | Optional internal reference |
| `date` | `Date`, `Event Date` | date | When the waste occurred |
| `product_id` | `Product ID` | text | Optional |
| `product_name` | `Product Name` | text | **Required** |
| `lot_id` | `Lot ID` | text | Links waste to a specific lot |
| `quantity_lost` | `Quantity Lost`, `Qty Lost` | decimal | **Required** |
| `reason` | `Reason`, `Reason Code` | text | e.g., Spoilage, Overripe, Damage, Temperature abuse |
| `estimated_value_lost` | `Estimated Value Lost`, `Value Lost ($)` | decimal | In dollars. If missing, HarvestMind uses unit cost × quantity |

**Waste loss** = sum of `estimated_value_lost`.
When `estimated_value_lost` is null, HarvestMind falls back to:
average `unit_cost` from `stg_supplier_deliveries` × `quantity_lost`.
If no cost data exists, the row contributes $0 to waste loss.

**Minimum viable**: `product_name`, `quantity_lost`.

---

## Date Formats

HarvestMind accepts any of the following date formats — all are auto-detected:

- `2026-05-27` (ISO 8601 — preferred)
- `05/27/2026` (US format)
- `27/05/2026` (European format)
- `May 27, 2026`
- `27-May-2026`

---

## Units of Measure

All quantity fields are stored as entered — HarvestMind does not convert between units.
Ensure all files for a given operator use the same unit for the same product.
Mixing kg and lb for the same product will produce incorrect ATP and waste calculations.

---

## Handling Missing Values

| Field type | Missing value behavior |
|---|---|
| Required columns | Upload rejected if 0% coverage. Warning if partial. |
| Recommended columns | Warning issued; calculations may be limited |
| Optional columns | Silently skipped |
| Dollar amounts | Falls back to unit cost × qty; then $0 |
| Dates | Parsed with `pd.to_datetime(errors='coerce')`; bad dates become null |
| Quantities | Null treated as 0 in aggregations |
