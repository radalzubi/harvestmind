# P3 supplier / sourcing portfolio: architecture

## One decision, one more declared layer

The frozen engine already chooses among approved sources jointly: one purchase column per source and
period, capacity, MOQ, packs, supplier orders across SKUs, payment terms through the cash balance,
shared resources, per-source fill and lead uncertainty, and shared-domain supply shocks (audit:
`P3_EXISTING_CAPABILITIES.md`). P3 does not add an optimizer, a candidate class, a supplier score or a
diversification rule. It adds what the operator knows and the engine could not:

```
Request.sourcing : SourcingPortfolio | None          (None = the frozen request; no hook is reached)
  risk_groups      SourceRiskGroup[]      sources that fail together: kind, members, correlation, provenance
  share_constraints SourceShareConstraint[] declared min / max share, committed units; horizon or period scope
  switching_costs  SourceSwitchingCost[]  declared cost of starting a source outside the incumbent mix
  incumbent_shares IncumbentSourceShare[] the operator's current mix per SKU and destination
  prune_zero_capability                  exact pruning switch (equivalence runs)
```

`zaad.sourcing.contracts.resolve(req)` returns a read-only `Sourcing` view (groups per source, shares per
pair, switching costs, the incumbent mix and the incumbent source set) or None.

## Ownership

| owner | decides | P3 change |
|---|---|---|
| P0 protection / recovery | protection, disruption, recovery | none (planner ownership routing untouched; invariant 31) |
| P1 purchasing economics | whether, when, how much in total | none; the total commitment is still the joint solve's (invariant 32) |
| P2 network | placement, transfers, pooling | none (invariant 33); the sourcing block never carries a transfer |
| sector physics | feasibility and inventory interpretation | none (invariant 34) |
| **P3 sourcing** | the split of the commitment across approved sources | declared constraints and risk on the same joint solve; the report's decomposition |

P1 and P3 are solved jointly (source-specific MOQ, MOV, tiers, capacity and terms change the total's
economics); the report keeps them interpretable: `sourcing.pairs[].total_committed_*` is the P1 total,
`options[]` its P3 split.

## Hooks (every one behind `sourcing is not None`)

* **Model** (`zaad/full/model.py`). (1) Zero-capability pruning, exact: a source-period whose purchase
  column is bounded at zero (unapproved, blocked, expired quote, zero capacity, physics-ineligible,
  outside a cadence) gets no pack, activation or quote-group binary; the column stays so every
  consumer that indexes it is unchanged. (2) Share rows: for each declared constraint, linear rows on
  the pair's purchase columns (`x_s >= min * sum x`, `x_s <= max * sum x`, `sum_t x_s >= committed`),
  over the horizon or per period; skipped when the plan is `fixed` (an evaluated incumbent is not
  re-chosen). (3) Switching: one first-stage binary per declared source outside the incumbent set,
  `sum_t x_s <= cap * switch`, the cost expensed at period 0 in every world. No source x world binary,
  no source x period binary beyond the frozen ones. Commitments stay scenario-invariant by
  construction (invariants 11, 12).
* **Worlds** (`zaad/full/worlds.py`, `zaad/sourcing/correlation.py`). The frozen shock of a source is
  a standard normal built from its shared failure domains. A member of groups g with correlations
  rho_g gets `sqrt(1 - sum rho_g) * z_frozen + sum sqrt(rho_g) * G_g`; the group factors come from a
  separate generator (seed plus a P3 salt), so the frozen stream is consumed exactly as before and
  every marginal is unchanged (invariants 13-15). A source in no group keeps its frozen draw bit for
  bit; a request with no groups draws exactly the frozen worlds.
* **Settlement** (`zaad/full/settlement.py`). The declared switching cost enters the ledger once per
  newly used source (`ledger["switching"]`, ORDERING component), so the selector, materiality and
  the benchmark see the same cost the model charged (invariants 18, 26).
* **Rule projections** (`zaad/full/policies.py`, `zaad/meio/baselines.py`, `zaad/sourcing/incumbent.py`).
  The declared incumbent mix splits the rule's period quantity across its sources (lot-fitted,
  capped by each source; the mix's combined capacity caps the total); a projected line never exceeds
  the room left on a resource shared across SKUs (`fit_resources`). Without declared shares the
  frozen single line stands.
* **Replay** (`zaad/full/replay.py`). An executed switch joins the operator's mix for the next
  review, so a declared switching cost is paid once, when the switch is executed.
* **Report** (`zaad/sourcing/explain.py`, `report["sourcing"]`). Per SKU and destination: total
  committed (period 0 and plan), each option's quantity and share, incumbent share, declared share,
  expected receipt period and fill, capacity and whether it binds, MOQ and packs, landed economics
  (price, freight, handling, financing fee, fixed fee, payment terms and a report-only timing value),
  reliability provenance (observed / declared, records, fill and late probability), risk groups with
  provenance and a weak-evidence flag, share constraints, switching cost status, eligibility reason,
  the recommendation (NO_ORDER / RETAIN_INCUMBENT_MIX / COMMIT_AS_INCUMBENT_MIX / CHANGE_SOURCE_MIX)
  and operator-language explanations. `approval_required = true`, `executable_purchase_order = false`.

## Economics and reconciliation

Every source economic component is the frozen one: unit price x FX, freight, handling, financing fee,
fixed order fee, supplier-order MOV / fixed cost / receiving / tiers / pallets, payment timing through
the cash balance and `cost_of_capital_per_period`, holding, shortage, expiry, continuation. P3 adds one
component, the declared switching cost, in the objective and in the ledger. Nothing is counted twice:
invariant 10 (payment terms priced once, through the cash balance) and invariant 26 (`economics.reconciled`
with no unmapped ledger key).

## Baselines and the benchmark

`scripts/p3_benchmark.py` replays every fixture with the P2 runner under: the incumbent mix
(`network:rop` with the declared shares), the cheapest landed single source (the same rule without a mix
or share limit, settled on the fixture's own request so a declared switching cost applies), ZAAD
restricted to each single supplier, and ZAAD P3. The economic gate uses `cost_p3`: the P2 continuation
rule with residual stock valued at the cheapest approved source's landed cost per received unit and no
policy-specific premium (the P2 basis credited a dear-freight source's residual at its own dearer
cost; both are recorded).

## Workspace, API, migration 018

`stg_fmcg_sources` (SKU x supplier: approval, compliance, cost, freight, handling, fixed cost, MOQ, case,
capacity, promised lead, age at receipt, shares, committed units, incumbent share, switching cost,
provenance) and four nullable supplier columns (`risk_group`, `risk_group_kind`, `risk_group_provenance`,
`switching_cost`). `build_request(..., sourcing=True)` attaches every declared alternate as a source
(`src_<sku>__<supplier>`) with the supplier's fitted fill and lead, and the block from the declared
cells; a vault without the table builds the frozen request with a warning; without the flag nothing
changes. `sourcing` query parameter on the workspace endpoints; declared inconsistencies answer 422
`sourcing_invalid`; interactive bounds (`INTERACTIVE_LIMITS`: 8 sources per pair, 50 groups, 200 share
rows, 100 switching costs, 200 incumbent rows) answer 413 before any model is built.

## Not built (by design)

Supplier scores; undeclared concentration limits; correlation inferred from names; general dominance
pruning (capacities are additive); scenario-contingent switching (P4); model-risk on the supply
distributions (P6); an upload path for `stg_fmcg_sources` (the table is filled by the operator's own
load; the intake router is unchanged).
