# HarvestMind 30-Day Diagnostic Pilot

A structured, time-bounded, paid engagement designed as the first commercial
step with a regional produce operator. The goal is to deliver enough value
in 30 days that the operator wants to continue into a live SaaS engagement.

---

## Who this is for

Regional produce operators — food hubs, aggregators, and small distributors —
with:

- $1M–$25M in annual revenue
- Aggregation from 5–60 farms
- Sales to institutional buyers (schools, hospitals, universities, foodservice,
  grocery)
- Existing operational data in QuickBooks plus spreadsheets, or in a
  light-weight tool like Local Line or AirTable
- A specific operational pain — recurring waste, recurring missed orders, a
  traceability conversation with a buyer, or a margin gap they can't explain

This is **not** for:

- Single-farm direct-to-consumer operations
- Operators already running on NetSuite, Famous, or a comparable ERP
- Operators who cannot export historical data to CSV
- Operators looking for free pilots

---

## What we deliver

By end of week 4 the operator receives:

1. **A 13-section HarvestMind diagnostic report** — printable, board-readable,
   with assumptions and limitations clearly stated
2. **An executive summary** — 1 page, 3 prioritized findings, an annualized
   savings opportunity figure
3. **A 60-minute readout call** with the operator's GM, Ops Lead, and (if
   they want) their CFO
4. **A redacted "before pilot / after pilot" data quality scorecard** — what
   gaps we found in the data and how they affect the diagnostic
5. **A 90-minute working session** to prioritize the three highest-impact
   actions and define what live monthly diagnostics would track

The report covers, at minimum:

- Waste loss in dollars, broken down by product and reason
- Shortage loss in dollars, broken down by buyer and product
- Supplier reliability scorecard with risk flags
- Buyer fulfillment risk scorecard
- Inventory near-expiry and expired exposure
- Available-to-promise recommendations for the top 10–20 products
- FSMA-204 traceability completeness percentage with specific gap list
- Annualized savings estimate with explicit reduction-percentage assumption

---

## What data the operator provides

CSV exports covering 6–12 months of operations. Specifically, the 5 files
documented in `docs/customer_intake/data_request_checklist.md`:

| File | Purpose |
|---|---|
| `stg_products.csv` | Product catalog with shelf life flags |
| `stg_supplier_deliveries.csv` | Inbound deliveries, ordered vs. delivered |
| `stg_inventory_lots.csv` | Current on-hand lots with expiry dates |
| `stg_buyer_orders.csv` | Outbound orders, requested vs. fulfilled |
| `stg_waste_adjustments.csv` | Waste/spoilage log with dollar values |

Column names do not need to match exactly. HarvestMind has a column mapping
layer that handles common operator data shapes.

**Time commitment from the operator**: 2–4 hours total over the 30 days
for data export, validation calls, and the readout. Not a full-time
commitment from any operator staff member.

---

## Timeline

| Week | Activity | Operator effort |
|---|---|---|
| **Week 1** | Kickoff call. Data export by the operator. Data validation by HarvestMind. Data-quality issues surfaced. | 1.5–2 hours |
| **Week 2** | Diagnostic engine run. Anomaly investigation. Follow-up questions on data interpretation. | 30–60 minutes |
| **Week 3** | Report drafting. Specific finding write-ups. Sanity checks against operator's intuition. | 30 minutes |
| **Week 4** | Final report delivered. 60-minute readout. 90-minute action-planning session. | 2.5 hours |

---

## Pricing

| Pilot type | Price | Scope |
|---|---|---|
| **Single product line** | $3,000 | One commodity category (e.g., leafy greens or vine crops). Single-warehouse operator. |
| **Multi-category** | $5,000 | 3–6 product categories. Single-warehouse operator. |
| **Multi-location** | $7,500 | Full product mix across 2–4 warehouse locations or DCs. |

50% paid at kickoff. 50% paid on delivery of the report.

Net-30 invoicing acceptable for operators with established procurement.

No annual commitment. No auto-renewal. No software license to buy.

---

## Success criteria

The pilot is mutually considered successful when:

- All 5 data files were loaded with > 60% data quality score
- The diagnostic identified at least one finding the operator confirms is
  directionally accurate and dollar-material
- The operator receives the report and rates it "useful and defensible" in
  the readout call
- At least one of the three prioritized actions is something the operator
  agrees to attempt internally

Detailed criteria are in `docs/customer_intake/pilot_success_criteria.md`,
which is signed by both parties before the pilot begins.

---

## Conversion path

After a successful diagnostic pilot, the operator may convert to a live
HarvestMind engagement:

| Tier | Price | What changes |
|---|---|---|
| **Monthly diagnostic refresh** | $1,500 / month | New CSV exports every month, refreshed report, monthly 30-minute readout |
| **Weekly ATP refresh** | $3,000 / month | Weekly data refresh, ATP recommendations before the operator's commitment window opens, monthly 60-minute review |

The diagnostic pilot fee is **not** credited toward live SaaS. The pilot
funds the diagnostic work; the SaaS fee funds the ongoing operations.

---

## Out of scope for the pilot

The following are explicitly not included and will not be promised:

- ERP integration (QuickBooks, NetSuite, Famous, etc.)
- WMS integration or barcode scanning
- Mobile application
- Multi-tenant cloud hosting
- Real-time inventory dashboards
- Automated reorder triggers or buyer notifications
- A FSMA-204 compliance certification — HarvestMind delivers a readiness
  assessment, not a regulatory sign-off
- An accounting reconciliation — diagnostic values are estimates, not GL entries
- Custom feature development requested during the pilot

If the operator requests any of the above, the answer is "noted for the
roadmap, not part of this pilot."

---

## Confidentiality and data handling

- A mutual NDA is signed before any data is shared
- All operator data is stored locally in a dedicated DuckDB file for that
  operator — no shared multi-tenant database
- Operator data is not used for any other engagement, demo, or marketing
  without written permission
- At end of pilot, the operator chooses one of:
  - Continue: data retained for live engagement
  - Pause: data archived for 90 days then deleted
  - Stop: data deleted within 7 days of report delivery
- A signed certificate of data deletion is provided on request

---

## Why this structure (internal rationale, not for the customer)

- **Paid, not free**: Free pilots produce no commitment, no urgency, and no
  operator review. A $3K diagnostic is buyable from a GM's discretionary
  budget and signals real intent.
- **Time-bounded**: 30 days forces the operator and HarvestMind both to make
  decisions instead of letting scope creep.
- **Diagnostic, not transformation**: We are not promising operational
  change. We are promising a credible report. The operator owns the change.
- **No auto-conversion to SaaS**: We earn the SaaS engagement by delivering
  a useful diagnostic, not by burying it in a contract.
- **Out-of-scope list**: Protects against feature requests during week 3 that
  would blow the timeline.
