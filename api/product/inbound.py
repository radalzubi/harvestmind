"""Where data comes in, as a seam.

Today every record enters through the upload path (`api/routers/intake.py`): a file, validated,
into the operator's own staging tables. Later a connector may pull products, inventory, purchase
orders, receipts, customer orders and suppliers from a system directly. Both must land the same
staging tables through the same validation, so this module names the contract and nothing more.
It does not replace the upload path and adds no framework.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

#: The sources a connector may sync, each to the staging table the upload path already validates.
INBOUND_SOURCES: dict[str, str] = {
    "products": "stg_fmcg_skus",
    "inventory": "stg_fmcg_inventory",
    "purchase_orders": "stg_fmcg_purchase_orders",
    "receipts": "stg_fmcg_receipts",
    "customer_orders": "stg_fmcg_orders",
    "suppliers": "stg_fmcg_suppliers",
}


@dataclass(frozen=True)
class SyncResult:
    source: str
    rows: int
    replaced: bool
    detail: str


class InboundConnector(Protocol):
    name: str
    real: bool

    def describe(self) -> dict[str, Any]: ...
    def available_sources(self) -> list[str]: ...
    def pull(self, source: str, *, since: str | None = None) -> list[dict[str, Any]]: ...


class UploadPath:
    """The one real inbound path: the operator's own files through the existing intake."""

    name = "upload"
    real = True

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "real": True, "sources": sorted(INBOUND_SOURCES),
                "note": "Files the operator uploads, validated into their own vault. Nothing is pulled from anywhere."}

    def available_sources(self) -> list[str]:
        return sorted(INBOUND_SOURCES)

    def pull(self, source: str, *, since: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("the upload path is pushed by the operator; it does not pull")
