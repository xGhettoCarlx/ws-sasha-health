"""Tests for app/routes/insurance.py — /api/insurance GET endpoint.

Coverage:
- GET /api/insurance/ — returns all 4 policies from страховка.md
- Auth required (401 without valid initData)
- File missing (404 when страховка.md does not exist)
"""

import pytest

from app.storage import MDStorage

TEST_TOKEN = "12345:TEST_AUTH_TOKEN"
TEST_USER = {"id": 777, "first_name": "Alice"}


# ── helpers ──────────────────────────────────────────────────────────────


def _reset_settings():
    """Reset the cached Settings singleton so monkeypatch takes effect."""
    import app.config as _cfg

    _cfg._settings = None


def _make_auth_headers(user: dict | None = None, dt=None) -> dict:
    """Return headers with a validly signed ``tma`` Authorization value."""
    from datetime import datetime, timezone

    from telegram_init_data import sign

    data = {"user": user or TEST_USER}
    init_data = sign(data, TEST_TOKEN, dt or datetime.now(timezone.utc))
    return {"Authorization": f"tma {init_data}"}


def _create_insurance_file(store: MDStorage) -> dict:
    """Create страховка.md in the store and return the metadata dict."""
    meta = {
        "trust_tier": "unverified",
        "date": "2026-07-02",
        "source": "Со слов пользователя (требуется верификация)",
        "tags": ["страховка", "ДМС"],
        "policies": [
            {
                "policy": "Даша (как муж)",
                "sum_insured": 930.0,
                "spent": 0.0,
                "remaining": 930.0,
                "expiry": "2026-12-31",
            },
            {
                "policy": "Тётя",
                "sum_insured": 570.0,
                "spent": 0.0,
                "remaining": 570.0,
                "expiry": "2026-12-31",
            },
            {
                "policy": "Беларусбанк",
                "sum_insured": 480.0,
                "spent": 0.0,
                "remaining": 480.0,
                "expiry": "2026-12-31",
            },
            {
                "policy": "Имклива",
                "sum_insured": 350.0,
                "spent": 0.0,
                "remaining": 350.0,
                "expiry": "2026-12-31",
            },
        ],
    }
    content = "# Страховка\n\n..."
    store.write("страховка.md", meta, content)
    return meta


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _insurance_env(monkeypatch, test_data_dir):
    """Set BOT_TOKEN (so auth works) and DATA_DIR (isolated storage)."""
    monkeypatch.setenv("BOT_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("DATA_DIR", str(test_data_dir))
    _reset_settings()


@pytest.fixture
def auth_headers():
    """Valid Authorization header for a test user."""
    return _make_auth_headers()


# ══════════════════════════════════════════════════════════════════════════
# GET /api/insurance/ — list all policies
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_insurance_returns_4_policies(client, auth_headers, test_data_dir):
    """страховка.md exists → 200 with 4 policies."""
    store = MDStorage(base_dir=test_data_dir)
    _create_insurance_file(store)

    resp = await client.get("/api/insurance/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "policies" in data
    assert len(data["policies"]) == 4
    assert data["policies"][0]["policy"] == "Даша (как муж)"

    # Verify all policies have required fields
    for p in data["policies"]:
        assert "policy" in p
        assert "sum_insured" in p
        assert "spent" in p
        assert "remaining" in p


@pytest.mark.asyncio
async def test_get_insurance_strips_internal_keys(client, auth_headers, test_data_dir):
    """Response must not include internal keys like _path or _id."""
    store = MDStorage(base_dir=test_data_dir)
    _create_insurance_file(store)

    resp = await client.get("/api/insurance/", headers=auth_headers)
    policies = resp.json()["policies"]
    for policy in policies:
        for key in policy:
            assert not key.startswith("_"), f"Internal key leaked: {key}"


# ══════════════════════════════════════════════════════════════════════════
# Auth — all endpoints MUST require auth
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_insurance_auth_required(client):
    """GET / without auth → 401."""
    resp = await client.get("/api/insurance/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_insurance_forged_auth_401(client):
    """Forged initData → 401 (NOT 200 or 500)."""
    forged = "user=%7B%22id%22%3A%7B777%7D%7D&auth_date=9999999999&hash=bad"
    resp = await client.get(
        "/api/insurance/",
        headers={"Authorization": f"tma {forged}"},
    )
    assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# Error handling
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_insurance_not_found(client, auth_headers):
    """No страховка.md → 404."""
    resp = await client.get("/api/insurance/", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
