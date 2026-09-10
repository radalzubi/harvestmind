# P2 multi-echelon / network optimization: closeout

Branch `claude/zaad-meio-p2`, worktree `harvestmind-p2`, parent `11f5459` (canonical `main`). Frozen
tags unchanged: `p0-frozen` = `2e30721`, `p1-frozen-product` = `f7e1e62`, `p1-frozen` = `12db66c`.
Not merged, not pushed. P2 commits: `377e6b5` (network domain), `5e6bec2` (network continuation,
benchmark, fixtures), `c6ff177` (workspace adapter, API, invariants, adversarial, scalability),
`0f2d50e` (closure rules, scenario rule, pre-registration), `660b2f4` (Correction 1), `04fa28b`
(authoritative evidence), then this closeout.

## Verdict

**P2 CORE ARCHITECTURE BUILT — FREEZE BLOCKED.**

Every freeze-gate item passes except item 19 (runtime commercially plausible) **as pre-registered**:
the per-review maximum of 180 s is exceeded on two of 344 ZAAD reviews (M seed 41002 review 7,
257 s; O seed 41001 review 6, 315 s), while the p50 (9.7 s) and p95 (86.9 s) gates pass and no
required candidate starved on the final set. The gate is not relaxed after the fact.

### The blocker, exactly

* **Classification:** runtime / scalability limitation (frozen P0 / P1 interface).
* **Mechanism:** a review's wall time is the number of candidate classes the frozen screen requests
  times the per-solve budget. The frozen adaptive budget scales with horizon and breadth
  (`solve_budget`: 15 s x 2.2 for a central with two branches x 1.3) and was fitted on three worlds;
  the pre-registered world rule for long lanes (`network_scenarios`: six worlds for a two- or
  three-period lane, eight for four) needs the budget to grow with the world count (Correction 1),
  which puts one capped solve at 86 s (six worlds) or 114 s (eight). A NETWORK_ALLOCATION or
  CAPITAL_OPTIMIZATION review requests three classes; three capped solves plus warm-start completions
  reach 257-315 s. Every such solve returned a physically valid plan (FEASIBLE_TIME_LIMIT, admitted by
  the frozen solve-quality gate); the decisions on those reviews pass every economic and service gate.
* **Economic consequence:** none measured (M +0.02% against its best baseline, O -0.69%; both PASS).
* **Service consequence:** none (M serves exactly what the incumbent serves under unavoidable
  unreachability; O above target on both branches).
* **Runtime consequence:** two reviews in 344 above three minutes; the worst 4.4 minutes.
* **Why local patching is inappropriate:** the only levers are (a) the frozen escalation policy
  (which classes a state requests) and the frozen budget policy - P0 code that P2 does not change;
  (b) the world rule or the budget rule of the pre-registration - changing either after seeing the
  authoritative result is tuning; (c) the gate itself - a post-hoc relaxation. Each is a decision for
  the owner, not a patch: re-pre-register the runtime maximum for long-lane networks (five minutes
  would cover every observed review with margin) and re-run the final set unchanged, or cap the world
  count at six and accept the D / M representation at that count, or scope the interactive API to
  one-period lanes and route longer lanes to the asynchronous job path (already bounded at 32 worlds
  and 26 periods). The code as committed needs no change for any of these.

## What passes (freeze gate items 1-31)

| item | evidence | result |
|---|---|---|
| 1 inventory conservation | invariant 01; every benchmark review residual <= 1e-12; accounting on every world | PASS |
| 2 no double counting | invariant 02 (settlement refuses 200 from 100; the model allocates at most the origin's stock) | PASS |
| 3 reachability | invariant 03 (four-period lane: nothing served in the first four periods, plan and settlement); M | PASS |
| 4 lane capacity | invariant 07; P completes | PASS |
| 5 shared central inventory | invariant 09 | PASS |
| 6 shared supplier constraints | invariant 10 (settlement refuses 120 against a 90 resource) | PASS |
| 7 service per location | accounting per service / location on every world; per-branch gates on every fixture | PASS |
| 8 principled allocation | invariant 17 (priority first, reason stated); G, J, K | PASS |
| 9 transfer economics | invariants 04-06 (monotone in lane cost, shorter lead more useful); E, F, O | PASS |
| 10 no transfer loops | reverse-pair units 0 on every cell; invariant 19; free reverse pairs refused | PASS |
| 11 no forced network action | L abstains 7.5 / 8; G, P 8 / 8; adversarial `already_perfect_incumbent` retains | PASS |
| 12 independent-demand pooling | invariant 13 (worlds p95 pooled / summed .945; pooled inventory below isolated); A | PASS |
| 13 correlated demand invents nothing | invariant 14 (ratio .998; pooled inventory rises with correlation); B | PASS |
| 14 short / long lead | branch cover D .84 against C .22 periods; invariant 06 | PASS |
| 15 already-efficient abstains | L | PASS |
| 16 all valid fixtures pass | 20 / 20 (`P2_RESULTS.md`) | PASS |
| 17 P0 frozen behaviour | canonical regression identical; six-cell arm: cells 15 / 16 / 20 / 90 identical under load, cell 108 30 / 30 identical to the record on an idle machine, cell 21 identical to the frozen code's own replay (its divergence from the record is documented run-to-run variability) (`P2_P0_P1_ISOLATION.md`) | PASS |
| 18 P1 frozen behaviour | B, T, Q, A twelve-review identity at the final SHA | PASS |
| 19 runtime commercially plausible | p50 9.7 s, p95 86.9 s PASS; **max 314.6 s against 180 s FAIL** | **FAIL** |
| 20 accounting reconciles | invariant 20; every benchmark and adversarial cell | PASS |
| 21 API / workspace smoke | network workspace smoke, API tests (workspace endpoints, bounds, refusal), canonical API tests | PASS |
| 22 full tests | 1,838 passed, 2 skipped (final code) | PASS |
| 23 static checks | ruff (canonical scope), mypy (144 files), bandit 0 medium / high, `git diff --check` | PASS |
| 24 clean tree | at the closeout commit | PASS |
| 25 no benchmark tuning | pre-registration with one dated correction (two coding defects), fixtures and rules unchanged after | PASS |
| 26-28 Validation7 / Validation8 / holdout4 | untouched | PASS |
| 29 Network Twin | PR #39 untouched | PASS |
| 30 sector physics | not started | PASS |
| 31 dashboard / website | not started | PASS |

## Frozen-file footprint (all default-off or telemetry; identity proved)

`contracts.py` (Transfer.multiple, fixed_cost_per_dispatch; IncumbentTransfer; incumbent_transfers;
demand_correlation; `network:` rules), `worlds.py` (copula hook), `correlation.py` (new), `model.py`
(executable-period packs, dispatch binaries, continuation feeds), `settlement.py` (pack check, dispatch
fee, flow telemetry), `planner.py` (incumbent transfers, continuation feeds and lane premium on
P1-owned reviews, JSON-safe recovery shortfall), `replay.py` (method registry, incumbent transfers,
lane-less inbound), `policies.py` (network rule dispatch), `lotsizing.py` (echelon-demand lots,
slabs at served locations, lane premium, feeds), `terminal.py` (origin residual through the cheapest
lane, location premium).

## Known limitations (recorded, not tuned)

* Long lanes need more worlds than P1's three; the rule is representation, and it multiplies the
  frozen budget (the blocker above).
* On a long lane ZAAD keeps its service target and accepts the small shortage a four-period local base
  stock avoids; at three worlds this cost 3.6% against the rule on D, at six worlds it is inside the
  tolerance (D -0.07%). The P1 shortage surrogate prices single-period tails, not the multi-period sum.
* Under a declared one-branch surge the mid-surge reviews are P0 recovery reviews; at three worlds the
  frozen selector retained the under-buying incumbent on two of them (H +2.06%, inside its 3%
  tolerance; at six worlds +1.2% at 86 s p50).
* The interactive API caps `scenarios` at four on the payload path; a long-lane network from the
  workspace adapter declares six or eight and runs on the workspace endpoints (bounded by the solve
  budgets) or the asynchronous job path.
* Correlation groups are SKUs; lane disruption is not represented in the worlds; branch -> branch and
  branch -> central lanes are accepted but the production topology built by the adapter is
  central -> branch.
