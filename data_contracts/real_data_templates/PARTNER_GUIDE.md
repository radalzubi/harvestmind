# HarvestMind Data Guide

This is what we need from your hub to run a free pilot analysis.

## What we need (3 files)

| File | What it is | Required? |
|---|---|---|
| `orders.csv` | Your order history — who ordered what, how much, when | **Required** |
| `deliveries.csv` | What suppliers actually delivered, by date and quantity | **Required** |
| `waste_events.csv` | Anything you logged as waste, spoilage, or markdown | Optional but valuable |

You can email the CSVs (or share via Google Drive / Dropbox). We'll never share them with anyone outside the analysis.

The four template files in this folder show exactly what columns we expect. If your system uses different headers (Local Line, QuickBooks, etc.), our column mapper handles it automatically — see "Common issues" below.

---

## How to export from Local Line

1. Sign in to Local Line → **Reports** → **Order Reports**
2. Date range: pick **the last 12 months** (6 months minimum)
3. Click **Export to CSV**
4. Save the file as `orders.csv`

For deliveries: **Inventory** → **Receiving** → **Export Receiving Log** → save as `deliveries.csv`.

## How to export from QuickBooks

1. Reports → **Sales by Customer Detail** → date range = last 12 months → **Export to CSV** → save as `orders.csv`
2. Reports → **Vendor Reports → Bills by Vendor Detail** → same date range → export → save as `deliveries.csv`
3. QuickBooks doesn't track waste directly. If you log it in a separate spreadsheet, export that as `waste_events.csv`.

## How to export from a spreadsheet

If you keep records in Excel or Google Sheets, just download each tab as a CSV with these names: `orders.csv`, `deliveries.csv`, `waste_events.csv`. Headers don't need to match exactly — the loader handles common variations like "Order Number", "PO #", "Customer", "Farm", "Vendor", "Quantity (lbs)", etc.

---

## Minimum requirements

| Coverage | Description |
|---|---|
| **6 months** | Minimum to run a backtest. Results will be directional only. |
| **12 months** | Recommended — captures one full season. |
| **18+ months** | Lets us model year-over-year demand patterns. |

Per-file minimums:
- Orders: at least 200 rows
- Deliveries: at least 200 rows
- Waste events: nice to have, but the analysis runs without it

---

## Common issues (fix these before sending)

- **Dates** — please use `YYYY-MM-DD` (e.g. `2025-06-02`). `06/02/2025` works but is ambiguous.
- **Quantities in kg** — if your records are in pounds, that's fine; just leave the column header containing "lbs" or "pounds" so we know to convert (×0.453592).
- **Blank cells** — leave truly empty. Don't write "N/A", "none", or "0" unless the value really is zero.
- **Customer/supplier names** — keep them consistent. "Sysco" and "Sysco Inc." look like two different buyers to the loader.
- **No private data** — please don't include anything you wouldn't put in a contract: SSNs, full credit card numbers, etc. The analysis only needs hub IDs, product IDs, dates, and quantities.

---

## What happens next

1. **You** export the CSVs from your system and email them.
2. **We** run validation, ingestion, and a 12-origin backtest.
3. **We** send back a 2-page pilot summary PDF with: projected annual benefit, ROI multiple, payback period, and a backtest detail page.
4. **Turnaround**: 48 hours from receipt of clean CSVs.

Questions? Email Roy Ballard, Purdue Extension (rballard@purdue.edu).

— *HarvestMind · Powered by Purdue University*
