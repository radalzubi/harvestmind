"""Two replay crashes from the M5 cash variant (run 1, commit ae1b73c), both engine defects.

1. A floating residue of debt (8.9e-16) above a zero credit limit made the rolled-forward request fail validation
   ("opening_debt <= credit_limit"), ending the run with an exception for every policy on that series.
2. A series with no opening stock, no inbound and no prepaid lots produced a settlement ledger without `opening_assets`
   and the replay raised KeyError at its first review."""
from __future__ import annotations

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.model import Solution
from zaad.full.replay import replay
from zaad.full.settlement import settle
from zaad.full.worlds import draw


def _bare(req: Request) -> Request:
    return req.model_copy(update={"incumbent_rule": None, "pipeline": (), "inbound_transfers": (), "order_lines": (), "incumbent_orders": ()})


def test_sub_tolerance_cash_residue_never_becomes_debt_above_the_credit_limit():
    req = _bare(example())
    H = req.horizon
    liquidity = req.liquidity.model_copy(update={"opening_cash": 0.3, "opening_debt": 0., "credit_limit": 0., "minimum_cash": 0., "interest_per_period": 0.,
                                                 "known_receivables": tuple([0.] * H), "other_payments": tuple([0.1 + 0.2] + [0.] * (H - 1))})
    req = req.model_copy(update={"liquidity": liquidity})
    world = draw(req, 1, 1)[0]
    plan = Solution("OPTIMAL", {}, {}, {}, {}, None, [], 0., 0, 0, None, 0., ["test"])
    out = settle(req, plan, world, steps=1)
    assert 0.3 - (0.1 + 0.2) < 0                       # the arithmetic residue the test relies on (-5.6e-17)
    assert out["trace"][0]["debt"] == 0. and out["trace"][0]["cash"] == 0.
    rolled = req.model_copy(update={"liquidity": liquidity.model_copy(update={"opening_cash": out["trace"][0]["cash"], "opening_debt": out["trace"][0]["debt"]})})
    Request.model_validate(rolled.model_dump())        # the next review's request is valid


def test_a_request_with_no_stock_or_inbound_has_an_opening_assets_ledger_and_replays():
    req = _bare(example()).model_copy(update={"stock": ()})
    world = draw(req, 3, 1)[0]
    plan = Solution("OPTIMAL", {}, {}, {}, {}, None, [], 0., 0, 0, None, 0., ["test"])
    out = settle(req, plan, world, steps=1)
    assert out["ledger"]["opening_assets"] == 0.
    from zaad.full.evaluation import long_truth
    result = replay(req, long_truth(req, 2, 2 - 1 + req.horizon), 2, "order_up_to", rolling=True)
    assert result["status"] == "COMPLETE", result.get("failure")
