"""Multi-tenant data isolation by Telegram user ID (HEALTH-MULTI-TENANT-ROUTING).

Layout::

    {DATA_DIR}/users/<telegram_id>/
        карточка.md
        schedule/
        ...

Known tenants:
  - Sasha  80101636
  - Dasha  1342974567  (from dasha-health Hermes profile)

Dev mock user id=0 is remapped to DEFAULT_TENANT_ID (Sasha) so local SPA
keeps seeing real seed data.
"""

from __future__ import annotations

import os
import re
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from app.config import get_settings

# ── known operators ────────────────────────────────────────────────────────

SASHA_TELEGRAM_ID = 80101636
DASHA_TELEGRAM_ID = 1342974567  # Hermes dasha-health TELEGRAM_HOME_CHANNEL

KNOWN_TENANTS: dict[int, str] = {
    SASHA_TELEGRAM_ID: "sasha",
    DASHA_TELEGRAM_ID: "dasha",
}

_current_user_id: ContextVar[Optional[int]] = ContextVar(
    "health_tenant_user_id", default=None
)


def default_tenant_id() -> int:
    """Dev / unauthenticated local fallback tenant (Sasha by default)."""
    raw = (os.environ.get("DEFAULT_TENANT_ID") or str(SASHA_TELEGRAM_ID)).strip()
    try:
        return int(raw)
    except ValueError:
        return SASHA_TELEGRAM_ID


def resolve_tenant_id(user: dict | None) -> int:
    """Map auth user dict → numeric telegram_id for data path.

    - Missing / invalid → 401
    - id 0 (dev mock) → DEFAULT_TENANT_ID (Sasha)
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    raw = user.get("id")
    if raw is None:
        raise HTTPException(status_code=401, detail="No user id in auth context")
    try:
        uid = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user id") from exc
    if uid == 0:
        return default_tenant_id()
    if uid < 0:
        raise HTTPException(status_code=401, detail="Invalid user id")
    return uid


def set_current_user_id(user_id: int) -> Token:
    """Bind tenant for the current async task / request."""
    return _current_user_id.set(int(user_id))


def reset_current_user_id(token: Token) -> None:
    _current_user_id.reset(token)


def peek_current_user_id() -> Optional[int]:
    return _current_user_id.get()


def get_current_user_id() -> int:
    """Return telegram_id for the active request (or raise 401)."""
    uid = _current_user_id.get()
    if uid is None:
        raise HTTPException(
            status_code=401,
            detail="No tenant context — call require_auth first",
        )
    return int(uid)


def users_root() -> Path:
    """``{DATA_DIR}/users``."""
    return Path(get_settings().DATA_DIR) / "users"


def user_data_dir(user_id: int | str | None = None) -> Path:
    """Absolute path ``{DATA_DIR}/users/<telegram_id>/``."""
    if user_id is None:
        user_id = get_current_user_id()
    uid = int(user_id)
    # Prevent path traversal
    if uid < 0 or not re.fullmatch(r"-?\d+", str(uid)):
        raise HTTPException(status_code=400, detail="Invalid tenant id")
    path = users_root() / str(uid)
    return path


def ensure_user_data_dir(user_id: int | str | None = None) -> Path:
    """Create tenant directory if missing; return path."""
    path = user_data_dir(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def bind_user_from_auth(user: dict) -> int:
    """Resolve tenant, set contextvar + return telegram_id."""
    uid = resolve_tenant_id(user)
    set_current_user_id(uid)
    user["tenant_id"] = uid
    user["tenant_label"] = KNOWN_TENANTS.get(uid, "user")
    return uid


def tenant_info(user_id: Optional[int] = None) -> dict[str, Any]:
    uid = int(user_id if user_id is not None else get_current_user_id())
    return {
        "telegram_id": uid,
        "label": KNOWN_TENANTS.get(uid, "user"),
        "data_dir": str(user_data_dir(uid)),
    }
