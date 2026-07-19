"""Tests for app/routes/pharmacy.py — /api/pharmacy CRUD + alerts.

Covers: GET list, POST create, PUT update, DELETE, GET alerts,
409 duplicate, 404 not found, 401 without auth, 422 invalid payload.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ── helpers ──────────────────────────────────────────────────────────────


def _reset_settings():
    """Reset cached Settings singleton so monkeypatching takes effect."""
    import app.config as _cfg

    _cfg._settings = None


def _make_auth_headers() -> dict[str, str]:
    """Return auth headers that work in dev mode (BOT_TOKEN="")."""
    return {"Authorization": "tma dev-mode-any-value"}


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _dev_mode(monkeypatch, tmp_path):
    """Every test runs in dev mode with an isolated DATA_DIR."""
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    _reset_settings()


@pytest.fixture
async def client():
    """Async HTTP client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def store(tmp_path):
    """Return an MDStorage instance pointed at the isolated DATA_DIR."""
    from app.storage import MDStorage

    return MDStorage(base_dir=tmp_path / "data")


@pytest.fixture
def sample_medicines(store):
    """Seed the data directory with three sample medicines."""
    medicines = [
        {
            "name": "Амитриптилин",
            "dose": "200 мг",
            "frequency": "на ночь",
            "stock": "60 таб",
            "prescription_expiry": "2026-12-01",
            "notes": "Принимать регулярно",
            "days_left": 30,
        },
        {
            "name": "Омепразол",
            "dose": "20 мг",
            "frequency": "утром",
            "stock": "5 таб",
            "prescription_expiry": "2027-06-15",
            "notes": "Перед едой",
            "days_left": 5,
        },
        {
            "name": "Преднизолон",
            "dose": "5 мг",
            "frequency": "редко",
            "stock": "10 таб",
            "prescription_expiry": "2026-07-05",
        },
    ]
    for med in medicines:
        slug = med["name"].lower().replace(" ", "_").replace("/", "_")
        store.write(f"лекарства/{slug}.md", med)
    return medicines


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/pharmacy/ — list all
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_empty(client):
    """GET /api/pharmacy/ → 200 [] when no medicines exist."""
    resp = await client.get("/api/pharmacy/", headers=_make_auth_headers())
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_medicines(client, sample_medicines):
    """GET /api/pharmacy/ → 200 with all medicines and index-based IDs."""
    resp = await client.get("/api/pharmacy/", headers=_make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # IDs are 0, 1, 2 based on alphabetical filename order
    assert data[0]["id"] == 0
    assert data[1]["id"] == 1
    assert data[2]["id"] == 2
    # Check that required fields are present
    for item in data:
        assert "name" in item
        assert "dose" in item
        assert "frequency" in item


@pytest.mark.asyncio
async def test_list_returns_ids_in_order(client, sample_medicines):
    """IDs are assigned by sorted filename order (алфавитный порядок)."""
    resp = await client.get("/api/pharmacy/", headers=_make_auth_headers())
    data = resp.json()
    # амитриптилин < омепразол < преднизолон (русский алфавит)
    names = [d["name"] for d in data]
    assert names == ["Амитриптилин", "Омепразол", "Преднизолон"]


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/pharmacy/ — create
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_minimal(client):
    """POST /api/pharmacy/ with required fields → 201 with created medicine."""
    payload = {"name": "Ибупрофен", "dose": "400 мг", "frequency": "при боли"}
    resp = await client.post(
        "/api/pharmacy/", json=payload, headers=_make_auth_headers()
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ибупрофен"
    assert data["dose"] == "400 мг"
    assert data["frequency"] == "при боли"
    assert data["id"] == 0  # first entry, index 0
    assert data["stock"] is None
    assert data["prescription_expiry"] is None
    assert data["days_left"] is None
    assert data["is_daily"] is False
    assert data["daily_dose"] is None


@pytest.mark.asyncio
async def test_create_with_all_fields(client):
    """POST /api/pharmacy/ with all optional fields → 201."""
    payload = {
        "name": "Цетрин",
        "dose": "10 мг",
        "frequency": "утром",
        "stock": "30 таб",
        "prescription_expiry": "2027-01-15",
        "notes": "При аллергии",
        "days_left": 30,
        "is_daily": True,
        "daily_dose": 1,
    }
    resp = await client.post(
        "/api/pharmacy/", json=payload, headers=_make_auth_headers()
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Цетрин"
    assert data["stock"] == "30 таб"
    assert data["prescription_expiry"] == "2027-01-15"
    assert data["notes"] == "При аллергии"
    assert data["days_left"] == 30
    assert data["is_daily"] is True
    assert data["daily_dose"] == 1


@pytest.mark.asyncio
async def test_create_duplicate_409(client, sample_medicines):
    """POST /api/pharmacy/ with existing name → 409 Conflict."""
    payload = {"name": "Амитриптилин", "dose": "200 мг", "frequency": "на ночь"}
    resp = await client.post(
        "/api/pharmacy/", json=payload, headers=_make_auth_headers()
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_invalid_422(client):
    """POST /api/pharmacy/ with missing required fields → 422."""
    payload = {"name": "No dose"}  # missing dose and frequency
    resp = await client.post(
        "/api/pharmacy/", json=payload, headers=_make_auth_headers()
    )
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# PUT /api/pharmacy/{id} — update
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_dose(client, sample_medicines):
    """PUT /api/pharmacy/0 → 200 with updated dose, other fields unchanged."""
    resp = await client.put(
        "/api/pharmacy/0", json={"dose": "250 мг"}, headers=_make_auth_headers()
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dose"] == "250 мг"
    assert data["name"] == "Амитриптилин"  # unchanged
    assert data["frequency"] == "на ночь"  # unchanged


@pytest.mark.asyncio
async def test_update_stock_and_days_left(client, sample_medicines):
    """PUT /api/pharmacy/1 → update stock + days_left."""
    resp = await client.put(
        "/api/pharmacy/1",
        json={"stock": "3 таб", "days_left": 3},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock"] == "3 таб"
    assert data["days_left"] == 3


@pytest.mark.asyncio
async def test_update_prescription_expiry(client, sample_medicines):
    """PUT /api/pharmacy/2 → update prescription_expiry."""
    resp = await client.put(
        "/api/pharmacy/2",
        json={"prescription_expiry": "2027-01-01"},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["prescription_expiry"] == "2027-01-01"


@pytest.mark.asyncio
async def test_update_not_found_404(client):
    """PUT /api/pharmacy/99 → 404 when no medicine exists at that index."""
    resp = await client.put(
        "/api/pharmacy/99", json={"dose": "99 мг"}, headers=_make_auth_headers()
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_no_fields_400(client, sample_medicines):
    """PUT /api/pharmacy/0 with empty body → 400."""
    resp = await client.put(
        "/api/pharmacy/0", json={}, headers=_make_auth_headers()
    )
    assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# DELETE /api/pharmacy/{id} — delete
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_delete(client, sample_medicines):
    """DELETE /api/pharmacy/0 → 204, then list shows only 2 medicines."""
    resp = await client.delete(
        "/api/pharmacy/0", headers=_make_auth_headers()
    )
    assert resp.status_code == 204

    # Verify it's gone from the list
    list_resp = await client.get("/api/pharmacy/", headers=_make_auth_headers())
    assert len(list_resp.json()) == 2


@pytest.mark.asyncio
async def test_delete_not_found_404(client):
    """DELETE /api/pharmacy/99 → 404."""
    resp = await client.delete(
        "/api/pharmacy/99", headers=_make_auth_headers()
    )
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/pharmacy/{id}/adjust-stock
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_adjust_stock_restock(client, sample_medicines):
    """POST adjust-stock with positive delta → 200, stock increased."""
    # Амитриптилин has stock="60 таб" at index 0
    resp = await client.post(
        "/api/pharmacy/0/adjust-stock",
        json={"delta": 20},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock"] == "80 таб"


@pytest.mark.asyncio
async def test_adjust_stock_dispense(client, sample_medicines):
    """POST adjust-stock with negative delta → 200, stock decreased."""
    resp = await client.post(
        "/api/pharmacy/0/adjust-stock",
        json={"delta": -10},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock"] == "50 таб"


@pytest.mark.asyncio
async def test_adjust_stock_underflow_400(client, sample_medicines):
    """POST adjust-stock that would make stock negative → 400."""
    resp = await client.post(
        "/api/pharmacy/0/adjust-stock",
        json={"delta": -200},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_adjust_stock_not_found_404(client):
    """POST adjust-stock for non-existent ID → 404."""
    resp = await client.post(
        "/api/pharmacy/99/adjust-stock",
        json={"delta": 5},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_adjust_stock_recalculates_days_left(client, store):
    """When is_daily=True and daily_dose is set, days_left recalculated."""
    from datetime import date as date_type

    store.write(
        "лекарства/daily_test.md",
        {
            "name": "DailyMed",
            "dose": "100 мг",
            "frequency": "утром",
            "stock": "60 таб",
            "is_daily": True,
            "daily_dose": 2,
            "days_left": 30,
        },
    )

    # List to find the ID
    list_resp = await client.get("/api/pharmacy/", headers=_make_auth_headers())
    items = list_resp.json()
    med_id = next(i["id"] for i in items if i["name"] == "DailyMed")

    # Dispense 10 → stock 50, days_left = 50 // 2 = 25
    resp = await client.post(
        f"/api/pharmacy/{med_id}/adjust-stock",
        json={"delta": -10},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock"] == "50 таб"
    assert data["days_left"] == 25


@pytest.mark.asyncio
async def test_adjust_stock_no_days_left_without_daily_dose(client, sample_medicines):
    """Adjust-stock without is_daily/daily_dose does NOT recalibrate days_left."""
    resp = await client.post(
        "/api/pharmacy/0/adjust-stock",
        json={"delta": -5},
        headers=_make_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock"] == "55 таб"
    # days_left unchanged (stored as 30 in fixture)
    assert data["days_left"] == 30


@pytest.mark.asyncio
async def test_adjust_stock_without_auth_401(client):
    """POST adjust-stock without auth → 401."""
    resp = await client.post(
        "/api/pharmacy/0/adjust-stock", json={"delta": 5}
    )
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/pharmacy/alerts
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_alerts_empty(client):
    """GET /api/pharmacy/alerts → 200 [] when no medicines."""
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_alerts_low_stock(client, sample_medicines):
    """Alert when days_left < 7 (Омепразол has days_left=5)."""
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    # Омепразол (days_left=5) and Преднизолон (expiry close) should trigger
    names = [d["name"] for d in data]
    assert "Омепразол" in names  # days_left=5 < 7


@pytest.mark.asyncio
async def test_alerts_expiring_prescription(client, sample_medicines):
    """Alert when prescription_expiry < 30 days from today.

    Преднизолон has prescription_expiry 2026-07-05, which is < 30 days from
    test date (2026-07-01).
    """
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    data = resp.json()
    names = [d["name"] for d in data]
    assert "Преднизолон" in names


@pytest.mark.asyncio
async def test_alerts_excludes_safe_medicines(client, sample_medicines):
    """Амитриптилин (days_left=30, expiry far away) should NOT appear in alerts."""
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    data = resp.json()
    names = [d["name"] for d in data]
    assert "Амитриптилин" not in names


@pytest.mark.asyncio
async def test_alerts_prescription_exactly_30_days(client, store):
    """Medicine with prescription_expiry exactly 29 days away → alert.

    (30 days or less = alert; today + 29 days = 29 remaining < 30)
    """
    from datetime import date as date_type
    from datetime import timedelta

    future = (date_type.today() + timedelta(days=29)).isoformat()
    store.write(
        "лекарства/test_soon.md",
        {"name": "SoonMed", "dose": "1 мг", "frequency": "утром",
         "prescription_expiry": future},
    )
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    data = resp.json()
    names = [d["name"] for d in data]
    assert "SoonMed" in names


@pytest.mark.asyncio
async def test_alerts_prescription_far_future_not_alerted(client, store):
    """Medicine with prescription_expiry far in future → no alert."""
    from datetime import date as date_type
    from datetime import timedelta

    future = (date_type.today() + timedelta(days=60)).isoformat()
    store.write(
        "лекарства/test_far.md",
        {"name": "FarMed", "dose": "1 мг", "frequency": "утром",
         "prescription_expiry": future},
    )
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    data = resp.json()
    names = [d["name"] for d in data]
    assert "FarMed" not in names


@pytest.mark.asyncio
async def test_alerts_days_left_exactly_7_not_alerted(client, store):
    """Medicine with days_left=7 → no alert (threshold is < 7, not <= 7)."""
    store.write(
        "лекарства/test_exact.md",
        {"name": "ExactMed", "dose": "1 мг", "frequency": "утром",
         "days_left": 7},
    )
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    data = resp.json()
    names = [d["name"] for d in data]
    assert "ExactMed" not in names


@pytest.mark.asyncio
async def test_alerts_both_conditions(client, store):
    """Medicine with both days_left<7 AND close expiry → alert (single entry)."""
    from datetime import date as date_type
    from datetime import timedelta

    future = (date_type.today() + timedelta(days=10)).isoformat()
    store.write(
        "лекарства/test_both.md",
        {"name": "BothMed", "dose": "1 мг", "frequency": "утром",
         "days_left": 3, "prescription_expiry": future},
    )
    resp = await client.get("/api/pharmacy/alerts", headers=_make_auth_headers())
    data = resp.json()
    names = [d["name"] for d in data]
    assert "BothMed" in names
    # Should appear exactly once even though both conditions trigger
    assert names.count("BothMed") == 1


# ═══════════════════════════════════════════════════════════════════════════
# Auth — require_auth
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_without_auth_401(client):
    """GET /api/pharmacy/ without auth header → 401."""
    resp = await client.get("/api/pharmacy/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_without_auth_401(client):
    """POST /api/pharmacy/ without auth header → 401."""
    resp = await client.post(
        "/api/pharmacy/",
        json={"name": "X", "dose": "1 мг", "frequency": "утром"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_alerts_without_auth_401(client):
    """GET /api/pharmacy/alerts without auth header → 401."""
    resp = await client.get("/api/pharmacy/alerts")
    assert resp.status_code == 401
