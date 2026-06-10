"""Cross-operator pooling hook (the third hierarchical level).

Today the supplier-yield population prior is "this operator's
suppliers." With multiple operators, operator populations should shrink
toward a global prior, so a new operator with thin history borrows
strength from the whole network — the data-moat property.

This module is the HOOK, deliberately not wired into the live path:
``global_prior`` refuses to pool fewer than two operators, and nothing in
the engine calls it while n_operators == 1. When a second operator
exists, wire its output in as the fallback prior in
risk/supplier_distribution.estimate_population.
"""

from __future__ import annotations

from risk.supplier_distribution import Population

MIN_OPERATORS_TO_POOL = 2


def global_prior(operator_populations: list[Population]) -> Population | None:
    """Precision-weighted pool of per-operator populations.

    Returns None below MIN_OPERATORS_TO_POOL — a single operator pooling
    with itself would only fabricate confidence.
    """
    pops = [p for p in operator_populations if p.n_deliveries > 0]
    if len(pops) < MIN_OPERATORS_TO_POOL:
        return None

    # Weight each operator by delivery count (its evidence).
    total_n = sum(p.n_deliveries for p in pops)
    mean = sum(p.mean * p.n_deliveries for p in pops) / total_n
    pooled_var = sum(p.pooled_variance * p.n_deliveries for p in pops) / total_n
    within = sum(p.within_variance * p.n_deliveries for p in pops) / total_n
    kappa = sum(p.kappa * p.n_deliveries for p in pops) / total_n

    return Population(
        mean=mean,
        pooled_variance=pooled_var,
        within_variance=within,
        kappa=kappa,
        n_deliveries=total_n,
        n_suppliers=sum(p.n_suppliers for p in pops),
        method="global_pooled",
    )
