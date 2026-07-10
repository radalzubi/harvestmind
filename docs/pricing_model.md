# HarvestMind — Pricing Model (Gain-Share)

_One-page pricing model for the deck. Figures are modeled on synthetic operators
(2-year simulated datasets) and are directional pending pilot validation._

---

## The model: we get paid from the savings, not before them

**HarvestMind charges a percentage of the validated savings it delivers.**
No subscription. No up-front fee. If we don't move the number, the operator
pays nothing. This aligns our incentive exactly with the operator's P&L and
removes the budget objection that kills most analytics pilots.

> **Headline:** *"25% of the savings we prove. No savings, no fee."*

---

## Where the savings come from

Every perishable operator loses money two ways. On a typical produce
distributor these run, annualized:

| Leak | Size (modeled) |
|---|---|
| Cash spoilage / waste | **~7.5% of revenue** |
| Lost margin on missed orders (fill rate ~89%) | **~1.8% of revenue** (18% margin on ~10% missed revenue) |
| **Recoverable economic loss** | **~9.3% of revenue** |

HarvestMind's optimizer recovers a **15–30%** slice of that loss by cutting
emergency spot buys and lifting fill rate. **Recoverable savings ≈ ~2% of the
operator's revenue per year.** Savings are measured against a leakage-guarded
"what would have happened" baseline — the same rolling-origin backtest that
underwrites the number is also the billing meter.

---

## What it means per operator (25% gain-share)

| Operator | Revenue/yr | Recoverable savings | **Operator keeps** | **HarvestMind** |
|---|--:|--:|--:|--:|
| Micro food hub | $0.75M | $16K | $12K | $4K |
| Small distributor | $3M | $63K | $47K | $16K |
| Regional hub | $8M | $168K | $126K | $42K |
| Large distributor | $25M | $524K | $393K | $131K |
| Very large distributor | $75M | $1.57M | $1.18M | $393K |

The operator always keeps **75%** of a number they weren't capturing at all.
HarvestMind revenue ≈ **0.5% of the operator's top line** — and scales linearly
with their size.

---

## Recommended structure

- **≥ $3M revenue → pure gain-share, 25% of validated savings.** Clean, no
  base fee, easiest "yes."
- **$1M–$3M revenue → hybrid:** a small base (≈ $500/mo) **+** 15% gain-share,
  to cover onboarding/measurement cost-to-serve while keeping skin in the game.
- **< $1M → low-touch / self-serve only** (or defer): gain-share alone doesn't
  cover a high-touch cost-to-serve at that scale.

### Why the floor exists (unit economics)
At a flat **$15K/yr cost-to-serve**, pure 25% gain-share **breaks even at
~$2.9M operator revenue**. Below that, the take doesn't cover the cost of
serving the account; above it, contribution margin climbs fast.

| Operator | Contribution at 25% take, $15K cost-to-serve | Margin |
|---|--:|--:|
| Micro $0.75M | **−$11K** | unprofitable |
| Small $3M | +$0.7K | ~break-even |
| Regional $8M | +$27K | 64% |
| Large $25M | +$116K | 89% |
| Very large $75M | +$378K | 96% |

**Go-to-market implication:** target **$3M+ operators**. That's where pure
gain-share is profitable on day one and the deal is friction-free.

### Break-even by take rate × cost-to-serve (operator revenue needed)

| Cost-to-serve | Take 15% | Take 20% | Take 25% | Take 30% |
|---|--:|--:|--:|--:|
| $10K | $3.2M | $2.4M | $1.9M | $1.6M |
| $15K | $4.8M | $3.6M | $2.9M | $2.4M |
| $25K | $7.9M | $6.0M | $4.8M | $4.0M |

Lower cost-to-serve (productized onboarding, automated measurement) is the
lever that opens the small-operator market to pure gain-share.

---

## Robustness

At an $8M regional hub, HarvestMind's 25% revenue stays healthy across the
assumption range — **$26K (conservative: 15% recovery, 12% margin) to $60K
(optimistic: 30% recovery, 25% margin)** — comfortably above cost-to-serve in
every corner. The model is not balanced on a knife-edge assumption.

---

## Honest caveats (for internal use, not the slide)

1. **Synthetic, modeled — not yet validated** on a real operator. These are
   directional. A paid pilot with a real baseline is the next proof point.
2. **Two assumptions drive everything:** the ~18% margin on missed orders and
   the 15–30% recovery band. Both are adjustable; the deck uses the midpoints.
3. **Gain-share lives or dies on measurement.** The contract needs an agreed,
   defensible baseline clause. The leakage-guarded backtest is that mechanism —
   it is a feature to sell, but it must be written into the agreement.
4. **Structure held constant** across scales in the simulation (same product /
   supplier counts), so this models how value scales with throughput, not with
   SKU/supplier complexity (which would add upside at the top end).
