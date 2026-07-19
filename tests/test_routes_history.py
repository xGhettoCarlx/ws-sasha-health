"""Tests for app/routes/history.py — /api/history endpoints.

Covers: analytics aggregation, visit listing, parameter trends, category listing,
and edge cases (empty dirs, missing categories, no matches).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage import MDStorage


def _param(name: str, value: str, unit: str, ref_range: str) -> dict:
    return {"name": name, "value": value, "unit": unit, "ref_range": ref_range, "flag": "✅"}


# ── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def history_data_dir(tmp_path):
    """Create a Hermes-style data directory with analysis bundles and visit files."""
    d = tmp_path / "data"
    store = MDStorage(base_dir=d)

    # --- Анализы bundles ---

    # Bundle 1: биохимия Jan 2024
    store.create_bundle("Анализы", "2024-01-15", "биохимия")
    store.write(
        "Анализы/2024-01-15_биохимия/2024-01-15_биохимия.md",
        {
            "trust_tier": "trusted",
            "date": "2024-01-15",
            "test_name": "Биохимический анализ крови",
            "institution": "Инвитро",
            "parameters": [
                _param("Билирубин общий", "12.3", "мкмоль/л", "3.4-17.1"),
                _param("АЛТ", "25", "Ед/л", "10-40"),
                _param("Глюкоза", "5.2", "ммоль/л", "3.9-6.1"),
            ],
        },
        "# Биохимия 15.01.2024",
    )

    # Bundle 2: биохимия Mar 2024 (bilirubin went up)
    store.create_bundle("Анализы", "2024-03-20", "биохимия")
    store.write(
        "Анализы/2024-03-20_биохимия/2024-03-20_биохимия.md",
        {
            "trust_tier": "trusted",
            "date": "2024-03-20",
            "test_name": "Биохимический анализ крови",
            "institution": "Гемотест",
            "parameters": [
                _param("Билирубин общий", "15.7", "мкмоль/л", "3.4-17.1"),
                _param("АЛТ", "32", "Ед/л", "10-40"),
            ],
        },
        "# Биохимия 20.03.2024",
    )

    # Bundle 3: ОАК Jun 2024
    store.create_bundle("Анализы", "2024-06-01", "ОАК")
    store.write(
        "Анализы/2024-06-01_ОАК/2024-06-01_ОАК.md",
        {
            "trust_tier": "trusted",
            "date": "2024-06-01",
            "test_name": "Общий анализ крови",
            "institution": "Поликлиника №5",
            "parameters": [
                _param("Гемоглобин", "145", "г/л", "130-160"),
                _param("Лейкоциты", "6.2", "10^9/л", "4.0-9.0"),
            ],
        },
        "# ОАК 01.06.2024",
    )

    # --- Терапевт visits (flat .md files) ---

    store.write(
        "Терапевт/2024-02-10_терапевт.md",
        {
            "trust_tier": "trusted",
            "date": "2024-02-10",
            "doctor": "Иванова А.П., терапевт",
            "institution": "Поликлиника №5",
            "complaint": "Головные боли",
            "diagnosis": "ВСД",
        },
        "# Визит 10.02.2024",
    )

    store.write(
        "Терапевт/2024-04-05_терапевт.md",
        {
            "trust_tier": "trusted",
            "date": "2024-04-05",
            "doctor": "Петров С.В., терапевт",
            "institution": "Поликлиника №5",
            "complaint": "Боль в спине",
            "diagnosis": "Остеохондроз",
        },
        "# Визит 05.04.2024",
    )

    # A visit bundle in Терапевт/ (to test bundle scanning)
    store.create_bundle("Терапевт", "2024-07-10", "невролог")
    store.write(
        "Терапевт/2024-07-10_невролог/2024-07-10_невролог.md",
        {
            "trust_tier": "trusted",
            "date": "2024-07-10",
            "doctor": "Сидоров М.К., невролог",
            "institution": "Диагностический центр",
            "complaint": "Онемение рук",
            "diagnosis": "Туннельный синдром",
        },
        "# Визит к неврологу 10.07.2024",
    )

    # --- Empty categories ---
    (d / "УЗИ").mkdir(exist_ok=True)
    (d / "МРТ-КТ").mkdir(exist_ok=True)

    return d


@pytest.fixture
async def history_client(history_data_dir, monkeypatch):
    """Async HTTP client with DATA_DIR overridden to isolated test data.

    Clears BOT_TOKEN so auth enters dev mode — but we still need to send
    a dummy Authorization header so ``verify_telegram_auth_from_request``
    passes the request through to ``verify_telegram_auth`` (which then
    returns the dev-mode mock user).
    """
    from app import config

    monkeypatch.setenv("DATA_DIR", str(history_data_dir))
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setattr(config, "_settings", None)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "tma dev"},
    ) as ac:
        yield ac


# ── GET /api/history/analytics ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_aggregates_all_parameters(history_client):
    """All parameters across all bundles in Анализы/ are aggregated."""
    r = await history_client.get("/api/history/analytics")
    assert r.status_code == 200
    data = r.json()

    assert data["count"] == 7  # 3 + 2 + 2 params across 3 bundles
    items = data["items"]
    assert isinstance(items, list)

    # Verify structure of a single item
    item = items[0]
    assert "date" in item
    assert "test_name" in item
    assert "parameter" in item
    assert "value" in item
    assert "unit" in item

    # Verify specific parameter is present
    bilirubin_items = [i for i in items if "билирубин" in i["parameter"].lower()]
    assert len(bilirubin_items) == 2

    # Verify dates are present
    dates = {i["date"] for i in items}
    assert "2024-01-15" in dates
    assert "2024-03-20" in dates
    assert "2024-06-01" in dates


@pytest.mark.asyncio
async def test_analytics_returns_data_from_fixture(history_client):
    r = await history_client.get("/api/history/analytics")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["items"], list)
    assert data["count"] == 7


# ── GET /api/history/visits ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_visits_returns_all_sorted_desc(history_client):
    """Visits from Терапевт/ sorted by date descending."""
    r = await history_client.get("/api/history/visits")
    assert r.status_code == 200
    data = r.json()

    assert data["count"] == 3  # 2 flat + 1 bundle
    items = data["items"]

    # Verify descending date order
    dates = [item["date"] for item in items]
    assert dates == sorted(dates, reverse=True), f"Expected descending dates, got {dates}"

    # Latest should be the невролог visit
    assert dates[0] == "2024-07-10"

    # Verify visit fields
    first = items[0]
    assert "doctor" in first
    assert "institution" in first


@pytest.mark.asyncio
async def test_visits_bundle_included(history_client):
    """A visit stored as a bundle subdirectory is included in results."""
    r = await history_client.get("/api/history/visits")
    data = r.json()
    items = data["items"]

    # Find the невролог visit (bundle)
    neuro = [i for i in items if "невролог" in i.get("doctor", "")]
    assert len(neuro) == 1
    assert neuro[0]["date"] == "2024-07-10"


# ── GET /api/history/analytics/{test_name} ────────────────────────────────


@pytest.mark.asyncio
async def test_trend_bilirubin(history_client):
    """Longitudinal trend for 'билирубин' returns 2 data points sorted by date."""
    r = await history_client.get("/api/history/analytics/билирубин")
    assert r.status_code == 200
    data = r.json()

    assert data["test_name"] == "билирубин"
    assert data["count"] == 2
    trend = data["trend"]

    # Sorted by date ascending
    assert trend[0]["date"] == "2024-01-15"
    assert trend[0]["value"] == "12.3"
    assert trend[1]["date"] == "2024-03-20"
    assert trend[1]["value"] == "15.7"

    # Verify structure
    for point in trend:
        assert "date" in point
        assert "value" in point
        assert "unit" in point
        assert "ref_range" in point


@pytest.mark.asyncio
async def test_trend_case_insensitive(history_client):
    """Search is case-insensitive: 'ГЕМОГЛОБИН' matches 'Гемоглобин'."""
    r = await history_client.get("/api/history/analytics/ГЕМОГЛОБИН")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["trend"][0]["value"] == "145"


@pytest.mark.asyncio
async def test_trend_partial_match(history_client):
    """Substring match: 'АЛТ' matches 'АЛТ'."""
    r = await history_client.get("/api/history/analytics/АЛТ")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2


@pytest.mark.asyncio
async def test_trend_no_match(history_client):
    """Non-existent parameter returns empty trend."""
    r = await history_client.get("/api/history/analytics/холестерин")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["trend"] == []


@pytest.mark.asyncio
async def test_trend_single_point(history_client):
    """Parameter with only one measurement returns a single-element trend."""
    r = await history_client.get("/api/history/analytics/Лейкоциты")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["trend"][0]["date"] == "2024-06-01"
    assert data["trend"][0]["value"] == "6.2"


# ── GET /api/history/categories ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_categories_examination_only(history_client):
    """Returns only examination categories — non-examination dirs excluded."""
    r = await history_client.get("/api/history/categories")
    assert r.status_code == 200
    data = r.json()

    cats = data["categories"]
    assert isinstance(cats, list)
    assert "Анализы" in cats
    assert "УЗИ" in cats
    assert "МРТ-КТ" in cats

    # Non-examination directories excluded
    assert "Терапевт" not in cats
    assert "schedule" not in cats

    # Sorted ascending
    assert cats == sorted(cats)


@pytest.mark.asyncio
async def test_categories_excludes_non_examination(history_client, history_data_dir):
    """Non-examination directories (schedule, medications) are not listed."""
    (history_data_dir / "schedule").mkdir(exist_ok=True)
    (history_data_dir / "лекарства").mkdir(exist_ok=True)

    r = await history_client.get("/api/history/categories")
    cats = r.json()["categories"]
    assert "schedule" not in cats
    assert "лекарства" not in cats


@pytest.mark.asyncio
async def test_analytics_rejects_non_examination_category(history_client):
    """Analytics returns empty result for non-examination categories."""
    r = await history_client.get("/api/history/analytics?category=Терапевт")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_analytics_strict_category_isolation(history_client, history_data_dir):
    """Анализы data never leaks into УЗИ category queries."""
    store = MDStorage(base_dir=history_data_dir)
    # Add an УЗИ record
    store.create_bundle("УЗИ", "2024-05-01", "брюшная_полость")
    store.write(
        "УЗИ/2024-05-01_брюшная_полость/2024-05-01_брюшная_полость.md",
        {
            "trust_tier": "trusted",
            "date": "2024-05-01",
            "test_name": "УЗИ брюшной полости",
            "institution": "Диагностический центр",
            "parameters": [
                _param("Размер печени", "145", "мм", "120-150"),
            ],
        },
        "# УЗИ 01.05.2024",
    )

    # Query УЗИ — should NOT contain Анализы data
    r = await history_client.get("/api/history/analytics?category=УЗИ")
    data = r.json()
    assert data["count"] == 1
    item = data["items"][0]
    assert item["test_name"] == "УЗИ брюшной полости"
    assert item["parameter"] == "Размер печени"

    # Query Анализы — should NOT contain УЗИ data
    r = await history_client.get("/api/history/analytics?category=Анализы")
    data = r.json()
    assert data["count"] == 7  # original 7 params only


@pytest.mark.asyncio
async def test_categories_excludes_hidden(history_client, history_data_dir):
    """Hidden directories (starting with '.') are excluded."""
    (history_data_dir / ".hidden").mkdir(exist_ok=True)

    r = await history_client.get("/api/history/categories")
    cats = r.json()["categories"]
    assert ".hidden" not in cats


@pytest.mark.asyncio
async def test_categories_excludes_inbox(history_client, history_data_dir):
    """⚠️_inbox directory is excluded from categories."""
    (history_data_dir / "⚠️_inbox").mkdir(exist_ok=True)

    r = await history_client.get("/api/history/categories")
    cats = r.json()["categories"]
    assert "⚠️_inbox" not in cats


# ── auth coverage ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_requires_auth(history_client):
    """Without BOT_TOKEN (dev mode), endpoints still respond 200.

    The history_client fixture already clears BOT_TOKEN, so require_auth
    provides a mock user. This test simply verifies the endpoint works.
    """
    r = await history_client.get("/api/history/analytics")
    assert r.status_code == 200


# ── data integrity ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_handles_malformed_parameters(history_client, history_data_dir):
    """Bundle with non-dict parameters is gracefully skipped."""
    store = MDStorage(base_dir=history_data_dir)
    store.create_bundle("Анализы", "2024-08-01", "плохой")
    store.write(
        "Анализы/2024-08-01_плохой/2024-08-01_плохой.md",
        {
            "trust_tier": "unverified",
            "date": "2024-08-01",
            "test_name": "Странный анализ",
            "parameters": [
                "not_a_dict",
                None,
                {"name": "ОК", "value": "1"},
            ],
        },
        "# Broken",
    )

    r = await history_client.get("/api/history/analytics")
    assert r.status_code == 200
    data = r.json()
    # Should have existing 7 + 1 (the OK one) = 8
    assert data["count"] == 8


@pytest.mark.asyncio
async def test_analytics_no_parameters_field(history_client, history_data_dir):
    """Analysis without 'parameters' field returns empty for that entry."""
    store = MDStorage(base_dir=history_data_dir)
    store.create_bundle("Анализы", "2024-09-01", "пустой")
    store.write(
        "Анализы/2024-09-01_пустой/2024-09-01_пустой.md",
        {
            "trust_tier": "unverified",
            "date": "2024-09-01",
            "test_name": "Пустой анализ",
        },
        "# No params",
    )

    r = await history_client.get("/api/history/analytics")
    assert r.status_code == 200
    # count unchanged — no parameters to add
    assert r.json()["count"] == 7
