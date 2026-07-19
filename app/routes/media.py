"""Media serving routes — /api/media file serving.

Supported formats: JPG (image/jpeg), PNG (image/png), PDF (application/pdf).
All routes protected with require_auth.
"""

from pathlib import Path

import frontmatter
from fastapi import APIRouter, HTTPException, Query
from starlette.responses import FileResponse

from app.auth import require_auth
from app.config import get_settings

router = APIRouter(prefix="/api/media", tags=["media"])

# ── MIME map ────────────────────────────────────────────────────────────

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}
_EXTENSIONS = list(_MIME_MAP.keys())


# ── helpers ─────────────────────────────────────────────────────────────


def _find_original(data_dir: Path, category: str, bundle_id: str) -> Path | None:
    """Locate the *_original.* file for a bundle (any supported extension)."""
    bundle_dir = data_dir / category / bundle_id
    if not bundle_dir.is_dir():
        return None
    for ext in _EXTENSIONS:
        candidate = bundle_dir / f"{bundle_id}_original{ext}"
        if candidate.is_file():
            return candidate
    return None


def _content_type(path: Path) -> str:
    """Return the MIME content-type for a file based on its extension."""
    return _MIME_MAP.get(path.suffix.lower(), "application/octet-stream")


# ── routes ──────────────────────────────────────────────────────────────


@router.get("/list")
async def list_bundles(
    category: str = Query(
        ...,
        description="Category name: Анализы, Терапевт, УЗИ, МРТ-КТ",
    ),
    user: dict = require_auth,
):
    """List all bundles in a category with preview info (date, name)."""
    data_dir = Path(get_settings().DATA_DIR)
    cat_path = data_dir / category

    if not cat_path.is_dir():
        return {"category": category, "bundles": [], "count": 0}

    bundles: list[dict] = []
    for entry in sorted(cat_path.iterdir()):
        if not entry.is_dir():
            continue

        bundle_id = entry.name  # e.g. "2026-06-10_ОАК"
        parts = bundle_id.split("_", 1)
        date_str = parts[0]
        type_name = parts[1] if len(parts) > 1 else ""

        # Check for original attachment
        has_original = any(
            (entry / f"{bundle_id}_original{ext}").is_file()
            for ext in _EXTENSIONS
        )

        # Read frontmatter from companion .md file
        metadata: dict = {}
        md_file = entry / f"{bundle_id}.md"
        if md_file.is_file():
            try:
                with open(md_file, encoding="utf-8") as fh:
                    post = frontmatter.load(fh)
                    metadata = dict(post.metadata)
            except Exception:
                pass

        bundles.append({
            "bundle_id": bundle_id,
            "date": date_str,
            "name": type_name,
            "has_original": has_original,
            "metadata": metadata,
        })

    return {"category": category, "bundles": bundles, "count": len(bundles)}


@router.get("/{category}/{bundle_id}/original")
async def serve_original(
    category: str,
    bundle_id: str,
    user: dict = require_auth,
):
    """Serve the original JPG/PNG/PDF file for a bundle."""
    data_dir = Path(get_settings().DATA_DIR)
    filepath = _find_original(data_dir, category, bundle_id)

    if filepath is None:
        raise HTTPException(status_code=404, detail="Original file not found")

    return FileResponse(
        filepath,
        media_type=_content_type(filepath),
        filename=filepath.name,
    )


@router.get("/{category}/{bundle_id}/thumbnail")
async def serve_thumbnail(
    category: str,
    bundle_id: str,
    user: dict = require_auth,
):
    """Serve the thumbnail for a bundle (same as original for now)."""
    data_dir = Path(get_settings().DATA_DIR)
    filepath = _find_original(data_dir, category, bundle_id)

    if filepath is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(
        filepath,
        media_type=_content_type(filepath),
        filename=filepath.name,
    )
