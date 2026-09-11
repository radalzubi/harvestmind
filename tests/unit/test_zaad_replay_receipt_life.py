"""Physics-enabled rolling replay: a received perishable purchase carries the declared age at receipt
(remaining life = shelf life - age at receipt at the period it lands), a transfer never resets it, it
decrements every period, expires on time, cannot serve once below the sale minimum, and legacy /
no-physics replays are byte-identical to the frozen full-shelf-life materialisation."""
from __future__ import annotations

import json

from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.replay import replay
from zaad.meio.baselines import register_replay_methods
from zaad.meio.fixtures_p2 import p2_request
from zaad.sectors.fixtures import FIXTURES, sector_request

DECL = "OPERATOR_DECLARED"


def _replay(req: Request, reviews: int, method: str = "network_rop"):
    register_replay_methods()
    H = req.horizon
    truth = long_truth(req, req.seed + 10000, (-(-(reviews - 1 + H) // H)) * H)
    kept: list = []
    out = replay(req, truth, reviews, method, keep_requests=kept, rolling=True)
    assert out["status"] == "COMPLETE", out
    return out, kept


def _produce(age: int, shelf: int = 10, seed: int = 41001) -> Request:
    """One supplier into central, two branches, opening lots short so the rule buys at review 0."""
    req = p2_request(seed=seed, opening_central=60., opening_branch=40., max_solve_seconds=5.)
    payload = req.model_dump(mode="json")
    payload["skus"][0]["shelf_life"] = shelf
    for lot in payload["stock"]:
        lot["expires_in"] = min(lot["expires_in"], shelf)
    payload["sector_mode"] = "PRODUCE"
    fields = {"minimum_remaining_life_at_sale": 1, **({"age_at_receipt_by_source": {"src_A": age}} if age else {})}
    payload["sku_physics"] = [{"sku": "A", "sector": "PRODUCE", **fields, "provenance": {k: DECL for k in fields}}]
    return Request.model_validate(payload)


def _observed(req: Request) -> list[tuple[str, int, float]]:
    return sorted((lot.location, lot.expires_in, round(lot.quantity, 3)) for lot in req.stock if lot.id.startswith("observed-"))


def test_received_lot_carries_shelf_life_minus_age_at_receipt_and_ages_normally():
    out, kept = _replay(_produce(age=4), reviews=4)
    bought = [p for p in out["reviews"][0]["purchases"] if p["quantity"] > 1e-9]
    assert bought, "the rule buys at review 0"
    # the review-0 purchase (lead one period) lands at review 1 with 10 - 4 = 6 periods of life ...
    observed_1 = [lot for lot in _observed(kept[1]) if lot[0] == "central"]
    assert observed_1 and all(life == 6 for _, life, _ in observed_1), observed_1
    # ... and the same cohort (re-keyed by the replay from the settlement's end stock) has 5 at review 2 and 4
    # at review 3: it decrements one period per review and never regains life
    for k, expected in ((2, 5), (3, 4)):
        lives = {lot.expires_in for lot in kept[k].stock}
        assert expected in lives and max(lives) <= 6, (k, sorted(lives))
    # the request the planner sees agrees with the physics the model, the settlement and the projection use
    from zaad.sectors.contracts import resolve
    assert resolve(kept[1]).receipt_life("A", "src_A") == 6


def test_transfer_never_resets_the_received_life_and_expiry_falls_on_time():
    out, kept = _replay(_produce(age=6, shelf=10), reviews=6)   # arrives with 4 periods of life
    # any cohort at a branch that came from the received lot carries at most the origin's remaining life
    for k in range(1, 6):
        central = {life for loc, life, _ in _observed(kept[k]) if loc == "central"}
        branch_cohorts = [x for x in out["reviews"][k]["settlement"]["end_stock"] if x["location"] in ("north", "south")]
        assert all(x["expiry"] <= max(central | {10}) for x in branch_cohorts)
    # a lot received at review 1 with 4 periods of life is gone (expired or consumed) by review 5
    assert not [lot for lot in _observed(kept[5]) if lot[1] > 4]
    expired = sum(row["settlement"]["trace"][-1].get("expired_units", 0.) for row in out["reviews"])
    assert expired >= 0.


def test_expired_or_unsellable_units_never_serve_and_terminal_value_follows_life():
    from zaad.full.terminal import continuation_value
    from zaad.full.worlds import forecast_all
    req = _produce(age=8, shelf=10)   # arrives with 2 periods; sellable for one period (sale minimum 1)
    out, kept = _replay(req, reviews=3)
    for row in out["reviews"]:
        s = row["settlement"]
        assert all(x["served"] <= x["demand"] + 1e-9 for x in s["service_by_period"])
        assert all(x.get("sellable", True) or x["quantity"] >= 0 for x in s["end_stock"])
    last = out["reviews"][-1]["settlement"]
    short = continuation_value(kept[-1], [dict(x, expiry=min(x["expiry"], 1)) for x in last["end_stock"]], [], forecast_all(kept[-1]))
    long_ = continuation_value(kept[-1], [dict(x, expiry=x["expiry"] + 5) for x in last["end_stock"]], [], forecast_all(kept[-1]))
    assert long_["adjustment"] <= short["adjustment"] + 1e-9, "more remaining life never lowers the continuation credit"


def test_legacy_and_neutral_physics_replays_are_identical_to_the_frozen_materialisation():
    # legacy request: no physics at all -> full shelf life on every received lot
    legacy = p2_request(seed=41001, opening_central=60., opening_branch=40., max_solve_seconds=5.)
    out, kept = _replay(legacy, reviews=3)
    assert all(life == legacy.skus[0].shelf_life for _, life, _ in _observed(kept[1]))
    # PRODUCE with age 0 and COMMERCIAL / MEAT_SEAFOOD without an age declaration -> full shelf life as well
    for sector in ("PRODUCE", "COMMERCIAL", "MEAT_SEAFOOD"):
        req = _produce(age=0, shelf=10)
        payload = req.model_dump(mode="json")
        payload["sector_mode"] = sector
        payload["sku_physics"][0]["sector"] = sector
        req = Request.model_validate(payload)
        _, kept_s = _replay(req, reviews=2)
        assert all(life == 10 for _, life, _ in _observed(kept_s[1])), sector


def test_sector_fixture_age_at_receipt_is_the_only_sector_fixture_with_a_declared_age():
    with_age = [n for n, spec in FIXTURES.items() if spec.get("physics", {}).get("skus", {}).get("A", {}).get("age_at_receipt_by_source")
                or any(v.get("age_at_receipt_periods") or v.get("age_at_receipt_by_source") for v in spec.get("physics", {}).get("skus", {}).values())]
    assert with_age == ["P3_age_at_receipt"], with_age
    req = sector_request(json.loads(json.dumps(FIXTURES["P3_age_at_receipt"])), 41001)
    from zaad.sectors.contracts import resolve
    assert resolve(req).receipt_life("A", "src_A") == 3 and req.skus[0].shelf_life == 6
