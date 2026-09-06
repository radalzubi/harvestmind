# Zaad: read-only to approved-live pilot

This is an operational acceptance and measurement plan, not a signed contract,
legal opinion or customer-validation claim. No operator data or live purchase
authority is implied by this document. Counsel and the operator must approve
the actual agreement, data rights and relevant compliance obligations.

## Buyer and deliberately narrow scope

Initial screening hypothesis: a stock-owning, shelf-stable importer/distributor
with an existing ERP, material inventory investment, buyer/rule-driven
replenishment, usable PO-to-receipt history, actionable approved supplier/route
alternatives and one accountable purchasing/inventory owner. Roughly
$20M–$250M revenue is a screening band, **not** a sufficient qualification.

Begin with one operator, a bounded SKU group and one or a few explicitly
modeled locations. The operator signs off the incumbent rule, source list,
service metric, cash/space limits and decision authority. Do not include fresh,
regulated or cold-chain products unless their age, handling and legal
constraints are actually supported end to end. Country choice follows data
access and an economic decision opportunity, not a presumed generic MENA gap.
See [competitive baseline](COMPETITIVE_BASELINE.md).

## Stage 0: signed evidence and authority boundary

Before intake, agree:

- Named sponsor, inventory owner, finance reviewer and approval operator.
- Exact tenant/site/SKU scope, data period and source systems; raw-data owner,
  access permissions, retention/deletion, vendor/feed rights and access audit.
- Read-only credentials initially; no PO, cancellation, transfer or booking
  writes. An optimization recommendation is not supplier acceptance.
- A unit-fill definition with demand denominator, due-time convention,
  lost-sales/backlog treatment, service tolerance and independent contractual
  requirements. Line fill and OTIF require separate event data.
- Incumbent behavior frozen from actual rules and buyer interviews, including
  fill haircuts, open-PO treatment, packs, capacity, expedites and overrides.
- Monetary ledger, currency dates, agreed carrying components, residual value,
  route premiums, change/cancellation fees and excluded speculative costs.
- Named authority for product/supplier/route approval. Unknown/expired legal,
  capacity, carrier or cold-chain status blocks the action, not a warning-only
  recommendation.
- Pre-agreed success, pause and failure criteria; adverse cells remain visible.

## Stage 1: read-only diagnostic and reconciliation

Ingest timestamped item/location data, on-hand/reservations, PO versions,
confirmed schedules, receipts/accepted quantities, demand and costs. Reconcile
stock movements and pending quantities to an operator-approved snapshot.
Distinguish source-event time, when it became available to Zaad and ingestion
time. Preserve immutable permitted raw data and transformation versions.

Deliver an auditable discrepancy list and baseline inventory/service/loss
ledger. Require the operator to resolve material unit, duplicate-PO, future
receipt, missing-demand or currency inconsistencies. Missing supplier history
gets explicit pooling/uncertainty or abstention, never invented confidence.
Do not sell every identified shortage/writeoff as recoverable savings.

Exit gate: reconciliation accepted, minimum causal history documented, and at
least one actionable decision with a plausible measurable economic benefit.
If no such decision exists, stop the pilot rather than build unused feeds.

## Stage 2: historical causal replay

Freeze development/evaluation periods and all policy/hyperparameter choices
before final evaluation. Use the operator's incumbent plus competent
fill-aware base-stock, constrained deterministic, service-target and
risk-aware candidates where implemented. Every policy receives identical
physical supply, capacities, information and monetary settlement, but carries
its own resulting inventory/pipeline from one review to the next.

Evaluate normal overstocked/understocked/balanced cases and relevant
disruption/false-alarm/late-signal/recovery cases. Preserve every seed, rejected
candidate, fallback, infeasible action and service breach. Break out incremental
value of operator history, port/physical evidence, news and other feeds;
unavailable licensed feeds are not credited as active evidence.

Historical current-vintage aggregates are not automatically historical
as-of observations. When publication vintage/latency is unknown, label the
replay as retrospective and do not claim an early-warning benefit. A real
port series with synthetic inventory/economics is **real-signal / synthetic-
operator**, not customer validation.

Exit gate: a recommendation class demonstrates interpretable economic value
at agreed service/downside limits on untouched periods. A selector that
always abstains may be safe but has not demonstrated a purchasable benefit.

## Stage 3: prospective shadow mode

At each agreed daily/weekly review, seal the as-of input snapshot and append:

1. What the incumbent actually ordered/rescheduled and when it became known.
2. Zaad's proposed new order, source/route split, defer/expedite or no-change.
3. Feasibility checks, current quote/approval status, assumptions and sources.
4. Expected unit fill, cash tied up, cost tradeoff, uncertainty and recovery
   condition; no false calibrated probability precision.
5. Human review: accept hypothetically, reject, override and why.
6. Subsequent observed demand/receipts/costs, without rewriting the original
   forecast or leaking them into that decision.

The operator continues its own process. A shadow counterfactual order does
not have an observed supplier response: extrapolating actual fills to an
unplaced larger order is a modeling assumption, especially near capacity.
Separate observed outcomes from simulated counterfactual outcomes and log
unverifiable alternate-route availability. Shadow mode can assess data,
workflow and decision plausibility; it cannot alone establish causal realized
savings for actions never taken.

Stage duration should cover several review/lead-time cycles and a meaningful
variety of demand states. Do not promise proof from an arbitrary two weeks
when the supplier lead time is six weeks. Rare-event protection may remain
stress-tested, not prospectively verified.

## Stage 4: limited, explicitly approved live use

Only after engineering, evidence and contractual gates pass: allow a small
pre-agreed SKU/source group and capped cash/quantity deviations. Keep all
writes human-approved, scoped, idempotent and auditable. No automatically
canceling firm orders or booking transport. Record vendor acceptance and
actual execution separately from approval. Keep the incumbent fallback and
a pause switch available to the operator.

Where practical, pre-specify a randomized or staggered SKU/location rollout
with contamination controls; shared capacity and common suppliers may prevent
independent randomization. Otherwise use a documented comparison design and
label attribution uncertainty. Do not present observational before/after
improvements as the model's causal effect without the assumptions.

## Acceptance scorecard

Threshold values are signed off before measurement; these are required
dimensions, not fabricated commercial performance guarantees.

| Dimension | Evidence | Pass/pause logic |
|---|---|---|
| Inventory/service | Average/peak inventory value and unit fill at agreed target | No stock saving purchased through an unapproved service cut |
| Recurring economics | Avoidable holding, shortage and expedite net of incremental costs | Finance-approved positive attributable benefit, with range and downside |
| Capital | Inventory release and temporary protection separately | Never book a recurring benefit equal to released principal |
| Resilience | Risk-aware minus same-policy risk-blind result | Positive net value after false alarms, premium and recovery; no credit merely for detecting an event |
| False alarms | Protection units, carry, premiums and expiry when supply stays normal | Pre-agreed acceptable false-positive cost; stale/unrelated stories cannot trigger action |
| Recovery | Peak crisis inventory, time back to approved band, post-event excess and carry | Avoid renewed shortage; do not require disposal to make stock look lean |
| Downside | Service breaches, worst-fold regret, tails, infeasible/failed recommendations | Stop unsafe classes; retain failures in reporting |
| Workflow | Recommendation acceptance, override reasons, planner time, data exceptions | Operator can execute and explain actions without excessive support burden |
| Safety | Data causality, tenant isolation, legal/availability gates, approvals | Any material breach pauses live recommendations |

Report service N/A for zero demand, probabilities as uncalibrated where
appropriate, and price/availability status explicitly. Criticality policies
must be approved; numerical margin alone cannot override a contractual
minimum or customer allocation commitment.

## Commercial measurement and fee definition

Keep these accounts separate:

- **One-time capital release:** reduced owned inventory investment net of
  disposal, transfers and changed unpaid liabilities. Not recurring profit.
- **Recurring benefit:** attributable net reduction in carrying, shortage,
  expedite and operating costs. Annualize only a representative period with
  seasonality and uncertainty disclosed.
- **Temporary resilience investment:** extra stock/pipeline/cash during a
  measured episode, including unwind cost.
- **Modeled protection:** expected/tail loss avoided; not realized savings
  merely because a scenario model predicts it.

A savings-share contract must specify the counterfactual, eligible line
items, measurement windows, attribution adjustment, dispute/reconciliation
process and treatment of negative periods. If Zaad takes fraction `s` of
verified recurring net benefit `B`, fee is `s × B`; customer keeps
`(1-s) × B` before its remaining implementation costs. That identity is not a
forecast of `B`. Do not charge repeatedly on the same released principal or
count both missed margin and the same lost sales revenue. Any subscription
minimum or pilot fee is agreed separately; it must not be implied to be
self-funding before evidence exists.

## Explicit no-go conditions

No pilot expansion when the normal engine loses to the competent incumbent,
the external signal adds no measurable decision value, route changes are
unavailable before the action deadline, or data/approval burden exceeds the
benefit. Continue a narrower diagnostic-only service only if the operator
values and pays for that actual output. Do not market autonomous or
Oracle-beating performance from synthetic prototype evidence.
