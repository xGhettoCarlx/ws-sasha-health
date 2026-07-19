"""Cron job: scan лекарства/*.md — alert on low stock (<7d) and expiring prescriptions (<30d).

Runs once daily (recommended: 10:00 via crontab).  Uses a JSON state file
at ``data/cron_state.json`` to prevent duplicate alerts on the same day.

Usage (standalone or crontab):
    python -m app.cron.check_medications

Environment:
    TELEGRAM_CHAT_ID  — recipient chat ID (required, else no-op)
    BOT_TOKEN         — Telegram bot token (required for aiogram)

State file (``data/cron_state.json``):
    {
      "medications": {
        "Амитриптилин": {"stock_alerted_at": "2026-07-01",
                          "rx_alerted_at":   "2026-06-28"}
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from app.bot import send_medication_alert, send_reminder
from app.config import get_settings
from app.storage import MDStorage

logger = logging.getLogger(__name__)

MEDICATIONS_DIR = "лекарства"
STATE_KEY = "medications"
STOCK_THRESHOLD_DAYS = 7
RX_THRESHOLD_DAYS = 30


# ---------------------------------------------------------------------------
# state persistence
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    """Per-tenant cron state under data/users/<id>/cron_state.json."""
    from app.storage import MDStorage

    return MDStorage().base_dir / "cron_state.json"


def _load_state() -> dict[str, Any]:
    sp = _state_path()
    if not sp.exists():
        return {}
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt cron_state.json — resetting.", exc_info=True)
        return {}


def _save_state(state: dict[str, Any]) -> None:
    _state_path().write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# alert logic
# ---------------------------------------------------------------------------


def _should_alert(med_name: str, alert_type: str, state: dict, today_str: str) -> bool:
    """Return True if today differs from the last alert date for this med+type."""
    last = (
        state.get(STATE_KEY, {})
        .get(med_name, {})
        .get(alert_type)
    )
    return last != today_str


def _mark_alerted(med_name: str, alert_type: str, state: dict, today_str: str) -> None:
    state.setdefault(STATE_KEY, {}).setdefault(med_name, {})[alert_type] = today_str


async def _stock_check(
    med_name: str,
    days_left: int,
    med_state: dict,
    today_str: str,
    chat_id: int,
) -> None:
    """Alert if days_left < threshold and not already alerted today."""
    if days_left >= STOCK_THRESHOLD_DAYS:
        return
    if not _should_alert(med_name, "stock_alerted_at", med_state, today_str):
        return

    logger.info("Low stock: %s — %d days left", med_name, days_left)
    await send_medication_alert(chat_id, med_name, days_left)
    _mark_alerted(med_name, "stock_alerted_at", med_state, today_str)


async def _rx_check(
    med_name: str,
    prescription_expiry: str | None,
    med_state: dict,
    today_str: str,
    today_date: date,
    chat_id: int,
) -> None:
    """Alert if prescription expires within RX_THRESHOLD_DAYS and not already alerted today."""
    if not prescription_expiry:
        return
    try:
        expiry_date = date.fromisoformat(prescription_expiry)
    except (ValueError, TypeError):
        logger.warning("Bad prescription_expiry for %s: %r", med_name, prescription_expiry)
        return

    days_left = (expiry_date - today_date).days
    if days_left < 0:
        logger.debug("Prescription for %s already expired.", med_name)
        return
    if days_left > RX_THRESHOLD_DAYS:
        return
    if not _should_alert(med_name, "rx_alerted_at", med_state, today_str):
        return

    logger.info(
        "Prescription expiring: %s — %d days left (expires %s)",
        med_name,
        days_left,
        prescription_expiry,
    )
    await send_reminder(
        chat_id,
        f"Prescription for <b>{med_name}</b> expires in <b>{days_left}</b> days "
        f"({prescription_expiry}).\n\nPlease renew soon.",
    )
    _mark_alerted(med_name, "rx_alerted_at", med_state, today_str)


# ---------------------------------------------------------------------------
# main runner
# ---------------------------------------------------------------------------


async def run() -> None:
    """Run the medication check — scan, check thresholds, alert with dedup."""
    settings = get_settings()
    chat_id = settings.TELEGRAM_CHAT_ID
    if chat_id is None:
        logger.warning("TELEGRAM_CHAT_ID not set — skipping medication check.")
        return

    from app.tenant import KNOWN_TENANTS, SASHA_TELEGRAM_ID, set_current_user_id

    # Multi-tenant: run for each known operator with a data dir
    tenant_ids = list(KNOWN_TENANTS.keys()) or [SASHA_TELEGRAM_ID]
    today_date = date.today()
    today_str = today_date.isoformat()

    for tenant_id in tenant_ids:
        set_current_user_id(tenant_id)
        store = MDStorage.for_user(tenant_id)
        med_state = _load_state()
        med_files = store.list_dir(MEDICATIONS_DIR)
        if not med_files:
            logger.debug(
                "No medication files for tenant %s in %s.",
                tenant_id,
                MEDICATIONS_DIR,
            )
            continue

        for meta in med_files:
            med_name = meta.get("name") or meta.get("_path", "unknown")
            days_left = meta.get("days_left")
            rx_expiry: str | None = meta.get("prescription_expiry")

            if isinstance(days_left, (int, float)):
                days_left = int(days_left)
            else:
                try:
                    days_left = int(days_left) if days_left is not None else None
                except (ValueError, TypeError):
                    days_left = None

            if days_left is not None:
                await _stock_check(
                    med_name, days_left, med_state, today_str, chat_id
                )

            await _rx_check(
                med_name, rx_expiry, med_state, today_str, today_date, chat_id
            )

        _save_state(med_state)
        logger.info(
            "Medication check tenant %s — %d files scanned.",
            tenant_id,
            len(med_files),
        )


def main() -> None:
    """Entry point for crontab invocation."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
