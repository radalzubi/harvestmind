"""Cross-location demand correlation for the scenario worlds (P2).

The frozen sampler draws every service independently: one bootstrap path per service and one level
shock per service. A distribution network needs the joint structure across branches, because risk
pooling is worth exactly what the diversification between branches is worth. This module supplies a
Gaussian copula per correlation group (the services of one SKU): for every period the group's
services share a common standard-normal factor with weight sqrt(rho) and keep an idiosyncratic
factor with weight sqrt(1 - rho); the resulting uniform is pushed through each service's own fitted
quantile function (`forecast.sample(u=...)`), so every marginal is the fitted mixture unchanged and
only the dependence changes. The level shock (`level_se`, perfectly correlated across the horizon
within a service) shares the same group factor. rho = 1 makes the branches move together; rho = 0 is
never routed here (the frozen independent path runs instead).

The generator is separate from the frozen stream (`seed` plus a P2 salt) so the frozen draw's own
supply, PO and truth streams are unaffected when this is not in use.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

from zaad.full.contracts import Request

SALT = 0x5AAD_0002


def correlation_groups(req: Request) -> dict[str, list[str]]:
    """Services grouped by SKU (the unit that pools across locations), in request order."""
    groups: dict[str, list[str]] = {}
    for service in req.services:
        groups.setdefault(service.sku, []).append(service.id)
    return groups


def copula_draws(req: Request, seed: int, count: int) -> dict:
    """Per service: `u[service]` (count x horizon uniforms) and `level[service]` (count standard
    normals), correlated within each SKU group at `req.demand_correlation`."""
    rho = float(req.demand_correlation)
    common, own = math.sqrt(rho), math.sqrt(max(0., 1. - rho))
    rng = np.random.default_rng([int(seed), SALT, int(count), int(req.horizon)])
    u: dict[str, np.ndarray] = {}
    level: dict[str, np.ndarray] = {}
    for _sku, members in correlation_groups(req).items():
        z_common = rng.standard_normal((count, req.horizon))
        l_common = rng.standard_normal(count)
        for service_id in members:
            z_own = rng.standard_normal((count, req.horizon))
            l_own = rng.standard_normal(count)
            z = common * z_common + own * z_own
            # keep the uniform strictly inside (0, 1): the quantile function's tails are the fitted sizes
            u[service_id] = np.clip(norm.cdf(z), 1e-9, 1. - 1e-9)
            level[service_id] = common * l_common + own * l_own
    return {"u": u, "level": level, "rho": rho}
