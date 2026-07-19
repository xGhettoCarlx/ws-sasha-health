"""Tests for app/routes/profile.py — /api/profile endpoints.

Covers: GET/PUT profile, GET strategy, GET/POST symptoms, 401 without auth,
404 when files missing, 422 for invalid payloads.
"""

from datetime import date
from urllib.parse import quote

import pytest
from httpx import AsyncClient, ASGITransport

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


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/profile
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_profile_200(client, store):
    """GET /api/profile → 200 when карточка.md exists."""
    today = date.today().isoformat()
    store.write(
        "карточка.md",
        {
            "full_name": "Калинов Александр Игоревич",
            "birth_date": "1993-08-26",
            "trust_tier": "verified",
            "date": today,
        },
        "# Карточка пациента",
    )

    resp = await client.get("/api/profile/", headers=_make_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Калинов Александр Игоревич"
    assert data["birth_date"] == "1993-08-26"
    assert data["trust_tier"] == "verified"
    assert data["content"] == "# Карточка пациента"


@pytest.mark.asyncio
async def test_get_profile_404_when_missing(client):
    """GET /api/profile → 404 when файл не существует."""
    resp = await client.get("/api/profile/", headers=_make_auth_headers())
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Profile not found"


@pytest.mark.asyncio
async def test_get_profile_401_without_auth(client):
    """GET /api/profile → 401 без авторизации (dev mode отключён)."""
    resp = await client.get("/api/profile/")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# PUT /api/profile
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_put_profile_update_existing(client, store):
    """PUT /api/profile обновляет существующие поля."""
    today = date.today().isoformat()
    store.write(
        "карточка.md",
        {
            "full_name": "Калинов А.И.",
            "birth_date": "1993-08-26",
            "trust_tier": "verified",
            "date": today,
        },
        "",
    )

    resp = await client.put(
        "/api/profile/",
        headers=_make_auth_headers(),
        json={"full_name": "Калинов Александр Игоревич"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Калинов Александр Игоревич"
    assert data["birth_date"] == "1993-08-26"  # unchanged


@pytest.mark.asyncio
async def test_put_profile_create_when_missing(client, store):
    """PUT /api/profile создаёт файл, если его нет."""
    resp = await client.put(
        "/api/profile/",
        headers=_make_auth_headers(),
        json={
            "full_name": "Калинов Александр Игоревич",
            "birth_date": "1993-08-26",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Калинов Александр Игоревич"
    assert data["birth_date"] == "1993-08-26"

    # Verify файл записан на диск.
    metadata, content = store.read("карточка.md")
    assert metadata["full_name"] == "Калинов Александр Игоревич"


@pytest.mark.asyncio
async def test_put_profile_with_diagnoses_and_allergies(client, store):
    """PUT /api/profile с диагнозами и аллергиями."""
    resp = await client.put(
        "/api/profile/",
        headers=_make_auth_headers(),
        json={
            "full_name": "Калинов А.И.",
            "birth_date": "1993-08-26",
            "diagnoses": [
                {
                    "status": "🔴 Активен",
                    "name": "Жировой гепатоз",
                    "source": "УЗИ 01.2024",
                    "trust_tier": "trusted",
                    "date": "2024-01-06",
                }
            ],
            "allergies": ["Парлазин Нео"],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["diagnoses"]) == 1
    assert data["diagnoses"][0]["name"] == "Жировой гепатоз"
    assert data["allergies"] == ["Парлазин Нео"]


@pytest.mark.asyncio
async def test_put_profile_401_without_auth(client):
    """PUT /api/profile → 401 без авторизации."""
    resp = await client.put(
        "/api/profile/",
        json={"full_name": "Test"},
    )
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/profile/strategy
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_strategy_200(client, store):
    """GET /api/profile/strategy → 200."""
    store.write(
        "стратегия.md",
        {
            "title": "Стратегия здоровья — июнь 2026",
            "updated": "2026-06-07",
            "trust_tier": "verified",
            "date": "2026-06-07",
            "steps": [
                {
                    "section": "ДО СТРАХОВКИ",
                    "priority": 1,
                    "symptom": "Нос не дышит",
                    "reason": "Ночная гипоксия + АГ",
                    "trust_tier": "verified",
                    "date": "2026-06-07",
                }
            ],
        },
        "# Стратегия",
    )

    resp = await client.get("/api/profile/strategy", headers=_make_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Стратегия здоровья — июнь 2026"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["section"] == "ДО СТРАХОВКИ"


@pytest.mark.asyncio
async def test_get_strategy_404(client):
    """GET /api/profile/strategy → 404."""
    resp = await client.get("/api/profile/strategy", headers=_make_auth_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_strategy_401_without_auth(client):
    """GET /api/profile/strategy → 401."""
    resp = await client.get("/api/profile/strategy")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/profile/symptoms
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_symptoms_200(client, store):
    """GET /api/profile/symptoms → 200 with entries."""
    store.write(
        "дневник_симптомов.md",
        {
            "trust_tier": "verified",
            "date": "2026-06-30",
            "entries": [
                {
                    "symptom": "Одышка в покое",
                    "severity": 4,
                    "trust_tier": "verified",
                    "date": "2026-06-30",
                },
                {
                    "symptom": "Экстрасистолы",
                    "severity": 3,
                    "trust_tier": "verified",
                    "date": "2026-06-29",
                },
            ],
        },
        "# Дневник",
    )

    resp = await client.get("/api/profile/symptoms", headers=_make_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 2
    assert data["entries"][0]["symptom"] == "Одышка в покое"


@pytest.mark.asyncio
async def test_get_symptoms_filtered_by_date(client, store):
    """GET /api/profile/symptoms?from_date=...&to_date=... filters correctly."""
    store.write(
        "дневник_симптомов.md",
        {
            "trust_tier": "verified",
            "date": "2026-06-30",
            "entries": [
                {
                    "symptom": "Event A",
                    "severity": 1,
                    "trust_tier": "verified",
                    "date": "2026-06-28",
                },
                {
                    "symptom": "Event B",
                    "severity": 2,
                    "trust_tier": "verified",
                    "date": "2026-06-29",
                },
                {
                    "symptom": "Event C",
                    "severity": 3,
                    "trust_tier": "verified",
                    "date": "2026-06-30",
                },
            ],
        },
        "",
    )

    resp = await client.get(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        params={"from_date": "2026-06-29", "to_date": "2026-06-30"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 2
    symptoms = [e["symptom"] for e in data["entries"]]
    assert "Event A" not in symptoms


@pytest.mark.asyncio
async def test_get_symptoms_paginated(client, store):
    """GET /api/profile/symptoms supports limit + offset."""
    entries = []
    for i in range(5):
        entries.append(
            {
                "symptom": f"Symptom {i}",
                "severity": i + 1,
                "trust_tier": "verified",
                "date": f"2026-06-{28 + i:02d}",
            }
        )

    store.write(
        "дневник_симптомов.md",
        {
            "trust_tier": "verified",
            "date": "2026-07-01",
            "entries": entries,
        },
        "",
    )

    # Page 1: limit=2, offset=0
    resp = await client.get(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        params={"limit": 2, "offset": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 2

    # Page 2: limit=2, offset=2
    resp = await client.get(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        params={"limit": 2, "offset": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 2

    # Page 3: limit=2, offset=4
    resp = await client.get(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        params={"limit": 2, "offset": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 1


@pytest.mark.asyncio
async def test_get_symptoms_404(client):
    """GET /api/profile/symptoms → 404 when файл не существует."""
    resp = await client.get("/api/profile/symptoms", headers=_make_auth_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_symptoms_401_without_auth(client):
    """GET /api/profile/symptoms → 401."""
    resp = await client.get("/api/profile/symptoms")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/profile/symptoms
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_post_symptom_201(client, store):
    """POST /api/profile/symptoms → 201, entry appended."""
    today = date.today().isoformat()

    # Pre-populate one entry so we can verify append.
    store.write(
        "дневник_симптомов.md",
        {
            "trust_tier": "verified",
            "date": today,
            "entries": [
                {
                    "symptom": "Existing entry",
                    "severity": 3,
                    "trust_tier": "verified",
                    "date": today,
                }
            ],
        },
        "",
    )

    resp = await client.post(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        json={"symptom": "New symptom", "severity": 7, "notes": "After coffee"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["symptom"] == "New symptom"
    assert data["severity"] == 7
    assert data["notes"] == "After coffee"
    assert data["trust_tier"] == "unverified"
    assert data["date"] == today

    # Verify persisted.
    metadata, content = store.read("дневник_симптомов.md")
    assert len(metadata["entries"]) == 2
    assert metadata["entries"][0]["symptom"] == "New symptom"  # newest first


@pytest.mark.asyncio
async def test_post_symptom_creates_diary_when_missing(client, store):
    """POST /api/profile/symptoms создаёт файл, если его нет."""
    today = date.today().isoformat()

    resp = await client.post(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        json={"symptom": "First entry", "severity": 5},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["symptom"] == "First entry"

    metadata, content = store.read("дневник_симптомов.md")
    assert len(metadata["entries"]) == 1


@pytest.mark.asyncio
async def test_post_symptom_422_invalid_severity(client):
    """POST /api/profile/symptoms → 422 при невалидном severity."""
    resp = await client.post(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        json={"symptom": "Bad", "severity": 0},
    )
    assert resp.status_code == 422

    resp = await client.post(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        json={"symptom": "Bad", "severity": 11},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_symptom_422_missing_required(client):
    """POST /api/profile/symptoms → 422 без обязательных полей."""
    resp = await client.post(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        json={"severity": 5},  # missing 'symptom'
    )
    assert resp.status_code == 422

    resp = await client.post(
        "/api/profile/symptoms",
        headers=_make_auth_headers(),
        json={"symptom": "No severity"},  # missing 'severity'
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_symptom_401_without_auth(client):
    """POST /api/profile/symptoms → 401."""
    resp = await client.post(
        "/api/profile/symptoms",
        json={"symptom": "Test", "severity": 5},
    )
    assert resp.status_code == 401
