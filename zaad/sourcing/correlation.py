"""Shared-risk factors for the scenario worlds (P3).

The frozen sampler gives every source a standard-normal supply shock built from the failure domains it
shares (declared resource domains and itinerary nodes); sources with no shared domain are independent.
A declared risk group adds a common factor: for a member of groups g with correlations rho_g the shock
becomes sqrt(1 - sum rho_g) * z_frozen + sum sqrt(rho_g) * G_g, which keeps the marginal standard normal
(so fill and lead marginals are unchanged) and makes two members of one group share exactly rho_g of
their shock. The factors come from a separate generator (seed plus a P3 salt), so the frozen stream -
demand, supply, PO and truth draws - is consumed exactly as before.
"""
from __future__ import annotations

import numpy as np

SALT = 0x5AAD_0003


def group_factors(req, seed: int, count: int) -> dict[tuple[str, int, int], float]:
    """{(group id, world, period): standard normal} for every declared risk group."""
    rng = np.random.default_rng([int(seed), SALT, int(count), int(req.horizon)])
    out: dict[tuple[str, int, int], float] = {}
    for g in req.sourcing.risk_groups:
        draws = rng.standard_normal((count, req.horizon))
        for w in range(count):
            for t in range(req.horizon):
                out[g.id, w, t] = float(draws[w, t])
    return out
