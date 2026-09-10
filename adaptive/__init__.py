"""The adaptive state layer: signals -> state -> posture.

Sits between the data and the optimizer. It infers the current operating
state from what has actually been observed, expresses it as regime
probabilities and a stress score with named components, and turns that
into an optimization POSTURE (how much freedom, how much risk aversion,
how wide the scenarios, how far from the incumbent, how long to commit).
Nothing here decides an order; it decides how the optimizer is allowed to.
"""
