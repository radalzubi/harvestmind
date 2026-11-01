# Does ZAAD add decision value? Phase 2 report (FreshRetailNet corrected, Walmart M5 holdout)

Date 2026-10-19. Branch `pilot/freshretailnet-50-series` (PR #114). Evidence: `FRN_AUDIT_REGISTER.md`,
`frn/FRN_RERUN.md`, `frn/FRN_COMPARISON.md`, `m5/M5_AUDIT.md`, `m5/M5_DESIGN_FREEZE.md`, `m5/M5_RESULTS.md`,
`m5/M5_CROSSTAB.md`. Every number is a modelled index under declared SYNTHETIC supply and economics on public observed
sales; no customer, supplier, cost or realized-service data exists in either dataset and nothing here is a saving.

## The eight questions

**1. Does ZAAD consistently beat a competent baseline under comparable service constraints?** No. Against the projected
reorder point at the same declared target, the holdout readings are: stable supply a tie on both datasets (FRN
+0.001, M5 −0.58 with the 95 % interval including zero; ZAAD re-issues the declared rule on 79–89 % of stable reviews);
lead-time spread a small, repeatable win on M5 (−2.8 to −3.8 per series-window, 0.8–1 % of cost, intervals excluding
zero, repeated on val2) and a marginal one on FRN (−0.038); fill and combined uncertainty inconclusive on the holdouts
and against ZAAD in the two validation cells whose intervals exclude zero (M5 val2 `uncertain` +4.24, FRN val1
`uncertain_fill_only` +0.47). On the coupled experiment the competent constraint-aware baseline is `economic_lot`;
ZAAD's holdout margin over it is 26–62 per group with intervals that include zero in two of three scenarios, and all
six validation cells favour `economic_lot`.

**2. Does its stochastic planning improve decisions when supplier uncertainty increases?** Only for lead-time
uncertainty, and only on weekly periods. There the planner's protection lowers shortage by 13–17 per series with 4
more units on hand, on the holdout and on val2 alike, and the effect doubles when the planner runs its own candidates
instead of retaining the declared rule (`no_incumbent`, −7.3, 36 / 12 wins). For fill-rate uncertainty and for lead
plus fill together the extra inventory (+10 to +25 units per series) costs about what the shortage it avoids saves, and
on the validation windows it costs more. On daily periods (FRN) the same regime is driven by a lateness calibration
that treats a one-day spread as frequent lateness (finding 7), and its inventory does not pay back inside 7-day windows.

**3. Does it manage shared budget and purchasing constraints better?** Not demonstrably. After the projection fixes
every policy respects the fixed cost, MOV, pallet cap and case lots without a breach. ZAAD beats the rules that order
every week by 100–170 per group, but that margin is the fixed order cost those rules pay 12 times; the lot-aware
`economic_lot` captures it too, and against that baseline the holdout is inconclusive and the validation windows are
negative, with ZAAD's own candidates on 15–29 % of reviews. The declared cash budgets were liquidations (no inflow);
the post-freeze single-SKU variant with declared revenue reproduces the primary readings, and the coupled cash
variant measures who runs out of cash last. No test here shows capital-aware purchasing beating a competent rule.

**4. Does it reduce capital exposure without disproportionate shortages?** The opposite trade: ZAAD carries more
inventory everywhere it is measured (M5 holdout +0.4 to +10 units per series, coupled +7 to +34 units per group) and
buys shortage down with it; fill is higher by 0.003 to 0.08. Where the shortage avoided is large (lead spread) the
trade pays slightly; where it is not (stable, fill-only), it is a wash. Capital exposure is not reduced.

**5. Are the improvements robust to assumptions or concentrated in selected scenarios?** Concentrated in the
lead-spread scenarios and robust to the economics there: target 0.90, holding ×2 (M5) and ×4, margin ×2 (FRN) do not
change any sign. Removing the declared incumbent enlarges the lead-spread win and the inventory carried. The verdict
on stable, fill-only and combined uncertainty is inconclusive under every variant.

**6. Are additional solver complexity and runtime justified?** Not by these results. ZAAD takes 3–6 s per 13-review
single-SKU run and 30–95 s per coupled group against 0.03–0.1 s for the rules; on the tightest coupling one group's
gated run exceeded 80 minutes at 100 % CPU against a 40 s per-solve budget (`coupled_tight`, section 6 of the M5
note), which is the solver-quality exposure already on record. The value it buys is a 1 % cost difference in one
supply regime.

**7. Which limitations prevent customer deployment?** The lateness slack is weekly-tuned and not a request parameter;
the planner's wall clock is not bounded by its declared solve budget on tight coupled cells; the abstention path
depends on the declared incumbent being projectable; capital constraints need receivables the operator must declare;
and every supply, cost and economic input in both pilots is declared, not observed. Nothing here speaks to a
distributor's purchase orders, supplier fills, lead times or prices.

**8. What evidence still requires actual distributor purchasing data?** Everything that would turn a modelled index
into a decision claim: real lead-time and fill distributions (the only regime where ZAAD wins is defined by them),
real holding and capital rates, demand under stockout, the operator's actual rule and how often the planner would have
changed it, and realized service. The public datasets give demand paths only.

## Conclusion: CONDITIONAL

Promising only in one direction: under declared lead-time uncertainty on weekly periods the planner's protection is a
small, repeatable, economics-robust improvement over the projected rules, with no constraint breaches once the
baselines are legal. Material gaps remain: no advantage on stable supply, none shown against a lot-aware baseline
under shared constraints, more inventory everywhere, two validation cells against ZAAD, runtime unbounded on a tight
coupled cell, and no observed supply or cost data behind any number. GO is not supported; NO-GO would discard a
measured, repeatable effect.

## Next step (bounded)

1. Owner decisions on the engine side: the lateness slack as a request-level calibration, a wall-clock bound on the
   gated run, and the undeclared-storage big-M conditioning. None was changed here.
2. One real operator's purchase-order history (even a few months) to replace the declared supply with observed lead
   and fill distributions; the harness takes it unchanged. Until then do not scale the public-data pilots beyond 50
   series: more series narrow intervals around the same inconclusive readings.
3. If the M5 harness is extended, run `coupled_tight` to completion under a wall-clock bound and add a lot-aware
   incumbent-free variant so the planner's own coupled candidates are measured against `economic_lot`.
