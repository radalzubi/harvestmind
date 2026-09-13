# P4B V1 development log

Branch `claude/zaad-commitments-p4b`, worktree `harvestmind-p4b`, from `main` `5dc87b4` (design-gate PR #74
merged; runtime `2fc7b50`, tag `p5-release-runtime`). BUILD V1 authorization only.

## 2026-09-13 — implementation

* Audit confirmed by code: the released P0 / P1 model already carries the amendment columns, conservation,
  exclusivity, fees, invoices, arrival shift and the sunk deposit; the released base-stock proxy incumbent
  was free to amend (the demo "recovery" case retained an incumbent that cancelled). P4B V1 makes KEEP the
  incumbent when a non-keep option is declared (`disabled` on the proxy solve), adds the bounded credit
  term (one guarded line in `model.py`, one in `settlement.py`), maps the fee keys and the credit to the
  ORDERING component, and builds the commitment-state module, the operator block, migration 022, the
  adapter and the `commitments=true` flag. `keep_fee` (always 0) stays unmapped so the no-declaration
  report is unchanged.
* Contract additions: `POOption.credit_per_unit` / `provenance`, `OpenPO.stage` vocabulary,
  `minimum_remaining_quantity`, `deposit_refundable_fraction`; refusals: assumed rights, credit above the
  refundable deposit, cancel cap through the floor (clipped cap), unknown stages, keep with a credit.

### Fixture runs (all preserved under `evidence/p4b/benchmarks/`)

* run 1 (`p4b_v1_run1_failed.log`): 2 fixtures then a runner crash - F03's "option absent" state is
  KEEP-only by design (no block, identity); runner restructured (main = deadline passed, variants = stage
  ineligible, option absent checked as identity). Profile crashed on the cancel-cap validator refusing a cap
  above the open quantity, which the released model accepts by clipping: the rule now applies to the
  clipped cap only.
* run 2 (`run2_failed`): 12 / 13 then a crash on F14 (the alternate source's route must start with its own
  supplier - contract rule). F06 KEEP: the released confirmation gate found only a 0.4 % fitted benefit
  (holding 0.25 / unit-period against demand-spread stockout risk) - fixture-state defect.
* run 3 (`run3_failed`): 18 / 21. F06 still KEEP: the demo base's incidental "tail" stress (fill 0.8,
  +14 days, demand x1.1) makes the released hedged gate reject any later arrival; F14 with no stock: every
  candidate failed the downside gate (unavoidable period-0 shortage); F20 with 60 on hand: the order was
  excess and cancel + a smaller purchase was the right answer. Re-registered: neutral base stress (F15
  declares tail + port closure explicitly), holding 0.4 on the defer states (F06 / F07 / F16 / F17), F17
  cash 1,000, F14 stock 20 with a same-period alternate, F20 stock 20 (20 + 100 = the horizon's demand).
* run 4 (`run4_failed`): 19 / 21, both runner defects: F14's check matched the word "route" inside an
  assumption sentence; F00's pre-P4B comparison serialised the old runtime's report with `report_json`
  (no datetime encoder). Fixed; no engine change.
* run 5 (`p4b_v1`): 21 / 21 including F00 (no-declaration identity against the pre-P4B runtime `2fc7b50`).

### CI

PR #75 head `7311d00`: CI run 34759841637 success (all twelve jobs). CodeQL run 34759841665 fails because code scanning is not enabled on the repository (pre-existing, identical on the P5 branches); recorded, not a P4B finding.

## 2026-09-13 — release audit (`release/p4b-v1-release-audit`, `docs/zaad_full/evidence/p4b/release_audit/`)

* Audit branch from PR #75 head `aacb7b9` (product `a6483ab`, tested head `7311d00`, non-docs diff empty). Six
  corrections, smallest scope each (R1-R6 in `P4B_RELEASE_AUDIT.md`): adapter normalisation boundary with
  `commitments:` refusals (stage / action / provenance / numbers / duplicates), option-set bounds (adapter +
  413 gate), split floor as a sum of clipped cancel caps + settlement floor check (guarded), credit on cancel
  options only, explicit `commitment_action` / `commitment_verdict` / `commitment_value_vs_keep` /
  `overall_plan_status` / `plan_changes_outside_commitments` / `reading` (block 1.1), and the pre-existing
  production defect of a numpy bool in `service_reliability` that 500s `/plan` (reproduced on `2fc7b50` and
  against production, cast to `bool`).
* Fixture integrity re-derived causally (`f06_boundary_scan.log`): every re-registration is a VALID FIXTURE
  REPAIR; F06 at the demo holding rate flips to DEFER at 200 on hand, and at 130 on hand the released
  confirmation gate retains until 0.4 (the mechanism is the excess-versus-tail-risk trade-off).
* Release-audit cases 35 / 35 (`run1.log` 30 / 34 preserved: three runner assumptions, E1 split into the
  released multi-dimensional materiality case and a below-every-threshold case); fixtures 21 / 21 with the
  pre-P4B identity; adversarial 16 / 16; profile structurally identical; suite 1,979 passed / 2 skipped.
* Release: CI 34774980685 green, PR #76 merged as `1851f40` (tree = tested head), Fly v23 `canonical-1851f40`, production smoke 12 / 12 + addendum, logs clean, tag `p4b-v1-release-runtime`.
