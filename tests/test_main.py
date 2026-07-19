"""Tests for app/main.py — health endpoint with storage check."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _reset_settings():
    import app.config as _cfg

    _cfg._settings = None


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("BOT_TOKEN", "")
    _reset_settings()


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def test_health_ok_writable_storage(client, tmp_path):
    data_dir = tmp_path / "data"
    os.environ["DATA_DIR"] = str(data_dir)
    _reset_settings()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "storage": "ok"}


def test_health_unhealthy_readonly_storage(client, tmp_path):
    data_dir = tmp_path / "readonly"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_dir.chmod(0o444)
    os.environ["DATA_DIR"] = str(data_dir)
    _reset_settings()

    try:
        response = client.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert "storage" in body
    finally:
        data_dir.chmod(0o755)


def test_health_unhealthy_disk_full(client):
    with patch("pathlib.Path.write_text", side_effect=OSError("No space left on device")):
        response = client.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert "storage" in body


def test_health_readback_mismatch_still_cleans(client):
    def fake_read_text(self, encoding=None):
        return "wrong content — tampered"

    with (
        patch("pathlib.Path.write_text"),
        patch("pathlib.Path.read_text", fake_read_text),
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        response = client.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert "read-back mismatch" in body["storage"]
        mock_unlink.assert_not_called()
