"""Tests for Telegram initData authentication (app/auth.py).

Coverage: valid initData passes, forged signature → 401, expired → 401,
missing header → 401, whitelist → 403, health bypass, dev mode, extraction
modes (tma header, X-Telegram-InitData, query param).
"""

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest
from httpx import AsyncClient, ASGITransport

from telegram_init_data import sign

from app.main import app

# ── constants ──────────────────────────────────────────────────────────

TEST_TOKEN = "12345:TEST_AUTH_TOKEN"
TEST_USER = {"id": 777, "first_name": "Alice", "username": "alice_dev"}
OTHER_USER = {"id": 999, "first_name": "Bob"}


# ── helpers ────────────────────────────────────────────────────────────


def _reset_settings():
    """Reset the cached Settings singleton so monkeypatching takes effect."""
    import app.config as _cfg

    _cfg._settings = None


def _make_valid_init_data(
    user: dict | None = None,
    token: str = TEST_TOKEN,
    dt: datetime | None = None,
) -> str:
    """Generate a validly signed initData string for *user*."""
    data = {"user": user or TEST_USER}
    return sign(data, token, dt or datetime.now(timezone.utc))


def _make_forged_init_data() -> str:
    """Return URL-encoded initData with a valid auth_date but wrong hash."""
    now = int(time.time())
    return f"user=%7B%22id%22%3A%7B777%7D%7D&auth_date={now}&hash=0000000000000000000000000000000000000000000000000000000000000000"


def _make_forged_with_user(user_dict: dict) -> str:
    """Return forged initData with valid user JSON but wrong hash.

    This simulates a user coming from a different bot (multi-bot scenario):
    the HMAC signature won't match our BOT_TOKEN, so ``verified`` will be
    ``False``, but the user identity is still extractable.
    """
    from urllib.parse import quote

    now = int(time.time())
    user_json = __import__("json").dumps(user_dict)
    return f"user={quote(user_json)}&auth_date={now}&hash=0000000000000000000000000000000000000000000000000000000000000000"


# ── fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    """Ensure BOT_TOKEN is set for auth tests.

    ``autouse=True`` means every test inherits a real token so auth
    doesn't silently degrade to dev mode.
    """
    monkeypatch.setenv("BOT_TOKEN", TEST_TOKEN)
    _reset_settings()


@pytest.fixture
async def client():
    """Async HTTP client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── 1. valid initData ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_initdata_tma_header(client):
    """Authorization: tma <valid> → 200 with user dict."""
    init_data = _make_valid_init_data()
    resp = await client.get("/api/me", headers={"Authorization": f"tma {init_data}"})
    assert resp.status_code == 200
    assert resp.json()["user"]["id"] == TEST_USER["id"]


@pytest.mark.asyncio
async def test_valid_initdata_x_telegram_header(client):
    """X-Telegram-InitData header → 200 with user dict."""
    init_data = _make_valid_init_data()
    resp = await client.get("/api/me", headers={"X-Telegram-InitData": init_data})
    assert resp.status_code == 200
    assert resp.json()["user"]["id"] == TEST_USER["id"]


@pytest.mark.asyncio
async def test_valid_initdata_query_param(client):
    """?initData=... query param (GET) → 200 with user dict.

    The initData string contains ``&`` and ``=`` characters, so it MUST be
    URL-encoded when passed as a query parameter value.  The server decodes
    it once via ``request.query_params.get()``, recovering the original
    initData.
    """
    init_data = _make_valid_init_data()
    encoded = quote(init_data, safe="")
    resp = await client.get(f"/api/me?initData={encoded}")
    assert resp.status_code == 200
    assert resp.json()["user"]["id"] == TEST_USER["id"]


# ── 2. forged signature → 401 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_forged_signature_401(client):
    """Forged initData with a bogus hash → 401.

    Uses a valid-looking auth_date so the library reaches the signature
    check (rather than hitting ExpiredError first).
    """
    forged = _make_forged_init_data()
    resp = await client.get("/api/me", headers={"Authorization": f"tma {forged}"})
    assert resp.status_code == 401
    detail = resp.json()["detail"].lower()
    assert "no user" in detail or "invalid" in detail


# ── 3. expired auth_date → 401 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_expired_auth_date_401(client):
    """initData signed > 24 h ago → 401."""
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    expired = _make_valid_init_data(dt=old)
    resp = await client.get("/api/me", headers={"Authorization": f"tma {expired}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


# ── 4. missing auth → 401 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_auth_header_401(client):
    """No Authorization / X-Telegram-InitData / query param → 401."""
    resp = await client.get("/api/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Authentication required"


@pytest.mark.asyncio
async def test_unsupported_auth_scheme_401(client):
    """Authorization: Bearer <data> → 401 because only 'tma' is allowed."""
    init_data = _make_valid_init_data()
    resp = await client.get(
        "/api/me", headers={"Authorization": f"Bearer {init_data}"}
    )
    assert resp.status_code == 401
    assert "tma" in resp.json()["detail"].lower()


# ── 5. whitelist → 403 ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_not_whitelisted_403(client, monkeypatch):
    """Unverified user not in ALLOWED_TELEGRAM_IDS → 403 pending_approval.

    With the multi-bot on-boarding flow, verified users (signature matches
    BOT_TOKEN) always pass — the whitelist only gates *unverified* users
    coming from different bots.
    """
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "111,222")  # 999 not in list
    _reset_settings()

    forged = _make_forged_with_user({"id": 999, "first_name": "Bob"})
    resp = await client.get("/api/me", headers={"Authorization": f"tma {forged}"})
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["status"] == "pending_approval"
    assert "Требуется одобрение" in detail["message"]


@pytest.mark.asyncio
async def test_whitelisted_passes(client, monkeypatch):
    """User in ALLOWED_TELEGRAM_IDS → 200."""
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", f"{TEST_USER['id']},888")
    _reset_settings()

    init_data = _make_valid_init_data()
    resp = await client.get("/api/me", headers={"Authorization": f"tma {init_data}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_whitelist_wildcard_passes(client, monkeypatch):
    """ALLOWED_TELEGRAM_IDS='*' → all users pass."""
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "*")
    _reset_settings()

    init_data = _make_valid_init_data()
    resp = await client.get("/api/me", headers={"Authorization": f"tma {init_data}"})
    assert resp.status_code == 200


# ── 6. health bypass ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_bypasses_auth(client):
    """GET /health → 200 without any auth header."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["storage"] == "ok"


# ── 7. dev mode ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dev_mode_returns_mock_user(client, monkeypatch):
    """When BOT_TOKEN is empty, auth passes with mock {id:0, first_name:'Dev'}."""
    monkeypatch.setenv("BOT_TOKEN", "")
    _reset_settings()

    resp = await client.get("/api/me", headers={"Authorization": "tma anything"})
    assert resp.status_code == 200
    user = resp.json()["user"]
    assert user["id"] == 0
    assert user["first_name"] == "Dev"


# ── 8. POST must not use query param ──────────────────────────────────


@pytest.mark.asyncio
async def test_post_rejects_query_param_auth(client):
    """POST /api/me with ?initData=... → 401 (only GET checks query param).

    The auth dependency deliberately skips query-param extraction for POST
    because the initData string would be logged in server access logs if
    included in the URL.
    """
    init_data = _make_valid_init_data()
    encoded = quote(init_data, safe="")
    resp = await client.post(f"/api/me?initData={encoded}")
    assert resp.status_code == 401


# ── 9. unit-level tests ───────────────────────────────────────────────


class TestVerifyTelegramAuth:
    """Direct unit tests for verify_telegram_auth()."""

    def test_valid_signature(self):
        from app.auth import verify_telegram_auth

        init_data = _make_valid_init_data()
        user = verify_telegram_auth(init_data)
        assert user["id"] == TEST_USER["id"]

    def test_forged_signature_raises(self):
        import app.config as _cfg

        _cfg._settings = None  # ensure fresh token

        from app.auth import verify_telegram_auth
        from fastapi import HTTPException

        forged = _make_forged_init_data()
        with pytest.raises(HTTPException) as exc:
            verify_telegram_auth(forged)
        assert exc.value.status_code == 401

    def test_expired_raises(self):
        from app.auth import verify_telegram_auth
        from fastapi import HTTPException

        old = datetime.now(timezone.utc) - timedelta(hours=25)
        expired = _make_valid_init_data(dt=old)
        with pytest.raises(HTTPException) as exc:
            verify_telegram_auth(expired)
        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail.lower()


class TestGetBotToken:
    def test_returns_token_when_set(self):
        from app.auth import get_bot_token

        token = get_bot_token()
        assert token == TEST_TOKEN

    def test_returns_none_when_missing(self, monkeypatch):
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        _reset_settings()

        from app.auth import get_bot_token

        token = get_bot_token()
        assert token is None


class TestIsWhitelisted:
    @pytest.mark.parametrize(
        "raw, uid, expected",
        [
            ("", 123, False),
            ("*", 123, True),
            ("123,456", 123, True),
            ("123,456", 789, False),
            ("  456  ,  789  ", 789, True),
        ],
    )
    def test_behaviour(self, monkeypatch, raw, uid, expected):
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", raw)
        _reset_settings()

        from app.auth import is_whitelisted

        assert is_whitelisted(uid) is expected
