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

## Review corrections (second pass)

- **Supplier-exact truth.** `build_truth` matched historical supply observations by SKU alone, so two suppliers
  of one SKU pooled their lead times, fills and MEASURED cells. It now identifies every received order with the
  comparator's business key (sku, supplier[, destination]); a MEASURED cell is the exact source's own order, an
  order with no supplier identity measures nothing, and a source with no own observation falls back to the
  existing INFERRED / SIMULATED / ASSUMED treatment. Tests: SKU X with supplier A (100 units, 7 days, 100 %) and
  supplier B (40 units, 28 days, 50 %) keep their own truth in both physical row orders; B with no deliveries is
  ASSUMED, never measured by A.
- **Incumbent order sets.** A bare `Request.incumbent_orders` is `INCUMBENT_ORDER_SET` / `ORIGIN_NOT_ESTABLISHED`
  / `NOT_AVAILABLE`, "the incumbent order set in the request"; operator provenance needs an
  `incumbent_orders_source` the caller establishes (H3b). `evidence_label = OPERATOR-SHADOW` is not one.
- **Decision-row fidelity.** `actual_identity_fidelity` (can the recorded action be mapped to this source?) and
  `actual_evaluation_fidelity` (was it changed before settlement?) are separate; the overall `actual_fidelity`
  is INCOMPLETE whenever identity is, TRANSFORMED when only the quantity changed, EXACT only when both hold.
  A sole-source fallback with no rounding stays INCOMPLETE.
- **Transformation unit.** Conformance works on source-review action groups, so the coverage reports
  `transformed_action_groups` with the unit stated; no PO-line count is invented. One changed group still
  denies the exact whole-scope claim.
- **Customer-facing surfaces.** The diagnostic report component, the orders detail page, the diagnostics,
  decisions, home and insights pages, the plan-state and decision-detail components, the plain-language reason
  terms and the PDF now take their labels from the backend (`comparator_label`, `reference_label`,
  `policy_benchmark.current_label`, `comparison.columns`, `decision_reference`) or say "ZAAD's decision
  reference"; decision-level detail shows recorded quantity and model-evaluated quantity separately with the
  identity and transformation notes. Marketing copy on the public site (how-it-works, i18n) describes a
  hypothetical distributor and was left alone.

## Review corrections (final pass)

- **PO-line identity in the truth.** `build_truth` aggregated receipts by `po_id` and keyed its exact-source lookup
  by `po_id`, so two SKU lines under one PO id pooled their receipts (100/100 after 7 days for X and 25/50 after 28
  days for Y became 125/150 for both). Receipts are now matched to a purchase-order LINE (po_id, sku); a receipt
  without a SKU is placed only on a single-line PO; a PO whose lines repeat a SKU, or a receipt that cannot be
  placed, is ambiguous and is not MEASURED. Nothing is summed across lines. Tests: two lines on one PO in both
  physical orders keep fill 1.0 / 0.5 and arrival 1 / 4 periods; receipts without SKU on a multi-line PO measure
  nothing; a duplicated line is ambiguous for that line only; two suppliers with distinct PO ids unchanged.
- **Zero rows are not exact observations.** `_decision_rows` marked a source row EXACT when both the observed and
  the evaluated quantity were zero, even if a recorded order of that SKU in that period mapped to no source. Rows now
  distinguish an identified action (EXACT / TRANSFORMED), incomplete identity (INCOMPLETE, including when an
  unidentified line of the SKU falls in the period, with `actual_unidentified_lines` and `actual_unidentified_qty`
  exposing it without inventing a source) and the absence of any recorded action (`NO_IDENTIFIED_ACTION`).
  Comparator permissions stay conservative: any unmapped line makes the comparator INCOMPLETE.
- **Remaining operator attribution.** The chart caption "your orders − ZAAD" (frontend and PDF), the benchmark
  question "than your own?", the holdout statement "your existing purchasing rule", the conformance note "your own
  staggered orders" and the "End stock (you / ZAAD)" header are gone. The replay section emits `periods.caption`
  from the comparator label; the benchmark question and statements use `reference_label`; the frontend derives every
  header from one helper (`web/src/lib/diagnostic/labels.ts`) that shortens to "recorded historical orders" only
  for an EXACT comparator and otherwise says "historical-action path"; a report without the contract reads
  "comparator fidelity not established". Tested for EXACT, TRANSFORMED, INCOMPLETE and legacy reports and for
  inferred versus operator-declared rules, in Python and in the frontend.

## Unresolved comparator-data limitations

- The planner cannot know from the Request alone whether a rule was inferred or declared; the planner's
  section says `provenance = RULE_IN_REQUEST` with a note, and the synchronous plan route refines it from the
  build. Asynchronous jobs carry the planner's section only.
- The workspace adapter derives shipment-history and pipeline identities from the PO id alone, so a vault whose
  multi-line PO is still open at the origin cannot build a Request ("duplicate entity ID"). Pre-existing, outside
  H3a (H1 identity area); the truth test builds its Request from an equivalent unique-id vault.
- Exact historical comparison needs every recorded line in scope to be identified and untransformed; on
  operator data with pack-multiple rounding, capped quantities or missing supplier ids the honest result is
  MODEL_COMPARISON, not an operator claim.
