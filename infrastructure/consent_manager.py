"""Consent management — pool participation is opt-in, hard infrastructure.

Consent lives in TWO places that must never drift: the operator's own
vault (data/operators/<id>/consent.json — their record, with full
history) and the registry (fast lookup for the contribution pipeline).
This module is the ONLY writer of both. Nothing else may touch either.

Withdrawal semantics, stated plainly: future contributions stop
immediately; anonymized signals already in the pool are not reversible
to the operator and therefore remain. Operators are told this BEFORE
consenting (docs/POOL_PRIVACY.md).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from infrastructure.operator_registry import OperatorRegistry

ConsentMethod = Literal["onboarding_form", "api_call", "dashboard_toggle"]


class ConsentEvent(BaseModel):
    consented: bool
    method: str
    at: datetime


class ConsentRecord(BaseModel):
    operator_id: str
    consented: bool
    method: str
    updated_at: datetime
    history: list[ConsentEvent] = Field(default_factory=list)
    withdrawal_note: str = (
        "Withdrawing stops all future pool contributions immediately. "
        "Anonymized signals already contributed cannot be traced back to "
        "you and therefore cannot be selectively removed."
    )


class ConsentManager:
    def __init__(self, registry: OperatorRegistry) -> None:
        self.registry = registry

    def _consent_file(self, operator_id: str):
        return (self.registry.operators_dir / operator_id / "consent.json")

    def record_consent(
        self,
        operator_id: str,
        consented: bool,
        method: ConsentMethod = "api_call",
    ) -> ConsentRecord:
        """Write consent to BOTH stores atomically-enough (vault first,
        then registry; a crash between the two is corrected on next write
        because the vault file is authoritative for history)."""
        rec = self.registry.get_operator(operator_id)
        now = datetime.now(timezone.utc)

        existing = self.get_consent(operator_id)
        history = existing.history if existing else []
        history.append(ConsentEvent(consented=consented, method=method, at=now))

        consent = ConsentRecord(
            operator_id=operator_id, consented=consented,
            method=method, updated_at=now, history=history,
        )
        f = self._consent_file(operator_id)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(consent.model_dump_json(indent=2))

        rec.pool_consent = consented
        rec.pool_consent_date = now
        self.registry._update_record(rec)
        return consent

    def get_consent(self, operator_id: str) -> Optional[ConsentRecord]:
        f = self._consent_file(operator_id)
        if not f.exists():
            return None
        return ConsentRecord.model_validate(json.loads(f.read_text()))

    def withdraw_consent(self, operator_id: str) -> ConsentRecord:
        return self.record_consent(operator_id, False, method="api_call")

    def get_consented_operators(self) -> list[str]:
        """Operator ids the pool contribution pipeline may read. Active
        AND consented — suspension or deletion gates contributions even
        if the consent flag was never flipped."""
        return [r.operator_id for r in self.registry.list_operators("active")
                if r.pool_consent]
