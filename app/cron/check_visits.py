"""Cron job: scan schedule/*.md — send visit reminders at 4 time windows.

Time windows (all relative to the visit's date + time):
  1. 3 days before visit, at 10:00            — "3d_before"
  2. Evening before visit, at 21:10            — "eve_before"
  3. 2 hours before visit time                 — "2h_before"
  4. 2 hours after visit time (follow-up)      — "2h_after"

Runs every 10 min via crontab.  Windows 1-2 need only the date; windows 3-4
require a parseable ``time`` field (HH:MM).  Once a window fires for a visit
it is marked complete and never repeats.

State file (``data/cron_visits_state.json``):
    {
      "visits": {
        "visit-uuid-1": {
          "3d_before": true,
          "eve_before": true,
          "2h_before": true,
          "2h_after":  true
        }
      }
    }

Usage (standalone or crontab):
    python -m app.cron.check_visits

Environment:
    TELEGRAM_CHAT_ID  — recipient chat ID (required, else no-op)
    BOT_TOKEN         — Telegram bot token (required for aiogram)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.bot import send_reminder
from app.config import get_settings
from app.storage import MDStorage

logger = logging.getLogger(__name__)

SCHEDULE_DIR = "schedule"

# Window definitions: (window_key, description, delta, time_of_day)
# delta and time_of_day are None for relative-to-visit-time windows.
WINDOW_CONFIG: list[dict[str, Any]] = [
    {
        "key": "3d_before",
        "desc": "3 days before at 10:00",
        "delta": timedelta(days=-3),
        "at_time": (10, 0),  # (hour, minute)
        "msg": (
            "Reminder: doctor visit with <b>{doctor}</b> in <b>3 days</b> "
            "— {date_str} at {time_str}"
        ),
    },
    {
        "key": "eve_before",
        "desc": "Evening before at 21:10",
        "delta": timedelta(days=-1),
        "at_time": (21, 10),
        "msg": (
            "Reminder: doctor visit <b>tomorrow</b> — "
            "<b>{doctor}</b>, {date_str} at {time_str}"
        ),
    },
    {
        "key": "2h_before",
        "desc": "2 hours before visit",
        "delta": timedelta(hours=-2),
        "at_time": None,  # relative to visit time
        "msg": (
            "Doctor visit with <b>{doctor}</b> starts in <b>2 hours</b> "
            "— {date_str} at {time_str}"
        ),
    },
    {
        "key": "2h_after",
        "desc": "2 hours after visit",
        "delta": timedelta(hours=2),
        "at_time": None,  # relative to visit time
        "msg": (
            "Your visit with <b>{doctor}</b> just ended. "
            "How did it go? Don't forget to update your health notes."
        ),
    },
]


# ---------------------------------------------------------------------------
# state persistence
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    return Path(get_settings().DATA_DIR) / "cron_visits_state.json"


def _load_state() -> dict[str, Any]:
    sp = _state_path()
    if not sp.exists():
        return {}
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt cron_visits_state.json — resetting.", exc_info=True)
        return {}


def _save_state(state: dict[str, Any]) -> None:
    _state_path().write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _window_done(visit_id: str, window_key: str, state: dict) -> bool:
    return state.get("visits", {}).get(visit_id, {}).get(window_key, False)


def _mark_window_done(visit_id: str, window_key: str, state: dict) -> None:
    state.setdefault("visits", {}).setdefault(visit_id, {})[window_key] = True


# ---------------------------------------------------------------------------
# time helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    """Return current datetime (timezone-naive, consistent with visit dates)."""
    return datetime.now()


def _parse_time(time_str: str | None) -> tuple[int, int] | None:
    """Parse HH:MM into (hour, minute) or return None."""
    if not time_str:
        return None
    for fmt in ("%H:%M", "%H.%M"):
        try:
            dt = datetime.strptime(time_str.strip(), fmt)
            return dt.hour, dt.minute
        except ValueError:
            continue
    return None


def _visit_dt(visit_date: date, hour: int, minute: int) -> datetime:
    """Combine date with hour/minute into a datetime."""
    return datetime(visit_date.year, visit_date.month, visit_date.day, hour, minute)


# ---------------------------------------------------------------------------
# window checking
# ---------------------------------------------------------------------------


def _absolute_at_time(
    visit_date: date,
    window_delta: timedelta,
    at_time: tuple[int, int] | None,
    time_tuple: tuple[int, int] | None = None,
) -> datetime | None:
    """Calculate the datetime when a window opens (the earliest we should alert).

    For absolute windows (3d_before, eve_before): on the target day at the given time.
    For relative windows (2h_before, 2h_after): visit datetime + delta.

    Returns None if the visit time is not parseable for a relative window.
    """
    if at_time is not None:
        target_date = visit_date + window_delta
        return datetime(
            target_date.year, target_date.month, target_date.day,
            at_time[0], at_time[1],
        )

    # Relative window — need visit time
    if time_tuple is None:
        return None
    visit_dt_val = _visit_dt(visit_date, time_tuple[0], time_tuple[1])
    return visit_dt_val + window_delta


# ---------------------------------------------------------------------------
# alert runners
# ---------------------------------------------------------------------------


async def _check_visit(visit: dict, state: dict, chat_id: int) -> None:
    """Evaluate all 4 windows for a single visit and send alerts as needed."""
    now = _now()

    visit_id: str = visit.get("id", "")
    if not visit_id:
        logger.debug("Skipping visit without id: %s", visit.get("doctor", "?"))
        return

    visit_date_str: str | None = visit.get("date")
    if not visit_date_str:
        return
    try:
        visit_date = date.fromisoformat(visit_date_str)
    except (ValueError, TypeError):
        return

    # Skip past visits and cancelled/completed
    status = visit.get("status", "")
    if status in ("cancelled", "completed"):
        return

    doctor = visit.get("doctor", "N/A")
    time_str = visit.get("time") or "—"
    time_tuple = _parse_time(time_str)

    for w in WINDOW_CONFIG:
        key: str = w["key"]
        if _window_done(visit_id, key, state):
            continue

        window_open = _absolute_at_time(visit_date, w["delta"], w.get("at_time"), time_tuple)
        if window_open is None:
            # Relative window with no parseable time — skip
            continue

        if now < window_open:
            # Window hasn't opened yet
            continue

        # Window is open — send the alert
        logger.info("Visit alert [%s] for visit %s (%s)", key, visit_id, doctor)
        msg = w["msg"].format(doctor=doctor, date_str=visit_date_str, time_str=time_str)
        await send_reminder(chat_id, msg)

        _mark_window_done(visit_id, key, state)


# ---------------------------------------------------------------------------
# main runner
# ---------------------------------------------------------------------------


async def run() -> None:
    """Run the visit check — scan schedule/*.md, check windows, alert with dedup."""
    settings = get_settings()
    chat_id = settings.TELEGRAM_CHAT_ID
    if chat_id is None:
        logger.warning("TELEGRAM_CHAT_ID not set — skipping visit check.")
        return

    store = MDStorage()

    metas = store.list_dir(SCHEDULE_DIR)
    if not metas:
        logger.debug("No visit files found in %s.", SCHEDULE_DIR)
        return

    state = _load_state()

    for meta in metas:
        await _check_visit(meta, state, chat_id)

    _save_state(state)
    logger.info("Visit check complete — %d visits scanned.", len(metas))


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
