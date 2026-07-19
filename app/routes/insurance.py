"""
Insurance API routes — /api/insurance GET endpoint.

Returns insurance policy data from ``data/страховка.md``.

Endpoints
---------
GET    /api/insurance/    — all insurance policies

All endpoints require Telegram initData authentication via ``require_auth``.
"""

from fastapi import APIRouter, HTTPException

from app.auth import require_auth
from app.schemas.frontmatter import from_frontmatter
from app.schemas.insurance import InsuranceSchema
from app.storage import MDStorage

router = APIRouter(prefix="/api/insurance", tags=["insurance"])


# ── helpers ────────────────────────────────────────────────────────────────


def _get_store() -> MDStorage:
    """Return a fresh MDStorage instance pointed at the configured data dir."""
    return MDStorage()


# ── endpoints ──────────────────────────────────────────────────────────────


@router.get("/")
async def list_insurance(_user: dict = require_auth):
    """Return all insurance policies from ``data/страховка.md``."""
    store = _get_store()
    try:
        meta, body = store.read("страховка.md")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Insurance data not found")

    # Propagate document-level fields into each policy so that
    # InsurancePolicy (inheriting CommonBase) passes validation.
    doc_date = meta.get("date", "")
    doc_trust_tier = meta.get("trust_tier", "unverified")
    for p in meta.get("policies", []):
        p.setdefault("date", doc_date)
        p.setdefault("trust_tier", doc_trust_tier)

    schema = from_frontmatter(InsuranceSchema, meta, body)
    return schema.model_dump(exclude_none=True)
