"""
Admin API routes — user management for Telegram ID 80101636.

Endpoints
---------
GET  /api/admin/pending  — list pending auth attempts from log files
POST /api/admin/approve  — approve a user (add to household.md)

All endpoints gate on user ID 80101636.
"""

import logging
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_auth
from app.storage import MDStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ── Admin guard ────────────────────────────────────────────────────────────

_ADMIN_ID = 80101636


def _require_admin(user: dict) -> None:
    """Raise 403 if the authenticated user is not the admin (80101636)."""
    uid = user.get("id", 0)
    if uid != _ADMIN_ID:
        raise HTTPException(
            status_code=403,
            detail="Admin access only — you are not authorized",
        )


# ── Pydantic models ────────────────────────────────────────────────────────


class PendingUser(BaseModel):
    """A single pending user from auth logs."""

    telegram_id: int = Field(description="Telegram user ID")
    first_name: Optional[str] = Field(
        default=None, description="First name if extractable from log"
    )
    timestamp: str = Field(description="ISO timestamp of last auth attempt")


class PendingList(BaseModel):
    """Response for GET /api/admin/pending."""

    count: int
    users: list[PendingUser]


class ApproveRequest(BaseModel):
    """Request body for POST /api/admin/approve."""

    telegram_id: int = Field(description="Telegram user ID to approve")
    first_name: str = Field(description="User first name")
    last_name: str = Field(default="", description="User last name")
    family: str = Field(default="", description="Family group (existing or new)")
    home: str = Field(default="", description="Home location")
    bot_token: str = Field(default="", description="Bot token for this user")


class ApproveResponse(BaseModel):
    """Response for POST /api/admin/approve."""

    status: str
    telegram_id: int
    household_entry: str


# ── Log parsing helpers ────────────────────────────────────────────────────

# Log files written by auth.py (app/app.log) and possibly data/auth.log
_LOG_PATHS = [
    Path(__file__).parent.parent / "app.log",  # app/app.log — primary
    Path(__file__).parent.parent.parent / "data" / "auth.log",  # data/auth.log — legacy
]

# Patterns for extracting user_id from log lines
_RE_USER_ID = re.compile(r"user_id=(\d+)")
_RE_TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})")
# Try to extract first_name from init_data_preview (URL-encoded user JSON)
_RE_FIRST_NAME = re.compile(r'"first_name"%3A%22([^%]+)')


def _parse_pending_users() -> list[PendingUser]:
    """Scan auth log files for unique non-admin users who attempted auth.

    Returns deduplicated list sorted by most recent first, excluding admin (80101636).
    """
    seen: dict[int, PendingUser] = {}

    for log_path in _LOG_PATHS:
        if not log_path.exists():
            continue
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for line in lines:
            # Skip non-auth lines (e.g., tracebacks, empty)
            if "user_id=" not in line:
                # Try to extract from ERROR lines with init_data_preview
                if "user=%" not in line:
                    continue

            # Extract user_id
            m = _RE_USER_ID.search(line)
            if not m:
                continue
            uid = int(m.group(1))

            # Skip admin
            if uid == _ADMIN_ID:
                continue

            # Extract timestamp
            ts = ""
            tm = _RE_TIMESTAMP.search(line)
            if tm:
                ts = tm.group(1).replace(" ", "T")

            # Try first_name from init_data
            fn = _RE_FIRST_NAME.search(line)
            first_name = fn.group(1) if fn else None

            # Keep most recent entry per user
            if uid not in seen or ts > seen[uid].timestamp:
                seen[uid] = PendingUser(
                    telegram_id=uid,
                    first_name=first_name,
                    timestamp=ts or "unknown",
                )

    # Sort newest first
    users = sorted(seen.values(), key=lambda u: u.timestamp, reverse=True)
    return users


# ── Household helpers ──────────────────────────────────────────────────────

_HOUSEHOLD_PATH = "household.md"


def _ensure_household() -> MDStorage:
    """Return store and ensure household.md exists with defaults."""
    store = MDStorage()
    filepath = store._resolve(_HOUSEHOLD_PATH)
    if not filepath.exists():
        from datetime import date as dt_date

        store.write(
            _HOUSEHOLD_PATH,
            {
                "trust_tier": "trusted",
                "date": dt_date.today().isoformat(),
                "tags": ["семья", "household"],
                "source": "Project5 Admin Panel",
                "members": [],
            },
            "# Семья / Household\n",
        )
    return store


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/pending", response_model=PendingList)
async def admin_pending(user: dict = require_auth):
    """List pending auth attempts — admin only (80101636).

    Scans auth log files for unique Telegram users who tried to authenticate
    but are not yet approved. Excludes the admin user (80101636).

    Returns list sorted by most recent attempt first.
    """
    _require_admin(user)

    users = _parse_pending_users()

    logger.info("Admin pending: %d unique users found", len(users))
    return PendingList(count=len(users), users=users)


@router.post("/approve", response_model=ApproveResponse)
async def admin_approve(body: ApproveRequest, user: dict = require_auth):
    """Approve a user — add to household.md.

    Admin only (80101636). Creates/updates household.md with the new member.
    Returns the path to the updated household entry.
    """
    _require_admin(user)

    if not body.telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id is required")
    if not body.first_name:
        raise HTTPException(status_code=400, detail="first_name is required")

    store = _ensure_household()

    # Read existing household
    metadata, content = store.read(_HOUSEHOLD_PATH)
    members: list[dict] = metadata.get("members", [])

    # Check for duplicate
    existing = [m for m in members if m.get("telegram_id") == body.telegram_id]
    if existing:
        # Update existing entry
        for m in members:
            if m.get("telegram_id") == body.telegram_id:
                m["first_name"] = body.first_name
                m["last_name"] = body.last_name
                m["family"] = body.family
                m["home"] = body.home
                if body.bot_token:
                    m["bot_token"] = body.bot_token
                m["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                break
    else:
        # Add new member
        member = {
            "telegram_id": body.telegram_id,
            "first_name": body.first_name,
            "last_name": body.last_name,
            "family": body.family,
            "home": body.home,
            "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if body.bot_token:
            member["bot_token"] = body.bot_token
        members.append(member)

    # Persist
    metadata["members"] = members
    from datetime import date as dt_date

    metadata["date"] = dt_date.today().isoformat()
    store.write(_HOUSEHOLD_PATH, metadata, content or "# Семья / Household\n")

    logger.info(
        "Admin approve: user_id=%s first_name=%s family=%s",
        body.telegram_id,
        body.first_name,
        body.family,
    )

    return ApproveResponse(
        status="ok",
        telegram_id=body.telegram_id,
        household_entry=str(body.telegram_id),
    )
