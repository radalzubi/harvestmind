# HarvestMind — Six-Slide Deck Outline

Designed for a 5–7 minute spoken walkthrough plus 5 minutes of Q&A.
Audience: Purdue advisors, DIAL Ventures, and prospect operators.
Tone: operator-first, evidence-based, non-hype.

---

## Slide 1 — Problem

**Title**: Regional produce operators commit before they know what arrives.

**Main message**: Overcommitment, waste, missed orders, and weak traceability
are quiet 5–15% margin losses for regional food hubs — and they have no system
to quantify it.

**Bullets**:
- Hubs commit institutional orders before knowing what suppliers will deliver
- 10–30% of orders are partially missed, substituted, or padded with buffer stock
- Near-expiry inventory is moved by eye, not by data
- FSMA-204 lot traceability is required for produce on the FTL, but most hubs cannot prove it
- Operators run on QuickBooks + spreadsheets and rarely see loss in dollars

**Visual**: A single number — "5–15% of gross margin" — over a faded produce
warehouse photo. Or: a stylized chart showing the gap between "committed" and
"actually delivered" lines.

**Speaker notes**:
"We are not solving food security. We are solving the unglamorous problem
that regional aggregators don't know how much money they leak each month.
Today they find out at year-end when QuickBooks shows lower margin than
expected, with no path to attribute it."

---

## Slide 2 — Customer

**Title**: Regional food hubs and produce aggregators, $1M–$25M revenue.

**Main message**: A specific, addressable wedge — not "the food industry."

**Bullets**:
- Serve schools, hospitals, universities, grocers, and foodservice
- Aggregate from 5–60 farms, ship 50–500 SKUs
- Use QuickBooks Desktop or Online plus Excel for ops
- Have a buyer (Sysco, a large school district, a hospital network) asking for traceability records they cannot easily produce
- Have USDA LFPP or Regional Food Business Center grant access for tools

**Visual**: A simple 2×2 — vertical axis: revenue, horizontal axis: technical
sophistication. Place HarvestMind's target in the lower-right quadrant
($1M–$25M, low tech sophistication). Mark ERP vendors (NetSuite, Famous, Silver Fern)
in the upper-left.

**Speaker notes**:
"This is a real segment with real budgets but no specialized tooling. ERP
vendors don't go down-market here, and generic BI tools don't understand
shelf life or lot traceability."

---

## Slide 3 — Product

**Title**: Upload your CSVs. Get a diagnostic in two minutes.

**Main message**: Lowest-friction wedge — no ERP integration, no IT project,
just CSV in / report out.

**Bullets**:
- 5 staging tables: products, supplier deliveries, inventory lots, buyer orders, waste
- DuckDB store — single file, runs locally for the operator's data
- Web dashboard for exploration + printable HTML report for the operator's GM/CFO
- Diagnostic metrics: waste loss $, shortage loss $, supplier fill rate, buyer fulfillment rate, ATP by product, traceability completeness %
- Sample dataset loader for demos — one click, real findings

**Visual**: A horizontal flow diagram — CSV files → HarvestMind diagnostic
engine → dashboard + report. Show the 5 file names on the left and the
report sections on the right.

**Speaker notes**:
"This is intentionally not an ERP. We do not own the operator's source of
truth. We read their data, find the patterns, and write a report. The wedge
is the diagnostic. Anything beyond that is earned over time."

---

## Slide 4 — Demo Flow

**Title**: A working diagnostic in 10 clicks.

**Main message**: We will show you the actual product, not a mockup.

**Bullets**:
- Click "Load sample dataset" → 5 tables populate in under 2 seconds
- Overview page shows waste loss, shortage loss, risky suppliers, traceability %
- Inventory Risk page surfaces near-expiry lots and expired stock
- Available-to-Promise page generates per-product commitment recommendations
- Traceability page shows FSMA-204 completeness gaps and the specific incomplete lots
- Export the diagnostic report — board-readable, printable

**Visual**: A 6-panel screenshot grid of the actual app: Overview, Inventory
Risk, ATP, Partners, Traceability, and the HTML report.

**Speaker notes**:
"The sample dataset is intentionally imperfect — one supplier with a 62% fill
rate, two expired lots, two lots with missing lot IDs. That's not random;
that's what real operator data looks like and it lets every panel show
something useful."

---

## Slide 5 — Pilot Structure

**Title**: 30-day paid diagnostic. $3K–$7.5K. One real dataset.

**Main message**: Concrete, time-bounded, and priced low enough that an
operator can buy it from a discretionary budget.

**Bullets**:
- 6–12 months of historical operator data, exported to CSV
- Week 1: data intake, validation, and quality review with the operator
- Weeks 2–3: diagnostic engine run, manual review, anomaly investigation
- Week 4: written findings, board-format report, and a 60-minute readout
- Deliverable: HTML/PDF report + executive summary + 3 prioritized actions
- Pricing: $3K (single product line) — $7.5K (multi-category, multi-location)
- Conversion path: live SaaS at $1.5K–$3K / month after pilot

**Visual**: A horizontal 4-week timeline with the deliverables marked under
each week. Pricing in a clean box on the right.

**Speaker notes**:
"This is not a free pilot. Free pilots produce no commitment. A $3K
diagnostic is buyable from a GM's discretionary budget and signals real
intent. If the diagnostic shows them $80K+ of addressable loss, the path to
$24K/year SaaS is obvious."

---

## Slide 6 — Ask

**Title**: We need one real operator dataset.

**Main message**: The MVP is built. The next bottleneck is data, not product.

**Bullets**:
- Expert feedback on the diagnostic model and data requirements
- A warm introduction to one regional food hub willing to share 6–12 months of data
- Pressure testing on the pilot price and structure
- Conversation, not commitment — no equity ask at this stage
- (Mutual fit later → formal advisor role via Purdue COI/IP process)

**Visual**: A clean "three asks" list — Feedback / Intros / Pressure test —
with our contact info underneath.

**Speaker notes**:
"We are not here for an investment, equity, or marketing. We are here for
honest feedback on the model and an introduction to one operator who has the
operational pain and the data to validate or invalidate this product. That's
it."

---

## Designer notes

- Use only screenshots from the actual running MVP — no Figma mockups
- Keep slide chrome minimal — title, body, no logos other than HarvestMind
- Avoid the words "AI", "platform", "revolutionize"
- Use dollar figures wherever possible — operators speak dollars
- Bottom-right of each slide: small footer with "HarvestMind · Purdue student team · Diagnostic MVP"
