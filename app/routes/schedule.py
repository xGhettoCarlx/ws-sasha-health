"""
Schedule API routes — /api/schedule CRUD.

Data is stored as individual .md files in ``data/schedule/``,
one file per visit.  Each file carries YAML frontmatter with all
VisitItem fields (except ``content``, which goes into the markdown
body) and is managed by ``MDStorage``.

Endpoints
---------
GET    /api/schedule/             — all visits
GET    /api/schedule/upcoming     — visits within next 30 days, sorted by date asc
POST   /api/schedule/             — create a new visit
PUT    /api/schedule/{visit_id}   — full update of an existing visit
DELETE /api/schedule/{visit_id}   — delete a visit

All endpoints require Telegram initData authentication via ``require_auth``.
"""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

from app.auth import require_auth
from app.hermes_notify import notify_hermes
from app.schemas.schedule import VisitItem
from app.storage import MDStorage

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

SCHEDULE_DIR = "schedule"


# ── helpers ────────────────────────────────────────────────────────────────


def _get_store() -> MDStorage:
    """Return a fresh MDStorage instance pointed at the configured data dir."""
    return MDStorage()


def _visit_path(visit_id: str) -> str:
    """Relative path for the visit .md file inside the schedule directory."""
    return f"{SCHEDULE_DIR}/{visit_id}.md"


def _split_visit(visit: VisitItem) -> tuple[dict, str]:
    """Split a VisitItem into (frontmatter_metadata, markdown_body).

    ``content`` from CommonBase is treated as the markdown body;
    every other field goes into YAML frontmatter.
    """
    meta = visit.model_dump(exclude_none=True)
    body = meta.pop("content", None) or ""
    return meta, body


def _visit_from_meta(meta: dict, body: str = "") -> dict:
    """Build a public visit dict from frontmatter metadata + optional body."""
    result = {k: v for k, v in meta.items() if not k.startswith("_")}
    if body:
        result["content"] = body
    return result


def _read_visit(store: MDStorage, visit_id: str) -> dict:
    """Read a visit file and return the full public dict.

    Raises HTTPException 404 if the file does not exist.
    """
    path = _visit_path(visit_id)
    try:
        meta, body = store.read(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Visit not found")
    return _visit_from_meta(meta, body)


# ── endpoints ──────────────────────────────────────────────────────────────


@router.get("/")
async def list_visits(_user: dict = require_auth):
    """Return all visits stored in ``data/schedule/``."""
    store = _get_store()
    metas = store.list_dir(SCHEDULE_DIR)
    visits = [_visit_from_meta(m) for m in metas]
    return {"visits": visits}


@router.get("/upcoming")
async def upcoming_visits(_user: dict = require_auth):
    """Return visits whose date falls within the next 30 days (inclusive).

    Results are sorted by date ascending.  Visits with a missing or
    unparseable ``date`` field are silently skipped.
    """
    today = date.today()
    cutoff = today + timedelta(days=30)

    store = _get_store()
    metas = store.list_dir(SCHEDULE_DIR)

    upcoming: list[dict] = []
    for m in metas:
        visit_date_str = m.get("date")
        if not visit_date_str:
            continue
        try:
            visit_date = date.fromisoformat(visit_date_str)
        except (ValueError, TypeError):
            continue
        if today <= visit_date <= cutoff:
            upcoming.append(_visit_from_meta(m))

    upcoming.sort(key=lambda v: v.get("date", ""))
    return {"visits": upcoming}


@router.post("/", status_code=201)
async def create_visit(visit: VisitItem, _user: dict = require_auth):
    """Create a new visit.

    If the visit has no ``id``, a UUID is generated automatically.
    """
    store = _get_store()
    visit_id = visit.id or str(uuid.uuid4())
    meta, body = _split_visit(visit)
    meta["id"] = visit_id
    store.write(_visit_path(visit_id), meta, body)
    notify_hermes("POST", {"endpoint": "/api/schedule", "visit_id": visit_id,
                           "purpose": visit.purpose or ""})
    return _read_visit(store, visit_id)


@router.put("/{visit_id}")
async def update_visit(visit_id: str, visit: VisitItem, _user: dict = require_auth):
    """Full update of an existing visit (replaces all fields)."""
    store = _get_store()
    _read_visit(store, visit_id)  # 404 if missing
    meta, body = _split_visit(visit)
    meta["id"] = visit_id
    store.write(_visit_path(visit_id), meta, body)
    notify_hermes("PUT", {"endpoint": f"/api/schedule/{visit_id}", "visit_id": visit_id})
    return _read_visit(store, visit_id)


@router.delete("/{visit_id}", status_code=204)
async def delete_visit(visit_id: str, _user: dict = require_auth):
    """Delete a visit by ID."""
    store = _get_store()
    path = _visit_path(visit_id)
    filepath = store._resolve(path)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Visit not found")
    filepath.unlink()
    notify_hermes("DELETE", {"endpoint": f"/api/schedule/{visit_id}", "visit_id": visit_id})
