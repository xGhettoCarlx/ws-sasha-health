"""
Inbox API routes — upload, OCR trigger, verify, reject, delete.

Prefix: /api/inbox
All routes require Telegram initData authentication (require_auth).

Inbox directory: {DATA_DIR}/⚠️_inbox/
File layout: {timestamp}_{filename}.md (frontmatter) + {timestamp}_{filename}_original{ext}
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import FileResponse

from app.auth import require_auth
from app.config import get_settings
from app.hermes_notify import notify_hermes
from app.ocr import GrokVisionOCR
from app.schemas.analysis import AnalysisSchema
from app.schemas.frontmatter import to_frontmatter
from app.schemas.inbox import InboxItemSchema, OcrStatus
from app.storage import MDStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

INBOX_DIR = "⚠️_inbox"


# ── Pydantic models for request/response ──────────────────────────────


class UploadResponse(BaseModel):
    """Response for POST /upload — the created inbox item."""

    id: str = Field(description="Inbox item ID (filename stem)")
    filename: str
    original_filename: str
    ocr_status: OcrStatus
    created_at: str
    file_size: int
    mime_type: Optional[str] = None
    extracted_data: dict = Field(default_factory=dict)


class VerifyRequest(BaseModel):
    """Request body for POST /{id}/verify — move from inbox to category bundle."""

    category: str = Field(description="Target category (e.g. 'analyses', 'visits')")
    date: str = Field(description="ISO-8601 date (YYYY-MM-DD)")
    type_name: str = Field(description="Human-readable type slug (e.g. 'кровь', 'терапевт')")
    verified_data: dict = Field(
        default_factory=dict,
        description="Verified/extracted data to write as frontmatter of the bundle .md",
    )


class VerifyResponse(BaseModel):
    """Response for POST /{id}/verify."""

    status: str = "ok"
    bundle_path: str = Field(description="Relative path of the created bundle .md file")


class InboxItemResponse(BaseModel):
    """Full inbox item with OCR results."""

    id: str
    filename: str
    original_path: Optional[str] = None
    ocr_status: OcrStatus
    extracted_data: dict
    created_at: str
    processed: bool
    source_tier: str


# ── helpers ────────────────────────────────────────────────────────────


def _get_store() -> MDStorage:
    """Return MDStorage instance for the configured DATA_DIR."""
    return MDStorage(base_dir=get_settings().DATA_DIR)


def _inbox_id_from_filename(md_filename: str) -> str:
    """Extract inbox item ID from the .md filename (strip .md extension)."""
    return md_filename[:-3] if md_filename.endswith(".md") else md_filename


def _inbox_item_to_response(meta: dict, content: str = "") -> InboxItemResponse:
    """Build an InboxItemResponse from frontmatter metadata dict."""
    return InboxItemResponse(
        id=meta.get("id", ""),
        filename=meta.get("filename", ""),
        original_path=meta.get("original_path"),
        ocr_status=meta.get("ocr_status", "pending"),
        extracted_data=meta.get("extracted_data", {}),
        created_at=meta.get("created_at", ""),
        processed=meta.get("processed", False),
        source_tier=meta.get("source_tier", "unverified"),
    )


def _delete_inbox_item(store: MDStorage, item_id: str) -> None:
    """Delete an inbox item's .md file and its _original file (if any).

    Reads the .md to find the original path, then removes both.
    """
    md_path = f"{INBOX_DIR}/{item_id}.md"
    try:
        meta, _ = store.read(md_path)
    except FileNotFoundError:
        return  # already gone — idempotent

    # Remove original file if it exists
    original_path = meta.get("original_path")
    if original_path:
        abs_original = store._resolve(original_path)
        if abs_original.exists():
            abs_original.unlink()

    # Remove the .md file
    abs_md = store._resolve(md_path)
    if abs_md.exists():
        abs_md.unlink()


async def _run_ocr_and_update(
    store: MDStorage,
    item_id: str,
    image_path: str,
    api_key: str | None,
) -> None:
    """Run OCR on the uploaded image and update the inbox item's .md file.

    On success: ocr_status="completed", extracted_data=AnalysisSchema dict.
    On failure: ocr_status="failed", extracted_data={}, content=error message.
    """
    md_path = f"{INBOX_DIR}/{item_id}.md"
    ocr = GrokVisionOCR(api_key=api_key)

    try:
        result: AnalysisSchema = await ocr.analyze_image(image_path)
        extracted = to_frontmatter(result)
        meta, _ = store.read(md_path)
        meta["ocr_status"] = "completed"
        meta["extracted_data"] = extracted
        store.write(md_path, meta, result.content or "")
        logger.info("OCR completed for inbox item %s: %s", item_id, result.test_name)
    except Exception as exc:
        logger.warning("OCR failed for inbox item %s: %s", item_id, exc)
        try:
            meta, content = store.read(md_path)
            meta["ocr_status"] = "failed"
            store.write(md_path, meta, f"OCR error: {exc}")
        except Exception:
            pass  # best-effort update; item remains with status="processing"
    finally:
        await ocr.close()


# ── routes ─────────────────────────────────────────────────────────────


@router.post("/upload", response_model=UploadResponse)
async def upload_to_inbox(
    file: UploadFile = File(...),
    user: dict = require_auth,
):
    """Accept a file upload → save to ⚠️_inbox → trigger OCR → return item.

    The file is saved as ``{timestamp}_{original_filename}_original{ext}``,
    with an accompanying ``{timestamp}_{original_filename}.md`` carrying
    ``InboxItemSchema`` frontmatter and ``ocr_status="processing"``.

    OCR runs synchronously before the response is returned (MVP behaviour).
    On OCR completion the item's .md file is updated with extracted data.
    """
    settings = get_settings()
    store = _get_store()

    # ── prepare paths ──
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    safe_name = file.filename or "upload"
    base_name = f"{timestamp}_{safe_name}"
    md_rel = f"{INBOX_DIR}/{base_name}.md"

    # Read file content
    file_bytes = await file.read()
    file_size = len(file_bytes)

    # ── save original file ──
    ext = Path(safe_name).suffix or ".jpg"
    original_rel = f"{INBOX_DIR}/{base_name}_original{ext}"
    original_abs = store._resolve(original_rel)
    original_abs.parent.mkdir(parents=True, exist_ok=True)
    original_abs.write_bytes(file_bytes)

    # ── create inbox .md file ──
    now = datetime.now(timezone.utc)
    meta = InboxItemSchema(
        id=base_name,
        filename=safe_name,
        original_path=original_rel,
        ocr_status="processing",
        created_at=now.isoformat(),
        processed=False,
        trust_tier="unverified",
        date=now.strftime("%Y-%m-%d"),
    )
    store.write(md_rel, to_frontmatter(meta), "")

    logger.info("Inbox item created: %s (%d bytes)", base_name, file_size)
    notify_hermes("POST", {"endpoint": "/api/inbox/upload", "item_id": base_name,
                           "filename": safe_name, "file_size": file_size})

    # ── trigger OCR (sync for MVP) ──
    await _run_ocr_and_update(store, base_name, str(original_abs), settings.XAI_API_KEY)

    # ── re-read after OCR update ──
    meta_updated, _ = store.read(md_rel)

    return UploadResponse(
        id=base_name,
        filename=safe_name,
        original_filename=safe_name,
        ocr_status=meta_updated.get("ocr_status", "processing"),
        created_at=meta.created_at,
        file_size=file_size,
        mime_type=file.content_type or "image/png",
        extracted_data=meta_updated.get("extracted_data", {}),
    )


@router.get("/pending", response_model=list[InboxItemResponse])
async def list_pending(user: dict = require_auth):
    """List all unverified inbox items (processed=False or ocr_status=pending/processing)."""
    store = _get_store()
    results = store.list_dir(INBOX_DIR)

    pending: list[InboxItemResponse] = []
    for meta in results:
        if meta.get("processed"):
            continue
        pending.append(_inbox_item_to_response(meta))
    return pending


@router.get("/unread-count")
async def get_unread_count(user: dict = require_auth):
    """Return count of unprocessed (processed=False) inbox items."""
    store = _get_store()
    results = store.list_dir(INBOX_DIR)
    count = sum(1 for meta in results if not meta.get("processed", False))
    return {"count": count}


@router.get("/{item_id}", response_model=InboxItemResponse)
async def get_inbox_item(item_id: str, user: dict = require_auth):
    """Get a single inbox item with its OCR results and content."""
    store = _get_store()
    md_path = f"{INBOX_DIR}/{item_id}.md"

    try:
        meta, content = store.read(md_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Inbox item '{item_id}' not found")

    return _inbox_item_to_response(meta, content)


@router.post("/{item_id}/verify", response_model=VerifyResponse)
async def verify_inbox_item(
    item_id: str,
    body: VerifyRequest,
    user: dict = require_auth,
):
    """Confirm and move inbox item to a category bundle.

    1. Reads the inbox item .md + original file.
    2. Creates a Hermes-style bundle in ``{category}/{date}_{type_name}/``.
    3. Writes the .md with *verified_data* as frontmatter + OCR content as body.
    4. Deletes the inbox item (both .md and _original file).
    5. Returns the bundle path.
    """
    store = _get_store()
    md_path = f"{INBOX_DIR}/{item_id}.md"

    # ── 1. read inbox item ──
    try:
        meta, content = store.read(md_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Inbox item '{item_id}' not found")

    original_path = meta.get("original_path")
    original_abs = str(store._resolve(original_path)) if original_path else None

    # ── 2. create bundle ──
    bundle_rel = store.create_bundle(
        category=body.category,
        date_str=body.date,
        type_name=body.type_name,
        original_path=original_abs,
    )

    # ── 3. write verified .md ──
    verified_md = body.verified_data or meta.get("extracted_data", {})
    verified_content = content or meta.get("content", "")
    store.write(bundle_rel, verified_md, verified_content)

    logger.info(
        "Inbox item %s verified → bundle %s (category=%s date=%s)",
        item_id,
        bundle_rel,
        body.category,
        body.date,
    )

    # ── 4. delete inbox item ──
    _delete_inbox_item(store, item_id)
    notify_hermes("POST", {"endpoint": f"/api/inbox/{item_id}/verify",
                           "item_id": item_id, "category": body.category,
                           "bundle_path": bundle_rel})

    return VerifyResponse(status="ok", bundle_path=bundle_rel)


@router.post("/{item_id}/reject")
async def reject_inbox_item(item_id: str, user: dict = require_auth):
    """Reject an inbox item — delete it without moving to a bundle."""
    store = _get_store()

    # Verify it exists first
    md_path = f"{INBOX_DIR}/{item_id}.md"
    if not store._resolve(md_path).exists():
        raise HTTPException(status_code=404, detail=f"Inbox item '{item_id}' not found")

    _delete_inbox_item(store, item_id)
    logger.info("Inbox item %s rejected (deleted)", item_id)
    notify_hermes("POST", {"endpoint": f"/api/inbox/{item_id}/reject", "item_id": item_id})

    return {"status": "ok", "detail": f"Inbox item '{item_id}' rejected and deleted"}


@router.get("/{item_id}/original")
async def serve_inbox_original(item_id: str, user: dict = require_auth):
    """Serve the original uploaded file for an inbox item (JPG/PNG/PDF)."""
    store = _get_store()
    md_path = f"{INBOX_DIR}/{item_id}.md"

    try:
        meta, _ = store.read(md_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Inbox item '{item_id}' not found")

    original_path = meta.get("original_path")
    if not original_path:
        raise HTTPException(status_code=404, detail="No original file attached")

    abs_path = store._resolve(original_path)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found on disk")

    suffix = abs_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".pdf": "application/pdf",
    }
    media_type = mime_map.get(suffix, "application/octet-stream")

    return FileResponse(abs_path, media_type=media_type, filename=abs_path.name)


@router.delete("/{item_id}")
async def delete_inbox_item(item_id: str, user: dict = require_auth):
    """Remove an inbox item completely (both .md and original file)."""
    store = _get_store()

    md_path = f"{INBOX_DIR}/{item_id}.md"
    if not store._resolve(md_path).exists():
        raise HTTPException(status_code=404, detail=f"Inbox item '{item_id}' not found")

    _delete_inbox_item(store, item_id)
    logger.info("Inbox item %s deleted", item_id)
    notify_hermes("DELETE", {"endpoint": f"/api/inbox/{item_id}", "item_id": item_id})

    return {"status": "ok", "detail": f"Inbox item '{item_id}' deleted"}
