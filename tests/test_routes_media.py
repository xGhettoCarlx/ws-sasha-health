"""Tests for app/routes/media.py — API media serving routes.

All routes require Telegram initData auth.  Tests run in dev mode
(empty BOT_TOKEN → mock user {id:0}) so auth passes automatically
as long as any ``Authorization: tma ...`` header is present.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ── constants ────────────────────────────────────────────────────────────

AUTH_HEADERS = {"Authorization": "tma dev-mode"}


# ── helpers ──────────────────────────────────────────────────────────────


def _reset_settings_cache():
    """Force a fresh Settings read on next ``get_settings()`` call."""
    import app.config

    app.config._settings = None


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _dev_mode(monkeypatch, tmp_path):
    """Every test in this module runs with BOT_TOKEN="" (dev mode)."""
    monkeypatch.setenv("BOT_TOKEN", "")
    # Default DATA_DIR — individual fixtures / tests may override below.
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    _reset_settings_cache()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def media_data_dir(tmp_path, monkeypatch):
    """Create test media directory structure and point DATA_DIR at it."""
    data_dir = tmp_path / "test_data"

    # Bundle: Анализы / 2026-06-10_ОАК /
    bundle_dir = data_dir / "Анализы" / "2026-06-10_ОАК"
    bundle_dir.mkdir(parents=True)

    # Fake JPEG original
    (bundle_dir / "2026-06-10_ОАК_original.jpg").write_bytes(
        b"\xff\xd8\xff\xe0\x00\x10JFIF"
    )

    # Companion .md file with frontmatter
    (bundle_dir / "2026-06-10_ОАК.md").write_text(
        "---\ndate: 2026-06-10\nname: ОАК\n---\n# ОАК\n\nResults here.\n",
        encoding="utf-8",
    )

    # Override DATA_DIR (dev mode already set by autouse fixture)
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    _reset_settings_cache()

    return data_dir


# ---------------------------------------------------------------------------
# Tests — serve original
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serve_original_returns_jpeg(client, media_data_dir):
    """GET /api/media/{category}/{bundle_id}/original returns JPEG with correct Content-Type."""
    resp = await client.get(
        "/api/media/Анализы/2026-06-10_ОАК/original",
        headers=AUTH_HEADERS,
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.content == b"\xff\xd8\xff\xe0\x00\x10JFIF"


@pytest.mark.asyncio
async def test_serve_original_404_missing_bundle(client, media_data_dir):
    """Non-existent bundle returns 404."""
    resp = await client.get(
        "/api/media/Анализы/9999-99-99_XXX/original",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_serve_original_404_missing_category(client, media_data_dir):
    """Non-existent category returns 404."""
    resp = await client.get(
        "/api/media/NonExist/2026-06-10_ОАК/original",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_serve_original_png_content_type(client, tmp_path, monkeypatch):
    """PNG files get ``image/png`` content-type."""
    data_dir = tmp_path / "test_data"
    bundle_dir = data_dir / "УЗИ" / "2026-07-01_почки"
    bundle_dir.mkdir(parents=True)

    (bundle_dir / "2026-07-01_почки_original.png").write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01"
        b"\x00\x00\x00\x01"
        b"\x08\x02"
        b"\x00\x00\x00"
    )

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    _reset_settings_cache()

    resp = await client.get(
        "/api/media/УЗИ/2026-07-01_почки/original",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_serve_original_pdf_content_type(client, tmp_path, monkeypatch):
    """PDF files get ``application/pdf`` content-type."""
    data_dir = tmp_path / "test_data"
    bundle_dir = data_dir / "МРТ-КТ" / "2026-05-15_МРТ"
    bundle_dir.mkdir(parents=True)

    (bundle_dir / "2026-05-15_МРТ_original.pdf").write_bytes(
        b"%PDF-1.4\n%\xaa\xbb\xcc\xdd\n"
    )

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    _reset_settings_cache()

    resp = await client.get(
        "/api/media/МРТ-КТ/2026-05-15_МРТ/original",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


# ---------------------------------------------------------------------------
# Tests — serve thumbnail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serve_thumbnail_returns_file(client, media_data_dir):
    """GET /api/media/{category}/{bundle_id}/thumbnail returns file."""
    resp = await client.get(
        "/api/media/Анализы/2026-06-10_ОАК/thumbnail",
        headers=AUTH_HEADERS,
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_serve_thumbnail_404_missing(client, media_data_dir):
    """Missing thumbnail returns 404."""
    resp = await client.get(
        "/api/media/Анализы/no-such-bundle/thumbnail",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — list bundles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_bundles_returns_preview(client, media_data_dir):
    """GET /api/media/list?category=Анализы returns bundle previews."""
    resp = await client.get(
        "/api/media/list",
        params={"category": "Анализы"},
        headers=AUTH_HEADERS,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "Анализы"
    assert data["count"] == 1
    assert len(data["bundles"]) == 1

    bundle = data["bundles"][0]
    assert bundle["bundle_id"] == "2026-06-10_ОАК"
    assert bundle["date"] == "2026-06-10"
    assert bundle["name"] == "ОАК"
    assert bundle["has_original"] is True
    assert bundle["metadata"]["date"] == "2026-06-10"
    assert bundle["metadata"]["name"] == "ОАК"


@pytest.mark.asyncio
async def test_list_bundles_empty_category(client, media_data_dir):
    """Empty or non-existent category returns empty list — no crash."""
    resp = await client.get(
        "/api/media/list",
        params={"category": "Терапевт"},
        headers=AUTH_HEADERS,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["bundles"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_list_bundles_multiple_sorted(client, tmp_path, monkeypatch):
    """Bundles are returned sorted by directory name (date order)."""
    data_dir = tmp_path / "test_data"
    cat_dir = data_dir / "Анализы"
    cat_dir.mkdir(parents=True)

    for bid in ("2026-03-01_биохимия", "2026-01-15_ОАК", "2026-05-20_гормоны"):
        bd = cat_dir / bid
        bd.mkdir()
        (bd / f"{bid}.md").write_text("---\n---\n", encoding="utf-8")

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    _reset_settings_cache()

    resp = await client.get(
        "/api/media/list",
        params={"category": "Анализы"},
        headers=AUTH_HEADERS,
    )

    data = resp.json()
    assert data["count"] == 3
    ids = [b["bundle_id"] for b in data["bundles"]]
    assert ids == ["2026-01-15_ОАК", "2026-03-01_биохимия", "2026-05-20_гормоны"]


# ---------------------------------------------------------------------------
# Tests — auth protection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_original_requires_auth(client, monkeypatch):
    """Without dev-mode token, requests without initData are rejected (401)."""
    monkeypatch.setenv("BOT_TOKEN", "12345:FAKE_TOKEN_FOR_AUTH_TEST")
    _reset_settings_cache()

    resp = await client.get("/api/media/Анализы/2026-06-10_ОАК/original")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_requires_auth(client, monkeypatch):
    """List endpoint is auth-protected — returns 401 without valid initData."""
    monkeypatch.setenv("BOT_TOKEN", "12345:FAKE_TOKEN_FOR_AUTH_TEST")
    _reset_settings_cache()

    resp = await client.get("/api/media/list", params={"category": "Анализы"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_thumbnail_requires_auth(client, monkeypatch):
    """Thumbnail endpoint is auth-protected — returns 401 without valid initData."""
    monkeypatch.setenv("BOT_TOKEN", "12345:FAKE_TOKEN_FOR_AUTH_TEST")
    _reset_settings_cache()

    resp = await client.get("/api/media/Анализы/2026-06-10_ОАК/thumbnail")
    assert resp.status_code == 401
