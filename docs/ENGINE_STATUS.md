# Engine Status

_Last updated: 2026-06-08 · code at commit `d7f610a` · suite: 333 passing_

A plain-language status of the HarvestMind math engine, written to be read by
an advisor or operator, not just an engineer. The honesty is the point: every
number below comes from synthetic data, and we say so wherever it matters.

---

## 1. What the engine does today

**Diagnostic layer — works, shippable.**
Reads an operator's order and delivery history and reports waste, shortage,
supplier reliability, buyer fulfillment, traceability coverage, and
available-to-promise by product. This is arithmetic on the operator's own data:
no forecasting, no optimization, no assumptions. It runs end-to-end through the
API and frontend today.

**Optimizer layer — fixed and internally validated, on synthetic data only.**
A two-stage stochastic program (and a deterministic LP baseline) that decides
how much to commit to each supplier ahead of demand, then models the recourse
(spot buys, waste, unmet demand) once demand lands. As of Phase 0.9 the
objective is newsvendor-correct and the solver commits at the right level. It
has **not** been run on a single real operator's data.

---

## 2. What was found (Phase 0.75 → 0.9)

A six-round investigation into whether the stochastic optimizer is worth its
complexity over a plain deterministic LP. In plain terms:

1. **Flat penalties hid everything.** With a flat unmet penalty far larger than
   the flat waste penalty, the optimal answer was always "cover demand fully,"
   so the stochastic program produced the *same* commitments as the
   deterministic LP. Stochastic looked worthless — but only because the cost
   structure was rigged toward full coverage.

2. **Honest per-product penalties exposed a real bug.** Switching to honest
   economics (waste = unit cost, unmet = lost margin) did not help — it made the
   stochastic program collapse to near-zero commitment. The cause was a
   **procurement double-count**: the objective charged the full purchase cost on
   every committed unit and then *also* penalized waste, while never crediting
   the revenue from units that actually sold. Under honest margins, committing
   anything looked strictly worse than committing nothing.

3. **Reformulation fixed it.** Rewriting the objective in newsvendor form —
   overage (unit cost) + underage (lost margin) + spot premium only, with
   committed-and-sold units carrying no penalty — removed the double-count. The
   optimizer now commits at the newsvendor q\* quantile (≈0.90× q\* on the test
   data), neither collapsing to zero nor blindly covering all demand.

The math is now sound. The legacy flat path is preserved behind a flag
(`newsvendor_objective=False`) so nothing regressed.

---

## 3. Honest value

On the realistic synthetic operator (~$8M hub, 28 products, weekly rolling
decisions), the reformulated stochastic SP beats the deterministic LP by:

| spot premium / availability | SP vs deterministic LP edge | win rate |
|---|---:|---:|
| 1.30× / 30% of demand | +17.4% | 21/25 |
| 1.30× / 15% of demand | +7.1% | 19/25 |
| 1.60× / 30% of demand | +3.9% | 17/25 |
| 1.60× / 15% of demand | +2.4% | 15/25 |
| 2.00× / 10% of demand | −0.8% | 9/25 |

**The robust, assumption-insensitive core value is ~+2–4%.** The headline
+17.4% is **spot-arbitrage**: it appears only when emergency/spot coverage is
cheap and abundant, which lets the optimizer under-commit and lean on the spot
backstop. That is a property of the *assumed spot market*, not a property of the
engine. As spot becomes realistically expensive and scarce (the bottom rows),
the edge falls toward the +2–4% core and eventually to zero.

---

## 4. The one parameter that governs everything

**Spot cost and availability.** It single-handedly moves the stochastic edge
between ~0% and ~17% in the table above. It is currently a guess, and it
**cannot be resolved by more simulation** — only by asking a real operator what
their emergency/short-notice coverage actually costs and how much they can get.
This is the first thing to measure with real data, and until it is measured,
the defensible claim is the +2–4% core, with anything above treated as upside to
be proven.

---

## 5. What is NOT yet proven

- **No real-operator data has touched any of this.** Every figure above is
  synthetic, generated from a calibrated simulation.
- **No market validation exists.** We have not shown that an operator will pay
  to solve the problem the diagnostic measures, or the problem the optimizer
  addresses.
- The optimizer's value depends on an unvalidated spot assumption (§4).
- "Validated" here means "internally consistent and correct on synthetic data,"
  not "validated against reality."

---

## 6. Honest claim language

**Can say:**
- "The engine works and the math is sound."
- "The diagnostic runs on an operator's own data today."
- "The stochastic layer is worth roughly +2–4% over a deterministic plan
  robustly, and more if emergency coverage is expensive — which we'd measure
  with your data, not assume."

**Cannot say:**
- "Validated" (without the synthetic-only qualifier).
- Any specific banked or guaranteed savings figure.
- "+17% savings" as a headline — it is contingent on a cheap-spot assumption we
  have not verified.

---

## 7. Parked / pending

**Reconciliation is deferred — on purpose.** Making System A (planning) the
canonical engine and wiring System B (diagnostic) into it is **not started**,
pending two real-world inputs that no amount of further simulation can supply:

1. **An operator's actual spot economics** — the parameter from §4 that decides
   whether the stochastic edge is ~0% or ~17%.
2. **Evidence the diagnostic addresses a problem operators will pay for** —
   market validation that does not yet exist.

We have six rounds of technical evidence and zero rounds of market evidence. The
next bottleneck is the market, not the code. No further engine phases are
scheduled without new (real) information.

### Known gaps (recorded so they are not lost — not a to-do list)

- **§9 calibration test** (`test_calibration.py`) — a test that the synthetic
  generator's outputs match the USDA/ERS targets it claims to hit. Not yet
  written.
- **Reorder-point / (s,S) baseline** — a simple inventory-policy baseline to sit
  alongside the deterministic LP, so the optimizer is benchmarked against the
  heuristic operators actually use, not just against an LP.
- **SAA optimality-gap reporting** — the stochastic program currently reports a
  solution but not a confidence bound on how close it is to the true optimum.

These are real omissions. They are listed here as known gaps, to be picked up
only if and when real operator data justifies resuming engine work.
