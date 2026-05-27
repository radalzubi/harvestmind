# HarvestMind 30-Day Diagnostic Pilot

A structured, time-bounded, paid engagement designed as the first commercial
step with a perishable produce operator. The pilot is **deliberately
designed as a business-model discovery mechanism** — not just an
analysis deliverable.

By the end of the engagement we expect the operator to answer one of three
questions:

1. *"This would be more useful as a recurring service."* → Path B
2. *"This would be more useful as a live tool we use weekly."* → Path A
3. *"Our ERP does inventory, but not this decision logic — can it plug in?"* → Path C

The pilot is priced to be buyable from a GM's discretionary budget and
structured to produce a clear "what next?" answer regardless of which
direction the operator leans.

---

## Who this is for

**Perishable operators across five segments**, broadened after the
public-source scan (Reddit + USDA + ag-feed sources) showed
operational pain extending well beyond food hubs:

1. **Produce aggregators / food hubs** — original ICP, $1M–$25M
2. **Seafood / shellfish operators** — strong Reddit signal,
   $500K–$10M
3. **Small food / beverage wholesalers and distributors** —
   actively searching for inventory + lot tracking, $2M–$30M
4. **Fresh-cut processors** — highest perishability, $3M–$50M
5. **Local food distributors serving institutions** —
   traceability pressure from school/hospital buyers, $1M–$10M

Common attributes across all five segments:

- $500K–$50M in annual revenue (open range — first pilots are about
  learning which segment converts, not about defending an exact ICP)
- Multiple suppliers, multiple buyers, or multiple SKUs
- Sales to institutional buyers (schools, hospitals, universities,
  foodservice, grocery), or to wholesale customers requiring lot
  traceability
- Existing operational data in QuickBooks plus spreadsheets, in a
  lightweight tool (Local Line, BlueTrace, etc.), or in a full ERP
  — **all tech stacks welcome**
- A specific operational pain — recurring waste, recurring missed
  orders, a traceability conversation with a buyer, double/triple
  data entry across systems, or a margin gap they can't explain

This is **not** for:

- Single-farm direct-to-consumer operations
- Operators who cannot export historical data to CSV at all
- Operators looking for free pilots
- Operators whose tech stack is so optimized that any addressable loss
  has already been captured

The earlier version of this offer screened out ERP-equipped operators.
**We've removed that screen.** If an operator has NetSuite or Famous and
still wants the diagnostic, that's some of the most valuable signal we
can collect at this stage — it directly tests whether Path C (ERP add-on)
is real.

---

## What we deliver

By end of week 4 the operator receives:

1. **A 13-section HarvestMind diagnostic report** — printable,
   board-readable, with assumptions and limitations clearly stated
2. **An executive summary** — 1 page, 3 prioritized findings, an
   annualized addressable-loss figure with explicit reduction-range
   assumption
3. **A 60-minute readout call** with the operator's GM, Ops Lead, and (if
   they want) their CFO
4. **A redacted "before pilot / after pilot" data quality scorecard** —
   what gaps we found in the data and how they affect the diagnostic
5. **A 90-minute working session** to prioritize the three highest-impact
   actions and discuss what an ongoing engagement could look like
6. **The discovery question, asked explicitly**: "Of these three options
   — a recurring quarterly diagnostic, a live tool connected to your
   system, or a one-time analysis you act on internally — which would
   be most valuable to you?"

The report covers, at minimum:

- Waste loss in dollars, broken down by product and reason
- Shortage loss in dollars, broken down by buyer and product
- Supplier reliability scorecard with risk flags (including an "Unknown"
  tier for suppliers without enough ordered-quantity data)
- Buyer fulfillment risk scorecard
- Inventory near-expiry and expired exposure
- Available-to-promise recommendations for the top 10–20 products,
  with near-expiry stock correctly excluded from committable quantity
- FSMA-204 traceability completeness percentage with specific gap list
- Annualized addressable-loss estimate, scaled from the data window by
  365/period_days, with explicit reduction-range assumption (15%–30%)

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

Column names do not need to match exactly. HarvestMind has a column
mapping layer that handles common operator data shapes.

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
| **Week 4** | Final report delivered. 60-minute readout. 90-minute action-planning + business-model discovery session. | 2.5 hours |

---

## Pricing

| Pilot type | Price | Scope |
|---|---|---|
| **Single product line** | $3,000 | One commodity category (e.g., leafy greens or vine crops). Single-warehouse operator. |
| **Multi-category** | $5,000 | 3–6 product categories. Single-warehouse operator. |
| **Multi-location** | $7,500 | Full product mix across 2–4 warehouse locations or DCs. |
| **Larger operator** | $10,000–$15,000 | $15M+ revenue, full product mix, multiple locations, deeper supplier/buyer analysis. |

50% paid at kickoff. 50% paid on delivery of the report.

Net-30 invoicing acceptable for operators with established procurement.

No annual commitment. No auto-renewal. No software license to buy.

---

## Success criteria

The pilot is mutually considered successful when:

- All 5 data files were loaded with > 60% data quality score
- The diagnostic identified at least one finding the operator confirms
  is directionally accurate and dollar-material
- The operator receives the report and rates it "useful and defensible"
  in the readout call
- At least one of the three prioritized actions is something the
  operator agrees to attempt internally
- **The operator gives a clear answer to the business-model question**:
  "Of these three options — a recurring quarterly diagnostic, a live
  tool connected to your system, or a one-time analysis — which would
  be most valuable?" Even "I don't know yet" is acceptable — silence
  is not.

Detailed criteria are in `docs/customer_intake/pilot_success_criteria.md`,
which is signed by both parties before the pilot begins.

---

## Conversion paths

After a successful diagnostic, the operator may engage HarvestMind in one
of three ways. **Which path is offered depends on which one the operator
says is most valuable** in the week-4 session — not on what we assume in
advance.

### Path B (productized) — Recurring diagnostic

| Tier | Price | What it includes |
|---|---|---|
| **Quarterly diagnostic refresh** | $2,500/quarter ($10K/yr) | New CSV exports every quarter, refreshed report, 60-minute readout |

Best for: operators who want analysis, not software. Already-busy
operators who want outside evaluation without changing their workflow.

### Path A (SaaS) — Live diagnostic platform

| Tier | Price | What it includes |
|---|---|---|
| **Monthly diagnostic refresh** | $1,500/month ($18K/yr) | Login + dashboard, monthly data refresh, monthly 30-minute readout |
| **Weekly ATP refresh** | $3,000/month ($36K/yr) | Weekly data refresh, ATP recommendations before commitment windows open, monthly 60-minute review |

Best for: operators who want HarvestMind in their weekly workflow.
Operators who say "can we use this every week?"

### Path C (ERP add-on) — Integration engagement

| Tier | Price | What it includes |
|---|---|---|
| **ERP add-on engagement** | $15K–$75K/yr | Integration with operator's ERP (NetSuite, Famous, Produce Pro, etc.), produce-specific ATP recommendations bolted on, scoped per operator |

Best for: operators on a full ERP who say "our system does inventory but
not this decision logic". Highest ceiling, longest sales cycle, requires
integration work.

The diagnostic pilot fee is **not** credited toward any ongoing
engagement. The pilot funds the diagnostic work; the conversion fees fund
the ongoing operations.

---

## Out of scope for the pilot

The following are explicitly not included and will not be promised:

- Full ERP integration during the pilot (that's the Path C conversion
  conversation, not the pilot itself)
- WMS integration or barcode scanning
- Mobile application
- Multi-tenant cloud hosting (each operator gets a dedicated instance)
- Real-time inventory dashboards
- Automated reorder triggers or buyer notifications
- A FSMA-204 compliance certification — HarvestMind delivers a readiness
  assessment, not a regulatory sign-off
- An accounting reconciliation — diagnostic values are estimates, not
  GL entries
- Custom feature development requested during the pilot

If the operator requests any of the above, the answer is "noted for the
roadmap, not part of this pilot."

---

## Confidentiality and data handling

- A mutual NDA is signed before any data is shared
- All operator data is stored locally in a dedicated DuckDB file for
  that operator — no shared multi-tenant database
- Operator data is not used for any other engagement, demo, or marketing
  without written permission
- At end of pilot, the operator chooses one of:
  - Continue: data retained for ongoing engagement
  - Pause: data archived for 90 days then deleted
  - Stop: data deleted within 7 days of report delivery
- A signed certificate of data deletion is provided on request

---

## Why this structure (internal rationale, not for the customer)

- **Paid, not free**: Free pilots produce no commitment, no urgency, no
  operator review. A $3K diagnostic is buyable from a GM's discretionary
  budget and signals real intent.
- **Time-bounded**: 30 days forces both sides to make decisions instead of
  letting scope creep.
- **Diagnostic, not transformation**: We're not promising operational
  change. We're promising a credible report. The operator owns the change.
- **No predetermined conversion path**: We don't decide in advance whether
  this becomes SaaS, recurring service, or ERP add-on. The operator
  decides, and we offer the path they choose.
- **Out-of-scope list**: Protects against feature requests during week 3
  that would blow the timeline.
- **Tech-stack-agnostic**: Open ICP for first pilots is a deliberate
  research choice. Each operator profile that converts (or doesn't)
  teaches us which path is real.
