"""Unit tests for ingestion.usda_ams_connector + usda_food_hub_directory."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from ingestion.usda_ams_connector import (
    LBS_PER_KG,
    TARGET_COMMODITIES,
    TARGET_MARKETS,
    _resolve_product_id,
    fetch_mymarketnews_prices,
)
from ingestion.usda_food_hub_directory import (
    DEFAULT_STATES,
    _hub_id,
    fetch_food_hubs,
)


# ── Schema bootstrap (in-memory test DB) ─────────────────────────────────────

def _bootstrap(c) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for sql in sorted((repo_root / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    _bootstrap(c)
    yield c
    c.close()


# ── Static configuration sanity ──────────────────────────────────────────────

def test_target_markets_includes_chicago_and_detroit():
    """Chicago is the primary FV terminal serving Indiana; Detroit is the
    secondary fallback. (No Indianapolis terminal exists in MARS — that
    legacy 'IN_MN035' code in the original spec doesn't resolve.)"""
    assert "HX_FV020" in TARGET_MARKETS  # Chicago vegetables
    assert "HX_FV010" in TARGET_MARKETS  # Chicago fruits
    assert "DU_FV020" in TARGET_MARKETS  # Detroit vegetables
    assert "DU_FV010" in TARGET_MARKETS  # Detroit fruits


def test_target_commodities_match_ftl_basket():
    """All five FTL crops + 'lettuce' (USDA's commodity column uses
    'Lettuce, Romaine' etc., so we include the bare term for matching)."""
    expected = {
        "cucumbers", "leafy greens", "tomatoes",
        "peppers", "cantaloupe", "lettuce",
    }
    assert set(TARGET_COMMODITIES) == expected


def test_lbs_per_kg_constant_is_correct():
    # Sanity: 1 kg = 2.2046 lbs
    assert 2.2 < LBS_PER_KG < 2.21


def test_resolve_product_id_basic():
    assert _resolve_product_id("Cucumbers") == "PRD-005"
    assert _resolve_product_id("Lettuce, Romaine") == "PRD-001"
    assert _resolve_product_id("Tomatoes, Cherry") == "PRD-003"


def test_resolve_product_id_substring():
    # Free-text USDA strings often have suffixes — substring match must work.
    assert _resolve_product_id("Spinach baby cut leaf") == "PRD-002"
    assert _resolve_product_id("Cantaloupe western states") == "PRD-008"


def test_resolve_product_id_unknown_returns_none():
    assert _resolve_product_id("Quinoa") is None
    assert _resolve_product_id("") is None


def test_commodity_map_covers_all_targets():
    """Every TARGET_COMMODITIES entry must resolve to a product_id."""
    for c in TARGET_COMMODITIES:
        pid = _resolve_product_id(c)
        assert pid is not None, f"no product mapping for {c!r}"
        assert pid in {"PRD-001", "PRD-002", "PRD-003", "PRD-004", "PRD-005",
                       "PRD-006", "PRD-007", "PRD-008", "PRD-009", "PRD-010"}


# ── Network-free behavior ────────────────────────────────────────────────────

def test_no_api_key_returns_empty(monkeypatch):
    """fetch_mymarketnews_prices returns empty df when key is unset."""
    monkeypatch.delenv("USDA_AMS_API_KEY", raising=False)
    df = fetch_mymarketnews_prices(market_slug="IL_MN250")
    assert df.empty


def test_food_hub_no_api_key_returns_empty(monkeypatch):
    monkeypatch.delenv("USDA_LOCALFOOD_API_KEY", raising=False)
    df = fetch_food_hubs()
    assert df.empty


# ── Hub id stability ─────────────────────────────────────────────────────────

def test_hub_id_uses_listing_id_when_present():
    h1 = _hub_id("Acme Hub", "Indy", "Indiana", "12345")
    h2 = _hub_id("Acme Hub", "Indy", "Indiana", "12345")
    assert h1 == h2 == "HUB-12345"


def test_hub_id_stable_across_calls_no_listing():
    h1 = _hub_id("Acme Hub", "Indy", "Indiana", None)
    h2 = _hub_id("Acme Hub", "Indy", "Indiana", None)
    assert h1 == h2
    assert h1.startswith("HUB-")


def test_hub_id_distinct_for_distinct_hubs():
    a = _hub_id("Acme Hub", "Indy", "Indiana", None)
    b = _hub_id("Beta Hub", "Indy", "Indiana", None)
    assert a != b


def test_default_states_includes_indiana():
    assert "Indiana" in DEFAULT_STATES


# ── Migration tables exist ──────────────────────────────────────────────────

def test_fact_usda_prices_table_exists(conn):
    """Migration 008 created the table — required for the connector."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(fact_usda_prices)").fetchall()]
    assert "price_id" in cols
    assert "price_per_kg" in cols
    assert "commodity" in cols
    assert "market_id" in cols


def test_dim_prospect_hubs_table_exists(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(dim_prospect_hubs)").fetchall()]
    assert "hub_id" in cols
    assert "hub_name" in cols
    assert "state" in cols
