# HarvestMind: Available-to-Promise and Traceability Diagnostics for Perishable Produce Operators

_One-page memo for Purdue advisors and DIAL Ventures_

---

## One-sentence description

HarvestMind ingests CSV data from regional produce operators and generates a
diagnostic report covering waste loss, shortage loss, supplier reliability,
buyer fulfillment risk, FSMA-204 traceability readiness, and lot-level
available-to-promise recommendations.

## Problem

Regional produce operators (food hubs, aggregators, distributors) commit
inventory to institutional buyers before they know what supply will arrive.
The result is a pattern of overcommitment, last-minute substitutions, missed
orders, and waste that operators rarely quantify in dollars.
Most run the business on spreadsheets with no lot-level visibility, which also
exposes them to FSMA-204 traceability gaps they did not know they had.

## Customer

Regional food hubs and produce aggregators selling to schools, hospitals,
universities, grocery, and foodservice. Typical revenue range: $1M–$25M.
Typical tooling: QuickBooks plus Excel.
Typical pain: 5–15% gross margin lost to waste + missed orders, no FSMA-204
record system, and a stronger buyer requiring a traceability audit.

## Product

CSV intake → DuckDB staging → diagnostic engine → web dashboard + printable
HTML report. Five staging tables: products, supplier deliveries, inventory
lots, buyer orders, waste adjustments. No ERP integration required for the
first diagnostic.

## What we built

A working local MVP: FastAPI backend, Next.js dashboard, DuckDB store,
one-click sample dataset loader, and a 13-section diagnostic HTML report.
287 backend tests pass. TypeScript and production build pass.

## Why now

FSMA-204 enforcement is approaching for produce on the FDA Food Traceability
List. Regional operators have grant funding under USDA LFPP and Regional Food
Business Centers to invest in operational tooling, but no specialized
diagnostic exists for this segment.

## Why Purdue

We are a Purdue student team applying optimization and data-engineering
coursework to a real food-system problem. We are seeking advisor pressure
testing on the diagnostic model, data requirements, pilot design, and
operator economics before approaching real customers.

## What we need feedback on

1. Are the diagnostic metrics the right ones to anchor an operator conversation on?
2. Are the data requirements realistic for a typical food hub's data hygiene?
3. Is a $3K–$7.5K paid diagnostic pilot the right wedge product?
4. What are we missing about how this segment actually buys software?

## Advisor ask

A 25-minute call to review the metrics and data model, plus warm introductions
to one or two regional food hub operators willing to share 6–12 months of
historical data for a diagnostic pilot.

## Current status

- Working local MVP, demo-ready
- Not yet customer-validated
- No real operator dataset yet
- No revenue, no LOIs
- Zero outside capital

## Next milestone

One real operator dataset and one paid diagnostic pilot or signed letter of
intent.

---

_If there is mutual fit after the conversation, we would be open to discussing
a formal advisor role through the proper Purdue conflict-of-interest and
intellectual-property process._
