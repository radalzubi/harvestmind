# HARDENING V1, H3a: comparator provenance and claim gating

Branch `hardening/h3a-comparator-provenance` on main `7efaa0b` (H0, H1a, H1b, H1c, H2 merged). One purpose:
every comparator and every relative-performance statement says exactly what it is comparing against.
Nothing here is customer evidence; the vaults are the SYNTHETIC sample and the unit-test fixture.

## Reproduced before the change (sample `A_stable` seed 7, origin 2025-09-01)

| case | before | after |
|---|---|---|
| B supplier identity | `actual_orders_by_review` mapped every PO of a SKU by SKU alone, to whichever source was listed last: with an alternate source declared, the primary supplier's own 1,896 units and the 103-unit alternate PO were all booked on `src_SKU-0001__SUP-ALT` | lines map by exact business key (sku, supplier[, destination]): the alternate PO lands on `src_SKU-0001__SUP-ALT` (EXACT), the primary supplier's orders stay on `src_SKU-0001` (EXACT); a supplier the request does not source from is INCOMPLETE and unmapped, never re-assigned |
| A conformance | a recorded 103 was settled as 96 (declared multiple 24) and the leg was still called `actual` / "the operator's actual orders" | the leg keeps `actual_observed_qty` = 103 and `actual_evaluated_qty` = 96 per decision row; the comparator is TRANSFORMED and the report says "a model-adjusted version of the recorded historical orders" |
| C reconstructed-rule wording | the policy benchmark and the diagnostic rendered an INFERRED_FROM_HISTORY rule as "your current policy", "Keep your current purchasing rule", "your rule" | the rendered report names it "the reconstructed historical rule" everywhere (`_reference_label`, applied to the whole report); a CUSTOMER_PROVIDED rule is "your operator-declared purchasing rule" |
| D relative claim | "ZAAD's adaptive decisions would have cost 6.1% less than your actual orders over the window" | "In this historical counterfactual replay ... ZAAD's modelled path cost 6.1% less than the path of the recorded historical orders over the evaluated window ... nothing here is a realized benefit" (exact comparator); the transformed / incomplete / legacy cases add the qualifier and lose the permission |
| E live plan | status RETAIN_INCUMBENT, `selected_policy = operator_rule:replace_sold`, no comparator metadata, build says INFERRED_FROM_HISTORY | `report["comparison"]`: mode PLAN_MODE, readiness READY, claim MODEL_COMPARISON, `can_claim_against_operator = false`; `decision_reference` = RECONSTRUCTED_POLICY / RECONSTRUCTED "the reconstructed historical rule"; `shadow.readiness = NOT_READY_FOR_THIS_DECISION` |
| F proposal evaluation | left column "Your current plan" from `baseline.incumbent` | left column labelled by the baseline's decision reference ("Reconstructed policy baseline" / "Operator-declared rule baseline" / "Model baseline"; "Decision reference (provenance not recorded)" for older reports) with `comparison.claim_class = MODEL_COMPARISON` |

## Contract (`zaad/full/comparator.py`)

- Comparator types: ACTUAL_HISTORICAL_ACTION, ACTUAL_OPERATOR_PLAN (reserved for H3b, never fabricated),
  RECONSTRUCTED_POLICY, SYSTEM_BASELINE, NONE.
- Fidelity: EXACT, DECLARED, RECONSTRUCTED, TRANSFORMED, INCOMPLETE, NOT_AVAILABLE.
- Decision reference (internal) vs evidence comparator (external): the planner keeps `incumbent_rule`,
  `incumbent_orders`, `baseline_plan` and its gates untouched; `report["decision_reference"]` and
  `report["comparison"]` sit above them.
- PLAN_MODE: a recommendation with no captured operator plan; MODEL_COMPARISON against the decision reference
  is allowed, claims against the operator are not; an absent comparator is not a planning failure
  (ABSTAIN → CANNOT_COMPARE, can_recommend false).
- SHADOW_COMPARISON_MODE: defined, requires ACTUAL_OPERATOR_PLAN; `shadow_readiness(None)` is
  NOT_READY_FOR_THIS_DECISION; evaluation raises NotImplementedError (H3b).
- Historical comparison: ACTUAL_HISTORICAL_ACTION only when every comparator line in scope is EXACT and
  untransformed → HISTORICAL_COUNTERFACTUAL_COMPARISON with `can_claim_historical_counterfactual_difference`;
  any TRANSFORMED or INCOMPLETE line → MODEL_COMPARISON, no claim against the operator; realized value never.
- Coverage: lines observed / exact / incomplete / unmapped, exact quantity share, exact value share (only when
  every line has a unit cost), lines out of scope (SKUs the replay does not plan are not comparator lines).
- Claim permissions: can_recommend, can_compare, can_claim_against_operator,
  can_claim_historical_counterfactual_difference, can_claim_shadow_difference, can_claim_realized_value
  (the last is the Operating Product V2 outcome contract, `realized_value`, unchanged).
- Readiness: READY, CONDITIONAL, NOT_READY_FOR_THIS_DECISION, CANNOT_COMPARE; decision readiness and
  comparison readiness are separate.

## Known-origin 2025-09-01 (E_mixed_portfolio): unchanged

Pipeline 3000 / 3888 / 72; opening stock 5454 / 2208 / 204 (READY_DIRECT, effective 2025-09-01T00:00,
source_known_at 2025-08-31T23:59:59). H3a adds report metadata only; Request fingerprints and optimizer
decisions are unchanged (H0 causal suite, H1c canonical order, frozen regression).

## Unresolved comparator-data limitations

- The planner cannot know from the Request alone whether a rule was inferred or declared; the planner's
  section says `provenance = RULE_IN_REQUEST` with a note, and the synchronous plan route refines it from the
  build. Asynchronous jobs carry the planner's section only.
- The frontend still hard-codes "Your current plan" in two places (orders detail, diagnostics page) and
  "Your actual orders" in the replay table; the backend now supplies `columns[].label` and
  `comparator_label`, but the frontend was out of scope for H3a.
- Exact historical comparison needs every recorded line in scope to be identified and untransformed; on
  operator data with pack-multiple rounding, capped quantities or missing supplier ids the honest result is
  MODEL_COMPARISON, not an operator claim.
