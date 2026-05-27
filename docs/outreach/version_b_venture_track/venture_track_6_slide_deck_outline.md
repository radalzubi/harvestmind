# Venture-Track Deck Outline — Version B

_Audience: DIAL Ventures, agrifood seed investors, Purdue Innovates.
Length: 5–7 minute spoken walkthrough + 10 minutes of Q&A._

The job of this deck is different from Version A. Version A is
"diagnose first; figure out business model from data." Version B
asks: **could this be venture-scale, and what would prove it?**

Use Version B only where the audience is funding-oriented and
fluent in the language of venture markets. Use Version A everywhere
else. Mixing the two destroys both.

---

## Slide 1 — The Broader Problem

**Title**: Perishable supply chains commit before certainty — and absorb the loss after.

**Core message**: This pattern repeats across every perishable
vertical, costs the industry billions in annual shrinkage, and no
software category owns the operational decision layer that would
prevent it.

**Bullets**:
- Perishable operators (produce, dairy, seafood, foodservice) commit
  inventory to buyers before they know what suppliers will deliver
- Industry-wide produce shrinkage runs 5–10% at the distributor level
- The resulting waste, missed orders, substitutions, and rework rarely
  surface in a P&L as a single line item — they appear as "low margin"
- Existing ERPs handle inventory and accounting; they don't make the
  commit/no-commit decision
- The data that would make those decisions exists in the operator's
  files; it is not currently translated into action

**Visual**: A simple horizontal timeline showing
"Commit → Supplier delivers → Some shortage → Substitute / miss → Buyer reacts"
with the dollar leakage points marked.

**Speaker notes**:
"This isn't a niche problem. USDA's loss-adjusted food availability
data puts produce loss at the distributor level alone at $5–8B/yr.
The reason it persists is that the operational decision layer —
'how much should I promise this buyer?' — is not currently software-mediated."

---

## Slide 2 — Why Produce First

**Title**: Produce is the highest-leverage starting wedge.

**Core message**: Among perishable verticals, produce concentrates
the most operators, the most data heterogeneity, and the most active
regulatory pressure — making it the right place to prove the
operational-intelligence thesis before generalizing.

**Bullets**:
- **Perishability**: highest shrinkage rate in commercial food
  distribution (5–10% at distributor level)
- **Fragmentation**: ~400 named food hubs + ~2,000–3,000 produce
  wholesalers in the US — many sellable accounts at wedge price
- **Regulatory anchor**: produce is on the FDA Food Traceability
  List (FSMA-204); current compliance/enforcement target is
  **July 20, 2028**. Operators are starting to ask "what records
  do I have to produce?" — most cannot answer cleanly today
- **Data hygiene heterogeneity**: produce operators range from
  pure QuickBooks-plus-spreadsheet to full ERP — exactly the
  range where a CSV-in diagnostic outperforms specialized tools
- **Founder access**: Purdue / Midwest geography puts us within
  driving distance of dozens of potential pilot operators

**Visual**: Map of US Midwest with food hub directory points
overlaid; FSMA-204 timeline below.

**Speaker notes**:
"Produce is not the only perishable vertical where the engine works.
It's the one where the wedge sale is the easiest and where the
regulatory forcing function lines up with our timeline."

---

## Slide 3 — The Wedge

**Title**: A 30-day paid diagnostic. CSV in, board-readable report out.

**Core message**: The first commercial product is not a SaaS
subscription. It is a one-time paid analysis, priced from a GM's
discretionary budget, that validates whether the operator has the
problem we believe they have.

**Bullets**:
- 5 CSV files (products, supplier deliveries, inventory lots,
  buyer orders, waste) → DuckDB single-file store → 13-section
  diagnostic report
- $3K–$15K per engagement depending on operator scope
- No integration, no IT project, no operator workflow change
- 30-day timeline: week 1 data intake, weeks 2–3 analysis,
  week 4 readout and business-model discovery session
- The closing question at week 4 makes the pilot a category-discovery
  mechanism: "Which would be most valuable — a one-time analysis,
  recurring quarterly diagnostics, or a live tool connected to your
  existing system?"

**Visual**: Screenshot grid of the actual product — Overview,
Inventory Risk, ATP, Partners, Traceability, Report. No mockups.

**Speaker notes**:
"This is intentionally not the venture-scale product. It is the
wedge that buys us access to operator data so we can answer the
larger question."

---

## Slide 4 — What the Diagnostic Produces

**Title**: Six measurable outputs, all defensible from raw operator data.

**Core message**: Each module computes a specific number that an
operator's GM or CFO can stand behind in a board meeting. The math
is deterministic, the assumptions are explicit, and the output is
printable.

**Bullets**:
- **Waste loss in dollars** (with cost-basis fallback when
  estimated value missing; unvalued rows surfaced explicitly)
- **Shortage loss in dollars** (with product-level price fallback)
- **Supplier reliability scorecard** (with "Unknown" tier for
  suppliers without enough data — no silent 100% ratings)
- **Buyer fulfillment risk scorecard** (fulfilled + substituted +
  missed = 100% sanity check)
- **Inventory near-expiry exposure**
- **FSMA-204 lot traceability completeness**
- **Available-to-Promise recommendations** (subtracts near-expiry
  stock from committable quantity)
- **Annualized addressable-loss estimate** (auto-detects period
  from data, scales 365/period_days, reports 15%–30% reduction range)

**Visual**: Side-by-side: a screenshot of the report's Savings
Opportunity box on the left, a screenshot of the corresponding
assumptions/limitations section on the right.

**Speaker notes**:
"Every output has a corresponding assumption that's visible on the
same page. We did a math audit before this conversation — the
diagnostic engine is more conservative than it was three days ago."

---

## Slide 5 — Larger Platform Thesis

**Title**: Traceability + compliance data → always-on operational intelligence.

**Core message**: The data operators are collecting to comply with
FSMA-204 is exactly the data needed to drive ongoing operational
decisions. The diagnostic is the entry point. The platform layer is
where this becomes venture-scale.

**Bullets**:
- Operators must capture lot-level traceability records to meet
  FSMA-204 (compliance target July 20, 2028)
- That same data, combined with shelf-life models and demand history,
  enables real-time commit/no-commit decisions at the sales rep level
- HarvestMind's diagnostic engine is the read-only version of this
  intelligence layer; the platform version sits in the operator's
  daily workflow
- Adjacent perishable verticals (dairy, seafood, fresh meat,
  floral) have the same data structure and decision problem — engine
  generalizes
- Comparable funded companies in adjacent categories: Crisp (~$90M
  raised, food supply chain analytics), Trustwell (FoodLogiQ
  acquired by Trustwell, food traceability + supplier mgmt),
  Wherefour (~$10M+ raised, traceability platform)

**Visual**: A funnel diagram — wedge product at the top (paid
diagnostic), recurring engagement in the middle, full
intelligence platform at the bottom. Adjacent verticals shown
expanding outward.

**Speaker notes**:
"Crisp, FoodLogiQ, and Trustwell prove the venture-scale outcome
exists in this category. The bet is whether HarvestMind, starting
from a different wedge, can carve out a defensible position
specifically around perishable operational decisions — not
compliance recordkeeping, not traceability auditing, but the
commit/no-commit decision layer."

---

## Slide 6 — What We Need to Prove

**Title**: First 3–5 paid diagnostics decide whether this is venture-fundable.

**Core message**: We are not asking you to take on faith that the
venture thesis is real. We are asking what evidence from the next
12 months would convince you it is, and what would kill it.

**Bullets**:
- **Within 90 days** — first paid diagnostic delivered with
  operator sign-off on directional accuracy
- **Within 6 months** — 3 paid diagnostics, at least 1 recurring
  conversion at $10K+/yr
- **Within 9 months** — proof the engine works on 2+ operator
  tech-stack profiles (QB+Excel and ERP) and meaningful interest
  from at least 1 ERP-equipped operator in a Path C engagement
- **Within 12 months** — operator-side co-founder or strong
  advisor on the team; seed round preparation if Paths A/B/C
  evidence is positive

**Visual**: A 12-month timeline with the 4 milestones marked.
Each milestone has a "we expect to know X by then" caption.

**Speaker notes**:
"What we are asking from DIAL or any venture-track conversation
today is feedback on whether those four milestones are the right
ones, and whether you would write a check if all four hit
positively. Saying 'yes, with those milestones' is the most useful
possible answer. Saying 'no — the bet is structurally
unfundable for these reasons' is the second most useful answer.
The least useful answer is 'come back when you have traction.'
We know that. We are asking for thesis-level feedback now."

---

## Designer notes

- Use only screenshots from the actual running MVP — no mockups
- Adjacent-company comparisons (Crisp, FoodLogiQ, Trustwell,
  Wherefour) must use **verified public information**. Do not
  cite funding amounts or revenue numbers that aren't on the
  company's own page or in a confirmed press release.
- Do not put any unvalidated dollar figure on a slide ("$X/yr
  addressable loss") — only put it in the live conversation
  with proper caveats
- Footer on every slide: "HarvestMind · Purdue student team ·
  Venture-track thesis · Pre-customer-validation"
- The "Pre-customer-validation" tag is deliberate. It signals you
  know exactly where you are in the funding maturity curve.
  That earns more respect from sophisticated investors than a
  louder claim would.

## What to never include in this deck

- "We will be a $1B company" (or any TAM headline you cannot
  defend with public sources)
- "We are like [funded company]" without verifying their actual
  positioning and funding figures
- Customer logos (you have none)
- Specific savings figures from any single operator
- "FSMA-204 enforcement starts January 2026" — the current
  compliance/enforcement target is **July 20, 2028**
- Any reference to Saudi Arabia, carbon accounting, or marketplace
  features. Those are noise. Cut them.
- "AI-powered" — the diagnostic is deterministic math. Saying AI
  here would attract attention you can't follow through on.

## Anticipated investor questions

| Q | A |
|---|---|
| What's the moat? | Honest answer: today, none. The moat develops as we accumulate operator-specific data and build integration depth. At the wedge stage, the moat is execution speed and operator trust. |
| Why won't an ERP vendor build this? | Some are positioning around it (Famous, Produce Pro). The diagnostic engine is product-shaped differently from ERP modules. The bet is that operators trust a focused diagnostic vendor more than they trust their incumbent ERP to grade itself. |
| Why now? | FSMA-204 compliance target (July 2028) is creating new data-capture urgency. USDA LFPP grants are funding operator tooling investment. ERPs are visibly positioning around compliance, which validates the problem but does not occupy the diagnostic layer. |
| What about [Crisp / FoodLogiQ / Trustwell]? | They prove the category exists at venture scale. They sit at different points in the workflow than where we're aiming. Crisp serves brands and CPGs; FoodLogiQ/Trustwell focus on compliance recordkeeping. Operational decision intelligence specifically for perishable distribution is not occupied by any of them today. |
| Why a student team? | Honest answer: we know that's a weakness. Our plan is to recruit an operator-side co-founder/advisor before any formal seed conversation. We've documented the recruitment in `operator_advisor_recruiting_note.md`. |
| When can you have customer references? | First paid diagnostic engagement starts within 90 days of our first operator yes. References in 4–6 months from there. |
