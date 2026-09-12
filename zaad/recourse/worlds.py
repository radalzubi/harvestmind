"""Scenario tree worlds for adaptive recourse (P4).

A recourse solve needs worlds whose observable histories are shared exactly by several futures:
otherwise every information set holds one world and the branch decision is optimised against that
world's own future draw, which overstates adaptation. `draw_tree` builds a small tree from the frozen
sampler: `histories` first-stage draws, and at every review epoch each branch is spliced with
`continuations` independent futures (demand from the epoch on, fills and arrivals of lines placed
from the epoch on). Marginal distributions are the sampler's; persistence of supply shocks across an
epoch is dropped and documented. Weights are the products of the branch weights, normalised.
"""
from __future__ import annotations

from dataclasses import replace

from zaad.full.worlds import World, draw
from zaad.recourse.contracts import Recourse

MAX_TREE_WORLDS = 16


def splice(history: World, future: World, epoch: int, name: str, weight: float) -> World:
    """One world whose periods before `epoch` come from `history` and from `epoch` on from `future`."""
    demand = {s: tuple(history.demand[s][t] if t < epoch else future.demand[s][t] for t in range(len(history.demand[s]))) for s in history.demand}
    arrival = {k: (history.arrival[k] if k[1] < epoch else future.arrival[k]) for k in history.arrival}
    fills = {k: (history.fills[k] if k[1] < epoch else future.fills[k]) for k in history.fills}
    return replace(history, name=name, weight=weight, demand=demand, arrival=arrival, fills=fills)


def draw_tree(req, recourse: Recourse, seed: int, histories: int, continuations: int) -> list[World]:
    """`histories` x `continuations` ** (number of epochs) worlds, one shared history per branch."""
    worlds = draw(req, seed, histories)
    for k, epoch in enumerate(recourse.epochs):
        futures = draw(req, seed + 700 + 31 * k, continuations)
        total = sum(f.weight for f in futures) or 1.
        grown: list[World] = []
        for w in worlds:
            for j, f in enumerate(futures):
                grown.append(splice(w, f, epoch, f"{w.name}|e{epoch}.{j}", w.weight * f.weight / total))
        worlds = grown
    weight = sum(w.weight for w in worlds) or 1.
    return [replace(w, weight=w.weight / weight) for w in worlds]
