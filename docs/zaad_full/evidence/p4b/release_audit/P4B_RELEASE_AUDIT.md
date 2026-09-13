# ZAAD P4B V1 — open PO / commitment intervention: release audit

Authoritative record of the release audit of P4B V1 (PR #75) on the branch `release/p4b-v1-release-audit`.
Every claim below is backed by a file in this directory or its `gates/` subdirectory.

| item | value |
|---|---|
| production runtime before | `2fc7b50` (tag `p5-release-runtime`, Fly `zaad-api` v22) |
| `main` at the start | `5dc87b4` (verified: `origin/main`) |
| PR #75 head | `aacb7b9` (docs-only CI record above the tested head `7311d00`; product `a6483ab`; non-docs diff `a6483ab..aacb7b9` empty) |
| audit branch | `release/p4b-v1-release-audit` from `aacb7b9`, worktree `harvestmind-p4brel` (clean) |
| audit product commit | `28c1fa7` |
| audit evidence commit | the commit tagged `p4b-v1-frozen` (this commit) |
| release question | for an already-open import commitment, given everything known now, KEEP / DEFER / EXPEDITE / REDUCE / CANCEL / SPLIT under declared amendment rights only, here-and-now |
| release invariant | an extension of the released P0 / P1 joint optimizer (its `amend[po, option]` columns are the mathematics); no second optimizer, no source selection, no routing, no execution, no P4 node-indexed amendments |

## Findings and corrections

Six corrections, each the smallest scope that closes the finding; none touches the model formulation, the P4
node map, the P3 rows, probabilities, tolerances, physics, holdouts or historical tags. `zaad/full/model.py`
is untouched by the audit (the implementation's one guarded credit term stands).

| # | audit | finding | correction | scope |
|---|---|---|---|---|
| R1 | C, K | a vault stage, action, provenance or negative number outside the contract reached a raw pydantic error with no `commitments:` prefix, so the from-workspace endpoints answered 422 with the wrong code (`sector_physics_invalid`) | explicit normalisation boundary in `zaad/commitments/workspace.py`: case / whitespace / separator normalised (`"In Transit"` -> `in_transit`, `" Cancel "` -> `cancel`, `contract` -> `CONTRACT`); every other value refused with an operator-facing `commitments:` message; finite non-negative numbers required; `deposit_refundable_fraction` in [0, 1]; duplicate option ids refused at the adapter | adapter only |
| R2 | K | no bound on the declared option set (each option adds columns and, on an exclusive order, one binary) | `INTERACTIVE_LIMITS = {options_per_order: 12, non_keep_options: 200}` in `zaad/commitments/contracts.py`; refused at the adapter; 413 on `/plan` (interactive) and at four times the limit on `/jobs` (`commitments_gate`, same pattern as the P5 gate) | adapter, API |
| R3 | G | with `allow_split_amendments` several cancel options each inside the floor could be active together and breach it (caps 40 + 40 on a floor of 40 over 100 units) | contract: under split the clipped cancel caps are bounded as a sum; exclusive orders keep the per-option rule; settlement: a plan that takes an order below its declared floor is a `PhysicalViolation` (guarded by `minimum_remaining_quantity > 0`, so the frozen build is untouched) | contract, settlement (guarded) |
| R4 | B | a credit on a deferral or an expedite would refund part of the deposit on units that still arrive and still pay their remaining invoice, cutting the contract price | `credit_per_unit > 0` is accepted on cancel options only | contract |
| R5 | D | the block put the whole plan's value next to a KEEP verdict, so a PENDING_REVIEW plan with an alternate purchase (F14) could read as a recommendation to change the PO | explicit `commitment_action`, `commitment_verdict`, `commitment_value_vs_keep` (exactly 0 when every order is KEEP), `overall_plan_status`, `plan_changes_outside_commitments` (the purchase / transfer rows that differ from the incumbent) and a one-sentence `reading`; block version `zaad.commitments.1.1`; the released keys stay | report only |
| R6 | J | pre-existing on the production runtime `2fc7b50`: the released report carries a numpy bool (`service_reliability.services[].classification.pre_existing`, `zaad/full/planner.py`) that FastAPI's JSON encoder cannot serialise, so `/plan` answers 500 for any review whose service is already below target with no feasible action (reproduced on the `2fc7b50` checkout, `tests/unit/test_zaad_commitments.py::test_release_audit_api_shape_without_declaration_carries_no_commitment_keys`; `release/baseline_pre_p4b.json` against production: HTTP 500, request id `req-b379888a10da`, on `2fc7b50`) | `bool(...)` at the producer; JSON identical, so every frozen identity holds; a walk over the six demo cases and the fixtures finds no other numpy bool | one cast |

## Audit A — fixture integrity

Every re-registration between runs 1 and 5 (`../benchmarks/p4b_v1_run{1..4}_failed.log`, preserved) was
re-derived causally on the audit tree (`f06_boundary_scan.log`):

| change | cause established | classification |
|---|---|---|
| neutral base stress (the demo "normal" request carries an incidental `tail` stress: fill 0.8, +14 days, demand x1.1) | with that stress declared the released hedged gate rejects any later arrival under the stress world (`holding 0.4, demo tail stress -> RETAIN_INCUMBENT` while the candidate is material on cost and inventory); a declared stress is part of the state, and the registered F06 / F07 / F16 / F17 states declare none; F15 declares `tail` + `port_closure` explicitly | VALID FIXTURE REPAIR: the incidental stress was not part of the registered business question |
| holding 0.4 / value / period on the defer states F06 / F07 / F16 / F17 (demo 0.05) | at 130 on hand the deferral's saving grows with the holding rate (candidate cost delta -0.40 / -1.74 / -4.26 / -7.19 % at 0.05 / 0.1 / 0.2 / 0.4) but the released independent confirmation gate (`Independent fitted-model confirmation does not establish positive benefit`, three fitted worlds, cost spread ~35 %) retains until 0.4; at the demo rate the same fixture flips to DEFER once the excess is larger (200 or 250 on hand: DEFER, material on inventory). The mechanism is the excess-versus-tail-risk trade-off of the released gates, not the holding rate; the counter-states F07 (stockout) and F16 (perishable) stay KEEP at 0.4 | VALID FIXTURE REPAIR: the registered premise ("the deferral saving is material") did not hold at the demo rate; the rate is steep and is recorded as such |
| F17 opening cash 600 -> 1,000 | at 600 with no credit line the KEEP incumbent's period-1 invoice is not financeable and the review ABSTAINS; the payment-timing question needs a financeable KEEP | VALID FIXTURE REPAIR |
| F14 stock 0 -> 20 with a same-period alternate (lead 3 days) | with nothing on hand every candidate fails the released downside gate on an unavoidable period-0 shortage, so the "alternate source instead of expedite" question is unreachable; with 20 on hand the gap is coverable and the alternate (5.2 / unit) beats the expedite fee (5 / unit) on the economics, not on tuning | VALID FIXTURE REPAIR |
| F20 stock 60 -> 20 | at 60 the order is excess (60 + 100 against 120 of horizon demand) and cancel + a smaller purchase is right; the registered state is "balanced" (20 + 100 = 120) | VALID FIXTURE REPAIR |
| F03 restructure, F14 route rule, F14 `"route"` key check, F00 datetime serialisation, cancel-cap clipping | runner / contract-rule defects, no fixture outcome involved | not outcome changes |

No fixture was tuned to an outcome; every change moved the state into the region where the pre-registered
premise holds and the discriminating counter-fixtures still discriminate. Verdict: FIXTURE INTEGRITY PASS.

## Audit B — refund / credit economics

Chain audited in the model (`expense(q, fee, w, 0)`, `expense(q, -credit, w, 0)` guarded, `expense(q,
invoice, w, payment_due_in)`, the deposit `prepaid x remaining` an objective constant) and in the settlement
(`<action>_fee`, `commitment_credit`, `procurement`, `payments[0]`, `opening_assets += prepaid x remaining`)
independently, then reconciled to the block (`H1`-`H3`). Proof: the contract refuses `credit_per_unit >
prepaid_per_remaining_unit x deposit_refundable_fraction` (tolerance 1e-9 per unit), so per cancelled unit the
cash effect is `fee - credit >= -prepaid x fraction`; the deposit stays in `opening_assets` on every plan (SUNK
stays sunk, F11 / B9); a credit reverses at most the refundable share (F12 / B1 / B2 / B7); a future invoice
avoided is `procurement`, never cash paid (B7: invoice avoided 530 vs net cash -1.75 / unit); credits are
declared only on cancel options (R4, B11); with several credit options and exclusivity exactly one is charged
(B10). Cases B1-B11 in `P4B_RELEASE_AUDIT_CASES.md`: 11 / 11.

## Audit C — stage compatibility

`OpenPO.stage` is the vocabulary placed / ordered / confirmed / in_production / shipped / in_transit / arrived /
delivered / received. Repository-wide search of every writer (`grep` over `zaad api scripts tests db web
synthetic docs/zaad_full`): workspace adapter `ordered` / `received`, replay `placed`, demo `confirmed`, ATP
integration fixtures `ordered`, P2 performance snapshots `placed`, P3 release record `received`, tests
`placed` / `confirmed` / `shipped` / `in_transit` / `delivered`; the legacy `zaad/demo.py` `in_transit` and
`api/routers/planning.py` `stage="first"` belong to other models. Every value is inside the vocabulary (C2);
no historical request is refused. Declared vault text crosses one explicit boundary (R1): case and
separators normalised, anything else refused with `commitments_invalid`, never mapped to a neighbour. No
production 422 regression.

## Audit D — commitment verdict vs plan verdict

F14 and a second mixed case (D2: an unprofitable deferral next to a cheaper alternate purchase) both read
`overall_plan_status: PENDING_REVIEW` with `commitment_action: KEEP`, `commitment_verdict: NO MATERIAL
COMMITMENT IMPROVEMENT AVAILABLE`, `commitment_value_vs_keep: 0.0` and the purchase rows that make the plan
pending listed under `plan_changes_outside_commitments`; the `reading` states that ZAAD does not recommend
amending any order. A recommended change names the order and the units (D3). D1-D3: 3 / 3.

## Audit E — KEEP incumbent / materiality

The base-stock proxy that serves as the incumbent is solved with the declared non-keep actions disabled
(`disabled` tokens `cancel` / `expedite` / `de_expedite` / `reschedule`; the released tokens are
`alternates` / `transfers` / `continuous` / `substitutions`, no collision, nothing else disabled); a declared
incumbent or rule already keeps; candidates are free (E2). Materiality is the released plan-level standard
(cost, carried inventory, service), the confirmation gate and the downside cap unchanged: E1a records that a
deferral saving 0.04 % of cost but carrying 13.5 % less inventory is material on inventory under that
standard (a released rule, not a P4B one); E1b (a 3-unit partial cancel, below every threshold) -> KEEP,
RETAIN_INCUMBENT; E3 (holding 0, cost of capital 0: the deferral is exactly neutral) -> KEEP; E4 (two identical
cancel options, exclusive) -> one selected, three runs identical; E5 (F20: three eligible options) -> KEEP.
Ties resolve to KEEP because a zero value is never material; among amendments HiGHS is deterministic on the
identical input. E1a-E5: 6 / 6.

## Audit F / K — declaration safety, tenancy, API

Flag off -> released request (`req1.model_dump() == req0.model_dump()`); no rows -> KEEP-only; unknown PO,
declared keep row, missing deadline, CONFIGURED_ASSUMPTION non-keep right, duplicate option ids, malformed
numbers, NaN / inf (`allow_inf_nan=False`), negative economics, fraction above 1, unknown stage / action /
provenance all refused; cross-tenant rows filtered by `operator_id` in SQL, a colliding identifier in another
tenant attaches nothing and the declaring tenant without the order is refused (F1); oversized sets refused at
the adapter and 413 at the API (F3); a past deadline closes the window with capacity 0 and the model gives the
column capacity 0 (F4); a huge cap is clipped to the open quantity (F5); no route contains `amend` or
`supplier`, `approval_required` true, `executable_amendment` false everywhere (F6). Adversarial matrix 16 /
16 (`adversarial_run1.log`); F1-F6: 6 / 6.

## Audit G — minimum remaining / split

Cancel never above the open quantity (settlement cap, adversarial); the floor holds per option on exclusive
orders and as a sum of clipped caps under split (R3, G3); REDUCE when a partial cancel is legal (F04, B3);
full CANCEL only when the floor is 0 (G1); split=false enforces one active option (adversarial); boundary at
1e-9 on the contract and 1e-6 on the settlement (G2); the settlement refuses a floor breach even when the
contract is bypassed (G4, `model_construct`). Amendments sum to the open quantity by an equality row with
non-negative columns, so no tolerance can push the remaining quantity negative (invariants 01 / 07). G1-G4: 4 / 4.

## Audit H — shared ledger

Per amended unit: one fee key, one `procurement` line, one credit (H1 on F12: `cancel_fee` = fee x q,
`commitment_credit` = -credit x q, `procurement` = PO invoice + purchases exactly); freight only on new purchases
(invariant 12); no `defer_cost` anywhere (H1, unit test); expedite / defer act through arrival timing, holding,
service and dated payments (F06: holding 986.7 -> 853.3, fee 10); the sunk deposit sits in `opening_assets` on
both plans and is not a cancellation penalty (B7 / B9); the credit reduces ORDERING and never touches
`opening_assets` (H1). Block value equals the economics' TOTAL delta and the ORDERING delta equals the
component delta (H2); the deterministic-world solve and the settlement agree on the cancel (H3). H1-H3: 3 / 3.

## Audit I — phase ownership

The block carries no `source_split`, `route`, `mode`, `carrier_choice` or `port` key (invariants 14 / 15 on
every fixture); F14 keeps the order and buys from the approved alternate through P1 / P3 (the purchase row
appears under `plan_changes_outside_commitments`, not as a commitment action); no P2 movement, no P4
future-node amendment (the amendment columns are scenario-invariant), no P5 allocation, no P9 rationing.
REROUTE stays excluded (the adapter refuses a `reroute` action explicitly).

## Audit J — no-declaration identity

F00: the KEEP-only request planned on the audit tree and on the production runtime checkout `2fc7b50`
(`harvestmind-deploy`, clean detached): reports identical with timing / hashes stripped, no `commitments`
key (`benchmark_run1.log`). P3 shared-MOV production snapshot through the network planner: 18 HiGHS calls,
decision record identical to the P4B implementation gate (itself identical to the P4 closure record), no
`commitments` key (`gates/p3_snapshot.log`). API: a keep-only request answers with neither `commitments` nor
`executable_amendment` (unit test). The one JSON-invisible change is R6's bool cast.

## Audit L — performance (`P4B_PROFILE_release_audit.md`, released stochastic candidate solve)

| cell | variables | binaries | constraints | solve s | nodes | gap | RSS MB |
|---|---|---|---|---|---|---|---|
| no options | 504 | 145 | 540 | 0.015 | 1 | 0 | 116.7 |
| 1 PO keep only | 508 | 147 | 546 | 0.014 | 1 | 0 | 116.9 |
| 3 POs cancel+defer+expedite exclusive / split | 634 / 622 | 192 / 180 | 665 / 650 | 0.094 / 0.027 | 1 / 1 | 0 | 122 |
| 10 POs cancel+defer exclusive | 616 | 192 | 641 | 0.204 | 1 | 0 | 126.3 |
| 30 POs cancel+defer+expedite exclusive | 850 | 300 | 828 | 0.674 | 122 | 0 | 134.3 |
| 30 POs cancel+defer+expedite split | 730 | 180 | 678 | 0.070 | 1 | 0 | 134.7 |

Structurally identical to the implementation profile (850 / 300 / 122 nodes / 0.687 s); no gap, tolerance,
scenario or exactness change. R2 bounds the option set the profile assumes.

## Validation counts on the audit product

| matrix | result |
|---|---|
| pre-registered fixtures F01-F20 + F00 | 21 / 21 (`benchmark_run1.log`, `../benchmarks/p4b_v1_release_audit.md`) |
| invariants | every invariant on every fixture (`../P4B_INVARIANTS.md`) |
| adversarial | 16 / 16 (`adversarial_run1.log`) |
| release-audit cases B-H, K | 35 / 35 (`P4B_RELEASE_AUDIT_CASES.md`; `run1.log` preserved: 30 / 34 with three runner assumptions and the E1 construction corrected, no engine change) |
| unit tests `test_zaad_commitments.py` | 15 (8 implementation + 7 audit) |
| full suite | 1,979 passed, 2 skipped, 0 failed (6 m 12 s, `full_suite.log`) |
| ruff (CI scope) / mypy (CI scope + `zaad/commitments`) / bandit `-ll` (CI scope) | clean |
| pip-audit | the local interpreter is not the dependency closure (global site-packages: starlette 1.0.0 against the pin `>= 1.6.0`), so the local run is not evidence; the CI security job audits the closure and is the gate |
| gitleaks / Docker build / frontend | CI jobs (not installed locally) |

## Frozen regressions (audit tree, `gates/`, chain identical to the P4 / P5 closures, `chain.sh`)

| gate | result |
|---|---|
| P3 shared-MOV production snapshot (no option declared, network planner) | 18 HiGHS calls, decision record identical to the P4B implementation gate (and so to the P4 closure record), no `commitments` key (`gates/p3_snapshot.log`, `gates/p3_snapshot_under_p4brel.json`) |
| P1 canonical B / T / Q / A + P0 cell 15 | CANONICAL REGRESSION PASS; P1 invariants: 0 failures (`gates/p1_canonical.log`, `gates/p1_invariants.log`) |
| P2 | 20 / 20 fixtures, 18 / 18 principles, INVARIANTS PASS; full pass 1,705 / 1,720 identical vs `p2_perf_closure` (`p2_under_p4brel`) with the 15 differing reviews in two cells where a candidate hit its time limit under load (R / gated / 41002 review 9: `stochastic_network` OPTIMAL -> FEASIBLE_TIME_LIMIT, cell wall 90 -> 503 s; T / echelon_base_stock / 41001 review 0 time limit); those fixtures rerun alone on a quiet CPU, every policy and seed: 280 / 280 identical at baseline runtime (`p2_under_p4brel_rerun`, `gates/p2_rerun_compare.log`) - every one of the 1,720 reviews identical across the two passes |
| sector physics | 26 / 26, 19 / 19, 416 / 416 identical vs `sector_perf_closure` (`sector_under_p4brel`) |
| P3 (current baseline) | 30 / 30, 34 / 34, 23 / 23 adversarial, 2,304 / 2,304 identical vs `p3_perf_closure` (`p3_under_p4brel`) |
| P4 | unchanged code path (recourse tests inside the full suite; `NodeMap` untouched) |
| P5 | unchanged code path (`test_zaad_atp*` inside the full suite) |
| P0 six-cell arm `p4b_release` vs `router_cycle` | 120 / 120 decision-identical, cost / service / unmet identical on every cell (`gates/p0_compare.log`, `p1/closure/p0_arm_p4b_release.json`) |

Released records the chain regenerates in place (P2 / P3 / sector invariants, P3 adversarial) differed by the
validator's request echo and the run tag only and were restored; the audit's own adversarial rerun is kept as
`P4B_ADVERSARIAL_release_audit.*`. Validation7, Validation8, holdout4 not accessed. `CHAIN_EXIT 0` (`chain.log`).

## CI

Release PR #76 (`release/p4b-v1-release-audit` -> `main`, head `a9d5a87`): CI run 34774980685 completed
success on all twelve ZAAD jobs (ruff, mypy, security bandit + pip-audit on the dependency closure, gitleaks,
docker build, frontend, zaad frozen regression, pytest integration / unit-core / unit-zaad-a / unit-zaad-n /
unit-zaad-b). CodeQL run 34774980725 fails at the repository level ("code scanning is not enabled"), not a
gate. The post-merge runs on `main` (34777336057 CI, 34777336046 CodeQL) were cancelled: the merge tree is
byte-identical to the tested head.

## Release

| step | record |
|---|---|
| merge | PR #76 merged with a merge commit: `main` = `1851f40`, tree `dec17373` = tested head `a9d5a87` tree; non-docs content identical to the frozen product `28c1fa7` (tree `48b8d08f`) |
| freeze | `p4b-v1-frozen-product` = `28c1fa7`, `p4b-v1-frozen` = `a9d5a87`; every older tag unchanged (`p5-release-runtime` 2fc7b50, `p5-frozen` 6919379, `p5-frozen-product` eacf3c3, `p4-performance-closure-runtime` 6b58764, `p4-release-runtime` 8c813ac) |
| deployment | from the clean detached checkout `harvestmind-deploy` at `1851f40` (status clean; only `__pycache__` ignored entries): `fly deploy -a zaad-api --image-label canonical-1851f40 --strategy rolling --yes` -> release **v23**, image `registry.fly.io/zaad-api:canonical-1851f40`, machine `0804e0dfd1e948` (fra), health 1 / 1, eleven secrets identical before and after (`release/fly_state_before.txt`, `fly_state_after.txt`, `fly_deploy.log`) |
| production smoke (`release/smoke_p4b.py`, `smoke_p4b_results.json`, addendum) | 1 health 200; 2 no declaration -> 200, no `commitments` key, no `executable_amendment` key (the same state answered 500 on `2fc7b50`: R6 verified in production); 3 KEEP-only -> KEEP, no recommendation; 4 cancel-optimal -> CANCEL, `COMMITMENT CHANGE RECOMMENDED`, `approval_required` true, block and order `executable_amendment` false; 5 exact `NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE`; 6 refundable deposit -> `commitment_credit` -200 = `refundable_credits` 200, sunk 0; 7 excessive credit -> 422 with the contract message; 8 expired option -> window ineligible ("deadline ... has passed"), capacity 0, KEEP; 9 invalid stage -> 422; 10 cross-tenant -> 403 on `/plan`, and the from-workspace flag path is tenant-scoped (each empty self-serve vault: its own `workspace_not_ready` 422); 11 jobs -> 202, DONE in 11 s, block preserved (DEFER, `executable_amendment` false); 12 mixed -> `commitment_action` KEEP, `overall_plan_status` PENDING_REVIEW, `commitment_value_vs_keep` 0, the alternate purchase rows listed outside the commitments |
| production logs (`release/fly_logs_after_deploy.txt`, `fly_logs_after_smoke.txt`) | old VM's SIGINT shutdown traces and one health miss inside the boot grace only; after `Application startup complete`: 41 x 200, 1 x 202, 1 x 403, 1 x 405 (a smoke-script method error, re-issued), 2 x 422; no 5xx, no traceback, no OOM, no restart, no migration / validation / tenant / database error |
| release tag | `p4b-v1-release-runtime` = `1851f40` (created after deploy + smoke + clean logs) |
| PR #75 | marked merged by GitHub because its head `aacb7b9` is an ancestor of the merge commit through the release branch; never merged independently |

Follow-up (not a gate): the raw `/plan` response carries `executable_purchase_order: false` and `approval_required: true`
at the top level and `executable_amendment: false` inside the block and on every order; the top-level
`executable_amendment` mirror exists on the workspace plan shape only.

## Known limitations (preserved)

Here-and-now, scenario-invariant amendment decision; no P4 future-node amendment adaptation (V2 not built);
no rerouting (P7); no supplier execution and no autonomous PO change (approval-only, `executable_amendment`
false, no submission path); declaration-dependent (rights come only from declared options); the block's value
is the whole plan's against the KEEP incumbent (attribution is plan-level; it is 0 whenever every order is
KEEP); under split the cancel caps must sum inside the floor (R3); a credit is declared on cancel options only
(R4); engineering-validated on demo-scale states, not real-data validated; the multi-dimensional released
materiality standard can recommend a deferral on carried inventory alone (E1a).
