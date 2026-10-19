# Public-data testing plan (first reproducible run)

Goal: one reproducible backtest of the ZAAD planner on a public dataset, with the synthetic assumptions named and
isolated, before any pilot claim. This plan is a scope note, not an implementation.

## Candidate datasets (demand side is public; supply side is not)

| dataset | what it gives | what it lacks |
|---|---|---|
| M5 (Walmart, Kaggle) | daily unit sales for 3,049 items, 10 stores, 5 years, prices, calendar | no purchase orders, suppliers, receipts, stock counts |
| Favorita (Corporación Favorita, Kaggle) | daily sales by store and item, promotions, oil price, holidays | same supply gap; perishables flagged |
| UCI Online Retail II | transaction lines with quantities and prices for one UK retailer | one node, no supply records |
| Instacart | order baskets | no quantities over time per SKU at a node |

None carries supplier deliveries, lead times or inventory. Every supply-side field must therefore be declared
synthetic and isolated (see below); the demand side is the only measured input.

## Schema mapping to the staging tables

- `stg_fmcg_skus`: item id, unit price from the dataset; unit cost = price × a declared margin assumption (labelled).
- `stg_fmcg_orders`: daily sales aggregated to weekly demand per item and store (`location_id` = store).
- `stg_fmcg_inventory`: NOT available. Options: (a) start every item at a declared cover of k weeks at the first
  origin with `snapshot_basis = START_OF_DAY` and `source_known_at` the origin minus one second, labelled
  SYNTHETIC_OPENING; (b) skip inventory-dependent metrics. H2 blocks planning without a count, so (a) is required
  and must be labelled.
- `stg_fmcg_purchase_orders`, `stg_fmcg_receipts`: NOT available. The replay's actual leg therefore has no
  ACTUAL_HISTORICAL_ACTION comparator; the only comparators are SYSTEM_BASELINE and RECONSTRUCTED_POLICY, and the
  H3a contract will say so (`comparator.type = NONE` for the actual leg, claim class MODEL_COMPARISON).
- Suppliers: one synthetic supplier per item with a declared lead time and fill distribution, labelled SYNTHETIC
  and held fixed across all policies.

## Baseline policies

Order-up-to, reorder point and base-stock at matched service targets, and the reconstructed rule inferred from the
synthetic ordering history the baseline itself generates (labelled as such). No operator plan exists, so
SHADOW_COMPARISON_MODE is NOT READY by construction and must be reported that way.

## Backtest methodology

Rolling-origin replay on weekly periods with the existing `zaad.full.historical` machinery; demand MEASURED from
the dataset, supply SIMULATED from the declared supplier model; frozen seeds; the leakage guard and H1b knowledge
rule unchanged (sales are known at the end of their day). Report settlement provenance shares on every leg.

## Evaluation metrics

Settled cost (purchase, carrying, shortage) per period and over the window with block-bootstrap intervals; unit
fill and periods with breaches; held-out validation folds as in the policy benchmark; stability of the decision
across seeds. No "savings": modelled differences between policies under one synthetic supply model.

## First run, minimal

M5, one store, 50 items with regular demand, 52 weeks of history then 12 weekly reviews; everything synthetic
isolated in one declaration file checked into `docs/remodel/evidence/`. Expected effort: a loader script and one
evidence note; no new ingestion platform.
