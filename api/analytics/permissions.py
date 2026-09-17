"""Analytics permissions over the existing governance: one auth system, no second one.

Roles are the four the workspace already has; the analytics capabilities were added to
`governance.CAPABILITIES` and every one of them is checked by the analytics router. On top of the
capability check, metrics and dimensions carry a `security_classification`, and a role may read only
the classes below:

  VIEWER    OPERATIONAL
  BUYER     OPERATIONAL + ECONOMIC
  APPROVER  OPERATIONAL + ECONOMIC + GOVERNANCE
  ADMIN     everything

RESTRICTED exists in the vocabulary for later scopes; nothing in V1 is classified RESTRICTED.
Row-level scopes below the workspace are not built (the actor record carries none); the permission
hash that keys the cache is therefore the role plus its readable classes.
"""
from __future__ import annotations

import hashlib
from typing import Any

from api.product.governance import Actor, Forbidden, need

CLASSES_BY_ROLE: dict[str, frozenset[str]] = {
    "VIEWER": frozenset({"OPERATIONAL"}),
    "BUYER": frozenset({"OPERATIONAL", "ECONOMIC"}),
    "APPROVER": frozenset({"OPERATIONAL", "ECONOMIC", "GOVERNANCE"}),
    "ADMIN": frozenset({"OPERATIONAL", "ECONOMIC", "GOVERNANCE", "RESTRICTED"}),
}


def readable_classes(actor: Actor | None) -> frozenset[str]:
    if actor is None:
        # permissive dev with no token: the workspace's own administrator
        return CLASSES_BY_ROLE["ADMIN"]
    return CLASSES_BY_ROLE.get(actor.role, CLASSES_BY_ROLE["VIEWER"])


def can_read(actor: Actor | None, classification: str) -> bool:
    return classification in readable_classes(actor)


def require(actor: Actor | None, capability: str) -> None:
    """Raise `Forbidden` unless the actor's role grants the capability. No actor = dev administrator."""
    if actor is None:
        return
    need(actor, capability)


def check(actor: Actor | None, capability: str) -> bool:
    try:
        require(actor, capability)
        return True
    except Forbidden:
        return False


def permissions_hash(actor: Actor | None) -> str:
    """What the cache key carries: role and readable classes, never the person."""
    role = actor.role if actor else "ADMIN"
    text = role + ":" + ",".join(sorted(readable_classes(actor)))
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def describe(actor: Actor | None) -> dict[str, Any]:
    return {"role": actor.role if actor else "ADMIN", "classes": sorted(readable_classes(actor)),
            "capabilities": sorted(actor.capabilities) if actor else ["*"]}
