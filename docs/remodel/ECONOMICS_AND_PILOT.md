# Revenue model, market sizing and minimum paid pilot

## What can honestly be valued today

HarvestMind has no demonstrated customer savings, paid conversion, retention
or repeatable onboarding cost in the evidence reviewed. **There is not enough
evidence for a defensible company valuation or numerical country TAM.** A
conditional revenue model is useful; disguising assumed firm counts as a
researched market estimate is not. Public food sales are not software revenue.

For each of Saudi Arabia, UAE, Jordan, Egypt, Kuwait, Qatar, Oman, Bahrain,
Morocco, Iraq, Lebanon, Algeria, Tunisia, Palestine and the US, qualified
buying-group counts remain unverified. GCC is the six GCC markets; MENA here
is the fourteen named markets, not a universal geographic definition. Never
add GCC to its constituent countries or count branches as independent buyers.

Use this bottom-up model once named accounts are available:

- `TAM = eligible buying groups × sustainable annual fee`, by segment/country.
- `SAM = TAM accounts actually supported by geography, data, workflow and integration × fee`.
- `3-year SOM = min(reachable qualified accounts × paid conversion × retention,
  sales capacity, implementation capacity) × realized annual fee`.

Counts must be deduplicated legal buying groups with stock ownership and
purchasing authority. Inputs need a registry/source date, eligibility rule,
parent/subsidiary treatment and sampling uncertainty. Research this through
trade registries/industry associations and a named-account list, not generic
FMCG-market research. US Census tables are a starting universe, not the final
qualified count. `evidence/market_inputs.json` explicitly leaves these unknown.

### Conditional revenue, not claimed market size

| Active customers | $12k ACV | $25k ACV | $50k ACV |
|---:|---:|---:|---:|
| 10 | $120k | $250k | $500k |
| 25 | $300k | $625k | $1.25m |
| 50 | $600k | $1.25m | $2.50m |
| 100 | $1.20m | $2.50m | $5.00m |
| 250 | $3.00m | $6.25m | $12.50m |

The machine-readable sensitivity includes all requested ACVs: $6k, $12k,
$18k, $25k, $36k, $50k, $75k and $100k. At $25k, $10m ARR requires 400 active
customers; $100m requires 4,000. At $50k, those counts halve. These are arithmetic
thresholds, not a pipeline forecast or evidence this is venture-scale.

## Charge a share of real incremental savings

Let B be **verified recurring annual economic benefit net of extra operating
costs**, relative to the signed-off incumbent. If revenue is rB:

| Verified recurring B | 10% share | 20% share | 25% share |
|---:|---:|---:|---:|
| $50k | $5k | $10k | $12.5k |
| $125k | $12.5k | $25k | $31.25k |
| $250k | $25k | $50k | $62.5k |
| $500k | $50k | $100k | $125k |

At a 20% share, 50 clients each proving $125k recurring benefit generate
$1.25m annual revenue **if** the benefit recurs and the clients remain. A pure
share model introduces counterfactual disputes, seasonal cash flow, operator
noncompliance and collection risk. Do not project revenue from simulated
percentage savings times all customer throughput.

Recommended offer to test: **$3k–$5k fixed diagnostic**, credited against a
subsequent pilot; then a proposed $12k–$25k annual minimum with an optional
performance component, but only after recurring benefit supports it. These
are proposed price tests, not market-clearing prices. At $25k we must beat an
operator's real alternative, including lower-priced inventory add-ons.
The public Netstock entry price is documented in the competitor report.

If selling pure gainshare, begin with 20% of jointly verified recurring net
benefit, define a cap and invoice timing, and price data cleanup separately.
Do not call a floor plus uncapped gainshare “20% of savings.” Model the actual
effective rate and operator payback. A contract/legal review is needed before
offering guaranteed savings or performance liability.

## $25,000 annual fee: benefit thresholds

Here 3x/5x/10x means **gross benefit divided by fee**, not net ROI. Net ROI is
200%/400%/900% respectively before implementation and customer labor.

| Benefit/fee | Required annual B | If all benefit is carry savings: stock needed* |
|---:|---:|---:|
| 3x | $75,000 | $3.75m |
| 5x | $125,000 | $6.25m |
| 10x | $250,000 | $12.50m |

\*Illustrative assumptions: 10% sustainable inventory reduction and 20% annual
avoidable carrying cost; recurring benefit is 2% of the starting stock value.
If fixed warehouse rent does not change, do not count it as avoidable savings.
At 15% stock reduction and 25% avoidable carry, the required stock for 5x is
$3.33m. If benefit also comes from fewer shortages or expedites, the minimum
stock threshold changes. Full sensitivity is in `evidence/roi_sensitivity.csv`.

Inventory released `R = I_before - I_after` is a **one-time balance-sheet/cash
effect**, dependent on selling down stock and supplier payments, not perpetual
annual profit. Recurring carry benefit can be `h × R`, provided h excludes
already-counted financing or other overlapping costs. If customers monetize
released capital elsewhere, model the incremental return separately and do
not count the same financing benefit twice.

Revenue is not profit: additional fulfilled sales contribute **margin after
incremental landed, delivery and fulfillment costs**, not the selling price.
Planner hours are monetary savings only if capacity is actually redeployed or
expense avoided. Stockouts inferred from zero sales need censored-demand
analysis; they are not observed lost sales by default.

## Founder economics and valuation discipline

At $25k annual fee and a **target assumption** of 70% contribution margin,
annual contribution is $17.5k. A $15k fully loaded acquisition cost then has
roughly 10.3 months contribution payback, before setup losses. At only 40%
margin it takes 18 months. Measure hosting, analyst/implementation hours,
support, sales, travel and collection costs; a consulting-heavy diagnostic
may be a good business without SaaS margins.

No valuation multiple is applied: a defensible one would require actual
growth, retention, margin, concentration and current financing/comparable
evidence. Synthetic cost reductions establish none of those. The strongest
near-term financial milestone is a paid pilot that renews profitably.

## Minimum real-customer pilot

### Qualification and data contract

Start with the commitment question: **“When you accept customer demand, have
you already confirmed supply, or are you committing before supplier quantities
and arrival dates are known?”** Then ask what action can still change: order
timing, quantity, supplier, substitute, expedite, transfer, or customer promise.
An alert about an unchangeable shortage is not procurement savings.

Need 52–104 weeks if available (26 supports a narrower, nonseasonal diagnostic),
SKU/product and supplier/location IDs; units and case/pallet/MOQ; dated POs,
requested/confirmed quantities and dates; cancellations; receipt/accepted/rejected
quantity and timestamps; customer order/ship/delivery lines and promises;
opening/closing stock and adjustments; open pipeline as of every origin;
unit landed cost, realized contribution, emergency premiums, service penalties,
expiry/age/salvage if relevant; planner rules and overrides; calendars; quote
availability and alternate sources. Record every field's known-at time.

Do not request unnecessary personal data. Read-only exports, encrypted transfer,
tenant isolation, bounded retention, access logging, deletion procedure and
explicit no-training/no-cross-customer-sharing terms are required. Never use
the demo or production training database for pilot data.

### Stages, responsibilities and exit criteria

| Stage | Work | Evidence required to proceed |
|---|---|---|
| Paid diagnostic, proposed 2–3 weeks | Reconcile stock, POs, receipts, service and cost ledger with buyer/CFO | Signed definitions and data completeness; report uncertainty and unavailable metrics |
| Historical replay, proposed 2–4 weeks | Freeze incumbent, compare fill-aware ERP rules and candidate plans using as-of data | Identical capacities and costs; no lookahead; every fold reported; net benefit conservative after implementation cost |
| Shadow mode, proposed 4–8 weeks | Publish recommendations before outcomes without placing orders | Buyer judges feasibility; track override reasons, latency, actual supplier alternatives and pipeline accuracy |
| Limited live pilot, proposed 8–12 weeks | Approved SKU/supplier cohort with human sign-off, fixed decision budget | Matched/control or phased design; preregister economics and service, measure realized changes |
| Renewal | CFO reconciliation, downside and operating burden | Positive verified recurring benefit, acceptable service, and profitable delivery |

Durations are proposals; rare disruptions cannot be validated just by waiting
eight weeks. Use stress tests separately and do not report their hypothetical
avoided loss as realized pilot benefit.

Success criteria proposed for contracting: at least 3x benefit/total annualized
customer cost under a conservative agreed estimate; no material service harm
beyond an explicit SKU/customer tolerance; no infeasible or unauthorized PO;
all severe exceptions visible; net implementation burden included. Compare
at a fixed approved service level, not by quietly cutting promised service.

Stop/rollback on unit/date reconciliation failure, material pipeline errors,
unavailable alternative supply, unsupported cash budget, unexpected solver
relaxation, service threshold breach, inability to reproduce the incumbent,
unauthorized data access, or buyer rejection of the counterfactual. Retain the
approved incumbent; do not “fix” a negative pilot by changing evaluation seeds
or excluding the loss-making weeks.

## CFO decision card: output contract

Every proposed change should show:

1. Current inventory, pipeline and current policy; which record supports them.
2. Suggested quantity/timing and supplier, plus capacity/pack feasibility.
3. Expected service and uncertainty; separate full-window fill from controllable
   modeled service and from OTIF.
4. Recurring net benefit, one-time release, implementation cost and fee separately.
5. Historical paired range, adverse folds, confirmation result and solver warnings.
6. Worst-case exposure within the specified stress set, not a universal guarantee.
7. What the buyer must approve and when the recommendation expires.
8. A clear **retain incumbent** result if evidence or data is insufficient.

This is a usable recommendation format. No current synthetic result fills in
the customer's dollar benefit; those fields remain unverified until the pilot.
