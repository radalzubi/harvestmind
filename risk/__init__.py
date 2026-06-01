"""Risk modeling layer for HarvestMind.

Produces the uncertainty quantities that both the diagnostic recommendations
and the two-stage stochastic optimizer consume:

  - supplier_distribution: hierarchical Beta-Binomial fill-rate distributions
  - shelf_life:            delivery-date-relative usability weights
  - safe_commit:           the unified safe-commit quantity
  - scenario_generation:   samples for the two-stage SP

One source of truth, three consumers (diagnostic, optimizer, backtest).
"""
