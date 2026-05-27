# Demo Verification Checklist

Step-by-step guide for verifying HarvestMind works end-to-end on a local machine
before a customer demo. Run through this checklist top-to-bottom; each section
has an expected result. Do not present the product as demo-ready until all items
are checked.

---

## Prerequisites

- Python 3.11+ installed (`python3 --version`)
- Node.js 18+ installed (`node --version`)
- Repository cloned at a known path (e.g. `~/Desktop/harvestmind`)
- No other process using ports 3000 or 8000

---

## 1. Backend Setup

```bash
cd harvestmind
pip install -e ".[dev]"
```

Apply the diagnostic staging migration if the DB does not exist yet:

```bash
python3 -c "
import duckdb, pathlib
conn = duckdb.connect('harvestmind.duckdb')
sql = pathlib.Path('db/migrations/010_diagnostic_staging.sql').read_text()
for stmt in sql.split(';'):
    s = stmt.strip()
    if s:
        try: conn.execute(s)
        except: pass
conn.close()
print('Migrations applied.')
"
```

Start the API server:

```bash
uvicorn api.main:app --reload
```

**Expected**: Terminal shows `Application startup complete.` and `Uvicorn running on http://127.0.0.1:8000`.

**Verify API is up**:

```bash
curl -s http://localhost:8000/intake/status | python3 -m json.tool | head -20
```

**Expected**: JSON with `tables` object containing 5 staging tables, all `row_count: 0`.

---

## 2. Frontend Setup

In a separate terminal:

```bash
cd harvestmind/web
npm install
npm run dev
```

**Expected**: `✓ Ready - started server on 0.0.0.0:3000`

Open `http://localhost:3000` in a browser.

**Expected**: Overview page loads with "No operator data loaded yet" empty state and an
"Upload your data or load sample dataset" button.

---

## 3. Load Sample Data (One-Click Path)

1. Navigate to `http://localhost:3000/upload`
2. Click **Load sample dataset** (green button at top of page)

**Expected**:
- Button shows spinner briefly, then "6X rows loaded across 5 tables" confirmation
- The 5 status indicators below turn green with row counts
- Toast notification appears in bottom corner

**Verify via API**:

```bash
curl -s http://localhost:8000/intake/status | python3 -m json.tool
```

**Expected**: All 5 tables show `"loaded": true` with `row_count > 0`.

---

## 4. Verify Each Dashboard Page

### 4a. Overview (`/`)

- [ ] 4 KPI cards visible: Waste Loss, Shortage Loss, Risky Suppliers, Traceability
- [ ] Waste Loss and Shortage Loss show dollar amounts > $0
- [ ] "⚠ Addressable loss detected" banner visible (if losses > 0)
- [ ] "Top Loss Drivers" table has at least 2–3 rows
- [ ] "Savings Opportunity" card shows estimated annual savings
- [ ] "Data Loaded" table shows 5 rows, all "✓ Loaded"

### 4b. Inventory Risk (`/inventory`)

- [ ] 4 KPI cards: Total On Hand, Near Expiry, Expired Stock, Waste Loss
- [ ] "Inventory by Product" table has at least 5 product rows
- [ ] Near Expiry column highlighted in amber for affected products
- [ ] Expired column highlighted in red for expired lots
- [ ] "Waste Loss by Product" and "Waste Loss by Reason" tables visible

### 4c. Available-to-Promise (`/atp`)

- [ ] ATP by Product table shows at least 5 products
- [ ] Risk badges (High/Medium/Low) displayed correctly
- [ ] Commitment Recommendations table visible for risky products

### 4d. Traceability (`/traceability`)

- [ ] Completeness % displayed (expect < 100% — sample data has some missing lot_ids)
- [ ] Status banner shows "Partial Compliance" or similar
- [ ] Missing Fields table shows `lot_id` with affected count > 0
- [ ] Incomplete Lots table shows specific lots

### 4e. Partners (`/partners`)

- [ ] Suppliers tab: 3 suppliers listed, Blue Ridge Produce shows "High" risk
- [ ] Buyer tab: 3 buyers listed, Northside Grocers shows "High" risk
- [ ] Fill rate colored red for low-performing supplier
- [ ] Tab switching works without page reload

### 4f. Data Quality (`/data-quality`)

- [ ] Quality Score displayed as a percentage
- [ ] All 5 tables show "Ready" status
- [ ] Re-validate button works (spinner then refreshes)

### 4g. Reports (`/reports`)

- [ ] Preview KPI row visible (waste + shortage numbers match Overview)
- [ ] "View Full Report" button opens report in new tab
- [ ] HTML report loads at `http://localhost:8000/reports/diagnostic`

---

## 5. HTML Report Verification

Open `http://localhost:8000/reports/diagnostic` in a new browser tab.

- [ ] Report header shows partner name and generation date
- [ ] All 13 sections present (Executive Summary through Assumptions & Limitations)
- [ ] Supplier table shows Blue Ridge Produce as High risk
- [ ] Buyer table shows Northside Grocers as High risk
- [ ] Savings opportunity box shows green dollar figure
- [ ] Section 13 (Assumptions & Limitations) is readable and complete
- [ ] **Print test**: Cmd+P → preview should show light background, readable text, no clipped content

---

## 6. Empty State Verification

In a separate test: clear one table and verify the correct empty state appears.

```bash
curl -s -X POST http://localhost:8000/intake/clear/stg_inventory_lots
```

Reload `http://localhost:3000/inventory`:

- [ ] "No inventory lot data loaded" EmptyState card appears
- [ ] "Upload stg_inventory_lots.csv" button links to `/upload`
- [ ] No JavaScript errors in browser console

Reload the sample data to restore:
```bash
curl -s -X POST http://localhost:8000/intake/load-sample-data
```

---

## 7. Error State Verification

Stop the backend server (Ctrl+C in its terminal), then reload any page.

- [ ] "Cannot reach the HarvestMind API" message appears
- [ ] Instructions show `uvicorn api.main:app --reload`
- [ ] No raw error stack trace or JSON visible to user

Restart the backend and reload.

---

## 8. Backend Tests

```bash
cd harvestmind
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

**Expected**: All tests pass. Zero failures. Zero errors.

Note the final line — it should read something like `XXX passed in X.Xs`.

---

## 9. Frontend Type Check + Build

```bash
cd harvestmind/web
npx tsc --noEmit && echo "TypeScript: OK"
npm run build 2>&1 | tail -20
```

**Expected**:
- `TypeScript: OK` printed (exit 0)
- `next build` completes without errors
- All routes compiled successfully

---

## 10. Demo Readiness Checklist

Check each item before a customer call:

| Gate | Check |
|---|---|
| Backend running on :8000 | `curl localhost:8000/intake/status` returns JSON |
| Frontend running on :3000 | Browser shows Overview page |
| Sample data loaded | All 5 tables show row counts in Upload page |
| Waste + shortage losses visible | Overview KPIs show > $0 |
| HTML report accessible | `/reports/diagnostic` opens in browser |
| All backend tests passing | `pytest tests/` all green |
| TypeScript clean | `tsc --noEmit` exits 0 |

---

## Known Demo Talking Points

- **Sample data is intentionally imperfect** — Blue Ridge Produce has ~62% fill rate,
  LOT-003/LOT-004 are near-expiry, 2 lots have missing lot_ids. This is by design to
  demonstrate every diagnostic panel.
- **Savings estimate context**: $X/year is based on 30% reduction of identified losses.
  Use this as a conversation opener, not a hard commitment.
- **"What do we need from you?"**: Refer to `docs/customer_intake/data_request_checklist.md`.
- **Traceability gap**: Near-expiry and lot_id gaps in the sample data demonstrate
  real FSMA-204 risk that most operators don't know they have.
