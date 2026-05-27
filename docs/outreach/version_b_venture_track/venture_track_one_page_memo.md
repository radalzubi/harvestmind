# HarvestMind — Venture-Track Thesis (Version B)

_Audience: DIAL Ventures, Purdue Innovates, agrifood venture investors, prospective operator-side co-founders/advisors._

**This is not the operator-facing memo.** Operators do not care about
"perishable supply chain intelligence." They care about waste, shortages,
and traceability. For operator conversations, use Version A.

This memo exists to answer one question:
**Could HarvestMind become bigger than a food-hub SaaS niche, and is that bet worth backing today?**

---

## One-sentence thesis

HarvestMind is operational intelligence for perishable supply chains,
starting with produce. The wedge is a paid diagnostic that uses messy
CSV exports from existing operator systems. The larger thesis is that
traceability and operational data — increasingly captured because of
FSMA-204 — can become an always-on decision layer for perishables.

## Why this could become larger than food hubs

The strict food-hub SaaS niche is too small to support a venture-scale
outcome on its own. We are not pretending otherwise. The reason this
project might still be venture-fundable is that the same diagnostic
engine, the same data shape, and the same operational decisions
generalize across:

| Adjacent perishable verticals | Approximate US operator count | Why the engine applies |
|---|---|---|
| Produce wholesalers + DCs | ~2,000–3,000 | Same commit-before-certainty problem; larger budgets |
| Foodservice produce divisions (Sysco, US Foods, PFG produce, regional broadline) | ~50–100 named accounts at scale | Same problem; structurally compliance-driven |
| Grocery DC produce departments | ~200 major chains' produce arms | Same problem; budget exists |
| Fresh seafood distribution | ~500–800 operators | Same shelf-life math, different regulatory profile |
| Dairy distribution | ~1,500 operators | Same perishability + supplier reliability dynamics |
| Cut flowers / florals | ~200 operators | Identical near-expiry / committable-quantity problem |

We are not claiming the company will win all of these. We are claiming
the diagnostic engine generalizes, and the wedge product (paid produce
diagnostic) is a credible entry point to test which adjacency expands.

## Starting wedge

A 30-day paid diagnostic, $3K–$15K, that ingests five CSVs from any
operator regardless of tech stack and produces:

- Waste loss in dollars
- Shortage loss in dollars
- Supplier reliability scorecard
- Buyer fulfillment risk
- Inventory near-expiry exposure
- FSMA-204 lot traceability completeness
- Available-to-promise recommendations
- Annualized addressable-loss estimate (15%–30% reduction range)

The wedge does not require operator tech-stack changes, integrations,
or workflow disruption. CSV in, report out. That is the entire surface
of the first sale.

## Why produce first

Several reasons converge:

1. **Perishability is highest** — produce shrinkage runs 5–10% at the
   distributor level; problem is largest in dollar terms per operator
2. **Fragmentation** — produce operators are smaller and more numerous
   than dairy or seafood; more sellable accounts at the wedge price
3. **Traceability pressure** — produce is on the FDA Food Traceability
   List, which creates a regulatory anchor for the conversation
4. **Data hygiene heterogeneity** — exactly the operators most likely
   to pay for a diagnostic are the ones whose data is messiest
5. **Founder access** — Purdue is in the Midwest with proximity to
   produce hubs and Regional Food Business Centers; cold reach is
   structurally easier here than in seafood or specialty

## Why now

| Forcing function | Detail |
|---|---|
| **FSMA-204 traceability rule** | FDA has indicated a 30-month extension; the current compliance/enforcement target is **July 20, 2028**. Operators are starting to look at what records they would need to produce — most discover they cannot produce them today. |
| **USDA LFPP + Regional Food Business Centers** | Grant funding for operator tooling is currently available; some hubs have discretionary technology budget for the first time |
| **ERP vendor positioning** | Produce ERPs (Famous Software, Produce Pro, Silo) are publicly emphasizing FSMA-204 and traceability — confirming the underlying problem is real, but not yet validating which segment will buy from a startup vs. an incumbent |
| **Demand-side pressure** | Sysco, hospital networks, large school districts are increasingly asking suppliers for traceability records as a prerequisite |

## What is built today

- FastAPI backend with diagnostic engine
- DuckDB single-file store (one operator per file)
- Next.js web dashboard, deployed at a private URL on Vercel
- 13-section HTML diagnostic report, board-readable, printable
- One-click sample dataset loader
- 5 staging tables accepting messy operator CSVs
- 296 backend tests passing; frontend TypeScript and production build clean
- ATP math correctly subtracts near-expiry stock
- Savings math annualizes from auto-detected period; reported as 15%–30% range

GitHub: private. Vercel: private deploy. Code review: done in-house.

## What is not proven yet

This is the part most often skipped in venture-track memos. Including
it is deliberate. If the answers to any of these are "no," the venture
thesis collapses or substantially changes shape.

| Open question | What would prove it |
|---|---|
| Do operators agree the diagnostic numbers are directionally accurate? | First 3 paid diagnostics with operator sign-off |
| Will operators pay $3K–$15K for the diagnostic? | First paid invoice |
| Does the diagnostic generate a recurring-revenue conversation? | One pilot operator says "can we run this every month/quarter" |
| Which business shape (SaaS / productized / ERP add-on) does the market support? | Pattern across first 3–5 pilots |
| Does the engine generalize beyond produce? | One paid diagnostic in an adjacent vertical |
| Can a small team execute against funded incumbents (Crisp, FoodLogiQ, Trustwell)? | Customer wins where the incumbent was also considered |
| Is there an operator-side co-founder or advisor willing to commit? | Open recruit — see `operator_advisor_recruiting_note.md` |

We expect to have meaningful answers on rows 1–3 within 90 days of the
first operator conversation. Rows 4–7 are 12–24 month questions.

## Three possible business paths

These are the same three paths laid out in Version A. The venture-track
view of them differs in interpretation, not in substance.

### Path A — SaaS for spreadsheet-heavy operators

| | |
|---|---|
| Pricing | $12K–$30K/year per customer |
| Realistic 5-year ceiling | Low single-digit millions ARR |
| Verdict for venture | Bootstrappable, not fundable as a standalone bet |

### Path B — Productized diagnostic / consulting

| | |
|---|---|
| Pricing | $3K–$15K per engagement, recurring $10K/year if quarterly |
| Realistic 5-year ceiling | Services-heavy; $1M–$3M revenue |
| Verdict for venture | Better as a revenue + learning track than as a venture thesis |

### Path C — ATP / traceability intelligence add-on for ERP-equipped operators

| | |
|---|---|
| Pricing | $15K–$75K/year per customer, more with integrations |
| Realistic 5-year ceiling | Potentially $20M+ ARR if adjacent verticals open up |
| Verdict for venture | **The only path that supports a venture-scale outcome.** Hardest execution. Requires integrations, enterprise trust, and incumbent competition. |

A venture-fundable shape of HarvestMind is almost certainly Path B as the
near-term revenue track and Path C as the long-term platform thesis,
with Path A as the smallest niche we would still serve. Which exact mix
the company commits to depends on what the first 3–5 paid diagnostics
surface.

## What evidence would make this venture-fundable

The bar most agrifood seed investors apply:

- 3+ paid diagnostics completed with operator sign-off
- At least 1 conversion to recurring engagement ($10K–$30K/yr)
- Evidence the same engine produced useful findings on at least 2
  different operator tech-stack profiles (e.g. QB+Excel and ERP)
- An operator-side co-founder or strong advisor on the team
- A signed letter of intent for a Path C engagement (ATP add-on with
  an ERP-equipped operator) — not required, but moves seed valuation
  meaningfully

If all five are true 9–12 months from now, a $1M–$3M seed at $8M–$15M
post-money is a credible raise.

## What evidence would kill the venture thesis

- Three paid diagnostics produced numbers operators agreed with but
  did not act on (problem is real but not painful enough to pay
  ongoing)
- Operators wanted only one-time analysis; nobody wanted recurring
  software (Path B is real, Paths A/C are not)
- Operators preferred existing ERP vendors' compliance modules over
  HarvestMind (Path C is occupied)
- The engine did not generalize beyond produce in a clean way (TAM
  argument collapses)
- No operator-side co-founder candidate engaged seriously
- Founders preferred bootstrap economics to venture risk

In any of those scenarios, the right answer is to keep building the
productized diagnostic business (Path B) at modest scale, decline
venture money, and revisit later.

## Ask for DIAL Ventures / Purdue advisors

We are not asking for capital today. We are asking for three things:

1. **Evaluate the thesis.** Is "perishable operational intelligence,
   starting with produce" a defensible category to attempt to win? If
   not, what's the closest version that is?

2. **One operator introduction.** Whoever in your network has
   operational pain and the data to validate or invalidate the
   diagnostic. Larger operators welcome — ERP-equipped operators are
   the most valuable signal we can collect for Path C.

3. **One co-founder/advisor candidate.** A produce-distribution or
   foodservice-produce operator with 10+ years of operational
   experience, willing to engage as advisor or co-founder. This is
   the single biggest credibility move available to us before any
   funding conversation.

The Version A memo and the live demo URL are available on request.

---

_Notes on framing:_

- _"Venture-fundable" and "scalable potential" are not the same as
  "venture-scale outcome." We are asking whether the bet is worth
  exploring, not asking you to bless the outcome._
- _If there is mutual fit later, we would be open to discussing a
  formal advisor role through the proper Purdue conflict-of-interest
  and intellectual-property process._
