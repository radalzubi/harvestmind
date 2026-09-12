"""Information sets (P4): deterministic grouping of a solve's worlds by their observable history
through each review epoch, and the node map the model builder indexes recourse columns by.

Two worlds share an information set at epoch e when every declared observable through period e-1
is equal after canonicalisation. Nothing about periods >= e, no labels, no seeds and no world order
enter the signature; the sets are sorted by signature so ids are order-independent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zaad.recourse.contracts import InformationSet, Recourse

PENDING = "pending"


def _quantise(value: float, grid: float) -> int:
    return int(round(float(value) / grid))


def observable_signature(req, recourse: Recourse, world, epoch: int) -> tuple:
    """Canonical observable history of one world through epoch-1 (see the design, section 4)."""
    spec = recourse.spec
    parts: list[Any] = []
    if "demand" in spec.observables:
        for service in sorted(req.services, key=lambda s: s.id):
            parts.append(("demand", service.id, tuple(_quantise(world.demand[service.id][t], spec.demand_grid) for t in range(epoch))))
    if "receipts" in spec.observables:
        seen_by = epoch - 1 - spec.confirmation_lag
        for source in sorted(req.sources, key=lambda s: s.id):
            for placed in range(epoch):
                due = int(world.arrival[source.id, placed])
                if due <= seen_by:
                    parts.append(("receipt", source.id, placed, due, _quantise(world.fills[source.id, placed], spec.fill_grid)))
                else:
                    parts.append(("receipt", source.id, placed, PENDING))
        for order in sorted(req.pipeline, key=lambda p: p.id):
            due = int(world.po_due.get(order.id, 10 ** 6))
            if due <= seen_by:
                parts.append(("po", order.id, due, _quantise(world.po_fill.get(order.id, 1.), spec.fill_grid)))
            else:
                parts.append(("po", order.id, PENDING))
    return tuple(parts)


def information_sets(req, recourse: Recourse, worlds: list) -> dict[int, tuple[InformationSet, ...]]:
    """Per epoch, the information sets of `worlds` (sorted by signature; ids `e<epoch>.<rank>`)."""
    out: dict[int, tuple[InformationSet, ...]] = {}
    for epoch in recourse.epochs:
        groups: dict[tuple, list[int]] = {}
        for w, world in enumerate(worlds):
            groups.setdefault(observable_signature(req, recourse, world, epoch), []).append(w)
        ordered = sorted(groups.items(), key=lambda kv: repr(kv[0]))
        out[epoch] = tuple(InformationSet(epoch=epoch, id=f"e{epoch}.{rank}", members=tuple(sorted(ws)),
                                          probability=float(sum(worlds[w].weight for w in ws)), signature=sig)
                           for rank, (sig, ws) in enumerate(ordered))
    return out


@dataclass(frozen=True)
class NodeMap:
    """What the model builder needs: for every period the nodes whose columns exist, and for every
    (world, period) the node that world reads. `None` is the here-and-now (root) node."""
    recourse: Recourse | None
    sets: dict[int, tuple[InformationSet, ...]]
    world_count: int
    perfect: bool = False

    def adapts(self, kind: str) -> bool:
        """Does this column kind ("purchase" / "transfer") adapt? Declared actions only; the
        perfect-information diagnostic adapts everything."""
        if self.perfect:
            return True
        return self.recourse is not None and kind in self.recourse.spec.actions

    def epoch(self, t: int, kind: str = "purchase") -> int | None:
        if not self.adapts(kind):
            return None
        if self.perfect:
            return 0
        return self.recourse.epoch_for(t) if self.recourse is not None else None

    def nodes(self, t: int, kind: str = "purchase") -> tuple[str | None, ...]:
        if not self.adapts(kind):
            return (None,)
        if self.perfect:
            return tuple(f"w{w}" for w in range(self.world_count))
        e = self.epoch(t, kind)
        return (None,) if e is None else tuple(s.id for s in self.sets[e])

    def node(self, w: int, t: int, kind: str = "purchase") -> str | None:
        if not self.adapts(kind):
            return None
        if self.perfect:
            return f"w{w}"
        e = self.epoch(t, kind)
        if e is None:
            return None
        for s in self.sets[e]:
            if w in s.members:
                return s.id
        raise KeyError(f"world {w} is in no information set at epoch {e}")

    def members(self, t: int, node: str | None, kind: str = "purchase") -> tuple[int, ...]:
        if node is None:
            return tuple(range(self.world_count))
        if self.perfect:
            return (int(node[1:]),)
        e = self.epoch(t, kind)
        assert e is not None
        return next(s.members for s in self.sets[e] if s.id == node)

    def set_of(self, node: str) -> InformationSet:
        for sets in self.sets.values():
            for s in sets:
                if s.id == node:
                    return s
        raise KeyError(node)


def node_map(req, recourse: Recourse | None, worlds: list, perfect: bool = False) -> NodeMap | None:
    """The node map for a solve, or None when no recourse column is needed (frozen builder path)."""
    if recourse is None and not perfect:
        return None
    if perfect:
        return NodeMap(recourse=recourse, sets={}, world_count=len(worlds), perfect=True)
    assert recourse is not None
    if len(worlds) < 1:
        return None
    return NodeMap(recourse=recourse, sets=information_sets(req, recourse, worlds), world_count=len(worlds))


def lookup(req, recourse: Recourse, sets: dict[int, tuple[InformationSet, ...]], world) -> dict[int, tuple[str | None, bool]]:
    """Policy lookup for a world that was not in the solve: per epoch, the information set whose
    canonical signature equals the world's observable history, exactly, or `(None, False)` when no
    modelled branch matches. Release rule (P4 release audit, blocker B): there is no nearest-signature
    routing anywhere. An observation outside the modelled branches never selects a branch action; the
    caller applies the declared fallback (`policy.world_plan`: the static commitments, REPLAN_REQUIRED)."""
    out: dict[int, tuple[str | None, bool]] = {}
    for epoch, members in sets.items():
        sig = observable_signature(req, recourse, world, epoch)
        exact = [s for s in members if s.signature == sig]
        out[epoch] = (exact[0].id, True) if exact else (None, False)
    return out
