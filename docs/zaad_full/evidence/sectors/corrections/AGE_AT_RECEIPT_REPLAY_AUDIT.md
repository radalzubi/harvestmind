# Audit: age-at-receipt in the rolling replay (2026-09-11, P3 corrective pass)

Scope: prove from code what changed between the released sector runtime `5ca3772` and the P3 product
freeze `9e496ed` for perishable receipts, where it activates, and which path (live planner or historical
replay) it touches. Historical tags `43d769f`, `4f358f7`, `5ca3772`, `p3-frozen-product` = `9e496ed` and
`p3-frozen` = `628d49f` are not moved by this audit.

## The exact code change

`git diff 5ca3772 9e496ed -- zaad/full/replay.py` contains two hunks. The second (incumbent-mix adoption
after an executed switch) is P3 behaviour behind `req.sourcing is not None` and is not the subject here.
The first is the correction, in `zaad.full.replay.replay`, in the block that materialises purchase
orders that have arrived at the current review ("OBSERVE arrivals at the current origin"):

```python
# before (5ca3772)
state["stock"].append({..., "expires_in": sku.shelf_life, "age_periods": 0})

# after (9e496ed), first present in commit 33f96cc
from zaad.sectors.contracts import resolve as sector_physics
physics = sector_physics(req)
...
life = sku.shelf_life if physics is None else physics.receipt_life(source.sku, source.id)
state["stock"].append({..., "expires_in": life, "age_periods": 0})
```

`Physics.receipt_life(sku, source) = shelf_life - age_at_receipt(sku, source)`, where the age is the
source-specific declared value, else the SKU-level declared value, else 0 (`zaad/sectors/contracts.py`,
unchanged since `43d769f`).

| item | finding |
|---|---|
| affected function | `zaad.full.replay.replay`, PO materialisation only |
| original behaviour | every received purchase became opening stock with `expires_in = sku.shelf_life`, whatever the declared age at receipt |
| corrected behaviour | on a physics request the received lot carries `shelf_life - age_at_receipt(sku, source)` periods; on a legacy request `shelf_life` exactly as before |
| activation condition | `zaad.sectors.contracts.resolve(req) is not None`, i.e. the request declares `sector_mode` or any `sku_physics`; the numeric effect is non-zero only when an age at receipt is declared for the source (or the SKU) |
| first commit containing it | `33f96cc` ("fix(zaad): P3 benchmark corrections, replay receipt life and API error code"); the runtime tree of `9e496ed` is identical to `33f96cc` (`git diff 33f96cc 9e496ed -- zaad api db` empty) |

## Planner, settlement, projection: unchanged and already correct

The live planner path already used the declared receipt life before the correction and is untouched by it:

* `zaad/full/model.py` line 528: `expiry = due + (shelf_life if physics is None else physics.receipt_life(source.sku, source.id))` for every purchase column; line 492 makes a source whose receipt life is at or below the receipt minimum ineligible; line 682 does the same for PO amendments.
* `zaad/full/settlement.py` lines 111, 161, 185: pending receipts (open POs and executed purchases) carry `physics.receipt_life`; a source below the receipt minimum raises `PhysicalViolation`.
* `zaad/meio/baselines.py` lines 99-100, 114, 217, 257: the network rule projection uses the same receipt life and eligibility.

None of these lines differ between `5ca3772` and `9e496ed` for receipt life (`git diff` of the three
files shows only the P3 hooks: sourcing view, share rows, switching, incumbent-mix split, resource fit).
Live planner semantics for age at receipt are therefore unchanged: the correction is confined to the
truth side of the rolling replay (`replay.py`), i.e. historical evaluation semantics.

Consequences within the original code: on a replay, the planner priced an import as arriving old (life 3
of 6 on fixture P3_age_at_receipt) and avoided it where a fresher local source existed, but the truth
handed it the full 6 periods when the PO landed. The evaluation therefore credited the "old" source with
freshness the physics denied; every cohort downstream of that lot (transfers, FEFO, expiry, sellable
service, terminal value) inherited the wrong life. The settlement of the review in which the purchase
was placed was correct (it prices the pending receipt itself); the defect entered only when the replay
turned the arrived PO into next-review opening stock.

## What is and is not affected

| path | changed? | why |
|---|---|---|
| legacy request (no `sector_mode`, no `sku_physics`) | no | `resolve` is None; `expires_in = sku.shelf_life` as before (bit-identical materialisation) |
| COMMERCIAL / MEAT_SEAFOOD / PRODUCE request with no age at receipt declared | no | `receipt_life = shelf_life - 0 = shelf_life` |
| PRODUCE request with age at receipt 0 | no | same |
| any physics request with a declared non-zero age at receipt | yes, replay truth only | received lots now carry `shelf_life - age` |
| live planner (`plan`, `solve`, `settle`, projections) | no | already used `receipt_life`; lines unchanged |
| P0 / P1 / P2 records | no | legacy requests throughout |
| sector record | 14 of 416 ZAAD reviews (fixture P3_age_at_receipt, the only sector fixture declaring an age at receipt) | see `AGE_AT_RECEIPT_REPLAY_CORRECTION.md` for the review-by-review table and the counterfactual |

Test: `tests/unit/test_zaad_replay_receipt_life.py` (shelf life 10, age 4 -> received life 6, decrementing
5, 4; transfer never resets; expiry on time; unsellable units never serve; more life never lowers the
continuation credit; legacy / neutral-age / COMMERCIAL / MEAT_SEAFOOD replays keep the full shelf life;
P3_age_at_receipt is the only sector fixture with a declared age).
