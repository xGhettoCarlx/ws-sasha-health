"""Telegram Mini App initData authentication.

Validates HMAC-SHA256 initData from Telegram WebApp using the
telegram-init-data library. Supports three extraction modes:
  1. Authorization header:    tma <initData>
  2. X-Telegram-InitData header
  3. Query param initData (GET only)

Dev mode: when BOT_TOKEN is not set, all auth passes with a mock user.
Exempt paths: /health, / (static files).
"""

import logging
from pathlib import Path

from fastapi import Depends, HTTPException, Request

from telegram_init_data import (
    AuthDateInvalidError,
    ExpiredError,
    SignatureInvalidError,
    SignatureMissingError,
    parse,
    validate,
)

from app.config import get_settings
from app.tenant import bind_user_from_auth, get_current_user_id, peek_current_user_id

# ── auth logger ──────────────────────────────────────────────────────────
_auth_log = logging.getLogger("auth")
_auth_log.setLevel(logging.INFO)
if not _auth_log.handlers:
    _log_path = Path(__file__).parent / "app.log"
    _fh = logging.FileHandler(str(_log_path), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _auth_log.addHandler(_fh)
    _auth_log.propagate = False

# ── helpers ────────────────────────────────────────────────────────────


# Placeholder tokens used in local .env / CI — treat as "no real bot" (dev auth).
_PLACEHOLDER_TOKENS = frozenset({
    "",
    "dev-local-placeholder",
    "ci-dummy-token-not-for-production",
    "change-me",
    "your-bot-token",
    "YOUR_BOT_TOKEN",
})


def get_bot_token() -> str | None:
    """Read the bot token from config.

    Returns None when BOT_TOKEN is not configured or is a known placeholder
    (local/dev mode — auth accepts mock user without Telegram initData).
    """
    try:
        token = (get_settings().BOT_TOKEN or "").strip()
    except Exception:
        return None
    if not token or token in _PLACEHOLDER_TOKENS:
        return None
    return token


def is_whitelisted(user_id: int) -> bool:
    """Check whether *user_id* appears in ALLOWED_TELEGRAM_IDS.

    An empty string means **no one** is pre-approved (registration-only mode).
    ``"*"`` means every user is allowed.
    """
    raw = get_settings().ALLOWED_TELEGRAM_IDS.strip()
    if raw == "*":
        return True
    if not raw:
        return False
    allowed = {int(x.strip()) for x in raw.split(",") if x.strip()}
    return user_id in allowed


# ── core validation ────────────────────────────────────────────────────


def verify_telegram_auth(init_data: str) -> dict:
    """Validate Telegram initData and return the **user** dictionary.

    Returns a dict with ``verified: bool`` indicating whether the HMAC
    signature matched the configured BOT_TOKEN.

    * ``verified=True``  — initData is from the bot configured in .env
    * ``verified=False`` — initData is from a different bot (multi-bot
      Mini App), but the user identity was still extracted.

    Raises ``HTTPException`` (401 / 403) on unparseable or missing data.
    The caller (dependency) is responsible for access-control decisions
    based on ``verified`` and the whitelist.
    """
    # ── 1. dev mode ──
    token = get_bot_token()
    if not token:
        return {"id": 0, "first_name": "Dev", "verified": True}

    # ── 2. signature + auth_date ──
    try:
        validate(init_data, token, {"expires_in": 86400})  # 24 h
    except AuthDateInvalidError:
        # ── multi-bot path: auth_date missing/invalid, try to parse user anyway ──
        #    validate() checks auth_date BEFORE HMAC — so multi-bot users with
        #    non‑standard auth_date fields get blocked here before reaching
        #    SignatureInvalidError. Fall through to parse + whitelist gate.
        try:
            data = parse(init_data)
        except Exception as exc:
            _auth_log.error(
                "Parse failed after AuthDateInvalidError: %s — "
                "token_len=%d init_data_preview=%r",
                type(exc).__name__,
                len(token),
                init_data[:50],
                exc_info=True,
            )
            raise HTTPException(status_code=401, detail="Invalid init data format") from None

        user: dict | None = data.get("user")  # type: ignore[assignment]
        if not user:
            _auth_log.warning(
                "No user in init_data after AuthDateInvalidError — "
                "token_len=%d init_data_preview=%r",
                len(token),
                init_data[:50],
            )
            raise HTTPException(status_code=401, detail="No user data in init data") from None

        _auth_log.warning(
            "AuthDateInvalid (multi-bot): user_id=%s init_data_preview=%r",
            user.get("id"),
            init_data[:50],
        )
        user["verified"] = False
        return user

    except (SignatureInvalidError, SignatureMissingError):
        # ── multi-bot path: signature mismatch/missing, try to parse user anyway ──
        try:
            data = parse(init_data)
        except Exception as exc:
            _auth_log.error(
                "Parse failed after signature issue: %s — "
                "token_len=%d init_data_preview=%r",
                type(exc).__name__,
                len(token),
                init_data[:50],
                exc_info=True,
            )
            raise HTTPException(status_code=401, detail="Invalid init data format") from None

        user: dict | None = data.get("user")  # type: ignore[assignment]
        if not user:
            _auth_log.warning(
                "No user in init_data after signature issue — "
                "token_len=%d init_data_preview=%r",
                len(token),
                init_data[:50],
            )
            raise HTTPException(status_code=401, detail="No user data in init data") from None

        _auth_log.warning(
            "Signature issue (multi-bot): user_id=%s init_data_preview=%r",
            user.get("id"),
            init_data[:50],
        )
        user["verified"] = False
        return user

    except ExpiredError as exc:
        _auth_log.error(
            "Auth failed: %s — token_len=%d init_data_preview=%r",
            type(exc).__name__,
            len(token),
            init_data[:50],
            exc_info=True,
        )
        raise HTTPException(status_code=401, detail="Authentication expired") from None

    # ── 3. parse (signature valid path) ──
    try:
        data = parse(init_data)
    except Exception as exc:
        _auth_log.error(
            "Parse failed: %s — token_len=%d init_data_preview=%r",
            type(exc).__name__,
            len(token),
            init_data[:50],
            exc_info=True,
        )
        raise HTTPException(status_code=401, detail="Invalid init data format") from None
    user: dict | None = data.get("user")  # type: ignore[assignment]
    if not user:
        _auth_log.warning(
            "No user in init_data — token_len=%d init_data_preview=%r",
            len(token),
            init_data[:50],
        )
        raise HTTPException(status_code=401, detail="No user data in init data")

    user["verified"] = True
    return user


# ── FastAPI dependency ─────────────────────────────────────────────────


def _extract_init_data(request: Request) -> str | None:
    """Extract Telegram initData from the request.

    Extraction order:
      1. ``Authorization: tma <initData>``
      2. ``X-Telegram-InitData`` header
      3. ``?initData=…`` query param (GET only)

    Returns ``None`` when no initData is present.
    Raises ``HTTPException`` (401) for unsupported Authorization schemes.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        if not auth_header.startswith("tma "):
            raise HTTPException(
                status_code=401,
                detail="Unsupported Authorization scheme — use 'tma <initData>'",
            )
        return auth_header[4:]

    init_data_header = request.headers.get("X-Telegram-InitData")
    if init_data_header:
        return init_data_header

    if request.method == "GET":
        qp = request.query_params.get("initData")
        if qp:
            return qp

    return None


async def verify_telegram_auth_from_request(request: Request) -> dict:
    """FastAPI dependency – extract, validate, check access, bind tenant.

    1. Web auth via ``X-User-ID`` header (sessionStorage after Login Widget).
    2. Extract initData from request (Authorization tma / X-Telegram-InitData).
    3. Validate HMAC signature (soft-fallback for multi-bot).
    4. Access gate: unverified users must be whitelisted.
    5. Dev mode (no real BOT_TOKEN): mock user → default tenant (Sasha).
    6. Bind ``tenant_id`` context so MDStorage scopes to data/users/<id>/.
    """
    path = request.url.path
    if path in ("/health", "/") or path.startswith("/static"):
        return {}

    user: dict

    # Prefer Telegram initData (signed) over forgeable X-User-ID
    init_data = _extract_init_data(request)
    if init_data:
        user = verify_telegram_auth(init_data)

        # Admin bypass — 80101636 is always allowed regardless of whitelist
        if user.get("id") == 80101636:
            user["verified"] = True
        elif not user.get("verified") and not is_whitelisted(user["id"]):
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "pending_approval",
                    "message": "Требуется одобрение администратора",
                    "user_id": user["id"],
                },
            )
        user["auth_method"] = user.get("auth_method") or "telegram"
    else:
        # ── Web / header path (no initData) ──
        web_user_id = request.headers.get("X-User-ID") or request.headers.get(
            "X-Telegram-User-Id"
        )
        if web_user_id:
            try:
                uid = int(web_user_id)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=401, detail="Invalid X-User-ID header"
                )
            # Admin bypass — 80101636 is always allowed regardless of whitelist
            if uid == 80101636:
                user = {"id": uid, "verified": True, "auth_method": "admin"}
            elif not is_whitelisted(uid):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "pending_approval",
                        "message": "Требуется одобрение администратора",
                        "user_id": uid,
                    },
                )
            else:
                user = {"id": uid, "verified": True, "auth_method": "web"}
        elif get_bot_token() is None:
            # Local/dev: placeholder BOT_TOKEN → open API for SPA smoke tests
            user = {
                "id": 0,
                "first_name": "Dev",
                "verified": True,
                "auth_method": "dev",
            }
        else:
            raise HTTPException(status_code=401, detail="Authentication required")

    # Multi-tenant: scope storage to data/users/<telegram_id>/
    tenant_id = bind_user_from_auth(user)
    request.state.user_id = tenant_id
    request.state.user = user
    return user


async def get_current_user_id_dep(
    user: dict = Depends(verify_telegram_auth_from_request),
) -> int:
    """Dependency: return telegram_id (tenant) for the authenticated user."""
    if "tenant_id" in user:
        return int(user["tenant_id"])
    return get_current_user_id()


# Module-level FastAPI dependency – inject with ``Depends(require_auth)``
require_auth = Depends(verify_telegram_auth_from_request)
# Explicit telegram_id for routes that only need the id
require_user_id = Depends(get_current_user_id_dep)

# re-export for ``from app.auth import get_current_user_id``
__all__ = [
    "require_auth",
    "require_user_id",
    "verify_telegram_auth",
    "verify_telegram_auth_from_request",
    "get_current_user_id",
    "get_current_user_id_dep",
    "peek_current_user_id",
    "get_bot_token",
    "is_whitelisted",
]
