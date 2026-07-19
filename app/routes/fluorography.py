"""
Fluorography API route — /api/fluorography.

Reads ``флюорография.md`` (YAML frontmatter) and serves
the FLG exam history as a structured JSON response.
"""

from fastapi import APIRouter, HTTPException

from app.auth import require_auth
from app.schemas.fluorography import FluorographySchema
from app.storage import MDStorage

router = APIRouter(prefix="/api/fluorography", tags=["fluorography"])

FLUOROGRAPHY_FILE = "флюорография.md"


@router.get("/")
async def get_fluorography(_user: dict = require_auth):
    """Return fluorography history and next due date.

    Reads ``data/флюорография.md``, parses the YAML frontmatter,
    and validates it against ``FluorographySchema``.

    Returns:
        200 — validated fluorography data with ``history`` and ``next_due``.
        404 — the .md file does not exist.
    """
    store = MDStorage()
    try:
        meta, _body = store.read(FLUOROGRAPHY_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Fluorography data not found")

    validated = FluorographySchema(**meta)
    return validated.model_dump(exclude_none=True)
