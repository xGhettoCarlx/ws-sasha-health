"""
Profile / Card / Strategy / Symptom diary API routes.

Endpoints
---------
GET  /api/profile             — read patient card (карточка.md)
PUT  /api/profile             — update patient card fields
GET  /api/profile/strategy    — read health strategy (стратегия.md)
GET  /api/profile/symptoms    — read symptom diary, paginated by date
POST /api/profile/symptoms    — append a symptom entry

All endpoints require Telegram Mini App authentication
(via ``require_auth`` from app.auth).
"""

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import require_auth
from app.hermes_notify import notify_hermes
from app.schemas import (
    DiagnosisItem,
    ProfileSchema,
    StrategySchema,
    SymptomDiarySchema,
    SymptomEntry,
    from_frontmatter,
)
from app.storage import MDStorage

# ── router ───────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/profile", tags=["profile"])

# ── helper ───────────────────────────────────────────────────────────────


def _today_str() -> str:
    """Return today's date as an ISO-8601 string."""
    return date_type.today().isoformat()


def _get_store() -> MDStorage:
    """Return a fresh MDStorage instance pointed at the configured data dir."""
    return MDStorage()


# ── Pydantic models for request bodies ───────────────────────────────────


class ProfileUpdate(BaseModel):
    """Partial update for the patient card — every field is optional."""

    full_name: Optional[str] = Field(default=None, description="Full name (ФИО)")
    birth_date: Optional[str] = Field(
        default=None, description="Date of birth (YYYY-MM-DD)"
    )
    diagnoses: Optional[list[DiagnosisItem]] = Field(
        default=None, description="Chronic / active diagnoses"
    )
    allergies: Optional[list[str]] = Field(
        default=None, description="Known allergies"
    )


class SymptomEntryCreate(BaseModel):
    """Payload for creating a single symptom diary entry.

    The server fills in ``date`` (today) and ``trust_tier`` ("unverified").
    """

    symptom: str = Field(description="Symptom name or description")
    severity: int = Field(ge=1, le=10, description="Subjective severity (1–10)")
    notes: Optional[str] = Field(
        default=None, description="Additional context (triggers, timing, etc.)"
    )


# ── file paths (relative to DATA_DIR) ────────────────────────────────────

_PROFILE_PATH = "карточка.md"
_STRATEGY_PATH = "стратегия.md"
_SYMPTOMS_PATH = "дневник_симптомов.md"

# ═══════════════════════════════════════════════════════════════════════════
# Profile — GET /, PUT /
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=ProfileSchema)
async def get_profile(_user: dict = require_auth):
    """Return the full patient card (карточка.md)."""
    store = _get_store()
    try:
        metadata, content = store.read(_PROFILE_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Profile not found")
    return from_frontmatter(ProfileSchema, metadata, content)


@router.put("/", response_model=ProfileSchema)
async def update_profile(
    update: ProfileUpdate,
    _user: dict = require_auth,
):
    """Update patient card fields.

    Only the provided fields are changed — everything else stays unchanged.
    If the карточка.md does not exist yet, a new one is created with
    sensible defaults.
    """
    store = _get_store()

    # Read existing or start with defaults.
    try:
        metadata, content = store.read(_PROFILE_PATH)
        existing = from_frontmatter(ProfileSchema, metadata, content)
    except FileNotFoundError:
        existing = ProfileSchema(
            full_name="",
            birth_date="",
            trust_tier="unverified",
            date=_today_str(),
        )

    # Merge updates.
    update_dict = update.model_dump(exclude_none=True)
    for field_name, value in update_dict.items():
        setattr(existing, field_name, value)

    # Persist (strip content from frontmatter — it goes in the body).
    fm_dict = existing.model_dump(exclude_none=True)
    fm_dict.pop("content", None)
    store.write(_PROFILE_PATH, fm_dict, existing.content or "")
    notify_hermes("PUT", {"endpoint": "/api/profile", "updated_fields": list(update_dict.keys())})
    return existing


# ═══════════════════════════════════════════════════════════════════════════
# Strategy — GET /strategy
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/strategy", response_model=StrategySchema)
async def get_strategy(_user: dict = require_auth):
    """Return the health strategy (стратегия.md)."""
    store = _get_store()
    try:
        metadata, content = store.read(_STRATEGY_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return from_frontmatter(StrategySchema, metadata, content)


# ═══════════════════════════════════════════════════════════════════════════
# Symptoms — GET /symptoms, POST /symptoms
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/symptoms", response_model=SymptomDiarySchema)
async def get_symptoms(
    from_date: Optional[str] = Query(
        default=None,
        description="Filter entries from this date (YYYY-MM-DD, inclusive)",
    ),
    to_date: Optional[str] = Query(
        default=None,
        description="Filter entries until this date (YYYY-MM-DD, inclusive)",
    ),
    limit: int = Query(default=50, ge=1, le=500, description="Max entries to return"),
    offset: int = Query(default=0, ge=0, description="Entries to skip"),
    _user: dict = require_auth,
):
    """Return the symptom diary, optionally filtered by date range.

    Entries are paginated via *limit* and *offset* after filtering.
    """
    store = _get_store()
    try:
        metadata, content = store.read(_SYMPTOMS_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Symptom diary not found")

    diary = from_frontmatter(SymptomDiarySchema, metadata, content)

    # Filter by date range.
    entries = diary.entries
    if from_date is not None:
        entries = [e for e in entries if e.date >= from_date]
    if to_date is not None:
        entries = [e for e in entries if e.date <= to_date]

    # Paginate.
    page = entries[offset : offset + limit]

    diary.entries = page
    diary.content = content
    return diary


@router.post("/symptoms", response_model=SymptomEntry, status_code=201)
async def add_symptom(
    entry: SymptomEntryCreate,
    _user: dict = require_auth,
):
    """Append a new symptom entry to the diary.

    The diary file is created automatically if it does not exist yet.
    """
    store = _get_store()
    today = _today_str()

    # Build the full SymptomEntry (server sets date + trust_tier).
    new_entry = SymptomEntry(
        symptom=entry.symptom,
        severity=entry.severity,
        notes=entry.notes,
        trust_tier="unverified",
        date=today,
    )

    # Read existing diary or start fresh.
    try:
        metadata, content = store.read(_SYMPTOMS_PATH)
        diary = from_frontmatter(SymptomDiarySchema, metadata, content)
    except FileNotFoundError:
        diary = SymptomDiarySchema(trust_tier="unverified", date=today)

    # Prepend the new entry (newest first).
    diary.entries.insert(0, new_entry)

    # Persist (strip content from frontmatter — it goes in the body).
    fm_dict = diary.model_dump(exclude_none=True)
    fm_dict.pop("content", None)
    store.write(_SYMPTOMS_PATH, fm_dict, diary.content or "")
    notify_hermes("POST", {"endpoint": "/api/profile/symptoms",
                           "symptom": entry.symptom,
                           "severity": entry.severity})
    return new_entry
