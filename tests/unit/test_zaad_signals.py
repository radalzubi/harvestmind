from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from pydantic import ValidationError

from zaad.signals import NOAA_URL, ProviderError, Signal, SignalStore, fetch_noaa_alerts, route_evidence

NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def signal(**overrides):
    values = dict(id="one", provider="physical_source", entity_ids=("PORT:USBAL",), kind="physical",
                  observed_at=NOW, published_at=NOW, ingested_at=NOW, effective_at=NOW,
                  valid_until=NOW + timedelta(days=10), magnitude=0.8, direction="deterioration",
                  confidence=1.0, source_url="https://example.org/official", syndication_key="event-family",
                  adapter_version="fixture-v1", license_status="open_verified")
    values.update(overrides)
    return Signal(**values)


@pytest.mark.parametrize("field", ["observed_at", "published_at", "ingested_at", "effective_at", "valid_until"])
def test_naive_timestamp_refused(field):
    with pytest.raises(ValidationError):
        signal(**{field: NOW.replace(tzinfo=None)})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0])
def test_nonfinite_or_negative_magnitude_refused(value):
    with pytest.raises(ValidationError):
        signal(magnitude=value)


def test_large_nonnegative_magnitude_is_retained_but_evidence_score_bounded():
    s = signal(magnitude=3.0)
    assert s.magnitude == 3.0
    assert route_evidence([s], ["PORT:USBAL"], NOW).physical_severity == 1.0


def test_signal_is_frozen_and_extra_payload_instructions_rejected():
    s = signal()
    with pytest.raises(ValidationError):
        s.magnitude = 0.1
    with pytest.raises(ValidationError):
        signal(execute_command="arbitrary source text")


def test_three_clock_availability_and_effective_time():
    late = signal(ingested_at=NOW + timedelta(hours=2), effective_at=NOW + timedelta(hours=1))
    store = SignalStore().replay([late])
    assert not store.as_of(NOW + timedelta(minutes=90))
    assert store.as_of(NOW + timedelta(hours=2)) == (late,)
    with pytest.raises(ValidationError):
        signal(published_at=NOW + timedelta(hours=1))


def test_replay_is_atomic_idempotent_and_refuses_changed_ids():
    old = SignalStore().replay([signal()])
    with pytest.raises(ValidationError):
        old.replay([signal(id="two"), {"id": "bad"}])
    assert len(old.signals) == 1
    assert old.replay([signal()]) == old
    with pytest.raises(ValueError, match="collision"):
        old.replay([signal(magnitude=0.2)])
    assert old.signals[0].magnitude == 0.8


@pytest.mark.parametrize("license_status", ["unknown", "denied", "legal_review"])
def test_uncleared_rights_cannot_produce_route_evidence(license_status):
    evidence = route_evidence([signal(license_status=license_status)], ["PORT:USBAL"], NOW)
    assert evidence.unavailable_reason
    assert evidence.physical_severity == 0


def test_freshness_decay_geographic_filter_and_no_probability_claim():
    s = signal()
    fresh = route_evidence([s], ["PORT:USBAL"], NOW)
    older = route_evidence([s], ["PORT:USBAL"], NOW + timedelta(hours=6))
    assert fresh.physical_severity == 0.8
    assert older.physical_severity == pytest.approx(0.4)
    assert not older.calibrated_probability
    assert route_evidence([s], ["PORT:JOAQJ"], NOW).unavailable_reason


def test_syndicated_news_is_not_independent_and_one_provider_not_many():
    signals = [signal(id="n1", kind="news", provider="paper1"),
               signal(id="n2", kind="news", provider="paper2"),
               signal(id="n3", kind="news", provider="paper2", syndication_key="another")]
    assert route_evidence(signals, ["PORT:USBAL"], NOW).independent_news_count == 1
    signals.append(signal(id="n4", kind="news", provider="paper3", syndication_key="independent"))
    assert route_evidence(signals, ["PORT:USBAL"], NOW).independent_news_count == 2


def test_zero_confidence_news_does_not_count_as_confirmation():
    evidence = route_evidence([signal(kind="news", confidence=0.0)], ["PORT:USBAL"], NOW)
    assert evidence.independent_news_count == 0
    assert evidence.physical_severity == 0


def test_recovery_supersedes_old_signal_without_erasing_independent_risk():
    recovery = signal(id="reopened", direction="recovery", published_at=NOW + timedelta(hours=1),
                      ingested_at=NOW + timedelta(hours=1), valid_until=NOW + timedelta(hours=2))
    signals = [signal(), recovery]
    at_recovery = route_evidence(signals, ["PORT:USBAL"], NOW + timedelta(hours=1))
    assert at_recovery.physical_severity == 0
    assert at_recovery.recovery_signal_ids == ("reopened",)
    assert route_evidence(signals, ["PORT:USBAL"], NOW + timedelta(hours=3)).unavailable_reason


def test_reconstructed_history_is_not_historical_evidence():
    s = signal(availability_basis="reconstructed_date_only", historical_eligible=False)
    assert not SignalStore(signals=(s,)).as_of(NOW)
    assert route_evidence([s], ["PORT:USBAL"], NOW).unavailable_reason
    with pytest.raises(ValidationError):
        signal(availability_basis="reconstructed_date_only")


class Response:
    status_code = 200

    def __init__(self, payload=None, status=200, raw=None):
        self.payload = payload
        self.status_code = status
        self.raw = raw
        self.closed = False

    def iter_content(self, chunk_size):
        yield self.raw if self.raw is not None else json.dumps(self.payload).encode()

    def close(self):
        self.closed = True


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def alert_payload(**overrides):
    p = {"id": "https://api.weather.gov/alerts/fixture", "status": "Actual", "severity": "Severe",
         "sent": "2026-09-05T11:00:00Z", "effective": "2026-09-05T11:00:00Z",
         "expires": "2026-09-06T11:00:00Z", "geocode": {"UGC": ["MDZ011"]},
         "messageType": "Alert", "description": "untrusted arbitrary text not promoted into actions"}
    p.update(overrides)
    return {"type": "FeatureCollection", "features": [{"properties": p}]}


def test_noaa_allowlist_bounded_request_and_normalization():
    response = Response(alert_payload())
    session = Session(response)
    result = fetch_noaa_alerts(user_agent="Zaad-test contact@example.org", ingested_at=NOW, session=session)
    assert len(result) == 1 and result[0].entity_ids == ("MDZ011",)
    assert result[0].magnitude == 0.75
    assert "description" not in result[0].model_dump()
    url, args = session.calls[0]
    assert url == NOAA_URL and args["allow_redirects"] is False and args["timeout"] == (5, 10)
    assert args["stream"] is True and response.closed


@pytest.mark.parametrize("response", [Response({}, status=429), Response({}, status=302),
                                      Response(raw=b"not json"), Response({}),
                                      Response(raw=b"x" * 4_000_001),
                                      Response({"features": [], "pagination": {"next": "https://evil.example"}})])
def test_noaa_failure_never_mutates_previous_store(response):
    old = SignalStore().replay([signal()])
    with pytest.raises(ProviderError):
        old.replay(fetch_noaa_alerts(user_agent="Zaad-test", ingested_at=NOW, session=Session(response)))
    assert len(old.signals) == 1
    assert response.closed


def test_noaa_network_and_license_fail_explicitly():
    class Timeout:
        def get(self, *args, **kwargs):
            raise requests.Timeout("fixture")
    with pytest.raises(ProviderError, match="Timeout"):
        fetch_noaa_alerts(user_agent="Zaad-test", session=Timeout())
    session = Session(Response(alert_payload()))
    with pytest.raises(ProviderError, match="license"):
        fetch_noaa_alerts(user_agent="Zaad-test", session=session, license_status="unknown")
    assert not session.calls


def test_noaa_atomic_malformed_batch_and_test_alert_not_real():
    payload = alert_payload()
    payload["features"].append({"properties": {"status": "Actual"}})
    with pytest.raises(ProviderError):
        fetch_noaa_alerts(user_agent="Zaad-test", ingested_at=NOW, session=Session(Response(payload)))
    assert not fetch_noaa_alerts(user_agent="Zaad-test", ingested_at=NOW,
                                session=Session(Response(alert_payload(status="Test"))))


def test_historical_metadata_fixture_discloses_date_precision():
    path = Path(__file__).resolve().parents[2] / "data/zaad/baltimore_official_metadata.json"
    fixture = json.loads(path.read_text())
    assert fixture["published_at"] is None
    assert fixture["publication_date"] == "2024-06-10"
    assert fixture["available_after_upper_bound"] == "2024-06-11T04:00:00Z"
    assert not fixture["historical_eligible"]
