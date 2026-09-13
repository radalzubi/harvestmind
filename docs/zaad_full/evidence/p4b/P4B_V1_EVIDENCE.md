# ZAAD P4B V1 — open PO / commitment intervention: implementation evidence

| item | value |
|---|---|
| starting `main` | `5dc87b4` (design-gate PR #74 merged; docs-only above the production runtime `2fc7b50`, tag `p5-release-runtime`) |
| branch / worktree | `claude/zaad-commitments-p4b`, `harvestmind-p4b` |
| authorization | BUILD V1 only: here-and-now KEEP / DEFER / EXPEDITE / REDUCE / CANCEL / SPLIT; no V2 node-indexed amendments, no REROUTE, no P6 / P7 / P8 / P9 |
| untouched | P0-P5 semantics, `zaad/full/model.py` beyond the one guarded credit term, P4 node map, P3 formulation, scenario probabilities, solver tolerances, sector physics, historical tags, Validation7 / Validation8 / holdout4 |

## Architecture implemented

The design gate's option B on the existing joint solve: the released P0 / P1 amendment columns
(`amend[po, option]`, conservation, exclusivity, fees, invoices, arrival shift, sunk deposit) are the
optimizer; P4B V1 adds a commitment-state module (`zaad/commitments/`: view `resolve()`, amendment
windows, irreversibility ladder, refund bound), the KEEP incumbent, the operator block, the
declaration path (migration 022, adapter, `commitments=true`) and the ledger mapping. No second
optimizer, no new MILP, no node-indexed amendments.

* `zaad/full/planner.py`: when a non-keep option is declared, the projected base-stock proxy that
  serves as the incumbent is solved with the non-keep actions disabled (KEEP is the incumbent; the
  released proxy was free to amend); candidates stay free; `report["commitments"]` is attached after
  the frozen report. Without a declaration the call is the released one (`disabled=frozenset()`).
* `zaad/full/model.py`: one guarded line - `expense(q, -credit_per_unit, w, 0)` only when a credit
  is declared (> 0); the frozen build is bit-identical otherwise.
* `zaad/full/settlement.py`: `commitment_credit` ledger key and the period-0 cash inflow, guarded
  the same way.
* `zaad/full/economics.py`: `cancel_fee` / `expedite_fee` / `de_expedite_fee` / `reschedule_fee` /
  `commitment_credit` mapped to the ORDERING component (order-level commercial charges, with the
  fixed order and switching costs). A new COMMITMENT component key would have changed every
  released report (`COMPONENTS` seeds every breakdown), and the released `keep_fee` (always 0)
  stays unmapped exactly as the runtime reports it, so the no-declaration report is unchanged; the
  commitment block carries its own fee / credit breakdown.
* workspace: `build_request(..., commitments=True)` attaches declared terms and options
  (`stg_po_commitments`, `stg_po_options`); unknown orders, declared keep rows, options without a
  deadline are refused (422 `commitments_invalid`); absent declarations keep every order KEEP-only.
* API: `commitments=true` on both from-workspace endpoints; the plan shapes carry the block with
  `executable_amendment: false`.

## Contract additions (additive, default-neutral)

| field | rule |
|---|---|
| `POOption.credit_per_unit` (>= 0, default 0) | refund / credit note per amended unit, paid at period 0 with the fee; keep carries none |
| `POOption.provenance` (CONTRACT default, OPERATOR_DECLARED, CONFIGURED_ASSUMPTION) | a non-keep option on a CONFIGURED_ASSUMPTION is refused: rights are never assumed |
| `OpenPO.stage` controlled vocabulary (placed, ordered, confirmed, in_production, shipped, in_transit, arrived, delivered, received) | every value the released paths write is a member; other values refused; `allowed_stages` validated |
| `OpenPO.minimum_remaining_quantity` (default 0) | a cancel option whose clipped cap would take the order below the floor is refused |
| `OpenPO.deposit_refundable_fraction` (0..1, default 0) | bounds every option credit: `credit_per_unit <= prepaid_per_remaining_unit x fraction` |

## Refund / credit proof (release-critical)

Money paid on an open order is the deposit `prepaid_per_remaining_unit x remaining` (the remaining
invoice is future money, never paid before arrival). SUNK = `prepaid x (1 - fraction)` per unit;
REFUNDABLE = `prepaid x fraction`. The contract refuses any `credit_per_unit` above REFUNDABLE, so
a cancel's net cash effect is `fee - credit >= fee - prepaid x fraction >= -prepaid`: the most a
cancellation can recover is the refundable deposit share; it can never create value beyond avoiding
the future invoice and recovering that share. The deposit stays in `opening_assets` (released sunk
treatment: cancelling forfeits it through the asset delta) and the credit reverses at most the
refundable part (F11: no credit key, `opening_assets` carries 200; F12: `commitment_credit` = -200,
cancel cheaper than F11 by exactly the credit). Adversarial: negative credit, credit above
`prepaid x fraction`, credit with fraction 0, credit with nothing prepaid all refused.

## Economic ownership (no double count)

| term | key | owner |
|---|---|---|
| amendment fees | `cancel_fee`, `expedite_fee`, `de_expedite_fee`, `reschedule_fee` (released keys) | declared option -> ORDERING component |
| refund / credit | `commitment_credit` (new, negative) | declared option, bounded -> ORDERING |
| remaining invoice under the option | `procurement` (released) | P1 ledger; charged once per amended unit (`13_no_duplicate_procurement`) |
| defer / expedite consequences | `holding`, `lost_sales_opportunity`, `sla`, dated `payments`, cost of capital (released) | P0 / P1 ledger: no "defer cost", no second holding, shortage, procurement or financing term |
| sunk deposit | `opening_assets` (released) | P0 ledger |
| freight | `freight` on new purchases only (released) | P1; never on amended units (`12_no_double_freight`) |

## Comparator and materiality

KEEP is the incumbent (declared incumbent orders / rule already keep; the base-stock proxy now keeps
when options are declared). The released selector's materiality and confirmation gates decide; the
block reports `NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE` when the plan is retained or the
selected plan keeps every order, and `COMMITMENT CHANGE RECOMMENDED` with the plan-level value
otherwise. Attribution is plan-level (purchases may also differ) - stated in the block.

## Fixture results (run 5, `benchmarks/p4b_v1`; runs 1-4 preserved as `*_failed.log`)

21 / 21 PASS. Re-registrations (dev log): neutral base stress (the demo's incidental
"tail" stress fails the released hedged gate on any later arrival), holding 0.4 / value / period on the
defer states, F17 cash 1,000, F14 stock 20 with a same-period alternate, F20 stock 20; runner defects in
runs 1 and 4. No engine code changed between runs 2 and 5.

| fixture | action | verdict | plan status | value | result |
|---|---|---|---|---|---|
| F01_cancel_optimal | CANCEL | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 111.667 | PASS |
| F02_cancel_not_worthwhile | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F03_cancel_prohibited | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F04_partial_reduction | REDUCE | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 182.799 | PASS |
| F05_minimum_remaining | REDUCE | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 67.0 | PASS |
| F06_defer_reduces_excess | DEFER | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 122.404 | PASS |
| F07_defer_stockout | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F08_expedite_justified | EXPEDITE | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 335.081 | PASS |
| F09_expedite_too_expensive | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F10_already_shipped | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F11_sunk_deposit | CANCEL | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 136.667 | PASS |
| F12_refundable_deposit | CANCEL | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 336.667 | PASS |
| F13_short_fill | EXPEDITE | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 287.64 | PASS |
| F14_alternative_source | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | PENDING_REVIEW | 332.586 | PASS |
| F15_correlated_disruption | CANCEL | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 458.305 | PASS |
| F16_perishable_delay | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F17_payment_timing | DEFER | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 153.22 | PASS |
| F18_deterministic | DEFER | COMMITMENT CHANGE RECOMMENDED | PENDING_REVIEW | 122.404 | PASS |
| F19_information_changes_action | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F20_keep_optimal | KEEP | NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE | RETAIN_INCUMBENT | 0.0 | PASS |
| F00_no_declaration_identity | None | None | None | None | PASS |

F00: the KEEP-only request (F20 without options) planned here and on the pre-P4B runtime checkout
`2fc7b50` gives identical reports (timing / hashes stripped) and no `commitments` key.

## Invariant results

`P4B_INVARIANTS.md`: every invariant passes on every fixture's selected plan (amendments sum to the
open quantity, never above open, never below the floor, none after a deadline or in a prohibited
stage, received unchanged, no negative balance, split rule, payment reconciliation, credit bounds,
sunk cost in `opening_assets`, no double freight, no duplicate procurement, no P3 leakage, no P7
routing, deterministic ties (F18, three identical runs), approval required, KEEP feasible, and the
no-declaration identity above).

## Adversarial results

`P4B_ADVERSARIAL.md`: 16 / 16 fail closed (unknown action, malformed stage, expired option,
prohibited stage, negative fee, negative credit, excessive refund, credit above the refundable /
paid amount, cancel above remaining, minimum-remaining violation, split when prohibited, unknown PO,
cross-tenant declaration, missing provenance, declared keep row, option without deadline).

## Performance (`P4B_PROFILE.md`, released stochastic candidate solve on the demo request)

| cell | variables | binaries | constraints | build s | solve s | proof s | nodes | gap | status | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|
| no options | 504 | 145 | 540 | 0.001 | 0.015 | 0.015 | 1 | 0.0 | OPTIMAL | 117.2 |
| 1 PO, keep only x3 | 508 | 147 | 546 | 0.001 | 0.013 | 0.013 | 1 | 0.0 | OPTIMAL | 117.4 |
| 3 POs, cancel+defer+expedite, exclusive | 634 | 192 | 665 | 0.001 | 0.096 | 0.096 | 1 | 0.0 | OPTIMAL | 121.8 |
| 3 POs, cancel+defer+expedite, split | 622 | 180 | 650 | 0.001 | 0.027 | 0.027 | 1 | 0.0 | OPTIMAL | 122.0 |
| 10 POs, cancel+defer, exclusive | 616 | 192 | 641 | 0.001 | 0.206 | 0.206 | 1 | 0.0 | OPTIMAL | 126.0 |
| 30 POs, cancel+defer+expedite, exclusive | 850 | 300 | 828 | 0.002 | 0.687 | 0.687 | 122 | 0.0 | OPTIMAL | 134.1 |
| 30 POs, cancel+defer+expedite, split | 730 | 180 | 678 | 0.002 | 0.071 | 0.071 | 1 | 0.0 | OPTIMAL | 134.4 |

Options add columns and, when splitting is not allowed, one exclusivity binary per (PO, option): the
30-PO exclusive cell is the only one that branches (122 nodes, 0.69 s); with splitting allowed the same
cell solves at the root in 0.07 s. Build time is unchanged (milliseconds); no scenario reduction, no
gap change. No performance work attempted.

## Frozen regressions (one pass on the product candidate `a6483ab`, `gates/`)

| gate | result |
|---|---|
| P3 shared-MOV production snapshot (no option declared) | 18 HiGHS calls, decision view and candidates identical to the P4 closure record (timing stripped), no `commitments` key |
| P1 canonical B / T / Q / A + P0 cell 15 | CANONICAL REGRESSION PASS; P1 invariants 720 checks, 0 failures |
| P2 | 20 / 20 fixtures, 18 / 18 principles, INVARIANTS PASS, 1,720 / 1,720 reviews identical vs `p2_perf_closure` (`p2_under_p4b`) |
| sector physics | 26 / 26, 19 / 19, 416 / 416 identical vs `sector_perf_closure` (`sector_under_p4b`) |
| P3 (current baseline) | 30 / 30, 34 / 34, 23 / 23 adversarial, 2,304 / 2,304 identical vs `p3_perf_closure` (`p3_under_p4b`) |
| P4 | unchanged code path (recourse tests inside the full suite; `NodeMap` untouched) |
| P5 | unchanged code path (`test_zaad_atp*` inside the full suite) |
| P0 six-cell arm `p4b_v1` vs `router_cycle` | 120 / 120 decision-identical (`p1/closure/p0_arm_p4b_v1.json`) |
| no-declaration identity | F00 against the pre-P4B runtime checkout `2fc7b50`: identical report |
| full suite | 1,973 passed, 2 skipped, 0 failed (6 m 11 s); ruff (CI scope), mypy (CI scope + `zaad/commitments`), bandit `-ll` clean |
| CI (PR #75, head `7311d00`) | run 34759841637 success: docker build, frontend, mypy, ruff, gitleaks, bandit/pip-audit, zaad frozen regression, pytest integration + unit-core + unit-zaad-a/n/b all pass. CodeQL run 34759841665 fails at the repository level ("Code scanning is not enabled for this repository"), the same pre-existing condition as every earlier branch; not a P4B finding |

Released records the chain regenerates in place differed by timing and the validator's request echo
only and were restored. Validation7, Validation8, holdout4 not accessed.

## Migration audit

Migration 022 adds two tables (`stg_po_commitments`, `stg_po_options`) with `CREATE TABLE IF NOT
EXISTS`; nullable declaration columns; no allocation, amendment or reservation stored; a second
`setup_db` run leaves the information schema identical (`test_migration_022_is_additive_and_the_flag_attaches_only_declared_options`).

## API / workspace audit

* declarations attach only with `commitments=true` and only for declared rows; absent rows ->
  KEEP-only request identical to the released build (`req1.model_dump() == req0.model_dump()`);
* unknown PO / declared keep row / missing deadline -> 422 `commitments_invalid`; another tenant's
  rows attach nothing; malformed values refused at the contract;
* the block travels with `/plan`, `/jobs` (through `plan()`), and the plan shapes with
  `executable_amendment: false`; every response keeps `approval_required: true`,
  `executable_purchase_order: false`;
* no flag gates the planner path itself: an explicit `atp`-style environment switch is not needed
  because a declared option is itself the operator's explicit request; nothing is inferred.

## Known limitations

* Here-and-now only: options whose windows outlast a review epoch are decided today (V2 not built).
* Expedite capacity is the declared `max_quantity`; supplier capacity for an earlier date is not
  modelled beyond it.
* Life lost while already-produced goods wait (a deferred shipment ageing in transit) is not
  representable: the arrival cohort's life starts at receipt (`receipt_life`); F16 tests what the
  released physics represents.
* The value in the block is plan-level (the released materiality frame); a per-order attribution
  solve is not built.
* `keep_fee` (always 0) remains an unmapped ledger key in the released breakdown by design (identity).
* Engineering evidence on the demo request; no real supplier terms.

## Unresolved questions

1. Whether the released API fixture `case=recovery` (a declared cancel option) should keep its
   pre-P4B report (incumbent free to cancel, RETAIN) or the P4B KEEP-incumbent report (CANCEL
   recommended): the code now gives the latter, which is the design gate's rule.
2. Whether a per-order attribution solve (selected plan with amendments fixed to keep) is worth its
   cost in a release audit.
