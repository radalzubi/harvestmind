"""Civil logistics observations with explicit availability and licensed provenance.

No networking occurs while selecting evidence. Hazard scores are descriptive,
not calibrated disruption probabilities or legal/navigation instructions.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlsplit

import requests
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

OPEN_LICENSES = frozenset({"open_verified", "contract_verified"})
NOAA_URL = "https://api.weather.gov/alerts/active"
MAX_RESPONSE_BYTES = 4_000_000
MAX_RECORDS = 2000


def _utc(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timestamp must be an aware UTC datetime")
    offset = value.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError("timestamp must use UTC; normalize explicitly in the adapter")
    return value.astimezone(timezone.utc)


class Signal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, allow_inf_nan=False)

    id: str = Field(min_length=1, max_length=512)
    provider: str = Field(min_length=1, max_length=80)
    entity_ids: tuple[str, ...] = Field(min_length=1, max_length=128)
    kind: Literal["physical", "news", "official"]
    observed_at: datetime
    published_at: datetime
    ingested_at: datetime
    effective_at: datetime
    valid_until: datetime
    magnitude: float = Field(ge=0)
    direction: Literal["deterioration", "recovery"]
    confidence: float = Field(ge=0, le=1)
    source_url: str = Field(max_length=2048)
    syndication_key: str = Field(min_length=1, max_length=512)
    adapter_version: str = Field(min_length=1, max_length=80)
    license_status: Literal["open_verified", "contract_verified", "legal_review", "unknown", "denied"]
    historical_eligible: bool = True
    availability_basis: Literal["captured", "synthetic_fixture", "reconstructed_date_only"] = "captured"
    historical_available_after: datetime | None = None

    @field_validator("observed_at", "published_at", "ingested_at", "effective_at", "valid_until", mode="before")
    @classmethod
    def aware_utc(cls, value: Any) -> datetime:
        return _utc(value)

    @field_validator("historical_available_after", mode="before")
    @classmethod
    def optional_utc(cls, value: Any) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator("entity_ids")
    @classmethod
    def valid_entities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not x or len(x) > 160 or any(ord(c) < 32 for c in x) for x in value):
            raise ValueError("invalid entity identifier")
        if len(set(value)) != len(value):
            raise ValueError("duplicate entity identifier")
        return value

    @field_validator("source_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        p = urlsplit(value)
        if p.scheme != "https" or not p.hostname or p.username or p.password:
            raise ValueError("source URL must be credential-free HTTPS")
        return value

    @model_validator(mode="after")
    def chronology(self) -> Signal:
        if max(self.observed_at, self.published_at) > self.ingested_at:
            raise ValueError("observed/publication time cannot follow ingestion")
        if self.valid_until <= self.effective_at:
            raise ValueError("valid_until must follow effective_at")
        if self.availability_basis == "reconstructed_date_only" and self.historical_eligible:
            raise ValueError("reconstructed publication dates are not captured historical vintages")
        return self


class SignalStore(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    signals: tuple[Signal, ...] = ()

    def replay(self, records: tuple[Signal | dict, ...] | list[Signal | dict]) -> SignalStore:
        """Validate the entire batch before returning a new immutable store.

        Duplicate identical IDs are idempotent; changed content under an existing
        ID is refused. Revisions need a new ID and the same syndication key.
        """
        if len(records) > MAX_RECORDS:
            raise ValueError("signal batch exceeds record bound")
        parsed = tuple(x if isinstance(x, Signal) else Signal.model_validate(x) for x in records)
        existing = {x.id: x for x in self.signals}
        for signal in parsed:
            if signal.id in existing and existing[signal.id] != signal:
                raise ValueError("signal ID collision; revisions require a new ID")
            existing[signal.id] = signal
        return SignalStore(signals=tuple(existing[k] for k in sorted(existing)))

    def as_of(self, when: datetime, *, historical: bool = True) -> tuple[Signal, ...]:
        when = _utc(when)
        return tuple(s for s in self.signals if (
            s.license_status in OPEN_LICENSES
            and (not historical or s.historical_eligible)
            and max(s.observed_at, s.published_at, s.ingested_at) <= when
            and s.effective_at <= when < s.valid_until
        ))


class RouteEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    physical_severity: float = 0.0
    official_severity: float = 0.0
    independent_news_count: int = 0
    signal_ids: tuple[str, ...] = ()
    recovery_signal_ids: tuple[str, ...] = ()
    unavailable_reason: str | None = None
    calibrated_probability: bool = False


def route_evidence(signals: tuple[Signal, ...] | list[Signal] | SignalStore,
                   entity_ids: tuple[str, ...] | list[str], as_of: datetime) -> RouteEvidence:
    """Visible, licensed evidence, deduplicated before fixed freshness decay.

    News count requires different providers AND different syndication keys.
    Recovery supersedes an earlier signal in the same source/event family;
    it does not erase an independent contradictory source.
    """
    when = _utc(as_of)
    store = signals if isinstance(signals, SignalStore) else SignalStore(signals=tuple(signals))
    # Keep expired versions until after supersession: an expired cancellation
    # must not resurrect an older, longer-lived warning.
    relevant = [s for s in store.signals if (
        s.historical_eligible and s.license_status in OPEN_LICENSES
        and max(s.observed_at, s.published_at, s.ingested_at) <= when
        and s.effective_at <= when and set(entity_ids).intersection(s.entity_ids)
    )]
    newest: dict[tuple[str, str], Signal] = {}
    for s in sorted(relevant, key=lambda x: (x.published_at, x.ingested_at, x.id)):
        newest[(s.kind, s.syndication_key)] = s
    if not newest:
        return RouteEvidence(unavailable_reason="no licensed, causal, unexpired evidence for route")
    severity = {"physical": 0.0, "official": 0.0}
    news_providers: set[str] = set()
    retained: list[str] = []
    recoveries: list[str] = []
    for s in newest.values():
        if when >= s.valid_until:
            continue
        half_life = {"physical": 6.0, "news": 12.0, "official": 24.0}[s.kind]
        age_hours = max(0.0, (when - s.observed_at).total_seconds() / 3600)
        weight = math.exp2(-age_hours / half_life)
        # Fixed freshness policy, not a statistically calibrated confidence.
        if weight < 0.01:
            continue
        retained.append(s.id)
        if s.direction == "recovery":
            recoveries.append(s.id)
        elif s.kind == "news":
            if s.confidence > 0:
                news_providers.add(s.provider)
        else:
            severity[s.kind] = max(severity[s.kind], min(1.0, s.magnitude * s.confidence * weight))
    return RouteEvidence(physical_severity=severity["physical"], official_severity=severity["official"],
                         independent_news_count=len(news_providers), signal_ids=tuple(sorted(retained)),
                         recovery_signal_ids=tuple(sorted(recoveries)),
                         unavailable_reason=None if retained else "all matching evidence exceeded freshness policy")


class ProviderError(RuntimeError):
    """Explicit unavailable/invalid-provider result; never a normal-condition value."""


def _provider_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ProviderError("missing provider timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ProviderError("provider timestamp lacks timezone")
    return dt.astimezone(timezone.utc)


def fetch_noaa_alerts(*, user_agent: str, ingested_at: datetime | None = None,
                      session: Any = None, license_status: str = "open_verified") -> tuple[Signal, ...]:
    """One bounded, allowlisted public NWS fetch; no planner calls this implicitly.

    Does not follow redirects or fetch arbitrary source_url fields. Errors leave
    caller stores untouched. Multi-page payloads are refused, not truncated.
    Severity mapping is ASSUMED and descriptive, not measured lane delay.
    """
    if license_status != "open_verified":
        raise ProviderError("NWS license approval absent; adapter disabled")
    if not user_agent.strip() or len(user_agent) > 256 or "\n" in user_agent or "\r" in user_agent:
        raise ValueError("supply a bounded identifying User-Agent")
    retrieved = _utc(ingested_at or datetime.now(timezone.utc))
    client = session if session is not None else requests
    started = time.monotonic()
    try:
        response = client.get(NOAA_URL, headers={"User-Agent": user_agent, "Accept": "application/geo+json"},
                              timeout=(5, 10), allow_redirects=False, stream=True)
        try:
            if response.status_code != 200:
                raise ProviderError(f"NWS unavailable: HTTP {response.status_code}")
            chunks = []
            size = 0
            for chunk in response.iter_content(chunk_size=65536):
                if time.monotonic() - started > 30:
                    raise ProviderError("NWS fetch exceeds total elapsed-time bound")
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    raise ProviderError("NWS response exceeds byte bound")
                chunks.append(chunk)
            payload = json.loads(b"".join(chunks))
        finally:
            response.close()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        raise ProviderError(f"NWS fetch failed: {type(exc).__name__}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise ProviderError("NWS schema missing features")
    pagination = payload.get("pagination") or {}
    if not isinstance(pagination, dict):
        raise ProviderError("NWS invalid pagination schema")
    if pagination.get("next") or len(payload["features"]) > MAX_RECORDS:
        raise ProviderError("NWS response incomplete or exceeds record bound")
    result: list[Signal] = []
    try:
        for feature in payload["features"]:
            p = feature["properties"]
            # Exercising/testing alerts and messages without geographic IDs do
            # not become apparent live conditions.
            if p.get("status") != "Actual":
                continue
            entities = tuple(sorted(set(p.get("geocode", {}).get("UGC", []))))
            if not entities:
                raise ProviderError("NWS alert lacks usable geographic identifiers")
            issued = _provider_datetime(p["sent"])
            effective = _provider_datetime(p["effective"])
            expiry = _provider_datetime(p["expires"])
            references = p.get("references") or []
            family = references[0]["identifier"] if references else p["id"]
            raw_severity = p["severity"]
            if raw_severity not in {"Extreme", "Severe", "Moderate", "Minor", "Unknown"}:
                raise ProviderError("unrecognized NWS severity")
            magnitude = {"Extreme": 1.0, "Severe": 0.75, "Moderate": 0.5, "Minor": 0.25, "Unknown": 0.0}[raw_severity]
            result.append(Signal(id=p["id"], provider="noaa_nws", entity_ids=entities,
                                 kind="official", observed_at=issued, published_at=issued, ingested_at=retrieved,
                                 effective_at=effective, valid_until=expiry, magnitude=magnitude,
                                 direction="recovery" if p.get("messageType") == "Cancel" else "deterioration",
                                 confidence=0.0 if raw_severity == "Unknown" else 1.0,
                                 source_url=NOAA_URL, syndication_key=family, adapter_version="nws-cap-v1",
                                 license_status="open_verified"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError(f"NWS normalization failed: {type(exc).__name__}") from exc
    return tuple(result)
