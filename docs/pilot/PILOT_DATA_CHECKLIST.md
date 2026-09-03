# Pilot data checklist (FMCG)

No commercial claim in this repository is proven until a real operator's
history has been evaluated. This is what that evaluation needs, and what
each missing item costs. `GET /fmcg/readiness` scores an upload against it
(`ingestion/pilot_readiness.py`).

## Required

| data | table | why |
|---|---|---|
| SKU master with supplier, unit cost, case pack | `stg_fmcg_skus` | the decision variables and their unit |
| historical customer orders (SKU, date, quantity) | `stg_fmcg_orders` | demand history for every fold |
| historical purchase orders | `stg_fmcg_purchase_orders` | the incumbent's actual behaviour; supplier lead |
| receipts against POs | `stg_fmcg_receipts` | actual supplier fill and lead, replayed in selection |
| inventory snapshots | `stg_fmcg_inventory` | opening state at every fold origin |
| costs and prices or contribution margins | `stg_fmcg_skus.contribution_margin` / `unit_price` | the shortage cost; without it the plan cannot price a lost sale |
| pack / MOQ | `stg_fmcg_skus` | whole-lot feasibility |
| supplier identities | `stg_fmcg_skus.supplier_id`, `stg_fmcg_suppliers` | supply uncertainty is per supplier |

At least **26 weeks** of order history is needed for multi-fold selection;
52 is preferred so seasonality can be resampled.

## Strongly preferred

| data | table / field | conclusion it protects |
|---|---|---|
| promised receipt dates | `stg_fmcg_purchase_orders.expected_delivery_date` | on-time measurement |
| partial receipts | multiple `stg_fmcg_receipts` rows per PO | quantity-over-time arrival modelling |
| supplier capacities | `stg_fmcg_skus.supplier_capacity_per_week`, `stg_fmcg_suppliers.capacity_per_week` | without them capacity is INFERRED from PO peaks |
| cancellations, stock adjustments, write-offs | (planned: `stg_fmcg_adjustments`) | waste and shrink economics |
| emergency purchases | flag on `stg_fmcg_purchase_orders` (planned) | the real cost of expediting |
| service penalties, freight | `stg_fmcg_economics` | SLA and landed-cost terms |
| promotions calendar | `stg_fmcg_promotions` | promotions as planned inputs, not surprises |
| location | `stg_fmcg_inventory.location_id` | transfers |
| route / carrier / port / manufacturer | `stg_fmcg_suppliers.route`, `.manufacturer` | correlated disruption |
| historic planner overrides | (planned) | the true incumbent, not just the PO log |

## Provenance and autonomy

Every commercially decisive parameter carries a provenance: OPERATOR,
MEASURED, PUBLIC_BENCHMARK, ASSUMED or UNKNOWN. The plan's autonomy is
reduced where a decisive term is UNKNOWN: those SKUs are anchored to the
incumbent and the response says why. Carrying cost is entered as named
annual components (`domain/carrying_cost.py`) and every plan reports a
sensitivity sweep over it, because the validation showed the policy
ranking can reverse with it.

## Classification of evidence

| label | meaning |
|---|---|
| REAL OPERATOR | the client's own records (none in this repository) |
| REAL PUBLIC | US Census, IMF PortWatch and other public series in `data/external/` |
| SYNTHETIC CALIBRATED | simulator output shaped by public benchmarks |
| ASSUMED | a stated default with no measurement behind it |
