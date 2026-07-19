"""Tests for app/routes/schedule.py — /api/schedule CRUD + upcoming filter.

Coverage:
- GET /api/schedule/        — list all visits
- GET /api/schedule/upcoming — filter next 30 days, sorted by date asc
- POST /api/schedule/        — create a new visit
- PUT /api/schedule/{id}     — update existing / 404 on missing
- DELETE /api/schedule/{id}  — delete existing / 404 on missing
- Auth required on all endpoints
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from telegram_init_data import sign

from app.storage import MDStorage

TEST_TOKEN = "12345:TEST_AUTH_TOKEN"
TEST_USER = {"id": 777, "first_name": "Alice"}


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


def _create_visit_file(store: MDStorage, visit_id: str, **overrides) -> dict:
    """Create a visit .md file in the store and return the metadata dict."""
    meta = {
        "id": visit_id,
        "date": "2026-07-15",
        "doctor": "Dr. Test",
        "purpose": "Routine checkup",
        "trust_tier": "unverified",
        "status": "planned",
        **overrides,
    }
    content = meta.pop("content", None) or ""
    store.write(f"schedule/{visit_id}.md", meta, content)
    return meta


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _schedule_env(monkeypatch, test_data_dir):
    """Set BOT_TOKEN (so auth works) and DATA_DIR (isolated storage)."""
    monkeypatch.setenv("BOT_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("DATA_DIR", str(test_data_dir))
    _reset_settings()


@pytest.fixture
def store(test_data_dir):
    """MDStorage instance pointed at the isolated test data directory."""
    return MDStorage(base_dir=test_data_dir)


@pytest.fixture
def auth_headers():
    """Valid Authorization header for a test user."""
    return _make_auth_headers()


# ══════════════════════════════════════════════════════════════════════════
# GET /api/schedule/ — list all visits
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_empty(client, auth_headers):
    """No visits yet → 200 with empty list."""
    resp = await client.get("/api/schedule/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"visits": []}


@pytest.mark.asyncio
async def test_list_all_visits(client, auth_headers, store):
    """Two visit files → both returned."""
    _create_visit_file(store, "v1", doctor="Dr. Alpha")
    _create_visit_file(store, "v2", doctor="Dr. Beta")
    resp = await client.get("/api/schedule/", headers=auth_headers)
    assert resp.status_code == 200
    visits = resp.json()["visits"]
    assert len(visits) == 2
    doctors = {v["doctor"] for v in visits}
    assert doctors == {"Dr. Alpha", "Dr. Beta"}


@pytest.mark.asyncio
async def test_list_strips_internal_keys(client, auth_headers, store):
    """Response must not include internal keys like _path."""
    _create_visit_file(store, "v1")
    resp = await client.get("/api/schedule/", headers=auth_headers)
    visits = resp.json()["visits"]
    for visit in visits:
        for key in visit:
            assert not key.startswith("_"), f"Internal key leaked: {key}"


# ══════════════════════════════════════════════════════════════════════════
# GET /api/schedule/upcoming
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_upcoming_empty(client, auth_headers):
    """No visits → 200 with empty list."""
    resp = await client.get("/api/schedule/upcoming", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"visits": []}


@pytest.mark.asyncio
async def test_upcoming_filters_by_30_days(client, auth_headers, store):
    """Only visits within next 30 days (inclusive) are returned."""
    today = date.today()
    _create_visit_file(store, "v_today", date=today.isoformat(), doctor="Today")
    _create_visit_file(store, "v_15d", date=(today + timedelta(days=15)).isoformat(), doctor="+15d")
    _create_visit_file(store, "v_30d", date=(today + timedelta(days=30)).isoformat(), doctor="+30d")
    _create_visit_file(store, "v_31d", date=(today + timedelta(days=31)).isoformat(), doctor="+31d")
    _create_visit_file(store, "v_past", date=(today - timedelta(days=1)).isoformat(), doctor="Past")

    resp = await client.get("/api/schedule/upcoming", headers=auth_headers)
    assert resp.status_code == 200
    visits = resp.json()["visits"]
    assert len(visits) == 3
    doctors = {v["doctor"] for v in visits}
    assert doctors == {"Today", "+15d", "+30d"}


@pytest.mark.asyncio
async def test_upcoming_sorted_by_date_asc(client, auth_headers, store):
    """Results must be sorted by date ascending (earliest first)."""
    today = date.today()
    _create_visit_file(
        store, "v_late", date=(today + timedelta(days=20)).isoformat(), doctor="Late"
    )
    _create_visit_file(
        store, "v_early", date=(today + timedelta(days=1)).isoformat(), doctor="Early"
    )
    _create_visit_file(store, "v_mid", date=(today + timedelta(days=10)).isoformat(), doctor="Mid")

    resp = await client.get("/api/schedule/upcoming", headers=auth_headers)
    visits = resp.json()["visits"]
    assert [v["doctor"] for v in visits] == ["Early", "Mid", "Late"]


@pytest.mark.asyncio
async def test_upcoming_skips_missing_date(client, auth_headers, store):
    """Visit without a date field → silently skipped."""
    today = date.today()
    _create_visit_file(store, "v_good", date=today.isoformat(), doctor="Good")
    # Write a file directly without date in frontmatter
    store.write("schedule/v_nodate.md", {"id": "v_nodate", "doctor": "NoDate"}, "")

    resp = await client.get("/api/schedule/upcoming", headers=auth_headers)
    visits = resp.json()["visits"]
    assert len(visits) == 1
    assert visits[0]["doctor"] == "Good"


@pytest.mark.asyncio
async def test_upcoming_skips_unparseable_date(client, auth_headers, store):
    """Visit with an invalid date string → silently skipped."""
    today = date.today()
    _create_visit_file(store, "v_good", date=today.isoformat(), doctor="Good")
    _create_visit_file(store, "v_bad", date="not-a-date", doctor="Bad")

    resp = await client.get("/api/schedule/upcoming", headers=auth_headers)
    visits = resp.json()["visits"]
    assert len(visits) == 1
    assert visits[0]["doctor"] == "Good"


# ══════════════════════════════════════════════════════════════════════════
# POST /api/schedule/ — create
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_visit_basic(client, auth_headers):
    """Create a visit → 201, returns the visit with an id."""
    payload = {
        "date": "2026-08-01",
        "doctor": "Dr. New",
        "institution": "Clinic X",
        "purpose": "Annual exam",
        "trust_tier": "unverified",
        "status": "planned",
    }
    resp = await client.post("/api/schedule/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["doctor"] == "Dr. New"
    assert data["purpose"] == "Annual exam"
    assert data["institution"] == "Clinic X"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_visit_with_explicit_id(client, auth_headers):
    """Client supplies an id → that id is used."""
    payload = {
        "id": "my-custom-id",
        "date": "2026-08-01",
        "doctor": "Dr. Custom",
        "purpose": "Custom exam",
        "trust_tier": "unverified",
        "status": "planned",
    }
    resp = await client.post("/api/schedule/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["id"] == "my-custom-id"


@pytest.mark.asyncio
async def test_create_visit_with_content(client, auth_headers):
    """Content field → stored as markdown body, returned in response."""
    payload = {
        "date": "2026-08-01",
        "doctor": "Dr. X",
        "purpose": "Checkup",
        "trust_tier": "unverified",
        "content": "Bring insurance card and passport.",
        "status": "planned",
    }
    resp = await client.post("/api/schedule/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["content"] == "Bring insurance card and passport."


@pytest.mark.asyncio
async def test_create_visit_persisted(client, auth_headers, test_data_dir):
    """After creation, GET returns the new visit."""
    payload = {
        "date": "2026-08-01",
        "doctor": "Dr. Persisted",
        "purpose": "Persist test",
        "trust_tier": "unverified",
        "status": "planned",
    }
    resp = await client.post("/api/schedule/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    visit_id = resp.json()["id"]

    resp2 = await client.get("/api/schedule/", headers=auth_headers)
    visits = resp2.json()["visits"]
    assert any(v["id"] == visit_id for v in visits)


# ══════════════════════════════════════════════════════════════════════════
# PUT /api/schedule/{visit_id} — update
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_visit_full(client, auth_headers, store):
    """Full replacement of all fields."""
    _create_visit_file(store, "v_upd", doctor="Old Name", status="planned")
    payload = {
        "date": "2026-09-15",
        "doctor": "New Name",
        "purpose": "Updated exam",
        "trust_tier": "verified",
        "status": "completed",
        "notes": "All done",
    }
    resp = await client.put("/api/schedule/v_upd", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["doctor"] == "New Name"
    assert data["status"] == "completed"
    assert data["notes"] == "All done"
    assert data["trust_tier"] == "verified"
    # Old field not in payload → gone
    assert data["date"] == "2026-09-15"


@pytest.mark.asyncio
async def test_update_nonexistent_404(client, auth_headers):
    """PUT on a non-existent visit id → 404."""
    payload = {
        "date": "2026-08-01",
        "doctor": "Dr. X",
        "purpose": "Checkup",
        "trust_tier": "unverified",
    }
    resp = await client.put("/api/schedule/nonexistent", json=payload, headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════
# DELETE /api/schedule/{visit_id} — delete
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_delete_visit(client, auth_headers, store):
    """Delete an existing visit → 204, visit removed from list."""
    _create_visit_file(store, "v_del")
    # Verify it exists first
    resp0 = await client.get("/api/schedule/", headers=auth_headers)
    assert len(resp0.json()["visits"]) == 1

    resp = await client.delete("/api/schedule/v_del", headers=auth_headers)
    assert resp.status_code == 204
    assert resp.content == b""  # 204 should have no body

    # Verify it's gone
    resp2 = await client.get("/api/schedule/", headers=auth_headers)
    assert resp2.json()["visits"] == []


@pytest.mark.asyncio
async def test_delete_nonexistent_404(client, auth_headers):
    """DELETE on a non-existent visit id → 404."""
    resp = await client.delete("/api/schedule/nonexistent", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════
# Auth — all endpoints MUST require auth
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_auth_required_list(client):
    """GET / without auth → 401."""
    resp = await client.get("/api/schedule/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_required_upcoming(client):
    """GET /upcoming without auth → 401."""
    resp = await client.get("/api/schedule/upcoming")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_required_create(client):
    """POST / without auth → 401."""
    resp = await client.post("/api/schedule/", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_required_update(client):
    """PUT /{id} without auth → 401."""
    resp = await client.put("/api/schedule/x", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_required_delete(client):
    """DELETE /{id} without auth → 401."""
    resp = await client.delete("/api/schedule/x")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_forged_auth_401(client):
    """Forged initData → 401 (NOT 200 or 500)."""
    forged = "user=%7B%22id%22%3A%7B777%7D%7D&auth_date=9999999999&hash=bad"
    resp = await client.get(
        "/api/schedule/",
        headers={"Authorization": f"tma {forged}"},
    )
    assert resp.status_code == 401
