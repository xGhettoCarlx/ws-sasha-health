"""Tests for static file serving and PWA shell."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_index_html_returns_200(client):
    """index.html must return 200 with text/html content type."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sasha Health" in response.text
    assert 'telegram-web-app.js' in response.text


@pytest.mark.asyncio
async def test_manifest_json_returns_200(client):
    """manifest.json must return 200 with valid JSON."""
    response = await client.get("/manifest.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert data["name"] == "Sasha Health"
    assert data["short_name"] == "Health"
    assert data["display"] == "standalone"
    assert "icons" in data


@pytest.mark.asyncio
async def test_sw_js_returns_200(client):
    """sw.js must return 200 with JavaScript content type."""
    response = await client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "sasha-health-v1" in response.text


@pytest.mark.asyncio
async def test_css_base_returns_200(client):
    """css/base.css must return 200."""
    response = await client.get("/css/base.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "--tg-theme-bg-color" in response.text


@pytest.mark.asyncio
async def test_js_app_returns_200(client):
    """js/app.js must return 200."""
    response = await client.get("/js/app.js")
    assert response.status_code == 200
    assert "navigate" in response.text


@pytest.mark.asyncio
async def test_js_telegram_returns_200(client):
    """js/telegram.js must return 200."""
    response = await client.get("/js/telegram.js")
    assert response.status_code == 200
    assert "TelegramApp" in response.text


@pytest.mark.asyncio
async def test_js_api_returns_200(client):
    """js/api.js must return 200."""
    response = await client.get("/js/api.js")
    assert response.status_code == 200
    assert "apiGet" in response.text


@pytest.mark.asyncio
async def test_nonexistent_file_returns_404(client):
    """Non-existent static files should return 404 (no shadowing)."""
    response = await client.get("/nonexistent.css")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_still_works(client):
    """API /health must not be shadowed by StaticFiles."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["storage"] == "ok"
