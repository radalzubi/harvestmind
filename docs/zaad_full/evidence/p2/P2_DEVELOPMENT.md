# P2 development record (Stage A, before pre-registration)

Every development run is kept (`dev_a`, `dev_b`, `dev_c`, `dev_d4`, `dev_d6`, `dev_dm`, `dev_h6`
`.jsonl` / `.summary.json` / `.tables.md` in this directory). One seed (41001), six rolling reviews,
the fixture matrix of `scripts/p2_fixtures.py` as it stood at each run. Nothing here is authoritative;
the pre-registered run is `p2_authoritative`.

## dev_a (first full matrix, 100 cells): what it exposed

| finding | mechanism | decision |
|---|---|---|
| ZAAD 3-17% worse than "independent" on A, C, D, E, J, L | the first Baseline A gave each branch a virtual direct supplier (no DC, lane cost folded into freight) - a different network design, not a policy; and the frozen asset-basis window score valued central residual at salvage (a demand-less location) while the plan valued branch residual at the steady-state cost | Baseline A redesigned as isolated chains with a private copy of the DC (same physics, no pooling); network continuation added (origin residual reaches the branches through its lanes, sharing their post-window demand; supplier lots sized on echelon demand; slabs at every served location; lane premium); the P2 scoring basis (received-unit replacement cost + lane premium) pre-registered as the headline, asset basis reported alongside |
| G, M, N, P, S INVALID | the first validity rule required every comparator to meet target - impossible on scarcity fixtures | comparators qualify when they serve no more than .05 below ZAAD |
| N: independent baseline ERROR | declared inbound transfers referenced an origin outside the isolated request | fixed with the chain redesign |
| Q: ZAAD wall p50 158 s, max 306 s | general-integer packs on unbounded lanes: a 1e6 capacity made the dispatch binary's big-M meaningless; the stochastic solve stopped at the cap with an achieved gap of 2e-4 against a requested 1e-6 | Q declares a real lane capacity (360) and the operational 1e-4 gap the frozen contract describes; measured: stochastic solve 43 s time-limited at 1e-6 -> 26 s optimal at 1e-4; packs alone (no fee) 43 s, fee alone 15 s, neither 0.5 s |
| F service below target under every policy | branches opened with 60 units against 100 / week: the first period is short whatever the policy | F opens the branches at 120 |
| the replay could not carry a declared inbound transfer without a lane | frozen assumption that an in-flight transfer has an arc | the replay keeps the destination as origin when no lane exists (isolated-branch projections) |

## dev_b (after the redesign, 100 cells): 20 valid, 14 pass, 14 / 18 principles

Remaining failures and what was learned:

| fixture | dev_b | mechanism |
|---|---|---|
| D long lane (+3.6% vs `network_rop`) | ZAAD served .976 / .998 (target .95) and lost 341 against the rule's 12: with a three-period lane the relevant risk is the four-period demand sum, and three LHS worlds per period under-represent its tail; the rule's local base stock over lead + 1 is conservative and, with holding at .3% of value per period against shortage at 12.5 per unit, cheap | experiment below |
| H demand shock (+5.6% vs `independent`) | the mid-surge reviews are P0-owned recovery reviews (targets jointly impossible); the frozen selector kept the incumbent because no candidate materially improved the priority-weighted shortfall on the confirmation worlds (`p2_h_diagnostic.py`); the isolated chains each carry a private supplier share | experiment below |
| M unreachable stock | every policy serves .40: the first four periods cannot be reached by anyone | the `feasible` service mode judges unavoidable starvation against the incumbent (invariant 03 proves the plan credits nothing unreachable) |
| N pipeline covers | period-0 shortfall is unavoidable (40 on hand, 260 landing next period) | N's service mode is `incumbent` |
| O two lanes (+4.1% vs `independent`) | the post-window valuation mapped origin residual through the FASTEST lane (the express at 1.00 / unit): a unit worth 5.10 valued at 4.17 | the cheapest lane values post-window residual (time is not binding after the window); every lane feeds the solve's continuation so the slow cheap lane serves later slabs |
| R order economics (+2.6% vs `independent`) | one economic lot of 2,055 units at review 1 and nothing after: a six-review window ends inside the lot cycle, the artefact the P1 horizon closure documented | R runs twenty reviews |
| `rebalance_before_purchase` | ZAAD's last-review purchase (the lot the window end cannot see through) dominated the six-review purchase total | the principle reads the first two reviews, when the pool is stocked |
| `short_lead_pools_more_centrally` | the end-stock share mixed lot timing with positioning | the principle reads branch cover in periods of demand (D >= C) |

## dev_c (after those changes, 100 cells): 20 valid, 17 pass, 17 / 18 principles

Failures: D (+3.6%, unchanged: three worlds), H (+5.6%), M (`feasible` mode before the unavoidable-
starvation clause). O passed (-1.2%), R passed at twenty reviews (-2.3%), Q wall p50 117 s before its
gap setting.

## Experiments on the two open fixtures

| experiment | ZAAD cost (P2 basis) | lost sales | service | wall p50 |
|---|---|---|---|---|
| D, 3 worlds (dev_c) | 6,498 (+3.6% vs rule 6,275) | 341 | .976 / .954 | 5 s |
| D, 4 worlds (dev_d4) | 6,472 (+3.1%) | 227 | .996 / .974 | 10 s |
| D, 6 worlds (dev_d6) | 6,386 (+1.8%) | 236 | .981 / .988 | 38 s |
| D, 6 worlds, every comparator (dev_dm) | 6,396 (+1.9% vs rule 6,275; independent 6,327) | 268 | .992 / .973 | 41 s |
| M, 8 worlds (dev_dm) | 11,594 (= incumbent 11,596) | 9,038 (unavoidable) | .412 / .401 | 44 s |

Reading: the frozen candidate set prices shortage from S worlds per period; a lane of L periods
makes the (L + 1)-period demand sum the relevant risk, so the world count must grow with the window.
The rule adopted (`zaad.meio.topology.network_scenarios`: three worlds per two periods of the longest
lane window, minimum three, maximum eight) is a representation setting, not a tuning of economics,
and applies to the workspace adapter as well as the fixtures. On D it brings ZAAD inside the 2%
tolerance on one seed with a residual lean bias (ZAAD meets its .95 target and accepts the small
shortage the rule avoids by carrying four periods of cover). If the authoritative run fails D, that
is reported as a limitation of the frozen P1 shortage representation on long lanes, not tuned away.

H (six worlds, `dev_h6`): recorded in the run file when complete; the mid-surge P0 recovery
decision is frozen behaviour and is not changed by P2.

## Adversarial review (`P2_ADVERSARIAL.md`)

Two findings on the first pass, both design decisions rather than defects:

* `central_full_load_economics`: a period-0 purchase of 3,339 units against 2,400 of horizon demand
  is the economic lot at a 400 order cost (EOQ 3,333), not a pathology; the flag now compares with
  the larger of horizon demand and the supplier's economic lot.
* `reverse_lane_free`: two free lanes in opposite directions produced 911 units of ping-pong. Nothing
  in the economics separates A -> B -> A from doing nothing when both moves are free, so the network
  layer refuses such a request (`NetworkRefused`, HTTP 422) rather than pricing a loop out by a
  fixture rule; a priced reverse pair (`reverse_lane_at_cost`) shows no loop.

Second pass: clean.

## Scalability (`P2_SCALABILITY.md`)

1 central + 2 / 5 / 8 branches, H = 12: stochastic three-world solve 3,744 / 8,532 / 13,320
variables in 1.1 / 7.0 / 35.4 s (all optimal); a full `plan_network` review 9.8 / 13.0 / 70.7 s; peak
RSS 215 / 288 / 427 MB. The joint MILP grows linearly in variables with branches and super-linearly in
solve time; eight branches remain inside the frozen solve budget ceiling.

## Workspace adapter findings

* The frozen model uses the location capacity as the big-M of its depletion and FEFO rows; the
  single-location adapter's "unbounded" 1e9 is numerically unsafe once a second served location holds
  more than a period of demand (HiGHS reports infeasible; 1e8 is not). The network adapter declares
  ten million eaches for an undeclared capacity.
* The frozen `lot_round` returns `min(q, maximum)` as is: a declared capacity that is not a whole pack
  makes every rule projection physically illegal. The network adapter brings such a maximum to the
  pack below it; the network policy projection rounds down to the pack after any cap.
* The network policy projection lands supply where the mean world lands it (fitted supply profiles,
  ETA evidence), so the incumbent solve that pins its transfers can see the stock they need.
