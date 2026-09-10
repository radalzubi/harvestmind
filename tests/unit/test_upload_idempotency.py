"""A retried upload must not double the staged quantities."""
import io

import pytest

import infrastructure.operator_registry as orm


@pytest.fixture()
def op_client(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    op = reg.create_operator("Idem Foods")
    tok = reg.issue_token(op.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    from fastapi.testclient import TestClient
    import api.main as api_main
    return TestClient(api_main.app), tok


CSV = b"Product Name,Category,Shelf Life (days)\nRomaine,leafy_green,7\n"


def _up(client, tok, force=False):
    return client.post(f"/intake/upload/stg_products{'?force=true' if force else ''}",
                       files={"file": ("p.csv", io.BytesIO(CSV), "text/csv")},
                       headers={"Authorization": f"Bearer {tok}"})


def test_identical_retry_is_refused_and_force_overrides(op_client):
    client, tok = op_client
    first = _up(client, tok).json()
    assert first["rows_inserted"] == 1, first
    second = _up(client, tok).json()
    assert second["rows_inserted"] == 0 and "already uploaded" in second["errors"][0]
    forced = _up(client, tok, force=True).json()
    assert forced["rows_inserted"] == 1


def test_different_content_is_not_a_duplicate(op_client):
    client, tok = op_client
    assert _up(client, tok).json()["rows_inserted"] == 1
    other = b"Product Name,Category\nSpinach,leafy_green\n"
    r = client.post("/intake/upload/stg_products", files={"file": ("q.csv", io.BytesIO(other), "text/csv")},
                    headers={"Authorization": f"Bearer {tok}"}).json()
    assert r["rows_inserted"] == 1
