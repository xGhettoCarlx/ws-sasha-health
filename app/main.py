"""Health MVP — FastAPI application."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app.auth import require_auth
from app.config import get_settings
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.fluorography import router as fluorography_router
from app.routes.history import router as history_router
from app.routes.inbox import router as inbox_router
from app.routes.insurance import router as insurance_router
from app.routes.media import router as media_router
from app.routes.navigator_api import router as navigator_router
from app.routes.pharmacy import router as pharmacy_router
from app.routes.profile import router as profile_router
from app.routes.schedule import router as schedule_router

logger = logging.getLogger(__name__)


app = FastAPI(title="Sasha Health Navigator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(fluorography_router)
app.include_router(history_router)
app.include_router(inbox_router)
app.include_router(insurance_router)
app.include_router(media_router)
app.include_router(navigator_router)
app.include_router(pharmacy_router)
app.include_router(profile_router)
app.include_router(schedule_router)


@app.get("/health")
async def health():
    """Health-check — no auth required.

    Checks:
      - Application process alive (implicit — this handler runs).
      - Storage: write → read → delete a .healthcheck temp file in DATA_DIR.
        Verifies the filesystem is mounted, writable, and accessible.

    Returns:
        200 — all checks pass, ``{"status": "healthy", "storage": "ok"}``
        503 — storage check failed, detailed error message.
    """
    storage_ok = True
    storage_detail = "ok"

    try:
        settings = get_settings()
        data_dir = Path(settings.DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)

        test_path = data_dir / ".healthcheck"
        test_content = f"healthcheck-{__import__('time').time()}\n"

        test_path.write_text(test_content, encoding="utf-8")
        read_back = test_path.read_text(encoding="utf-8")
        if read_back != test_content:
            storage_ok = False
            storage_detail = "read-back mismatch"
        else:
            test_path.unlink()

    except PermissionError:
        storage_ok = False
        storage_detail = "storage directory not writable"
    except OSError as exc:
        storage_ok = False
        storage_detail = f"storage I/O error: {exc}"
    except Exception as exc:
        storage_ok = False
        storage_detail = f"storage check failed: {exc}"

    if storage_ok:
        return {"status": "healthy", "storage": "ok"}

    logger.error("Health check FAILED — storage: %s", storage_detail)
    return JSONResponse(
        status_code=503,
        content={"status": "unhealthy", "storage": storage_detail},
    )


@app.get("/api/me")
async def api_me(user: dict = require_auth):
    """Return the current Telegram user (auth required)."""
    return {"user": user}


@app.post("/api/me")
async def api_me_post(user: dict = require_auth):
    """Same as GET /api/me but POST — query-param auth is rejected for POST."""
    return {"user": user}


@app.get("/")
async def root_redirect():
    """Redirect root to /sh/ for Mini App compatibility."""
    return RedirectResponse(url="/sh/")


# ── SPA fallback: serve index.html for client-side routes ──────────
# Mounted before any catch-all to handle /sh/ and /sh specifically,
# and /sh/{rest_of_path} for all other SPA routes.


@app.get("/sh")
@app.get("/sh/")
async def serve_spa_root():
    """Serve index.html for the /sh/ root."""
    settings = get_settings()
    index_path = Path(settings.STATIC_DIR) / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    response = FileResponse(index_path)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/sh/{rest_of_path:path}")
async def serve_spa(rest_of_path: str):
    """Serve static files or SPA fallback for client-side routes.

    If the requested path exists as a real file in STATIC_DIR, serve it.
    Otherwise serve index.html so React Router can handle the route.
    """
    settings = get_settings()

    # Security: block path traversal attempts
    if ".." in rest_of_path:
        raise HTTPException(status_code=404, detail="Not found")

    static_dir = Path(settings.STATIC_DIR)
    requested = static_dir / rest_of_path

    # Serve real files (JS, CSS, images, fonts, etc.)
    if requested.is_file():
        response = FileResponse(requested)
        if rest_of_path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response

    # SPA fallback: serve index.html for React Router client-side routes
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")

    response = FileResponse(index_path)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response
