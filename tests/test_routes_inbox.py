"""Tests for app/routes/inbox.py — upload, OCR trigger, verify, reject, delete.

All routes require Telegram initData auth.  Tests run in dev mode
(empty BOT_TOKEN → mock user {id:0}) so auth passes automatically
as long as any Authorization header is present.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.analysis import AnalysisSchema, ParameterItem
from app.storage import MDStorage

# ── helpers ────────────────────────────────────────────────────────────


def _reset_settings():
    import app.config as _cfg

    _cfg._settings = None


def _fake_analysis() -> AnalysisSchema:
    return AnalysisSchema(
        test_name="Биохимический анализ крови",
        date="2026-06-15",
        institution="Городская поликлиника №1",
        parameters=[
            ParameterItem(
                name="Глюкоза",
                value="5.2",
                unit="ммоль/л",
                ref_range="3.3-5.5",
                trust_tier="unverified",
                date="2026-06-15",
            ),
            ParameterItem(
                name="Холестерин",
                value="4.8",
                unit="ммоль/л",
                ref_range="3.0-5.2",
                trust_tier="unverified",
                date="2026-06-15",
            ),
        ],
        conclusion="Показатели в пределах нормы",
        trust_tier="unverified",
        source="Grok Vision OCR",
    )


def _make_item(
    item_id,
    filename,
    ocr_status="completed",
    original_path=None,
    extracted_data=None,
    processed=False,
):
    """Create an InboxItemSchema with required CommonBase fields."""
    from app.schemas.inbox import InboxItemSchema

    return InboxItemSchema(
        id=item_id,
        filename=filename,
        original_path=original_path,
        ocr_status=ocr_status,
        extracted_data=extracted_data or {},
        created_at="2026-07-01T12:00:00+00:00",
        processed=processed,
        trust_tier="unverified",
        date="2026-07-01",
    )


# ── constants ──────────────────────────────────────────────────────────

AUTH_HEADERS = {"Authorization": "tma anything"}

# ── fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _dev_mode(monkeypatch, tmp_path):
    """Dev mode: empty BOT_TOKEN + isolated DATA_DIR."""
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    _reset_settings()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def data_root():
    from app.config import get_settings

    return Path(get_settings().DATA_DIR)


@pytest.fixture
def store(data_root):
    return MDStorage(base_dir=data_root)


# ── Mock OCR ───────────────────────────────────────────────────────────


class MockOCR:
    analyze_image = AsyncMock(return_value=_fake_analysis())
    close = AsyncMock()


# ── upload ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_creates_inbox_item(client, data_root):
    with patch("app.routes.inbox.GrokVisionOCR", return_value=MockOCR()):
        fake_content = b"fake-jpeg-bytes-12345"
        resp = await client.post(
            "/api/inbox/upload",
            files={"file": ("blood_test.jpg", fake_content, "image/jpeg")},
            headers=AUTH_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()

    assert "id" in data
    assert data["filename"] == "blood_test.jpg"
    assert data["original_filename"] == "blood_test.jpg"
    assert data["file_size"] == len(fake_content)
    assert data["mime_type"] == "image/jpeg"
    assert data["ocr_status"] == "completed"

    item_id = data["id"]
    inbox_dir = data_root / "\u26a0\ufe0f_inbox"
    md_file = inbox_dir / f"{item_id}.md"
    assert md_file.exists()

    original_file = inbox_dir / f"{item_id}_original.jpg"
    assert original_file.exists()
    assert original_file.read_bytes() == fake_content


@pytest.mark.asyncio
async def test_upload_triggers_ocr_and_updates_metadata(client):
    with patch("app.routes.inbox.GrokVisionOCR", return_value=MockOCR()):
        resp = await client.post(
            "/api/inbox/upload",
            files={"file": ("analysis.png", b"fake-png", "image/png")},
            headers=AUTH_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ocr_status"] == "completed"
    extracted = data.get("extracted_data", {})
    assert extracted.get("test_name") == "Биохимический анализ крови"
    assert len(extracted.get("parameters", [])) == 2


@pytest.mark.asyncio
async def test_upload_without_file_422(client):
    resp = await client.post("/api/inbox/upload", headers=AUTH_HEADERS)
    assert resp.status_code == 422


# ── pending ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_pending_returns_unverified_items(client, store):
    from app.schemas.frontmatter import to_frontmatter

    item1 = _make_item("20260701T120000_test1", "test1.jpg", processed=False)
    store.write(
        "\u26a0\ufe0f_inbox/20260701T120000_test1.md",
        to_frontmatter(item1),
        "",
    )

    item2 = _make_item("20260701T120001_test2", "test2.jpg", processed=True)
    store.write(
        "\u26a0\ufe0f_inbox/20260701T120001_test2.md",
        to_frontmatter(item2),
        "",
    )

    resp = await client.get("/api/inbox/pending", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["filename"] == "test1.jpg"
    assert items[0]["processed"] is False


@pytest.mark.asyncio
async def test_list_pending_empty(client):
    resp = await client.get("/api/inbox/pending", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


# ── get ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_inbox_item(client, store):
    from app.schemas.frontmatter import to_frontmatter

    item = _make_item(
        "20260701T130000_scan",
        "scan.jpg",
        extracted_data={"test_name": "Глюкоза", "value": "5.2"},
    )
    store.write(
        "\u26a0\ufe0f_inbox/20260701T130000_scan.md",
        to_frontmatter(item),
        "Some OCR content",
    )

    resp = await client.get(
        "/api/inbox/20260701T130000_scan", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "20260701T130000_scan"
    assert data["filename"] == "scan.jpg"
    assert data["ocr_status"] == "completed"
    assert data["extracted_data"]["test_name"] == "Глюкоза"


@pytest.mark.asyncio
async def test_get_nonexistent_inbox_item_404(client):
    resp = await client.get("/api/inbox/nonexistent_id", headers=AUTH_HEADERS)
    assert resp.status_code == 404


# ── verify ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_creates_bundle_and_deletes_inbox(client, data_root, store):
    from app.schemas.frontmatter import to_frontmatter

    inbox_dir = data_root / "\u26a0\ufe0f_inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    item_id = "20260701T140000_verify_test"
    original_rel = f"\u26a0\ufe0f_inbox/{item_id}_original.jpg"
    original_abs = store._resolve(original_rel)
    original_abs.parent.mkdir(parents=True, exist_ok=True)
    original_abs.write_bytes(b"original-jpeg")

    item = _make_item(
        item_id,
        "verify_test.jpg",
        original_path=original_rel,
        extracted_data={"test_name": "Test"},
    )
    store.write(
        f"\u26a0\ufe0f_inbox/{item_id}.md",
        to_frontmatter(item),
        "OCR body",
    )

    resp = await client.post(
        f"/api/inbox/{item_id}/verify",
        json={
            "category": "analyses",
            "date": "2026-07-01",
            "type_name": "кровь",
            "verified_data": {
                "test_name": "Verified Test",
                "trust_tier": "verified",
            },
        },
        headers=AUTH_HEADERS,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "analyses/2026-07-01_кровь/2026-07-01_кровь.md" in data["bundle_path"]

    assert not (inbox_dir / f"{item_id}.md").exists()
    assert not original_abs.exists()

    bundle_dir = data_root / "analyses" / "2026-07-01_кровь"
    assert bundle_dir.is_dir()
    md_file = bundle_dir / "2026-07-01_кровь.md"
    assert md_file.exists()

    meta, content = store.read(
        "analyses/2026-07-01_кровь/2026-07-01_кровь.md"
    )
    assert meta["test_name"] == "Verified Test"
    assert meta["trust_tier"] == "verified"
    assert "OCR body" in content

    original_copied = bundle_dir / "2026-07-01_кровь_original.jpg"
    assert original_copied.exists()
    assert original_copied.read_bytes() == b"original-jpeg"


@pytest.mark.asyncio
async def test_verify_nonexistent_item_404(client):
    resp = await client.post(
        "/api/inbox/nonexistent/verify",
        json={
            "category": "analyses",
            "date": "2026-07-01",
            "type_name": "test",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_without_original_file(client, data_root, store):
    from app.schemas.frontmatter import to_frontmatter

    item_id = "20260701T150000_no_orig"
    item = _make_item(item_id, "noorig.jpg")
    store.write(
        f"\u26a0\ufe0f_inbox/{item_id}.md",
        to_frontmatter(item),
        "No original content",
    )

    resp = await client.post(
        f"/api/inbox/{item_id}/verify",
        json={
            "category": "visits",
            "date": "2026-07-01",
            "type_name": "терапевт",
        },
        headers=AUTH_HEADERS,
    )

    assert resp.status_code == 200
    assert "visits/2026-07-01_терапевт" in resp.json()["bundle_path"]
    inbox_dir = data_root / "\u26a0\ufe0f_inbox"
    assert not (inbox_dir / f"{item_id}.md").exists()


# ── reject ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_deletes_inbox_item(client, data_root, store):
    from app.schemas.frontmatter import to_frontmatter

    inbox_dir = data_root / "\u26a0\ufe0f_inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    item_id = "20260701T160000_reject_test"
    original_rel = f"\u26a0\ufe0f_inbox/{item_id}_original.jpg"
    original_abs = store._resolve(original_rel)
    original_abs.parent.mkdir(parents=True, exist_ok=True)
    original_abs.write_bytes(b"to-reject")

    item = _make_item(
        item_id, "reject_test.jpg", original_path=original_rel
    )
    store.write(
        f"\u26a0\ufe0f_inbox/{item_id}.md", to_frontmatter(item), ""
    )

    resp = await client.post(
        f"/api/inbox/{item_id}/reject", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    assert not (inbox_dir / f"{item_id}.md").exists()
    assert not original_abs.exists()


@pytest.mark.asyncio
async def test_reject_nonexistent_item_404(client):
    resp = await client.post(
        "/api/inbox/nonexistent/reject", headers=AUTH_HEADERS
    )
    assert resp.status_code == 404


# ── delete ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_removes_inbox_item(client, data_root, store):
    from app.schemas.frontmatter import to_frontmatter

    inbox_dir = data_root / "\u26a0\ufe0f_inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    item_id = "20260701T170000_delete_test"
    original_abs = inbox_dir / f"{item_id}_original.jpg"
    original_abs.write_bytes(b"to-delete")

    item = _make_item(
        item_id,
        "delete_test.jpg",
        original_path=f"\u26a0\ufe0f_inbox/{item_id}_original.jpg",
    )
    store.write(
        f"\u26a0\ufe0f_inbox/{item_id}.md", to_frontmatter(item), ""
    )

    resp = await client.delete(
        f"/api/inbox/{item_id}", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    assert not (inbox_dir / f"{item_id}.md").exists()
    assert not original_abs.exists()


@pytest.mark.asyncio
async def test_delete_nonexistent_item_404(client):
    resp = await client.delete(
        "/api/inbox/nonexistent", headers=AUTH_HEADERS
    )
    assert resp.status_code == 404


# ── auth ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inbox_routes_require_auth_without_dev_mode(client, monkeypatch):
    """With a real BOT_TOKEN but no valid initData, all routes return 401."""
    monkeypatch.setenv("BOT_TOKEN", "12345:FAKE_TOKEN_FOR_AUTH_TEST")
    _reset_settings()

    resp = await client.post("/api/inbox/upload")
    assert resp.status_code == 401

    resp = await client.get("/api/inbox/pending")
    assert resp.status_code == 401

    resp = await client.get("/api/inbox/some_id")
    assert resp.status_code == 401

    resp = await client.post("/api/inbox/some_id/verify", json={})
    assert resp.status_code == 401

    resp = await client.post("/api/inbox/some_id/reject")
    assert resp.status_code == 401

    resp = await client.delete("/api/inbox/some_id")
    assert resp.status_code == 401
