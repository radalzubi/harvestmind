# HarvestMind: A Diagnostic Engine for Perishable Produce Operations

_One-page memo for Purdue advisors and DIAL Ventures._

---

## One-sentence description

HarvestMind is a diagnostic engine for perishable produce operators. It uses
CSV exports from existing systems — spreadsheets, ERPs, inventory tools, or
order platforms — to estimate waste loss, shortage loss, supplier reliability,
buyer fulfillment risk, traceability gaps, and available-to-promise
recommendations.

## What we built

A working local MVP:

- FastAPI backend with diagnostic engine and CSV intake
- Next.js dashboard, deployed at a private URL on Vercel
- DuckDB single-file data store (one operator per file)
- One-click sample dataset loader for demos
- 13-section diagnostic HTML report, board-readable and printable
- 296 backend tests passing, frontend TypeScript and production build clean
- 5 staging tables that accept messy operator CSVs without schema migration

## Problem we believe exists

Regional produce operators (food hubs, aggregators, distributors, and
foodservice produce departments) commit inventory to institutional buyers
before they know what supply will arrive. The result is a pattern of
overcommitment, last-minute substitutions, missed orders, waste, and
FSMA-204 traceability gaps that operators rarely quantify in dollars.

Most run on QuickBooks plus spreadsheets, or on an ERP that does inventory
but not produce-specific available-to-promise logic. Either way, the
diagnostic information that would tell them where margin is leaking is
not produced by their existing systems.

## What we have NOT yet validated

- That this diagnostic produces a number an operator agrees is real
- That the right buyer segment is food hubs vs. wholesalers vs. ERP-equipped operators
- That the right business model is SaaS vs. productized diagnostic vs. ERP add-on
- That the dollar savings we'd identify are large enough to justify any specific price point

The MVP is built. The next step is real operator data — without it, every
claim about market size or savings is modeled, not measured.

## Three possible business shapes — the first paid diagnostics will tell us which is real

| Path | If we hear from operators... | Implication |
|---|---|---|
| **A. SaaS for spreadsheet-heavy hubs** | "Can we use this every week?" + recurring workflow pain | Tight vertical SaaS, ~$12K–$30K/yr per customer. Honest ceiling: low single-digit millions ARR. Bootstrappable, not venture-scale alone. |
| **B. Productized diagnostic / consulting** | "Can you run this once a quarter?" | $3K–$15K per engagement. Services-heavy but sellable now. Works across any tech stack. Best for revenue and learning in the next 6 months. |
| **C. ATP add-on for ERP-equipped operators** | "Our ERP does inventory but not this decision logic" | $15K–$75K/yr. Highest ceiling, hardest execution (integrations, enterprise trust, incumbent ERP competition). Real but speculative until validated. |

We are not pretending we know which one is correct. The first 3–5 paid
diagnostics are designed to surface which way the market pulls us.

## Why now

FSMA-204 enforcement is approaching for produce on the FDA Food Traceability
List. Regional Food Business Centers and USDA LFPP grants are funding
operational tooling for produce hubs. Produce ERPs are publicly positioning
around traceability and compliance — Famous Software, Produce Pro, Silo —
which is evidence the underlying problem is real but does not yet validate
which segment will pay for which kind of solution.

## Why Purdue

We are a Purdue student team applying optimization, data engineering, and
ag-economics coursework to a real food-system problem. Before approaching
operators we want advisor pressure-testing on the diagnostic model, data
requirements, and the segmentation hypothesis.

## What we need feedback on

1. Are the diagnostic metrics the right ones to anchor an operator conversation on?
2. Is the data we ask for realistic for a typical operator's data hygiene?
3. Which of the three paths (SaaS / productized / ERP add-on) is most worth
   the bet, and what evidence would change your answer?
4. Who in your network is most likely to share 6–12 months of messy
   operational data for a structured diagnostic?

## Advisor ask

A 25-minute call to pressure-test the diagnostic and the segmentation, plus
warm introductions to one or two produce operators willing to share
historical data for a paid diagnostic.

We are not asking for an equity decision, a commitment, or any role beyond
honest feedback.

## Current status

- Working local MVP, demo-ready
- GitHub repo (private)
- Vercel-deployed frontend at a private URL
- Zero real-operator data yet
- Zero revenue, no LOIs, no outside capital

## Next milestone

One real operator dataset, run through the diagnostic, with the operator
confirming the findings are directionally accurate. Everything downstream
of that — pricing, segment, business model — depends on it.

---

_If there is mutual fit after the conversation, we would be open to discussing
a formal advisor role through the proper Purdue conflict-of-interest and
intellectual-property process._
