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

