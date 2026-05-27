# HarvestMind — Six-Slide Deck Outline

Designed for a 5–7 minute spoken walkthrough plus 5 minutes of Q&A.
Audience: Purdue advisors, DIAL Ventures, and prospect operators.
Tone: operator-first, evidence-based, openly uncertain about business
model until pilots validate it.

---

## Slide 1 — Problem

**Title**: Produce operators commit before they know what arrives.

**Main message**: Overcommitment, waste, missed orders, and traceability
gaps are quiet margin losses that operators rarely see in dollars.

**Bullets**:
- Hubs and produce distributors commit institutional orders before knowing what suppliers will deliver
- A meaningful share of orders are partially missed, substituted, or padded with buffer stock
- Near-expiry inventory is moved by intuition, not by data
- FSMA-204 lot traceability is required for produce on the FTL but operationally hard to prove
- Most operators run on QuickBooks plus spreadsheets, or on an ERP that does inventory but not produce-specific available-to-promise

**Visual**: A stylized diagram showing the gap between "committed" and
"actually delivered" volume over a few weeks of operator data — without a
specific dollar number attached.

**Speaker notes**:
"We are not solving food security or building an AI platform. We are
solving the unglamorous problem that regional produce operators leak
margin in ways their accounting system doesn't surface. The size of that
leak per operator is exactly what we want real data to tell us."

---

## Slide 2 — Customer (the open question)

**Title**: We see three possible buyer profiles. We don't know which one is right yet.

**Main message**: The diagnostic engine works for any operator handling
perishables. Who actually pays — and for which version of the product — is
the open question.

**Bullets**:
- **Spreadsheet-heavy food hubs** ($3M–$10M revenue, QuickBooks + Excel)
- **Productized-consulting buyers** (any size, any tech stack, want analysis not software)
- **ERP-equipped operators** (already on NetSuite, Famous, Produce Pro, Silo — have inventory but not produce-specific ATP)

**Visual**: A 2×3 grid: rows = each buyer profile; columns = "tech they
have", "pain we'd solve", "what they'd pay for". Leave the last column with
question marks, deliberately, to signal we don't claim to know.

**Speaker notes**:
"We are not pretending the food hub niche alone is a venture-scale market —
USDA's directory lists roughly 400 hubs nationally. The honest pitch is
that the diagnostic engine generalizes across all three profiles, and the
first three to five paid diagnostics are what tell us which path is real."

---

## Slide 3 — Product

**Title**: Upload your CSVs. Get a diagnostic in two minutes.

**Main message**: Lowest-friction product surface — no ERP integration, no
IT project, just CSV in / report out.

**Bullets**:
- Five CSV files: products, supplier deliveries, inventory lots, buyer orders, waste
- DuckDB store — single file per operator, runs locally
- Web dashboard for exploration + printable HTML report for the operator's GM/CFO
- Diagnostic metrics: waste loss $, shortage loss $, supplier fill rate, buyer fulfillment rate, ATP by product, FSMA-204 lot completeness
- Sample dataset loader so demos work without setup

**Visual**: A horizontal flow diagram — CSV files → diagnostic engine →
dashboard + report. Show the 5 file names on the left and the 13 report
sections on the right.

**Speaker notes**:
"This is intentionally not an ERP. We don't own the operator's source of
truth. We read their data, find the patterns, and write a report. The
wedge is the diagnostic. Anything beyond that is earned over time and
shaped by what the operators tell us they want."

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
- Export the 13-section diagnostic report

**Visual**: A 6-panel screenshot grid of the actual app: Overview,
Inventory Risk, ATP, Partners, Traceability, and the HTML report.

**Speaker notes**:
"The sample dataset is intentionally imperfect — one supplier with a 62%
fill rate, near-expiry lots, two lots with missing lot IDs. That's not
random; that's the shape of real operator data, and it lets every panel
show something useful. The dollar numbers on this sample are too small
to draw business conclusions from — that's exactly why we need real data
next."

---

## Slide 5 — Pilot Structure (and Why It's Designed To Resolve the Open Question)

**Title**: 30-day paid diagnostic. $3K–$7.5K. Three pilots will tell us which business shape is real.

**Main message**: The pilot is priced to be buyable from a GM's
discretionary budget AND structured to surface which business model the
market is pulling toward.

**Bullets**:
- 6–12 months of historical operator data, exported to CSV
- Week 1: data intake, validation, and quality review with the operator
- Weeks 2–3: diagnostic engine run, manual review, anomaly investigation
- Week 4: written findings, board-format report, 60-minute readout, 90-minute action-planning session
- Pricing: $3K (single product line) – $7.5K (multi-category, multi-location); $10K–$15K for larger operators
- **Closing question we ask each operator**: "Which would be most valuable — a one-time analysis, recurring quarterly diagnostics, or a live tool connected to your existing system?"

**Visual**: A horizontal 4-week timeline with deliverables marked under
each week, and the three-path question framed as a decision point at the
end of the engagement.

**Speaker notes**:
"This is not a free pilot. Free pilots produce no commitment. A paid
diagnostic priced from a discretionary budget signals real intent. The
closing question makes the pilot a business-model discovery mechanism —
which is what we actually need it to be at this stage."

---

## Slide 6 — Ask

**Title**: We need three things.

**Main message**: The MVP is built. The next bottleneck is data, then
segmentation clarity, then business-model validation.

**Bullets**:
- **Pressure-test** the diagnostic model and the data requirements
- **One warm introduction** to a produce operator willing to share 6–12 months of messy data for a structured diagnostic
- **Help us decide**, after the first 3–5 paid diagnostics, whether this should become a SaaS, a productized diagnostic, or an ERP add-on

**Visual**: A clean "three asks" list — Pressure-test / Intro / Help us
decide — with contact info underneath.

**Speaker notes**:
"We are not here for an investment, equity, or marketing. We are here for
honest feedback on the model, an introduction to one operator with
operational pain and the data to validate or invalidate the diagnostic,
and help interpreting what the first paid diagnostics tell us. That's it."

---

## Designer notes

- Use only screenshots from the actual running MVP — no Figma mockups
- Keep slide chrome minimal — title, body, no logos other than HarvestMind
- **Do not include any unvalidated dollar figures** ("$X/yr addressable loss")
  on the slides themselves — those go in the live conversation only, with
  the proper caveats
- Avoid the words "AI", "platform", "revolutionize"
- Bottom-right footer: "HarvestMind · Purdue student team · Diagnostic MVP · Pre-customer-validation"

The last footer phrase is deliberate: it tells the advisor you know where
you actually are in the journey. That earns more credibility than a louder
claim.
