"""Tests for app/routes/fluorography.py — GET /api/fluorography.

Coverage:
- GET /api/fluorography/    — returns 4 history records + next_due
- GET /api/fluorography/    — file missing → 404
- Auth required
"""

from datetime import datetime, timezone

import pytest
from telegram_init_data import sign

from app.storage import MDStorage

TEST_TOKEN = "12345:TEST_AUTH_TOKEN"
TEST_USER = {"id": 777, "first_name": "Alice"}

FLUOROGRAPHY_DATA = """\
---
trust_tier: trusted
date: '2026-07-02'
source: Электронный кабинет (tutmed.by)
tags:
  - флюорография
  - профилактика
history:
  - date: '2026-06-10'
    number: '10254'
    result: Отрицательный (норма) ✅
    institution: УЗ «Могилёвская поликлиника №10»
  - date: '2025-03-11'
    number: '3322'
    result: Отрицательный (норма) ✅
    institution: УЗ «Могилёвская поликлиника №10»
  - date: '2023-12-18'
    number: '9130'
    result: Отрицательный (норма) ✅
    institution: УЗ «Могилёвская поликлиника №10'
  - date: '2021-12-16'
    number: Н13552
    result: Отрицательный (норма) ✅
    institution: УЗ «Могилёвская поликлиника №10'
next_due: '2027-06-01'
---
# Флюорография

| Дата | № снимка | Результат |
|------|----------|-----------|
| **10.06.2026** | **10254** | **Отрицательный ✅** |
| 11.03.2025 | 3322 | Отрицательный ✅ |
| 18.12.2023 | 9130 | Отрицательный ✅ |
| 16.12.2021 | Н13552 | Отрицательный ✅ |

⚠️ Следующая плановая — июнь 2027.
"""


# ── helpers ──────────────────────────────────────────────────────────────


def _reset_settings():
    """Reset the cached Settings singleton so monkeypatch takes effect."""
    import app.config as _cfg

    _cfg._settings = None


def _make_auth_headers(user: dict | None = None, dt: datetime | None = None) -> dict:
    """Return headers with a validly signed ``tma`` Authorization value."""
    data = {"user": user or TEST_USER}
    init_data = sign(data, TEST_TOKEN, dt or datetime.now(timezone.utc))
    return {"Authorization": f"tma {init_data}"}


def _create_fluorography_file(store: MDStorage):
    """Create the флюорография.md file in the test data directory."""
    store.base_dir.mkdir(parents=True, exist_ok=True)
    filepath = store.base_dir / "флюорография.md"
    filepath.write_text(FLUOROGRAPHY_DATA, encoding="utf-8")


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _fluoro_env(monkeypatch, test_data_dir):
    """Set BOT_TOKEN (so auth works) and DATA_DIR (isolated storage)."""
    monkeypatch.setenv("BOT_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("DATA_DIR", str(test_data_dir))
    _reset_settings()


@pytest.fixture
def auth_headers():
    """Valid Authorization header for a test user."""
    return _make_auth_headers()


# ══════════════════════════════════════════════════════════════════════════
# GET /api/fluorography/ — existing file
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fluorography_returns_history(client, auth_headers, test_data_dir):
    """Existing флюорография.md → 200 with 4 history records and next_due."""
    store = MDStorage(base_dir=test_data_dir)
    _create_fluorography_file(store)

    resp = await client.get("/api/fluorography/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["history"]) == 4
    assert data["next_due"] == "2027-06-01"

    # Spot-check first record
    first = data["history"][0]
    assert first["date"] == "2026-06-10"
    assert first["number"] == "10254"
    assert "Отрицательный" in first["result"]
    assert "Могилёвская поликлиника №10" in first["institution"]


@pytest.mark.asyncio
async def test_fluorography_records_structure(client, auth_headers, test_data_dir):
    """Each history record has all required fields (no extra underscores)."""
    store = MDStorage(base_dir=test_data_dir)
    _create_fluorography_file(store)

    resp = await client.get("/api/fluorography/", headers=auth_headers)
    data = resp.json()
    for record in data["history"]:
        for key in record:
            assert not key.startswith("_"), f"Internal key leaked: {key}"


# ══════════════════════════════════════════════════════════════════════════
# GET /api/fluorography/ — missing file
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fluorography_missing_file_404(client, auth_headers):
    """No флюорография.md in data dir → 404."""
    resp = await client.get("/api/fluorography/", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════
# Auth — all endpoints MUST require auth
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_auth_required(client):
    """GET / without auth → 401."""
    resp = await client.get("/api/fluorography/")
    assert resp.status_code == 401
