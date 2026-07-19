#!/usr/bin/env python3
"""
Cron script: daily medication reminder with inline "Выпил" button.

Usage:
    python scripts/cron_pill_reminder.py --chat-id 123456789

Sends a Telegram message for each daily medication with an inline
"✅ Выпил" button. The callback handler in bot.py processes the
button press and decrements stock.

Environment:
    BOT_TOKEN — Telegram bot token (from .env)
    DATA_DIR — path to data directory (default: ./data)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so we can import app modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramAPIError
from app.storage import MDStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cron_pill_reminder")

MEDICINES_DIR = "лекарства"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send daily medication reminders")
    parser.add_argument(
        "--chat-id",
        type=int,
        required=True,
        help="Telegram chat ID to send reminders to",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data")),
        help="Path to data directory",
    )
    return parser.parse_args()


def get_medications(data_dir: str) -> list[dict]:
    """Read all medications from data/лекарства/, return list of metadata dicts with IDs."""
    store = MDStorage(base_dir=data_dir)
    entries = store.list_dir(MEDICINES_DIR)
    entries.sort(key=lambda e: e.get("_path", ""))
    return entries


def filter_daily(medications: list[dict]) -> list[tuple[int, dict]]:
    """Return (id, metadata) pairs for medications with is_daily=True."""
    daily = []
    for i, entry in enumerate(medications):
        if entry.get("is_daily") is True:
            daily.append((i, entry))
    return daily


async def send_reminders(
    bot: Bot,
    chat_id: int,
    medications: list[tuple[int, dict]],
) -> int:
    """Send a reminder for each daily medication. Returns count of successfully sent messages."""
    sent = 0

    for med_id, entry in medications:
        name = entry.get("name", "Неизвестный препарат")
        dose = entry.get("dose", "")
        stock = entry.get("stock", "?")

        # Build message text
        text_lines = [
            "💊 <b>Пора принять лекарство!</b>",
            "",
            f"<b>{name}</b>",
        ]
        if dose:
            text_lines.append(f"Дозировка: {dose}")
        text_lines.append(f"Остаток: {stock}")

        # Build inline keyboard with "Выпил" button
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ Выпил",
                    callback_data=f"action=pill_taken&med_id={med_id}",
                ),
            ]],
        )

        try:
            await bot.send_message(
                chat_id=chat_id,
                text="\n".join(text_lines),
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            logger.info("Sent reminder for '%s' (med_id=%d)", name, med_id)
            sent += 1
        except TelegramAPIError as exc:
            logger.error("Failed to send reminder for '%s': %s", name, exc)

    return sent


async def main() -> None:
    args = parse_args()

    # Get bot token from environment
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        # Try loading from .env file
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BOT_TOKEN="):
                        bot_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment or .env file")
        sys.exit(1)

    # Read medications
    data_dir = args.data_dir
    if not Path(data_dir).is_dir():
        logger.error("Data directory not found: %s", data_dir)
        sys.exit(1)

    medications = get_medications(data_dir)
    logger.info("Found %d medications in %s", len(medications), data_dir)

    daily = filter_daily(medications)
    logger.info("Filtered %d daily medications", len(daily))

    if not daily:
        logger.info("No daily medications — nothing to remind about")
        return

    bot = Bot(token=bot_token)
    sent = await send_reminders(bot, args.chat_id, daily)
    logger.info("Sent %d/%d reminders", sent, len(daily))

    # Clean up bot session
    await bot.session.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
