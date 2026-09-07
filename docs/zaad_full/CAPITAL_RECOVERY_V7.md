# Capital Recovery V7

Development cycle 7 of the ZAAD full optimizer, stacked on the V6 multi-echelon branch (PR #36,
verdict NEEDS FURTHER MULTI-ECHELON / RECOVERY ENGINEERING). V6 fixed *where* inventory sits; it
did not reduce *how much* there is. This cycle is about capital: what every unit on hand is for,
which units have no reason left, why the selector keeps buying them, and whether temporary
protection ever comes back off.

Scope is deliberately narrow. Forecasting is untouched. Protection is not lowered globally.
Holdout4 stays frozen and unrun. Every adverse result is retained and no historical evidence file
is rewritten.

## 0. Governance

| Item | Value |
| --- | --- |
| Branch | `claude/zaad-capital-recovery-v7` on `claude/zaad-meio-recovery-v6` (tip 4b7eac9) |
| Manifest | `docs/zaad_full/evidence/v7/PHASE0_MANIFEST.json`, committed before any engine change (6224449) |
| Development7 seed | 36001 (fresh) |
| Validation7 seeds | 37001, 37002 (fresh) |
| Holdout4 | 31001, 31002: frozen, **unrun** |
| Never tuned against | development1–6, validation1–6, holdout1–3 |
| Matrix | `v7`: the 97 v6 cells unchanged (ids 0–96) plus 27 v7 cells — fast-arc pooling at three transfer leads and two capacities, and recovery scenarios A–G at 26–32 reviews |
| Comparators | `gated_pr24`, `gated_pr30`, `gated_v4`, `gated_v5`, `gated_v6` (the direct predecessor), `base_stock`, `echelon_base_stock`, `stochastic`, `robust` (validation7, where the solver completes; timeout rows kept visible) |

`protection_v7=False` reproduces the V6 engine exactly (`gated_v6`). The projected base-stock proxy
— which is both ZAAD's incumbent and the `base_stock` comparator — is asserted byte-identical with
the flag on and off (`test_the_echelon_origin_gets_a_row_and_the_proxy_still_ignores_it`).

One honest correction to the manifest: it lists a "transfer lead 0 (same review)" pooling cell.
`Transfer.lead_periods` is at least one review by contract, so a genuinely same-review arc cannot
be expressed in the model. The one-review arc is the fastest the model allows and is used as the
fast case throughout; no cell was fabricated to fill the gap.

## 1. Why V6 still held capital

Four findings, in the order they were made. All of them are structural; none is a coefficient.

### 1.1 A transfer-fed branch was protected as if it could never be restocked

`protection_profile` sets a location's replenishment window from its own approved, cleared sources.
A branch in a central-plus-branch network has none — it is fed by transfer — so the window fell
through to `req.horizon`, and every protection term was sized over 12, 20 or 26 periods.

On development7 cell 35 (intermittent demand, central plus one branch) that produced a lean
baseline of **111 units** at the branch against 18.8 units per period of demand: six periods of
safety stock, for a branch one review away from its own DC. On cell 87 (two branches, 26 reviews)
the branch lean baselines were 21 and 17 units where the correct two-period figures are 5.7 and
4.8.

This is the single largest source of local safety stock on fed branches, and it is precisely
backwards from the multi-echelon result: the faster the arc, the *less* the branch should hold.

### 1.2 The location holding half the network's inventory had no risk state at all

`protection_profile` iterates over `{(sku, location) for service in req.services}`. A central DC
with no customers of its own is not in that set. It therefore had no lean baseline, no regime, no
active drivers, no recovery exit, no duplicated-buffer accounting and — because the V6 excess
charge is keyed on protection rows — no excess charge either.

The capital decomposition puts **54.3% of all units on hand** on development7 cell 87 at that
central location. Half the network's working capital sat outside the entire recovery machinery.

### 1.3 The absolute service gate applies to the candidate and never to the incumbent

The confirmation stage requires `service_ok(candidate_rows)` before a candidate can be accepted.
The retained incumbent is never subjected to the same test. Whenever the target is unreachable on
the independent confirmation draw, every candidate is rejected and the incumbent's capital stays,
however much leaner and cheaper the candidates are.

Development7 cell 87, review 22, V6 engine:

| candidate | Δ inventory | Δ cost | Δ service (worst) | outcome |
| --- | --- | --- | --- | --- |
| `joint_recovery` | −86.1 units | −75.4 | −0.013 | rejected |
| `deterministic_network` | −77.5 units | −69.9 | −0.021 | rejected |
| `stochastic_network` | −76.6 units | −56.3 | −0.159 | rejected |
| retained incumbent | — | — | also misses the target | kept |

### 1.4 Equal-priority customers could never be reallocated between

`_priority_consistent` rejects any service that falls without a *strictly higher-priority*
beneficiary. Two branches of the same customer priority have no strictly higher beneficiary
between them, so no reallocation across equal-ranked branches was ever allowed — it was always
recorded as a hidden sacrifice.

Development7 cell 72, review 6: a plan **37.8 units leaner and 134 cheaper**, service-neutral on
the confirmation draw, was rejected because under a declared stress carrying **zero evidential
credibility** (`effective_stress_weight = 0.0`) it moved about four service points from one branch
to its equally ranked neighbour. The priority-weighted shortfall moved from 1.2621 to 1.2666 — a
change of 0.0045, well inside the material gap — and both plans failed that stress badly anyway.

### 1.5 How often this happens

Retention audit over 192 reviews of ten development7 diagnostic cells on the V6 engine:

| measure | value |
| --- | --- |
| reviews that retained the incumbent | 136 / 192 (**71%**) |
| retained because the stress gate rejected the candidate | 90 |
| retained because no positive cost benefit was established | 17 |
| retained where a rejected candidate was **leaner** | 36 (26% of retentions) |
| median inventory that leaner candidate would have released | **98.4 units** (mean 161, max 639) |
| median modelled cost those candidates would have saved | **+133.5** |
| of those, service-neutral on the confirmation draw (≥ −0.005) | 17, median 129.3 units |

The concentration is entirely in network cells (35, 72, 85, 87, 88, 89); the single-location
recovery cells (20, 21, 90) show essentially no trapped capital.

## 2. What V7 changes

Every rule is additive and switched by `Request.protection_v7`.

1. **Transfer replenishment window.** A branch with no direct source but an approved inbound arc
   from a stocked origin whose capacity covers a period of demand is replenished by that arc:
   window = transfer lead + one review. The arc's declared loss stands in for fill spread; the
   supplier's own lead and fill risk belongs to the origin's row and is not counted twice.
2. **Echelon-origin protection state.** An origin that feeds branches which cannot buy directly
   gets a protection row whose service obligation is those branches' demand, capped by what its
   arcs can carry. The row is marked `echelon_origin`; the projected base-stock proxy ignores it,
   so the incumbent and the `base_stock` comparator are unchanged.
3. **Capital decomposition (P0).** `zaad/full/capital.py` partitions the units on hand into named
   reasons — cycle, local service, source lead, pooled network, active protection, pack rounding,
   early order, transfer positioning, stale protection, unexplained — in a waterfall, most
   defensible first, so the parts sum to the total exactly and the residual is the part with no
   operational reason left. Owner (inherited versus purchased or transferred) is a second,
   independent partition. Periods of demand are reported only where the mean is a meaningful
   divisor; on intermittent demand `periods_meaningful` is false and units are the number to read.
4. **Explicit duplicated-buffer detection (P1).** Pairwise per arc: overlap is counted only when
   the two buffers cover the same risk source, both sit above their own echelon's need, and the
   arc can carry the overlap inside the interval the branch stock exists to cover. The contributing
   pair, the arc, both needs and both holdings are reported with a sentence. Nothing is netted off
   a target mechanically.
5. **Fast-arc pooling split (P2).** Period by period over the origin's replenishment window: demand
   falling before a transfer ordered now could land is local immediate stock; later demand is
   pooled, capped by arc capacity.
6. **Confirmed demand-decline liquidation (P3).** A detected level change that has held for three
   observations at or below 85% of the previous level enters RECOVER while stock exceeds a lean
   base stock at the *new* level, so the existing excess charge runs the surplus down through
   demand, transfers and cancellations. One low reading changes nothing, and no further decline is
   forecast.
7. **Recovery burden (P4).** The excess allowance is now the lean base stock — mean demand over the
   replenishment window plus the lean baseline — instead of the baseline plus one period, which
   ignored the window and could never apply to an origin. The charge adds the operator's own
   declared financing rate to twice the holding rate.
8. **Source-specific recovery confidence (P5).** A supplier that stopped delivering entirely is its
   own driver kind — a closure — and retires on two corroborating receipts rather than six, but
   only once capacity is back, measured as the accepted ratio over the trailing clean run rather
   than over a window that still contains the failure. Fill deterioration keeps six and gains the
   same capacity test; lateness keeps three; an open backlog still retires nothing. A declared
   promotion that has ended retires its own demand protection at once unless demand stayed up.
   `risk_recovery_confidence`, `recovery_evidence_count`, `reviews_to_exit_protect` and
   `reason_not_lean` are reported per SKU and location.
9. **Working-capital view on procurement timing (P6).** Per planned order: earliest feasible,
   latest safe and selected order period, the cash commitment and payment periods, cash days
   advanced, premature units, premature inventory days, storage days and service slack.
10. **Minimum useful protection (P7).** V5 ranked feasible candidates by inventory only inside a
    cost band of about one per cent, so protection costing slightly more was never questioned
    however little service it bought. V7 ranks by *service equivalence*: candidates within the
    operator's own service tolerance of the best priority-weighted service, fitted and under the
    declared stress, and within the operator's own downside tolerance on cost. The leanest of those
    wins; ties go to the plan that commits cash latest.
11. **Symmetric confirmation and the capital tie-break (P8).** When the incumbent itself misses a
    target under independent confirmation, the candidate is judged the way the recovery path
    already judges: no larger priority-weighted shortfall, priority consistent, inside the economic
    downside tolerance — plus, for V7, a material capital or cost benefit, so nothing changes
    without a reason. Separately, a candidate that meets every target at no material economic
    penalty and materially less inventory is accepted, because the plan horizon credits closing
    stock back at terminal value and structurally cannot price capital still on the shelf at the
    end of the window. Materiality on both is the operator's own declared downside tolerance; no
    new constant is introduced.
12. **Equal-priority reallocation.** An equal-priority beneficiary now counts. Robbing a
    higher-priority customer to serve a lower-priority one is still refused, and every caller still
    pairs the check with an aggregate weighted-shortfall condition, so the total can never quietly
    get worse.

Not changed: the forecast, the MILP objective apart from the excess term above, the incumbent
proxy, the `base_stock` and `echelon_base_stock` comparators, and the frozen holdout.

Terminal continuation (P9) remains **off**. V6 found that both of its forms deferred buying into
closures and severe delays; V7 did not re-enable it and re-tests it as an ablation only.

## 3. The inventory decomposition (P0)

Every unit on hand at every review of the development7 fixture, assigned to exactly one reason by
the waterfall. Shares are unit-weighted across the 33-cell fixture on the V7 engine.

| reason | share of units held |
| --- | --- |
| pooled network stock | 37.6% |
| demand cycle stock | 34.4% |
| local service stock | 13.5% |
| **unexplained** | **11.0%** |
| source lead protection | 1.4% |
| active disruption protection | 1.2% |
| stale protection | 0.8% |
| MOQ / pack rounding | 0.0% |
| early-order inventory | 0.0% |
| transfer positioning | 0.0% |

Median unexplained share per cell: **0.042**. Median stale-protection share per cell: **0.0008**.
The identity holds exactly on every row (`capital_reconciles` is true for every method, including
the comparators).

This is the central result of the cycle, and it reframes the V6 verdict.

**The capital V6 was holding is not, in the main, stale protection or duplicated buffers.** It is
cycle stock and pooled network stock: the demand a location must cover between replenishments, and
the demand a central DC must cover for the branches it feeds over its own supplier lead. Together
those two categories are 72% of every unit held. Protection whose risk driver has expired is 0.8%.
Pack rounding, early ordering and transfer positioning are indistinguishable from zero.

Two consequences follow, and neither was visible before the decomposition existed:

1. A large inventory reduction cannot come from unwinding protection, because there is very little
   protection to unwind. It can only come from lowering cycle or pooled stock, and those are set by
   the replenishment window and the service target. Lowering them *is* weakening service.
2. The V6 headline "quiet inventory 1.60 periods" is dominated by intermittent-demand network
   cells, where periods-of-demand divides by a mean that describes nothing. On the development7
   fixture the quiet cells sit at 1.07 periods for V7 and 1.08 for V6 — and the independent
   echelon base-stock comparator sits *higher*, at 1.18, for the same service. On the cells where
   the unit is meaningful, ZAAD is already at or below an independent MEIO policy.

## 4. Duplicated buffers (P1)

The explicit pairwise detector fires on the two-branch fixture cells when both echelons sit above
their own needs and the arc can carry the overlap in time (`test_duplication_names_the_pair_and_
the_arc_that_makes_it_real`), and correctly does not fire on a three-review arc from the same
stock. On the development7 fixture the *median* detected overlap on the running engine is **0.0
units**: the two-branch cells reach a state where the branch is at or below its local need, so
there is no second buffer to double-count.

The honest reading is that duplicated buffers were a smaller problem than V6 assumed. V6 could not
say so because it had no origin-side need to compare against — the origin had no protection row.

## 5. Fast-arc pooling (P2)

The period-by-period split behaves exactly as the theory requires, and the benchmark confirms the
arc lead is what decides it:

| arc | cells | service | inventory periods | pooled units | local immediate units |
| --- | --- | --- | --- | --- | --- |
| lead 1, capacity 50 | 6 | 0.955 | 2.40 | 19.5 | 24.3 |
| lead 1, capacity 15 | 1 | 0.809 | 1.10 | 14.9 | 28.2 |
| lead 2, capacity 50 | 1 | 0.946 | 1.36 | 0.0 | 44.8 |
| lead 3, capacity 50 | 1 | 0.851 | 1.64 | 0.0 | 43.8 |
| lead 3, capacity 15 | 1 | 0.726 | 0.90 | 0.0 | 43.8 |

A one-review arc pools about 44% of the branch's window demand; a two- or three-review arc pools
none of it, because on a two-period origin window nothing the branch needs arrives in time. That
is the correct multi-echelon answer and it is now computed rather than approximated by a static
credit.

What it does **not** show is a fast arc producing a leaner network: the lead-1 cells carry *more*
inventory than the lead-2 and lead-3 cells. That comparison is confounded — the slower-arc cells
also deliver much worse service (0.851 and 0.726 against 0.955), so they are not leaner by choice
but starved. The pooling target is therefore **not met**, and the fixture cannot separate the two
effects at this size.

## 6. Demand decline (P3)

The confirmed-decline state fires only on a detected level change that has held for three
observations at or below 85% of the previous level, and never on a single low reading
(`test_a_confirmed_decline_becomes_liquidation_and_one_low_reading_does_not`,
`test_a_decline_is_never_confirmed_under_v6`). On the development7 decline cells it enters RECOVER
while stock exceeds a lean base stock at the *new* level, and the excess charge then runs the
surplus down through demand, transfers and cancellations rather than replenishing it. Nothing is
disposed of and no further decline is forecast.

The measured effect on cell 87 (decrease, two branches, 26 reviews) is small — 5.21 inventory
periods against V6's 5.40, at identical service (1.000) — because the decomposition explains why:
the stock on that cell is cycle and pooled stock at the *new* level, not protection left over from
the old one. The forecast had already followed the level down; there was less to liquidate than
the V6 verdict assumed.

## 7. Recovery as an objective (P4) and recovery confidence (P5)

The excess allowance is now the stock a lean policy holds *on average* — `lean_baseline + mu ×
window / 2` — because the charge is levied on end-of-period inventory in every period. That
reproduces V6's `lean_baseline + mu` exactly at the two-period window every single-location cell
happens to have, generalises correctly to longer windows, and for the first time applies to
echelon origins, which had no protection row at all under V6. The charge is twice the holding rate
plus the operator's own declared financing rate.

Charging against the *peak* base stock instead was measured on development7 and rejected: the
charge stopped biting and inventory rose from 0.65 to 1.98 periods on cell 1 and from 1.07 to 2.75
on cell 2, both of which already met their targets
(`evidence/v7/dev7_c_peak_allowance_partial.jsonl`).

Source-specific recovery confidence behaves as specified in the unit tests: a closure retires on
two corroborating receipts against a fill deterioration's six, but only once the accepted ratio
over the trailing clean run is back at the declared level; a reopened route whose capacity is still
short does not retire; a single late-but-complete receipt retires after three; an open backlog
retires nothing. `risk_recovery_confidence`, `recovery_evidence_count`, `reviews_to_exit_protect`
and `reason_not_lean` are on every protection row.

On the development7 long-horizon temporary-risk cells the share of reviews in LEAN is **0.600** for
both V7 and V6 — already at the 60% gate, but *not a V7 gain*. The V6 headline of 48% came from the
validation6 mix; on this fixture the two engines are indistinguishable on recovery, and the reason
is section 3: there is very little temporary protection in the system to unwind.

## 8. Procurement timing (P6)

Every planned order now carries its earliest feasible, latest safe and selected order period, its
cash-commitment and payment periods, the cash days advanced, the premature units and inventory
days, and the service slack. On the development7 fixture the V7 engine reports a median of 937
premature purchase units and 266 cash days advanced per replay; V6 reports neither, because the
measurement did not exist.

The plan that commits cash latest is preferred as a tie-break after inventory burden among
candidates inside the cost band. This is a genuine tie-break and it moved nothing measurable on
the fixture: inventory burden almost always separates the candidates first. **Procurement timing
is measured but not yet improved**, and this is an unmet V7 target.

## 9. Marginal protection (P7) and the selector (P8)

The V5 rule ranked feasible candidates by inventory only inside a cost band of one fifth of the
downside tolerance — about one per cent of modelled cost — which is far too narrow to reach a
leaner plan, because a plan that carries less also risks a little more lost margin and lands
outside the band immediately. V7 uses the operator's own declared downside tolerance as the band.
That single change is responsible for essentially all of the inventory the cycle released on
single-location cells (cell 20: 0.88 against 1.99 periods; cell 15: 2.10 against 3.05; cell 16:
1.27 against 1.67), verified by the `V7_DISABLED` ablation, which reproduces V6 exactly when the
rank rule alone is switched off.

Two narrower bands were tried first and both failed for the same structural reason — they anchor
on the *best* candidate's service, and since every candidate in `feasible` already meets every
target, "within a tolerance of the best" admits only the plans nearest the maximum, which are the
fattest, and "then take the leanest of those" ratchets upward:

| band | development7 result | evidence |
| --- | --- | --- |
| best fitted priority-weighted service | quiet-cell inventory 0.86 → 2.21 periods | `dev7_b_service_band_partial.jsonl` |
| best stress priority-weighted service | cell 1 mean inventory value 60.3 → 183.5, selecting the lexicographic service-first plan in half the reviews | `dev7_c_peak_allowance_partial.jsonl` |

Both are recorded in the code beside the rule that replaced them.

Symmetric confirmation and the capital tie-break are in place and correct by test, but the
ablation shows neither moved the fixture measurably on its own. They matter where the incumbent is
already failing and a materially leaner candidate exists — 17 such reviews in the 192-review
retention audit — which is real but rare relative to the whole matrix.

## 10. Equal-priority reallocation: proposed, measured, rejected

The reasoning was sound and the measurement contradicted it, so the rule is not in V7. It is
documented here and in `_priority_consistent` because the same reasoning will recur.

`_priority_consistent` refuses any service that falls without a *strictly higher-priority*
beneficiary. Two branches of equal customer priority have no strictly higher beneficiary between
them, so no reallocation across equal-ranked branches is ever allowed. Development7 cell 72 review
6 showed that rejecting a plan 38 units leaner and 134 cheaper, service-neutral on the confirmation
draw, over a priority-weighted shortfall change of 0.004 under a stress carrying **zero** evidential
credibility.

Allowing an equal-priority beneficiary fixed that review and made the replay worse on both axes:

| variant | cell 72 service | cell 72 mean inventory value |
| --- | --- | --- |
| V6 | 0.971 | 161.7 |
| V7 with equal-priority reallocation | 0.949 | 234.7 |
| the same, tightened to require the weighted total not to rise | 0.952 | 230.6 |
| V7 without the rule | 0.971 | 171.4 |

Across the 33-cell fixture the rule set containing it produced **19 service breaches against V6's
16** with no inventory gain (1.70 against 1.67 periods), concentrated in exactly the stable
two-branch cells it applies to. A lateral shuffle between equals buys nothing the operator asked
for and costs the rolling plan its continuity. The rule is removed and a regression test pins the
strict behaviour.

