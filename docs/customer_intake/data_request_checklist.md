# Data Request Checklist

**For HarvestMind Pilot Onboarding**

Share this document with your operations contact at the partner organization.
Each CSV file below corresponds to one staging table in HarvestMind.
All 5 files are required for a complete diagnostic.

---

## How to Use This Checklist

1. Fill out the "Data Available?" column for each file
2. Note where the data lives (ERP, spreadsheet, WMS, QuickBooks export, etc.)
3. Export a sample of 30–90 days of data for each file
4. Send to your HarvestMind contact or upload directly to the portal

Column names do not need to match exactly — HarvestMind has a column mapping layer.
See `field_definitions.md` for the full list of accepted column name variants.

---

## File 1: Products (`stg_products.csv`)

**Purpose**: Master list of products you handle.

| Field | Required? | Notes |
|---|---|---|
| Product name | ✅ Required | |
| Product ID / SKU | Optional | Helps match across files |
| Category | Optional | e.g., Leafy Greens, Berries |
| Unit of measure | Optional | kg, lb, case, etc. |
| Default shelf life (days) | Optional | Used if expiry dates are missing |
| FSMA-204 / traceability required | Optional | Y/N flag |

**Data source at your org**: ___________________________

**Data available?**: ☐ Yes  ☐ Partial  ☐ No

**Export format**: ☐ Spreadsheet  ☐ CSV export from ________  ☐ Manual entry

---

## File 2: Supplier Deliveries (`stg_supplier_deliveries.csv`)

**Purpose**: History of inbound deliveries from each supplier — ordered, delivered, accepted, rejected quantities.

**Time range needed**: 30–90 days of recent history

| Field | Required? | Notes |
|---|---|---|
| Product name | ✅ Required | |
| Delivery date | ✅ Required | |
| Supplier name or ID | Recommended | |
| Ordered quantity | Recommended | |
| Delivered quantity | Recommended | |
| Accepted quantity | Recommended | |
| Rejected quantity | Optional | |
| Unit cost (per kg or unit) | Optional | Used for waste valuation |
| Lot ID | Optional | Required for traceability |
| Quality grade | Optional | A/B/C or similar |

**Data source at your org**: ___________________________

**Data available?**: ☐ Yes  ☐ Partial  ☐ No

**Export format**: ☐ Spreadsheet  ☐ CSV export from ________  ☐ Manual entry

---

## File 3: Inventory Lots (`stg_inventory_lots.csv`)

**Purpose**: Current on-hand inventory, lot by lot, with expiry dates.
This is the most important file for ATP and traceability diagnostics.

**Time range needed**: Current snapshot (today's inventory)

| Field | Required? | Notes |
|---|---|---|
| Product name | ✅ Required | |
| Quantity on hand | ✅ Required | In kg or your standard unit |
| Lot ID | Recommended | Required for FSMA-204 traceability |
| Product ID | Recommended | |
| Supplier ID | Recommended | |
| Arrival date | Recommended | |
| Expiration date | **Strongly recommended** | Without this, near-expiry analysis is unavailable |
| Warehouse location | Optional | Bin, zone, cool-room |
| Quality grade | Optional | |
| Committed quantity | Optional | Reserved for pending orders |

**Data source at your org**: ___________________________

**Data available?**: ☐ Yes  ☐ Partial  ☐ No

**Export format**: ☐ Spreadsheet  ☐ CSV export from ________  ☐ Manual entry

---

## File 4: Buyer Orders (`stg_buyer_orders.csv`)

**Purpose**: Order history from your buyers, including what was requested vs. fulfilled.

**Time range needed**: 30–90 days of recent history

| Field | Required? | Notes |
|---|---|---|
| Product name | ✅ Required | |
| Requested quantity | ✅ Required | |
| Buyer name or ID | Recommended | |
| Order date | Recommended | |
| Delivery date | Recommended | |
| Fulfilled quantity | Recommended | Actual quantity delivered |
| Substituted quantity | Optional | Different product or grade delivered |
| Sales price (per kg or unit) | Recommended | Required for shortage loss valuation |
| Required quality grade | Optional | |

**Data source at your org**: ___________________________

**Data available?**: ☐ Yes  ☐ Partial  ☐ No

**Export format**: ☐ Spreadsheet  ☐ CSV export from ________  ☐ Manual entry

---

## File 5: Waste Adjustments (`stg_waste_adjustments.csv`)

**Purpose**: Log of spoilage, waste, and inventory write-downs.

**Time range needed**: Same 30–90 day window as supplier deliveries

| Field | Required? | Notes |
|---|---|---|
| Product name | ✅ Required | |
| Quantity lost | ✅ Required | In kg or your standard unit |
| Date | Recommended | |
| Reason / reason code | Recommended | e.g., Spoilage, Overripe, Damage |
| Estimated value lost | Recommended | In dollars. Falls back to unit cost × qty if missing. |
| Lot ID | Optional | Links waste event to specific lot |
| Adjustment ID | Optional | Your internal reference |

**Data source at your org**: ___________________________

**Data available?**: ☐ Yes  ☐ Partial  ☐ No

**Export format**: ☐ Spreadsheet  ☐ CSV export from ________  ☐ Manual entry

---

## Summary

| File | Required? | Available at Your Org |
|---|---|---|
| Products | ✅ | ☐ Yes  ☐ Partial  ☐ No |
| Supplier Deliveries | ✅ | ☐ Yes  ☐ Partial  ☐ No |
| Inventory Lots | ✅ | ☐ Yes  ☐ Partial  ☐ No |
| Buyer Orders | ✅ | ☐ Yes  ☐ Partial  ☐ No |
| Waste Adjustments | ✅ | ☐ Yes  ☐ Partial  ☐ No |

---

## If Data Is Partially Available

HarvestMind will still run diagnostics with partial data, but some metrics
will be limited or unavailable:

| Missing file | Impact |
|---|---|
| No inventory lots | ATP, near-expiry, and traceability analysis unavailable |
| No supplier deliveries | Fill rate and supplier risk analysis unavailable; waste valuation may use $0 |
| No buyer orders | Shortage loss unavailable; buyer fulfillment analysis unavailable |
| No waste adjustments | Waste loss shows $0; inventory risk still available |
| No products | Traceability completeness may be limited |

For a first diagnostic, prioritize: **inventory lots** + **buyer orders** + **waste adjustments**.
These three files generate the highest-value findings.

---

## Data Privacy Notes

- Do not include personally identifiable information (customer names, addresses, contacts)
  in the CSV files — use buyer IDs or organization names only
- Sample data covering 30–60 days is sufficient for a diagnostic; you do not need to
  share your full history
- Data uploaded to HarvestMind is stored locally in a single-file database; nothing is
  sent to third-party services
