"""
PWA / web auth API routes.

Endpoints
---------
POST /api/auth/pwa                — verify Telegram initData, return approval status
POST /api/auth/telegram-callback  — validate Telegram Login Widget hash (web auth)

Used by the frontend on first load to determine whether the user
has access (approved), needs admin whitelisting (pending_approval),
or the initData is invalid.
"""

import hashlib
import hmac
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth import is_whitelisted, verify_telegram_auth
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PWAAuthRequest(BaseModel):
    """Request body for PWA auth endpoint.

    ``init_data`` — raw Telegram initData string from WebApp.initData.
    """

    init_data: str


class TelegramLoginRequest(BaseModel):
    """Request body for Telegram Login Widget callback.

    Fields sent by the Telegram Login Widget after successful
    user authentication via the web login flow.

    All fields except ``id``, ``auth_date``, and ``hash`` are optional
    (may be missing depending on the user's Telegram privacy settings).
    """

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class AuthResponse(BaseModel):
    """Response returned after auth verification.

    ``status`` — "approved" (has access), "pending_approval" (needs whitelisting),
    or "invalid" (data failed verification).

    ``user_id`` — Telegram user ID (even for pending users, so the UI can show it).

    ``message`` — human-readable explanation for pending/invalid cases.
    """

    status: str
    user_id: int
    message: str | None = None


# ── Telegram Login Widget hash validation ─────────────────────────────


def _validate_telegram_login_hash(data: dict[str, Any], bot_token: str) -> bool:
    """Validate the hash from Telegram Login Widget data.

    Algorithm (from Telegram docs):
      1. Sort all fields alphabetically (excluding ``hash``).
      2. Build data_check_string: ``key1=value1\\nkey2=value2\\n...``
      3. secret_key = SHA256(bot_token)
      4. computed_hash = HMAC-SHA256(data_check_string, secret_key) → hex digest
      5. Compare with the ``hash`` field.
    """
    received_hash = data.pop("hash", "")
    if not received_hash:
        return False

    # Build data_check_string: sorted key=value pairs joined by newline
    check_items = []
    for key in sorted(data.keys()):
        value = data[key]
        if value is None:
            continue
        check_items.append(f"{key}={value}")

    data_check_string = "\n".join(check_items)

    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return computed_hash == received_hash


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/pwa", response_model=AuthResponse)
async def pwa_auth(body: PWAAuthRequest):
    """Verify Telegram initData and return approval status.

    Used by the frontend on app startup (both in Telegram and PWA contexts).
    Does NOT require prior authentication — this IS the auth entry point.

    **Flow**:

    1. Validate initData HMAC-SHA256 signature.
    2. If ``verified=True`` (same bot) → user is trusted, check whitelist.
    3. If ``verified=False`` (multi-bot) → user identity is still extracted
       but must be in ``ALLOWED_TELEGRAM_IDS`` to get "approved" status.

    Returns 200 with ``status`` in all cases (including pending) —
    only invalid/corrupt initData gets a 4xx error.
    """
    if not body.init_data or not body.init_data.strip():
        raise HTTPException(status_code=400, detail="init_data is required")

    # Validate — returns user dict with "verified" flag
    try:
        user = verify_telegram_auth(body.init_data.strip())
    except HTTPException:
        # Re-raise 401/403 from verification
        raise
    except Exception as exc:
        logger.exception("Unexpected error during PWA auth verification")
        raise HTTPException(status_code=500, detail="Auth verification failed") from exc

    user_id: int = user.get("id", 0)
    verified: bool = user.get("verified", False)

    if not user_id:
        raise HTTPException(status_code=401, detail="No user ID in init data")

    # ── Access gate ──
    if verified:
        if is_whitelisted(user_id):
            status = "approved"
            message = None
        else:
            status = "pending_approval"
            message = "Требуется одобрение администратора"
    else:
        if is_whitelisted(user_id):
            status = "approved"
            message = None
        else:
            status = "pending_approval"
            message = "Требуется одобрение администратора"

    logger.info(
        "PWA auth: user_id=%s verified=%s status=%s",
        user_id,
        verified,
        status,
    )

    return AuthResponse(
        status=status,
        user_id=user_id,
        message=message,
    )


@router.post("/telegram-callback", response_model=AuthResponse)
async def telegram_login_callback(body: TelegramLoginRequest):
    """Validate Telegram Login Widget data and return approval status.

    This is the web authentication entry point. Users who open the app
    in a regular browser (not Telegram) use the Login Widget to prove
    their Telegram identity.

    **Flow**:

    1. Frontend renders Telegram Login Widget with ``data-onauth`` callback.
    2. Widget returns user data after Telegram confirms the login.
    3. Frontend POSTs user data to this endpoint.
    4. Backend validates the ``hash`` field using HMAC-SHA256.
    5. Checks ``auth_date`` freshness (max 24 hours).
    6. Checks whitelist for access decision.

    Returns 200 with ``status`` in all cases (including pending) —
    only invalid hash or expired auth_date gets a 4xx error.
    """
    bot_token = get_settings().BOT_TOKEN
    if not bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN not configured")

    # ── 1. Check auth_date freshness (max 24 hours) ──
    now = int(time.time())
    auth_age = now - body.auth_date
    if auth_age < 0:
        raise HTTPException(status_code=400, detail="auth_date is in the future")
    if auth_age > 86400:  # 24 hours
        logger.warning(
            "Telegram Login: expired auth_date — user_id=%s auth_age=%ds",
            body.id,
            auth_age,
        )
        raise HTTPException(status_code=401, detail="Authentication expired")

    # ── 2. Validate hash ──
    login_data = body.model_dump()
    if not _validate_telegram_login_hash(login_data, bot_token):
        logger.warning(
            "Telegram Login: invalid hash — user_id=%s",
            body.id,
        )
        raise HTTPException(status_code=403, detail="Invalid authentication hash")

    # ── 3. Access gate ──
    user_id = body.id
    if is_whitelisted(user_id):
        status = "approved"
        message = None
    else:
        status = "pending_approval"
        message = "Требуется одобрение администратора"

    logger.info(
        "Telegram Login: user_id=%s status=%s first_name=%s",
        user_id,
        status,
        body.first_name,
    )

    return AuthResponse(
        status=status,
        user_id=user_id,
        message=message,
    )
