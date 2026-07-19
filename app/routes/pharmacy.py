"""
Pharmacy API routes — medicine CRUD + stock/expiry alerts.

Prefix: /api/pharmacy
All routes require Telegram initData authentication (require_auth).

Medicines stored as individual .md files in {DATA_DIR}/лекарства/.
ID = index in alphabetically-sorted file listing (simple MVP approach).
"""

import logging
import re
from datetime import date as date_type
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_auth
from app.hermes_notify import notify_hermes
from app.storage import MDStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pharmacy", tags=["pharmacy"])

MEDICINES_DIR = "лекарства"


# ── helpers ────────────────────────────────────────────────────────────────


def _get_store() -> MDStorage:
    """Return a fresh MDStorage instance pointed at the configured data dir."""
    return MDStorage()


def _list_medicines(store: MDStorage) -> list[dict]:
    """Return all medicine metadata dicts, sorted by filename for stable ID ordering."""
    entries = store.list_dir(MEDICINES_DIR)
    entries.sort(key=lambda e: e.get("_path", ""))
    return entries


def _find_by_id(store: MDStorage, medicine_id: int) -> tuple[dict, str]:
    """Look up a medicine by its index-based ID. Returns (metadata, filepath_relative).

    Raises HTTPException 404 if the ID is out of range.
    """
    entries = _list_medicines(store)
    if medicine_id < 0 or medicine_id >= len(entries):
        raise HTTPException(status_code=404, detail="Medicine not found")
    entry = entries[medicine_id]
    return entry, entry["_path"]


def _slugify(name: str) -> str:
    """Turn a medicine name into a filesystem-safe slug."""
    return name.lower().replace(" ", "_").replace("/", "_")


def _parse_stock_number(stock_str: str | None) -> int:
    """Extract the numeric part from a stock string like '60 таб' → 60.

    Returns 0 if stock_str is None or contains no digits.
    """
    if not stock_str:
        return 0
    match = re.search(r"(\d+)", stock_str)
    return int(match.group(1)) if match else 0


def _rebuild_stock(stock_str: str | None, new_number: int) -> str:
    """Replace the numeric part of a stock string with a new number.

    '60 таб' + 45 → '45 таб'.  Falls back to str(new_number) if parsing fails.
    """
    if not stock_str:
        return str(new_number)
    return re.sub(r"\d+", str(new_number), stock_str, count=1)


def _infer_is_daily(entry: dict) -> bool:
    """Agent medicine files often omit is_daily; infer from frequency/notes."""
    if entry.get("is_daily") is True:
        return True
    if entry.get("is_daily") is False and "is_daily" in entry:
        # Explicit false only if we cannot infer regular use from text
        pass
    blob = f"{entry.get('frequency') or ''} {entry.get('notes') or ''}".lower()
    if any(k in blob for k in ("редко", "по необходимости", "при боли", "при аллерг", "п/н")):
        return False
    if any(k in blob for k in ("ежеднев", "регулярр", "на ночь", "утром", "каждый день", "1 раз в день")):
        return True
    return bool(entry.get("is_daily", False))


def _build_response(i: int, entry: dict) -> dict:
    """Build a JSON-safe dict from raw metadata dict + index-based ID."""
    stock_raw = entry.get("stock")
    stock_num = _parse_stock_number(str(stock_raw) if stock_raw is not None else None)
    return {
        "id": i,
        "name": entry.get("name", ""),
        "dose": entry.get("dose", ""),
        "frequency": entry.get("frequency", ""),
        # Keep original string for display + numeric for UI progress bars
        "stock": stock_raw if stock_raw is not None else stock_num,
        "stock_count": stock_num,
        "prescription_expiry": entry.get("prescription_expiry"),
        "notes": entry.get("notes"),
        "days_left": entry.get("days_left"),
        "is_daily": _infer_is_daily(entry),
        "daily_dose": entry.get("daily_dose"),
    }


# ── Pydantic models for request bodies ─────────────────────────────────────


class MedicineCreate(BaseModel):
    """Payload for POST / — all required fields except optional ones."""

    name: str = Field(description="Medication name")
    dose: str = Field(description="Dosage (e.g. '200 мг', '5 мг')")
    frequency: str = Field(description="How often taken (e.g. 'на ночь')")
    stock: Optional[str] = Field(default=None, description="Remaining stock")
    prescription_expiry: Optional[str] = Field(
        default=None, description="ISO date when prescription expires"
    )
    notes: Optional[str] = Field(default=None, description="Extra info")
    days_left: Optional[int] = Field(
        default=None,
        description="Estimated days of remaining stock (pre-computed, stored as-is)",
    )
    is_daily: bool = Field(default=False, description="Whether taken daily")
    daily_dose: Optional[int] = Field(
        default=None, description="Daily dosage count (e.g. pills per day)"
    )


class MedicineUpdate(BaseModel):
    """Payload for PUT /{id} — every field is optional (partial update)."""

    dose: Optional[str] = Field(default=None, description="Updated dosage")
    stock: Optional[str] = Field(default=None, description="Updated remaining stock")
    prescription_expiry: Optional[str] = Field(
        default=None, description="Updated prescription expiry (ISO date)"
    )
    notes: Optional[str] = Field(default=None, description="Updated notes")
    days_left: Optional[int] = Field(
        default=None, description="Updated estimated days of remaining stock"
    )
    is_daily: Optional[bool] = Field(default=None, description="Updated daily flag")
    daily_dose: Optional[int] = Field(
        default=None, description="Updated daily dosage count"
    )


class StockAdjustment(BaseModel):
    """Payload for POST /{id}/adjust-stock — positive = restock, negative = dispense."""

    delta: int = Field(description="Stock change (positive = restock, negative = dispense)")


# ═══════════════════════════════════════════════════════════════════════════════
# GET / — list all medicines
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/")
async def list_medicines(_user: dict = require_auth):
    """List all medicines alphabetically, each assigned an index-based ID."""
    store = _get_store()
    entries = _list_medicines(store)
    return [_build_response(i, entry) for i, entry in enumerate(entries)]


# ═══════════════════════════════════════════════════════════════════════════════
# POST / — add a new medicine
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/", status_code=201)
async def add_medicine(body: MedicineCreate, _user: dict = require_auth):
    """Add a new medicine. The filename is derived from the name (slugified).

    Returns 409 Conflict if a medicine with the same slug already exists.
    """
    store = _get_store()
    slug = _slugify(body.name)
    filepath = f"{MEDICINES_DIR}/{slug}.md"

    full_path = store._resolve(filepath)
    if full_path.exists():
        raise HTTPException(
            status_code=409, detail=f"Medicine '{body.name}' already exists"
        )

    metadata = body.model_dump(exclude_none=True)
    store.write(filepath, metadata)
    logger.info("Medicine added: %s", body.name)
    notify_hermes("POST", {"endpoint": "/api/pharmacy", "name": body.name,
                           "dose": body.dose, "frequency": body.frequency})

    # Re-list to find the newly inserted index
    entries = _list_medicines(store)
    for i, entry in enumerate(entries):
        if entry.get("_path", "").endswith(f"{slug}.md"):
            return _build_response(i, entry)

    # Fallback (shouldn't normally reach here)
    return _build_response(len(entries) - 1, metadata)


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /{id} — update a medicine
# ═══════════════════════════════════════════════════════════════════════════════


@router.put("/{medicine_id}")
async def update_medicine(
    medicine_id: int, body: MedicineUpdate, _user: dict = require_auth
):
    """Partial-update a medicine's dose, stock, prescription_expiry, or notes.

    Only the provided fields are changed — everything else stays unchanged.
    """
    store = _get_store()
    entry, filepath = _find_by_id(store, medicine_id)

    update_fields = body.model_dump(exclude_none=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Merge updates into existing metadata (strip internal _path before writing)
    merged = {k: v for k, v in entry.items() if k != "_path"}
    merged.update(update_fields)
    store.write(filepath, merged)
    logger.info("Medicine %d updated: %s", medicine_id, list(update_fields.keys()))
    notify_hermes("PUT", {"endpoint": f"/api/pharmacy/{medicine_id}",
                          "medicine_id": medicine_id,
                          "updated_fields": list(update_fields.keys())})

    return _build_response(medicine_id, merged)


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /{id} — delete a medicine
# ═══════════════════════════════════════════════════════════════════════════════


@router.delete("/{medicine_id}", status_code=204)
async def delete_medicine(medicine_id: int, _user: dict = require_auth):
    """Delete a medicine. Its .md file is permanently removed."""
    store = _get_store()
    _, filepath = _find_by_id(store, medicine_id)
    full_path = store._resolve(filepath)
    full_path.unlink()
    logger.info("Medicine %d deleted: %s", medicine_id, filepath)
    notify_hermes("DELETE", {"endpoint": f"/api/pharmacy/{medicine_id}",
                             "medicine_id": medicine_id})
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# POST /{id}/adjust-stock — adjust stock (restock / dispense)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/{medicine_id}/adjust-stock")
async def adjust_stock(
    medicine_id: int, body: StockAdjustment, _user: dict = require_auth
):
    """Adjust the stock count of a medicine.

    - Positive delta = restock (add to stock).
    - Negative delta = dispense (subtract from stock).

    If the resulting stock would be negative, returns 400.
    If the medicine has is_daily=True and daily_dose set, days_left is
    recalculated as floor(stock / daily_dose).

    Returns the updated medicine object (same shape as GET /{id}).
    """
    store = _get_store()
    entry, filepath = _find_by_id(store, medicine_id)

    current = _parse_stock_number(entry.get("stock"))
    new_stock = current + body.delta

    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock: have {current}, requested change {body.delta} "
            f"would result in {new_stock}",
        )

    # Rebuild stock string preserving unit (e.g. "45 таб")
    new_stock_str = _rebuild_stock(entry.get("stock"), new_stock)

    # Compute days_left if is_daily + daily_dose available
    recalculated_days_left: int | None = None
    if entry.get("is_daily") and entry.get("daily_dose"):
        daily_dose = entry["daily_dose"]
        if isinstance(daily_dose, int) and daily_dose > 0:
            recalculated_days_left = new_stock // daily_dose

    # Merge + save
    merged = {k: v for k, v in entry.items() if k != "_path"}
    merged["stock"] = new_stock_str
    if recalculated_days_left is not None:
        merged["days_left"] = recalculated_days_left

    store.write(filepath, merged)
    logger.info(
        "Stock adjusted for medicine %d: %d → %d (delta=%d)",
        medicine_id, current, new_stock, body.delta,
    )
    notify_hermes("POST", {
        "endpoint": f"/api/pharmacy/{medicine_id}/adjust-stock",
        "medicine_id": medicine_id,
        "delta": body.delta,
        "new_stock": new_stock_str,
    })

    return _build_response(medicine_id, merged)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /alerts — filter by stock < 7 days OR prescription_expiry < 30 days
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/alerts")
async def get_alerts(_user: dict = require_auth):
    """Return medicines that trigger an alert:

    - days_left < 7 (stock running critically low), or
    - prescription_expiry < 30 days from today (prescription about to expire).

    days_left is read directly from stored metadata (no backend calculation).
    """
    store = _get_store()
    entries = _list_medicines(store)
    today = date_type.today()

    alerts = []
    for i, entry in enumerate(entries):
        is_alert = False

        # Check days_left (pre-computed, stored as-is — rule: < 7 → alert)
        dl = entry.get("days_left")
        if isinstance(dl, int) and dl < 7:
            is_alert = True

        # Check prescription_expiry
        expiry_str = entry.get("prescription_expiry")
        if expiry_str:
            try:
                expiry_date = datetime.fromisoformat(expiry_str).date()
                remaining = (expiry_date - today).days
                if remaining < 30:
                    is_alert = True
            except (ValueError, TypeError):
                logger.debug(
                    "Invalid prescription_expiry for %s: %r",
                    entry.get("name"),
                    expiry_str,
                )

        if is_alert:
            alerts.append(_build_response(i, entry))

    return alerts
