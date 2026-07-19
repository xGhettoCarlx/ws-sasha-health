"""
History/Analytics routes — /api/history endpoints.

Pure file-scan based: no SQL, no caching without invalidation.
All routes protected with require_auth.

Scans Hermes-style directory layout:
    {category}/{YYYY-MM-DD}_{type_name}/{date}_{type}.md   (bundles)
    {category}/*.md                                        (flat files)
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_auth
from app.config import get_settings
from app.storage import MDStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])

EXAMINATION_CATEGORIES: frozenset[str] = frozenset(
    {"Анализы", "УЗИ", "МРТ-КТ", "Осмотры"}
)

VISITS_DIR = "Терапевт"
QUICK_RECORDS_DIR = "дневник"

# ── helpers ──────────────────────────────────────────────────────────────


def _get_store() -> MDStorage:
    """Return tenant-scoped MDStorage (data/users/<telegram_id>/)."""
    return MDStorage()


def _read_metadata_safe(store: MDStorage, rel_path: str) -> dict | None:
    """Read a .md file's frontmatter; return None on any error."""
    try:
        metadata, content = store.read(rel_path)
    except Exception:
        return None
    metadata["content"] = content
    return metadata


def _scan_category(store: MDStorage, category: str) -> list[dict]:
    """Scan all bundles and flat .md files in a category directory.

    Yields metadata dicts (with ``_path`` and optional ``_bundle`` keys)
    from both:
      * Bundle subdirs: {category}/{YYYY-MM-DD}_{type_name}/{date}_{type}.md
      * Flat .md files:  {category}/*.md

    Duplicate paths (e.g. flat file that was also scanned inside a bundle)
    are deduplicated.
    """
    cat_path = store.base_dir / category
    if not cat_path.is_dir():
        return []

    results: list[dict] = []
    seen: set[str] = set()

    # 1. Scan bundle subdirectories
    for bundle_dir in sorted(cat_path.iterdir()):
        if not bundle_dir.is_dir():
            continue
        md_files = sorted(bundle_dir.glob("*.md"))
        for mdf in md_files:
            rel = str(mdf.relative_to(store.base_dir))
            seen.add(rel)
            meta = _read_metadata_safe(store, rel)
            if meta is not None:
                meta["_path"] = rel
                meta["_bundle"] = str(bundle_dir.relative_to(store.base_dir))
                results.append(meta)

    # 2. Flat .md files in the category dir (not already read from a bundle)
    for mdf in sorted(cat_path.glob("*.md")):
        rel = str(mdf.relative_to(store.base_dir))
        if rel not in seen:
            seen.add(rel)
            meta = _read_metadata_safe(store, rel)
            if meta is not None:
                meta["_path"] = rel
                results.append(meta)

    return results


def _slugify(text: str) -> str:
    """Turn text into a filesystem-safe slug."""
    return text.lower().replace(" ", "_").replace("/", "_")


def _list_visits(store: MDStorage) -> list[dict]:
    """Return all visit metadata dicts from Терапевт/, sorted by path for stable ID ordering."""
    entries = store.list_dir(VISITS_DIR)
    entries.sort(key=lambda e: e.get("_path", ""))
    return entries


def _find_visit_by_id(store: MDStorage, visit_id: int) -> tuple[dict, str]:
    """Look up a visit by its index-based ID. Returns (metadata, filepath_relative).

    Raises HTTPException 404 if the ID is out of range.
    """
    entries = _list_visits(store)
    if visit_id < 0 or visit_id >= len(entries):
        raise HTTPException(status_code=404, detail="Visit not found")
    entry = entries[visit_id]
    return entry, entry["_path"]


def _build_visit_response(index: int, entry: dict) -> dict:
    """Build a JSON-safe dict from raw metadata dict + index-based ID."""
    return {
        "id": index,
        "date": entry.get("date", ""),
        "time": entry.get("time"),
        "doctor": entry.get("doctor", ""),
        "institution": entry.get("institution"),
        "purpose": entry.get("purpose"),
        "status": entry.get("status", "planned"),
        "notes": entry.get("notes"),
        "tags": entry.get("tags", []),
    }


# ── Pydantic models for visit CRUD ────────────────────────────────────────


class VisitCreate(BaseModel):
    """Payload for POST /visits."""

    date: str = Field(description="Visit date (YYYY-MM-DD)")
    time: Optional[str] = Field(default=None, description="Appointment time (HH:MM)")
    doctor: str = Field(description="Doctor name and speciality")
    institution: Optional[str] = Field(default=None, description="Medical institution")
    purpose: Optional[str] = Field(default=None, description="Reason for the visit")
    status: str = Field(default="planned", description="planned / pending / completed / cancelled")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    tags: Optional[list[str]] = Field(default=None, description="Tags / categories")


class VisitUpdate(BaseModel):
    """Payload for PUT /visits/{visit_id} — every field is optional."""

    date: Optional[str] = Field(default=None, description="Visit date (YYYY-MM-DD)")
    time: Optional[str] = Field(default=None, description="Appointment time (HH:MM)")
    doctor: Optional[str] = Field(default=None, description="Doctor name and speciality")
    institution: Optional[str] = Field(default=None, description="Medical institution")
    purpose: Optional[str] = Field(default=None, description="Reason for the visit")
    status: Optional[str] = Field(default=None, description="planned / pending / completed / cancelled")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    tags: Optional[list[str]] = Field(default=None, description="Tags / categories")


# ── Pydantic models for quick journal records ─────────────────────────


class QuickRecordCreate(BaseModel):
    """Payload for POST /quick — BP and/or weight (pulse deprecated, optional)."""

    bp: Optional[str] = Field(default=None, description="Blood pressure (e.g. '120/80')")
    weight_kg: Optional[float] = Field(default=None, ge=30, le=300, description="Weight kg")
    pulse: Optional[int] = Field(
        default=None,
        description="Deprecated — not shown in UI; kept for backward compatibility",
        ge=0,
        le=300,
    )
    notes: Optional[str] = Field(default=None, description="Optional notes")


class VisitRateRequest(BaseModel):
    """Payload for POST /{visit_id}/rate — star rating + tags."""

    rating: int = Field(ge=1, le=5, description="Star rating 1-5")
    tags: list[str] = Field(default_factory=list, description="Selected tags")


# ── endpoints ────────────────────────────────────────────────────────────


@router.get("/analytics")
async def get_analytics(category: str = None, user: dict = require_auth):
    """Aggregate all analysis parameters from a category across dates.

    Optional ``?category=`` query param specifies which examination category
    to scan (e.g. ``Анализы``, ``УЗИ``, ``МРТ-КТ``).  Defaults to
    ``Анализы`` for backward compatibility.  Non-examination categories
    return an empty result set.

    Each bundle's .md file is scanned for ``parameters`` (list of
    dicts with ``name``, ``value``, ``unit``, ``ref_range``, ``flag``).
    All parameters from all bundles are returned in a flat list.
    """
    store = _get_store()
    target = category if category else "Анализы"

    if target not in EXAMINATION_CATEGORIES:
        logger.warning("Analytics requested for non-examination category: %s", target)
        return {"count": 0, "items": []}

    analyses = _scan_category(store, target)

    aggregated: list[dict] = []
    for entry in analyses:
        date = entry.get("date", "")
        test_name = entry.get("test_name", "Неизвестный анализ")
        params = entry.get("parameters", [])
        if isinstance(params, list):
            for p in params:
                if not isinstance(p, dict):
                    continue
                aggregated.append({
                    "date": date,
                    "test_name": test_name,
                    "parameter": p.get("name", ""),
                    "value": p.get("value", ""),
                    "unit": p.get("unit"),
                    "ref_range": p.get("ref_range"),
                    "flag": p.get("flag"),
                })

    return {"count": len(aggregated), "items": aggregated}


@router.get("/visits")
async def get_visits(user: dict = require_auth):
    """List medical visits from Терапевт/, sorted by date descending.

    Scans both bundle subdirs and flat .md files in the Терапевт/ category.
    """
    store = _get_store()
    visits = _scan_category(store, "Терапевт")
    visits.sort(key=lambda v: v.get("date", ""), reverse=True)
    return {"count": len(visits), "items": visits}


@router.get("/analytics/{test_name}")
async def get_trend(test_name: str, user: dict = require_auth):
    """Longitudinal trend for a specific test parameter (e.g. 'билирубин').

    Returns ``[{date, value, unit, ref_range}]`` sorted by date ascending.
    Uses case-insensitive substring matching so ``билирубин`` matches
    ``Билирубин общий``.
    """
    store = _get_store()
    analyses = _scan_category(store, "Анализы")

    trend: list[dict] = []
    for entry in analyses:
        date = entry.get("date", "")
        params = entry.get("parameters", [])
        if isinstance(params, list):
            for p in params:
                if not isinstance(p, dict):
                    continue
                pname = p.get("name", "")
                if test_name.lower() in pname.lower():
                    trend.append({
                        "date": date,
                        "value": p.get("value", ""),
                        "unit": p.get("unit"),
                        "ref_range": p.get("ref_range"),
                    })

    trend.sort(key=lambda x: x["date"])
    return {"test_name": test_name, "count": len(trend), "trend": trend}


@router.get("/categories")
async def get_categories(user: dict = require_auth):
    """List examination category directories present in DATA_DIR.

    Only directories whose name is in ``EXAMINATION_CATEGORIES`` are returned.
    Non-examination dirs (schedule, лекарства, Терапевт) are excluded.
    """
    store = _get_store()
    cat_path = store.base_dir
    if not cat_path.is_dir():
        return {"categories": []}

    categories = sorted(
        d.name
        for d in cat_path.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and d.name in EXAMINATION_CATEGORIES
    )
    return {"categories": categories}


# ═══════════════════════════════════════════════════════════════════════════════
# POST /visits — create a visit
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/visits", status_code=201)
async def create_visit(body: VisitCreate, _user: dict = require_auth):
    """Create a new doctor visit. The filename is derived from date and doctor.

    Returns 409 Conflict if a visit with the same slug already exists.
    """
    store = _get_store()
    slug = _slugify(f"{body.date}_{body.doctor}")
    filepath = f"{VISITS_DIR}/{slug}.md"

    full_path = store._resolve(filepath)
    if full_path.exists():
        raise HTTPException(
            status_code=409, detail=f"Visit '{body.date} - {body.doctor}' already exists"
        )

    metadata: dict[str, object] = {
        "date": body.date,
        "doctor": body.doctor,
        "institution": body.institution,
        "purpose": body.purpose,
        "status": body.status,
        "tags": body.tags,
    }
    if body.time is not None:
        metadata["time"] = body.time

    store.write(filepath, metadata, content=body.notes or "")
    logger.info("Visit created: %s - %s", body.date, body.doctor)

    # Re-list to find the newly inserted index
    entries = _list_visits(store)
    for i, entry in enumerate(entries):
        if entry.get("_path", "").endswith(f"{slug}.md"):
            return _build_visit_response(i, entry)

    return _build_visit_response(len(entries) - 1, metadata)


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /visits/{visit_id} — update a visit
# ═══════════════════════════════════════════════════════════════════════════════


@router.put("/visits/{visit_id}")
async def update_visit(visit_id: int, body: VisitUpdate, _user: dict = require_auth):
    """Partial-update a visit. Only provided fields are changed."""
    store = _get_store()
    entry, filepath = _find_visit_by_id(store, visit_id)

    update_fields = body.model_dump(exclude_none=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    merged = {k: v for k, v in entry.items() if k not in ("_path", "content")}
    content = update_fields.pop("notes", None)
    if content is None:
        content = merged.pop("content", entry.get("content", ""))

    merged.update(update_fields)
    store.write(filepath, merged, content=content or "")
    logger.info("Visit %d updated: %s", visit_id, list(update_fields.keys()))

    return _build_visit_response(visit_id, merged)


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /visits/{visit_id} — delete a visit
# ═══════════════════════════════════════════════════════════════════════════════


@router.delete("/visits/{visit_id}", status_code=204)
async def delete_visit(visit_id: int, _user: dict = require_auth):
    """Delete a visit. Its .md file is permanently removed."""
    store = _get_store()
    _, filepath = _find_visit_by_id(store, visit_id)
    full_path = store._resolve(filepath)
    full_path.unlink()
    logger.info("Visit %d deleted: %s", visit_id, filepath)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# POST /quick — create a quick journal entry (BP + pulse)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/quick", status_code=201)
async def create_quick_record(body: QuickRecordCreate, _user: dict = require_auth):
    if body.bp is None and body.weight_kg is None:
        raise HTTPException(status_code=400, detail="Provide bp and/or weight_kg")

    today = date.today().isoformat()
    filename = f"{today}_быстрая_запись.md"
    filepath = f"{QUICK_RECORDS_DIR}/{filename}"

    store = _get_store()

    metadata: dict[str, object] = {
        "date": today,
        "tags": ["быстрая_запись"],
        "trust_tier": "unverified",
    }
    if body.bp is not None:
        metadata["bp"] = body.bp
    if body.weight_kg is not None:
        metadata["weight_kg"] = body.weight_kg
    # pulse intentionally not required / not preferred
    if body.pulse is not None:
        metadata["pulse"] = body.pulse
    if body.notes is not None:
        metadata["notes"] = body.notes

    store.write(filepath, metadata, content=body.notes or "")
    logger.info("Quick record created: %s bp=%s weight=%s", today, body.bp, body.weight_kg)

    record = {
        "date": today,
        "bp": body.bp,
        "weight_kg": body.weight_kg,
        "tags": ["быстрая_запись"],
        "trust_tier": "unverified",
    }
    if body.notes is not None:
        record["notes"] = body.notes
    return record


# ═══════════════════════════════════════════════════════════════════════════════
# GET /quick — list recent quick journal records
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/quick")
async def get_quick_records(user: dict = require_auth):
    store = _get_store()
    dir_path = store.base_dir / QUICK_RECORDS_DIR
    if not dir_path.is_dir():
        return []

    records: list[dict] = []
    for md_file in sorted(dir_path.glob("*.md"), reverse=True):
        rel = str(md_file.relative_to(store.base_dir))
        meta = _read_metadata_safe(store, rel)
        if meta is not None:
            records.append(meta)
        if len(records) >= 3:
            break

    return records


@router.post("/{visit_id}/rate")
async def rate_visit(visit_id: int, body: VisitRateRequest, _user: dict = require_auth):
    """Rate a visit with stars 1-5 and optional tags."""
    store = _get_store()
    entry, filepath = _find_visit_by_id(store, visit_id)
    merged = {k: v for k, v in entry.items() if k not in ("_path", "content")}
    merged["rating"] = body.rating
    merged["rate_tags"] = body.tags
    content = entry.get("content", "")
    store.write(filepath, merged, content=content or "")
    return {"status": "ok", "rating": body.rating}


