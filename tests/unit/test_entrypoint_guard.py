import pytest

from api.dependencies import assert_safe_to_serve


def test_dev_on_public_interface_refuses(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    monkeypatch.delenv("HARVESTMIND_AUTH_REQUIRED", raising=False)
    monkeypatch.setenv("HARVESTMIND_BIND_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError, match="refusing to serve"):
        assert_safe_to_serve()


def test_dev_on_loopback_is_fine(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    monkeypatch.setenv("HARVESTMIND_BIND_HOST", "127.0.0.1")
    assert_safe_to_serve()


def test_pilot_on_public_interface_is_fine(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    monkeypatch.setenv("HARVESTMIND_BIND_HOST", "0.0.0.0")
    assert_safe_to_serve()


def test_startup_hook_runs_the_guard(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as api_main
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    monkeypatch.delenv("HARVESTMIND_AUTH_REQUIRED", raising=False)
    monkeypatch.setenv("HARVESTMIND_BIND_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError):
        with TestClient(api_main.app):
            pass
