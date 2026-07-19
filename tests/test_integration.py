"""Integration test: upload → verify → read full flow.

Covers the complete user journey:
  1. Upload a file to /api/inbox/upload (with mocked OCR to avoid real API calls).
  2. Read the created inbox item via GET /api/inbox/{item_id}.
  3. Verify the item: move to a category bundle via POST /api/inbox/{item_id}/verify.
  4. Read the bundle via GET /api/history/analytics (category scan).
  5. Serve the original file via GET /api/media/{category}/{bundle_id}/original.

No real xAI API key needed — OCR is mocked.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

AUTH_HEADERS = {"Authorization": "tma dev-mode-int-test"}

# Fake JPEG header — valid enough for MIME detection
FAKE_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n"
    b"\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d"
    b"\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x1f"
    b"\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9"
)


def _reset_settings():
    import app.config as _cfg

    _cfg._settings = None


@pytest.fixture(autouse=True)
def _dev_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("XAI_API_KEY", "test-fake-key")
    _reset_settings()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_ocr():
    """Mock GrokVisionOCR.analyze_image to return fake OCR data instantly."""
    with patch(
        "app.routes.inbox.GrokVisionOCR",
        autospec=True,
    ) as MockOCR:
        instance = MockOCR.return_value
        instance.analyze_image = AsyncMock(return_value=_fake_analysis())
        instance.close = AsyncMock()
        yield MockOCR


def _fake_analysis():
    """Return an AnalysisSchema-like object for the OCR mock."""
    from app.schemas.analysis import AnalysisSchema, ParameterItem

    return AnalysisSchema(
        test_name="Общий анализ крови",
        date="2026-07-01",
        institution="Городская поликлиника №1",
        parameters=[
            ParameterItem(
                name="Гемоглобин",
                value="145",
                unit="г/л",
                ref_range="130-160",
                flag="normal",
                trust_tier="trusted",
                date="2026-07-01",
            ),
            ParameterItem(
                name="Эритроциты",
                value="4.8",
                unit="10^12/л",
                ref_range="4.0-5.0",
                flag="normal",
                trust_tier="trusted",
                date="2026-07-01",
            ),
        ],
        conclusion="Показатели в пределах нормы",
        trust_tier="trusted",
    )


@pytest.mark.asyncio
async def test_upload_verify_read_full_flow(client, mock_ocr, tmp_path):
    """Full integration: upload file → verify to bundle → read it back."""

    # ── 1. Upload ────────────────────────────────────────────────────────
    resp = await client.post(
        "/api/inbox/upload",
        files={"file": ("blood_test.jpg", FAKE_JPEG, "image/jpeg")},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    upload_data = resp.json()
    item_id = upload_data["id"]
    assert upload_data["ocr_status"] in ("completed", "processing", "failed")
    assert upload_data["filename"] == "blood_test.jpg"

    # ── 2. Read inbox item ───────────────────────────────────────────────
    resp = await client.get(f"/api/inbox/{item_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    item = resp.json()
    assert item["id"] == item_id
    assert item["filename"] == "blood_test.jpg"
    assert item["original_path"] is not None

    # ── 3. Verify — move to bundle ───────────────────────────────────────
    extracted = item.get("extracted_data", {})
    if isinstance(extracted, str):
        extracted = json.loads(extracted) if extracted else {}
    verify_payload = {
        "category": "Анализы",
        "date": "2026-07-01",
        "type_name": "ОАК",
        "verified_data": extracted or {"test_name": "ОАК", "date": "2026-07-01"},
    }

    resp = await client.post(
        f"/api/inbox/{item_id}/verify",
        json=verify_payload,
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"Verify failed: {resp.text}"
    verify_data = resp.json()
    assert verify_data["status"] == "ok"
    assert "2026-07-01_ОАК" in verify_data["bundle_path"]

    # ── 4. Read bundle via history/analytics ─────────────────────────────
    resp = await client.get("/api/history/analytics", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    analytics = resp.json()
    assert analytics["count"] >= 1

    # ── 5. Serve original file ───────────────────────────────────────────
    resp = await client.get(
        "/api/media/Анализы/2026-07-01_ОАК/original",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.content == FAKE_JPEG

    # ── 6. Inbox item is gone after verify ───────────────────────────────
    resp = await client.get(f"/api/inbox/{item_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_reject_flow(client, mock_ocr):
    """Upload → reject → item deleted, nothing in bundles."""

    resp = await client.post(
        "/api/inbox/upload",
        files={"file": ("reject_test.jpg", FAKE_JPEG, "image/jpeg")},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    item_id = resp.json()["id"]

    # Reject
    resp = await client.post(
        f"/api/inbox/{item_id}/reject",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Item is gone
    resp = await client.get(f"/api/inbox/{item_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_without_auth_is_rejected(client):
    """Upload without auth header returns 401."""
    resp = await client.post(
        "/api/inbox/upload",
        files={"file": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint_integration(client):
    """Health endpoint returns 200 with storage=ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["storage"] == "ok"
