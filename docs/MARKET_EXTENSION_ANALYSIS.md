# Market Extension Analysis: Shelf-Stable CPG and Vertically Integrated Growers

_Drafted 2026-08-28. Assesses whether the engine transfers to (A) commercial
FMCG distribution and franchise distributors such as NTDCO in Jordan, and
(B) vertically integrated grower-distributors such as ASTRA. US perishable
midstream remains the primary focus._

---

## Headline verdict

| | Case A: FMCG / franchise distribution | Case B: Vertically integrated grower |
|---|---|---|
| Engine transfers | Mostly, with conditions | Partially, needs re-parameterization |
| Value proposition | Re-anchors from spoilage to capital and stockout | Strengthens on weather, weakens on urgency |
| Optimizable | Yes, clearly | Yes, well-studied in ag OR |
| Worth pursuing now | Only as a data-access play | Not yet, cadence is the blocker |

Neither is unoptimizable. The question is value density and feedback speed,
not feasibility.

---

## Case A: FMCG and franchise distribution

### Company grounding

**NTDCO** (National Trading & Distribution Co, Amman): founded 1964,
family-owned, FMCG food and non-food, operating across retail, key retail,
wholesale, key accounts, supermarkets, catering, **cash van**, and logistics.
Holds multiple international brand agencies.

That structure matters more than the product category.

### Why the earlier "it degenerates" concern was overstated

The initial concern was that for shelf-stable goods the newsvendor collapses:
overage costs almost nothing (product does not spoil), so the critical
fractile approaches 1 and the answer becomes "order lots." That holds for
short-lead-time domestic distribution of cheap goods with free warehousing.

It does NOT hold for an import brand-agency distributor, for four reasons.

1. **Lead time restores the commitment structure.** Importing to Jordan from
   Europe or Asia runs 6 to 10 weeks. The decision is genuinely made under
   uncertainty resolved much later, which is precisely the two-stage shape.
2. **Ordering is lumpy and constrained.** Containers and MOQs make this an
   integer problem with binding capacity, not a smooth newsvendor. That is a
   modeling change (LP becomes MIP) but it INCREASES the value of
   optimization, because binding constraints are where optimizers earn money.
3. **Capital is genuinely expensive.** Holding 8 to 12 weeks of imported
   stock at Jordanian cost of capital, plus FX exposure, makes overage a real
   cost rather than a rounding error.
4. **Stockout is semi-permanent, not one lost sale.** An exclusive agent who
   goes out of stock risks losing shelf facings to a competing brand and
   risks the principal's volume targets. Underage cost is far above lost
   margin.

### The OTIF finding, which is the strongest single argument

Modern trade penalizes fill-rate failure in hard currency. Walmart's OTIF
regime charges **3 percent of cost of goods** on non-compliant cases against
thresholds of 98 percent collect-ready, 90 percent on-time prepaid, and 95
percent in-full. A brand shipping 10 million dollars annually at 95 percent
OTIF pays roughly **15,000 dollars per month in avoidable fines**.

That is a quantified, invoiced underage cost. Wherever an operator faces an
OTIF or service-level penalty regime, the newsvendor tradeoff is fully
restored and the optimizer has real money to chase. This is the single best
qualifying question for any commercial prospect: **do you pay fill-rate
penalties, and how much last year?**

### Cash van is an under-appreciated fit

NTDCO runs cash van operations. Loading each van each morning against an
uncertain day's route demand, subject to hard van capacity, is a repeated
constrained newsvendor with daily feedback. It is arguably a cleaner
application of the engine than the weekly produce commitment, and the
feedback loop is daily rather than weekly.

### What breaks

- Shelf-life decay, near-expiry ATP, and the temperature models go idle.
  Obsolescence (packaging changes, SKU rationalization, seasonal items) is
  soft perishability and could reuse that machinery, but it is slower and
  harder to value.
- FSMA-204 traceability is irrelevant outside US food, losing a door-opener.
- The headline diagnostic number must move from waste dollars to working
  capital, stockout, and penalty dollars. That is a product change, not a
  cosmetic one.
- The category is competitive: SAP, Oracle, Blue Yonder, RELEX, plus regional
  distributor ERPs. In perishables we can say nobody built this. Here they did.

### Verdict on A

Transfers, with the value story re-anchored. Best fit is an import or agency
distributor with long lead times, binding capital or capacity constraints, or
penalty-bearing service obligations. Worst fit is short-lead-time domestic
distribution of cheap shelf-stable goods with free warehousing and no
penalties.

---

## Case B: Vertically integrated grower-distributors

### Company grounding

**ASTRA Food Company**: since 1976, based in Tabuk, Saudi Arabia. Producer
and exporter, uses its own transportation, drip irrigation and fertigation
with integrated pest management, expanding exports to East Asia under Vision
2030.

**Date context**: Saudi harvest runs August to October. Cold storage is
viable for 12 months at 5C; dried dates keep up to 3 years frozen. Fresh
varieties such as Barhi require a complete cold chain. Saudi date exports
reached 133 countries and 1.695 billion dollars in 2024.

### What genuinely strengthens

1. **Yield uncertainty does not disappear, it moves inward.** Instead of
   modeling whether a supplier delivers, we model whether the farm produces.
   For a single-region operation like Tabuk, output is driven by one weather
   system, which is exactly the correlated-failure structure the copula layer
   was built for, now applied across blocks and varieties instead of across
   suppliers.
2. **The weather work becomes central rather than a hook.** This is the one
   segment where the weather-yield modeling is the main event.
3. **Data access is far easier.** A vertically integrated producer owns its
   agronomic and sales records end to end. No need to persuade a third party
   to share supplier data.
4. **The commitment gap is wider, not narrower.** Export contracts and
   letters of credit are signed before harvest resolves. That is a two-stage
   problem with a longer and higher-stakes information gap than the weekly
   produce case.

### What breaks

1. **The cadence is wrong.** Weekly commitment becomes a single annual
   harvest followed by a 12-month depletion. The problem shifts from
   newsvendor toward multi-period inventory allocation and revenue
   management: how fast to sell down a fixed stock, into which channels, at
   what prices, under uncertain future demand. That is a different model
   class, not a re-parameterization of the current one.
2. **The supplier fill-rate model partly loses its subject.** There are no
   external suppliers to score, though most integrated producers also buy
   third-party volume to top up, so the model is reduced rather than removed.
3. **Perishability urgency splits by product.** Fresh Barhi needing a full
   cold chain fits our value story strongly. Dried Sukkari or Khalas with one
   to three year shelf life does not: there is no urgency, and the pressure
   that makes the pitch land disappears.
4. **Planting decisions are out of reach.** Date palms take years to bear.
   Anything upstream of harvest is a horizon we cannot serve.

### The blocker nobody mentions: feedback speed

An annual harvest means **one live decision cycle per year**. A backtest on
history still works, but we could not learn from live deployment at any
useful rate. For an early-stage company that needs to iterate, a one-year
feedback loop is close to fatal. Case A's weekly or daily cadence, and cash
van in particular, gives feedback in days.

### Verdict on B

Optimizable and academically well-trodden, and the weather angle is a genuine
strength. But it requires a different model class for the depletion problem,
and the annual cadence makes it a poor place to learn. Worth revisiting once
the core is proven, not now.

---

## What this means for the current plan

Neither case justifies a pivot. There are zero pilots in the core segment,
and broadening scope before the first real dataset is the standard way an
early team dilutes its wedge.

**But the reasoning changes for NTDCO specifically, and not for market
reasons.** A family-owned distributor founded in 1964 with decision authority
in one room, and a personal connection into it, is the easiest real
operational dataset this team is likely to obtain. Right now the binding
constraint is not market size. It is that no real records have touched any
layer of the engine. A friendly operator who says yes to a data share is
worth more today than a perfect-fit operator who says no.

Recommended framing: pursue NTDCO as a **data-access and validation
opportunity**, not as a market entry. Run the diagnostic on their records,
learn what messy real data actually looks like, and let that harden the
ingestion and diagnostic layers. Keep the commercial positioning in US
perishables.

### Qualifying questions for any commercial prospect

1. Do you pay fill-rate or OTIF penalties, and how much last year?
2. What is your lead time from order to receipt?
3. Are you ever capital or warehouse constrained on what you can hold?
4. Do you carry exclusive agency volume commitments to a principal?

Two or more yes answers means the newsvendor economics hold and the engine
has real money to chase. All no means it likely degenerates and we should
decline politely.

---

# Appendix: Building for US Commercial Goods

_Added 2026-08-30. What would actually change to serve US shelf-stable and
franchise distribution, in build order._

## The reframe that makes it work

In perishables the binding cost is **spoilage**. In US shelf-stable
distribution spoilage is near zero, which is why a naive port of the engine
degenerates: overage costs almost nothing, the critical fractile approaches
1, and the optimizer recommends "hold plenty," which any planner already
knows.

The binding costs in US commercial distribution are different, and there are
three of them:

1. **Service penalties.** OTIF and similar regimes convert a fill-rate miss
   into an invoice. Walmart charges 3 percent of cost of goods on
   non-compliant cases against 98 / 90 / 95 percent thresholds.
2. **Working capital.** Thousands of SKUs competing for finite cash and
   finite warehouse slots.
3. **Obsolescence.** Promotional calendars ending, packaging changes, SKU
   rationalization, seasonal items. Soft perishability on a slow clock.

Re-anchor the objective on those three and the optimization problem becomes
non-trivial again.

## The one mathematically interesting change

OTIF is **not a linear underage cost**. It is a threshold penalty: below 95
percent in-full you pay 3 percent of COGS, above it you pay nothing. That is
a step function in the recourse, which turns the second stage into either a
chance-constrained program (hold P(fill >= threshold) above a target) or a
piecewise penalty.

This matters because it changes the shape of the optimal policy. A linear
underage cost produces smooth safety stock. A threshold penalty produces
**cliff-edge behavior**: it is worth a great deal to move from 94 to 96
percent, and almost nothing to move from 96 to 98. An optimizer that
understands the cliff beats a planner using a flat service target, which is
the actual value proposition in this segment.

## Build order

### Phase 1: re-point the diagnostic (weeks, cheap, sellable alone)

The diagnostic needs the least work and carries the wedge. From the same
order, delivery, and inventory tables already ingested, compute:

- OTIF performance by customer and by period, decomposed into on-time
  versus in-full failures
- **Penalty dollars paid or exposed**, which is the headline number that
  replaces waste dollars
- Fill rate by customer and by SKU, with the distance to each penalty
  threshold
- Inventory turns, dead and slow-moving stock, and capital tied up in each
- Stockout margin lost

No optimizer changes at all. A US commercial distributor would engage with
this report today, and it is the same free-backtest motion already used.

### Phase 2: re-cost the objective (moderate)

- Replace the spoilage overage term with carrying cost, meaning capital times
  holding period, plus warehouse opportunity cost, plus an obsolescence
  hazard.
- Replace the linear underage term with a threshold penalty or chance
  constraint reflecting the customer's actual service agreement.
- Repurpose the shelf-life decay machinery for obsolescence: same curve
  shape, far slower clock, driven by promo calendar end dates and
  discontinuation risk rather than temperature.

### Phase 3: constraints that make it genuinely hard (significant)

- **Integer structure.** Case packs, pallet layers, MOQs, and full-truckload
  breakpoints turn the LP into a MIP. HiGHS supports this, but the
  interaction with SAA scenario counts will hurt solve times. Expect to need
  scenario reduction or an LP relaxation with a rounding heuristic.
- **Shared resource constraint.** Working capital and warehouse space across
  thousands of SKUs is a knapsack layered on the newsvendor. This is where
  the real value sits in shelf-stable: not how much of one SKU, but which
  SKUs deserve the cash.

### Phase 4: demand model upgrades

CPG demand is dominated by trade promotions. The existing gradient boosted
quantile model can absorb promo features directly, but the data must come
with them: promotion calendar, price points, competing-SKU cannibalization,
and forward-buy or pantry-loading effects. Croston routing already covers the
long intermittent tail, which CPG has in abundance.

## What carries over untouched

- Supplier fill-rate modeling. Manufacturers allocate during shortages, and
  CPG tracks case fill rate formally, so the empirical Bayes Beta-Binomial
  applies directly and on cleaner data than produce.
- Conformal calibration. Domain agnostic.
- Correlation machinery, repointed from correlated supplier yields to
  correlated demand across locations or accounts. This is the natural fit for
  a franchisor allocating to many franchisees.
- The whole ingestion, validation, and leakage-guard layer.
- The backtest motion and the VSS validation design.

## Who to sell to in the US

The same missing-middle thesis, different vertical: too small for a Blue
Yonder or RELEX implementation, too big for spreadsheets.

- Mid-market food and beverage distributors selling into modern trade
- CPG brands large enough to pay OTIF penalties but too small for enterprise
  planning software
- Franchise supply networks, where a franchisor commits to manufacturers and
  allocates across franchisees, with correlated demand across locations
- Convenience and c-store distributors, high SKU count and high turn
- Specialty and ethnic food distributors, often import-driven, which
  restores the long-lead-time structure

## Sequencing judgment

Phase 1 is genuinely cheap and could run in parallel with the perishable
push, because it reuses the ingestion layer and changes only which metrics
are computed. Phases 2 through 4 are a second product and should not start
before a first real perishable dataset has landed.

The honest risk remains competitive rather than technical: in perishables the
answer to "why has nobody built this" is that the market looked unattractive.
In US commercial distribution, the answer is that they did. Entering means
being the least proven option in a category with reference customers, so the
wedge has to be the penalty-exposure diagnostic, which incumbents bury inside
six-figure implementations, rather than the optimizer itself.

---

# Appendix B: Full Research Audit of the Commercial Goods Pivot

_Added 2026-08-30. This audit contradicts the "missing middle" thesis stated
in Appendix A. That thesis was asserted, not tested. Tested, it fails._

## Finding 1: the mid-market is already served, at low cost

**Netstock** publishes a starting price of **900 dollars per month** and
positions explicitly at "SMB and lower-mid-market distributors and
manufacturers who want to keep their existing ERP." That is precisely the
segment Appendix A described as too small for enterprise vendors and too big
for spreadsheets. It is not a gap. It is a product with published pricing.

Above it sit **Slimstock (Slim4)**, **ToolsGroup**, **RELEX**, **Blue
Yonder**, **o9**, **Kinaxis**, **SAP IBP**, plus newer entrants (Flowlity,
Deposco, Safio). The category is dense at every price point.

## Finding 2: ToolsGroup already ships our stack

ToolsGroup SO99+ is described as: probability-based forecasting that
"identifies a range of outcomes and the probability of each," service-level
driven optimization rather than accuracy-driven, integral modeling of "the
probabilistic (or stochastic) nature of the supply chain across all planning
functions," multi-echelon inventory optimization, and explicitly best in
class for "slow-moving and intermittent demand items."

Published claims: 5 to 10 percentage points forecast accuracy improvement, 3
to 5 points service level increase, 20 to 30 percent inventory reduction.

Point for point that is our probabilistic forecasting, our service floor, our
Croston routing for intermittent series, and our stochastic optimization,
already productized with reference customers.

**Lokad** is the closest philosophical competitor: coined "Quantitative
Supply Chain," has produced quantile forecasts since 2012, full probabilistic
forecasting since 2016, uses stochastic optimization and differentiable
programming, and placed first at SKU level in the M5 forecasting competition
in 2020.

## Finding 3: the penalty diagnostic wedge is also occupied

Appendix A proposed penalty exposure as the wedge. Deduction and chargeback
management is an established category: the chargeback management market was
roughly **2.6 billion dollars in 2025**, projected to about 9.3 billion by
2035 at 13.5 percent CAGR, with iNymbus, HighRadius, Chargebacks911 and
others competing in it.

The underlying pain is real and broad. Walmart charges 3 percent of COGS
against 98 / 90 / 95 percent thresholds. Target charges a 5 percent chargeback
on short or over shipments plus 3 percent for a missing or late ASN under its
2025 Perfect Order Program. Kroger requires 98 percent on-time and 95 percent
case fill with a 3 percent penalty. Costco and Amazon run their own regimes.

Real pain, already served.

## Finding 4: the structural argument, which is decisive

Our genuine differentiation has never been demand forecasting. It is
**two-sided uncertainty**: supplier delivery is itself random, correlated
across suppliers by shared weather, and that correlation materially changes
the optimal commitment. Independent supplier draws erased the value of
stochastic modeling entirely in our own testing.

In commercial goods that second side collapses. **Typical CPG and grocery
fill-rate benchmarks are 98 to 99 percent**, and factory output is largely
uncorrelated across suppliers. Compare that to produce growers delivering
somewhere between 60 and 95 percent of committed volume, correlated by
region and weather.

At 98 to 99 percent supplier reliability there is almost no supply-side
uncertainty left to model. What remains is demand forecasting plus inventory
optimization, which is the single most crowded category in supply chain
software.

**The commercial pivot removes the one thing that makes us different.**

## What the pivot actually does, stated plainly

1. **Destroys the differentiation.** The copula correlation layer, the
   supplier yield model, and the weather work all become near-irrelevant.
   Those are the genuinely novel parts of the system.
2. **Trades an empty market for a full one.** In perishables the answer to
   "why has nobody built this" is that the market looked fragmented and
   unattractive. In commercial goods the answer is that six vendors did, one
   of them for 900 dollars a month.
3. **Strands a large share of the differentiated code.** Copulas, weather
   yield, shelf-life decay, near-expiry ATP, and FSMA-204 traceability are
   all perishable-specific.
4. **Does not solve the actual bottleneck.** The binding constraint is that
   no real operator data has touched the engine. Pivoting changes who we ask,
   not whether we get it.
5. **Raises buyer sophistication.** A CPG planner knows ToolsGroup and RELEX
   and will ask how we differ. Post-pivot there is no strong answer.

## The one crack worth noting

Lokad's own market analysis argues that although vendors now use the words
"probabilistic" and "stochastic," almost none "have rebuilt their stack so
that uncertainty is modeled and carried all the way into automated
decisions." If true, incumbent implementations are shallower than their
marketing.

Two caveats. First, exploiting that means competing directly with Lokad, who
has a decade of head start and an M5 first place. Second, our own OTIF
threshold insight, that the penalty is a cliff rather than a linear cost and
optimal policy should be cliff-aware, is a genuine feature-level idea but not
a company.

## Verdict

**Do not pivot.** The commercial goods market is larger and better funded,
and that is precisely why it is defended. Our advantage exists only where
supply is unreliable and correlated, and commercial goods is defined by
supply being reliable and uncorrelated.

## The constructive reframe

The audit gives a selection rule, not just a prohibition. **Our value scales
with supplier unreliability and its correlation.** Rank any candidate market
by two questions:

1. What fraction of committed volume actually arrives?
2. Do suppliers fail together?

Commercial goods: 98 to 99 percent, uncorrelated. Wrong market.
Produce and perishables: 60 to 95 percent, weather-correlated. Right market.

Adjacent segments worth screening by that rule rather than by intuition:
seafood and shellfish, specialty and small-farm aggregation, imported produce
exposed to origin disruption, and any category where growers or small
producers rather than factories are the supply base.

Retain from Appendix A only the NTDCO recommendation, and only on its stated
grounds: a friendly family-owned distributor is a **data-access opportunity**
that would harden the ingestion and diagnostic layers regardless of vertical.
That reasoning survives this audit because it was never a market argument.

---

# Appendix C: Auditing the Core Thesis Itself

_Added 2026-08-30. Appendix B claimed commercial goods was defended while
perishables was empty. The second half of that claim was never tested. It
does not survive testing either, though it fails less badly._

## The fresh produce landscape, mapped

**Layer 1, grocery retail.** Afresh raised 34 million dollars in April 2026,
runs in over 12,500 departments with 70 percent year-over-year revenue growth
in 2025, and claims 25 percent shrink reduction, 3 percent sales uplift, and
7 percent higher inventory turns. Also Invafresh, Shelf Engine, Freshflow,
Aravita, and RELEX. AI in food retail is projected to grow from 2.7 billion
dollars in 2024 to 13.4 billion by 2030. Crowded and well capitalized.

**Layer 2, produce ERPs serving midstream.** Produce Pro, Famous ERP, Silo,
Aptean, Agriful, iTradeNetwork. Critically, these already claim forecasting.
Famous ERP advertises "demand forecasting to predict consumption patterns,
seasonal fluctuations, and market trends to help optimize sales and purchases
and decrease risk of overstocking or understocking." Produce Pro advertises
forecasting tools that "help buyers anticipate needs and adjust purchasing
decisions based on historical patterns and trends."

**Layer 3, supply disruption prediction.** Helios AI predicts agricultural
supply chain disruptions and helps distributors monitor disruptions and price
shifts ahead of the growing season. That is adjacent to our weather work.

**Layer 4, commercial de-risking.** ProducePay has raised 38 million dollars,
supported over 4.5 billion dollars in transactions, and sells a "Predictable
Commerce Platform" offering growers pre-season capital and reliable offtake
while offering retailers assured 52-week supply, predictable pricing, and
lower rejection rates. A pilot reported under 1 percent rejection rates on
table grapes, an 80 percent improvement on standard sourcing.

Industry data also shows the pain is recognized: a ProducePay survey found 38
percent of growers rank supply chain disruption as their top concern, and 52
percent of supply chain respondents cite rapid demand shifts as the biggest
threat.

## What this does to our positioning

The claim "nobody serves midstream perishable operators" is false. The
segment is served by produce ERPs, the retail side is served aggressively,
supply disruption has a dedicated player, and supply predictability has a
well funded commercial alternative.

**What survives is narrower and purely methodological.** No vendor found
appears to: treat grower delivery as a calibrated probability distribution
rather than a point estimate, model correlation between growers so that
shared weather exposure is priced, and feed both into a two stage stochastic
commitment optimization with honest out of sample validation.

The competitors forecast, alert, or contract. None of them appear to optimize
the commitment decision under two sided uncertainty. That is a real gap, but
it is a gap in **method**, not in market coverage.

## Applying our own consistency test

In Appendix B the OTIF cliff insight was dismissed as "a genuine feature-level
idea but not a company." The same test must be applied here.

Is "we do stochastic optimization where incumbents do deterministic
forecasting" enough to build a company on? That is precisely the argument
Lokad has made for over a decade. Lokad is credible, technically excellent,
first at SKU level in M5, and still a specialist rather than a category
winner. Being methodologically right is not the same as winning a market.

This does not kill the thesis, but it changes what must be true for it to
work. The differentiation has to show up as a number an operator cares about,
not as a better formulation.

## Two specific threats

1. **Afresh is the real competitive risk.** Produce native, well funded,
   growing fast, and explicitly expanding into "distribution center buying
   and supply chain optimization." Today they serve grocery retailers and
   their DCs, not independent midstream distributors. If they extend outward,
   they arrive with far more capital and existing produce credibility.
2. **ProducePay is a substitute, not a competitor.** They remove supply
   uncertainty commercially through contracts and financing rather than
   optimizing under it. If a buyer has guaranteed offtake and assured supply,
   the uncertainty our engine prices is contractually reduced. That is
   arguably a cleaner solution to the same pain, and it is funded.

## What is now the single most valuable thing to learn

Whether produce ERP "forecasting" is genuinely decision support or an
exponential smoothing module driving reorder points. Brochure language
strongly suggests the latter, but that is an assumption and this document has
now been wrong twice by assuming.

**That question is answerable in one operator conversation.** It should be
asked in the first discovery call and it should be treated as the gate: if
operators say their existing system already tells them what to commit, the
wedge is much weaker than believed. If they say the system records but does
not recommend, the wedge holds.

## Revised verdict

Fresh produce midstream remains the better market than commercial goods,
because supply is genuinely unreliable and correlated there and that is where
our method has an edge. But it is a contested market, not an empty one, and
the pitch must change from "nobody does this" to something specific,
testable, and expressed in operator dollars.

The conclusion is the same as everywhere else in this document: the binding
constraint is not market selection. It is that no real operator data has
touched the engine, and every strategic question here resolves the moment it
does.
