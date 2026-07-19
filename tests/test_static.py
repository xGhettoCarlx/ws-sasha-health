"""Tests for SPA static serving under /sh/ (Vite React build)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_redirects_to_sh(client):
    """Root redirects to /sh/ for Mini App compatibility."""
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in (301, 302, 307, 308)
    assert "/sh" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_sh_index_html_returns_200(client):
    """SPA index at /sh/ must return 200 with Telegram WebApp script."""
    response = await client.get("/sh/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sasha Health" in response.text
    assert "telegram-web-app.js" in response.text
    assert "/sh/assets/" in response.text


@pytest.mark.asyncio
async def test_sh_spa_assets_resolve(client):
    """JS/CSS bundles referenced by index.html must exist."""
    index = await client.get("/sh/")
    assert index.status_code == 200
    text = index.text
    # hashed asset paths from Vite
    import re

    assets = re.findall(r'(?:src|href)="(/sh/assets/[^"]+)"', text)
    assert assets, "expected hashed /sh/assets/* references in index.html"
    for path in assets:
        r = await client.get(path)
        assert r.status_code == 200, path


@pytest.mark.asyncio
async def test_manifest_webmanifest_returns_200(client):
    """PWA manifest under /sh/."""
    response = await client.get("/sh/manifest.webmanifest")
    assert response.status_code == 200
    data = response.json()
    assert data.get("short_name") or data.get("name")
    assert data.get("display") == "standalone"


@pytest.mark.asyncio
async def test_sw_js_returns_200(client):
    """Service worker under /sh/."""
    response = await client.get("/sh/sw.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "") or response.text


@pytest.mark.asyncio
async def test_spa_client_route_fallback(client):
    """Unknown /sh/* client routes fall back to index.html."""
    response = await client.get("/sh/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sasha Health" in response.text


@pytest.mark.asyncio
async def test_health_still_works(client):
    """API /health must not be shadowed by SPA routes."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["storage"] == "ok"
