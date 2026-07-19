"""Telegram bot module — notification sender only (no handlers).

Uses aiogram 3.x with lazy singleton bot initialization.
All functions are async and use HTML parse mode.
"""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

# --- Lazy singleton ---

_bot: Bot | None = None


def get_bot() -> Bot:
    """Return the cached Bot singleton, creating it lazily on first call."""
    global _bot
    if _bot is None:
        settings = get_settings()
        _bot = Bot(token=settings.BOT_TOKEN)
        logger.info("Bot singleton initialized")
    return _bot


def _mini_app_button() -> list[list[InlineKeyboardButton]]:
    """Return a single-row inline keyboard with an Open Mini App button."""
    button = InlineKeyboardButton(
        text="Open",
        web_app=WebAppInfo(url=get_settings().mini_app_url_with_cache_bust),
    )
    return [[button]]


def get_health_keyboard() -> InlineKeyboardMarkup:
    """Return an inline keyboard with the Sasha Health open button.

    Use for /start command or any entry-point message.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🏥 Открыть Sasha Health",
                web_app=WebAppInfo(url=get_settings().mini_app_url_with_cache_bust),
            ),
        ]],
    )
    return keyboard


async def _safe_send(chat_id: int, text: str, reply_markup: Any = None) -> bool:
    """Send a message with error handling. Returns True on success, False on failure."""
    bot = get_bot()
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        logger.info("Message sent to chat_id=%d", chat_id)
        return True
    except TelegramAPIError as exc:
        logger.error(
            "Telegram API error sending to chat_id=%d: %s",
            chat_id,
            exc,
        )
        return False


# --- Public notification API ---


async def send_reminder(
    chat_id: int,
    text: str,
    buttons: list[list[InlineKeyboardButton]] | None = None,
) -> bool:
    """Send a reminder message with optional inline keyboard.

    Args:
        chat_id: Telegram chat ID to send to.
        text: Message text (HTML formatted).
        buttons: Optional inline keyboard rows (list of lists of InlineKeyboardButton).

    Returns:
        True if sent successfully, False on API error.

    Example:
        >>> await send_reminder(123, "Time for your <b>workout</b>!")
    """
    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    return await _safe_send(chat_id, text, reply_markup)


async def send_verification_prompt(chat_id: int, filename: str) -> bool:
    """Notify user that a document is ready for verification.

    Sends a message with an inline "Open" button that launches
    the Telegram Mini App for document review.

    Args:
        chat_id: Telegram chat ID to send to.
        filename: Name of the document ready for verification.

    Returns:
        True if sent successfully, False on API error.
    """
    kwargs = {
        "text": (
            f"Document ready for verification:\n"
            f"<b>{filename}</b>\n\n"
            f"Tap <b>Open</b> to review it in the app."
        ),
        "reply_markup": InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="Open",
                    web_app=WebAppInfo(url=get_settings().mini_app_url_with_cache_bust),
                ),
            ]],
        ),
    }
    return await _safe_send(chat_id, **kwargs)


async def send_visit_reminder(chat_id: int, visit_info: dict[str, str]) -> bool:
    """Send a visit reminder with time and doctor info.

    Args:
        chat_id: Telegram chat ID to send to.
        visit_info: Dict with keys: doctor (str), date (str), time (str),
                    and optionally location (str), notes (str).

    Returns:
        True if sent successfully, False on API error.
    """
    doctor = visit_info.get("doctor", "N/A")
    date = visit_info.get("date", "N/A")
    time = visit_info.get("time", "N/A")
    location = visit_info.get("location", "")
    notes = visit_info.get("notes", "")

    lines = [
        "Upcoming doctor visit:",
        "",
        f"Doctor: <b>{doctor}</b>",
        f"Date: <b>{date}</b>",
        f"Time: <b>{time}</b>",
    ]
    if location:
        lines.append(f"Location: {location}")
    if notes:
        lines.append(f"Notes: {notes}")

    return await _safe_send(chat_id, "\n".join(lines))


async def send_medication_alert(
    chat_id: int,
    medicine_name: str,
    days_left: int,
) -> bool:
    """Send a low-stock warning for a medication.

    Args:
        chat_id: Telegram chat ID to send to.
        medicine_name: Name of the medication running low.
        days_left: Number of days until the supply runs out.

    Returns:
        True if sent successfully, False on API error.
    """
    urgency = "critical" if days_left <= 2 else "low"
    emoji = "🔴" if days_left <= 2 else "🟡"
    day_word = "day" if days_left == 1 else "days"

    text = (
        f"{emoji} <b>Medication Low Stock</b>\n\n"
        f"<b>{medicine_name}</b> — only <b>{days_left}</b> {day_word} left.\n"
        f"Urgency: <b>{urgency}</b>\n\n"
        f"Please refill soon."
    )
    return await _safe_send(chat_id, text)


# ── Inline button callback handler ───────────────────────────────────────


def parse_callback_data(callback_data: str) -> dict[str, str]:
    """Parse callback_data string like 'action=pill_taken&med_id=5' into a dict."""
    params = {}
    for pair in callback_data.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[key] = value
    return params


async def handle_pill_taken(
    callback_data: dict[str, str],
    message_id: int,
    chat_id: int,
) -> bool:
    """Process a pill_taken callback: decrement stock, update message.

    Args:
        callback_data: Parsed dict with keys 'action' and 'med_id'.
        message_id: Telegram message ID to edit.
        chat_id: Telegram chat ID.

    Returns:
        True if successful, False on error.
    """
    from app.storage import MDStorage

    med_id_str = callback_data.get("med_id")
    if not med_id_str:
        logger.error("Missing med_id in callback data: %s", callback_data)
        return False

    try:
        med_id = int(med_id_str)
    except ValueError:
        logger.error("Invalid med_id: %s", med_id_str)
        return False

    # Read the medication
    store = MDStorage()
    try:
        entries = store.list_dir("лекарства")
        entries.sort(key=lambda e: e.get("_path", ""))
    except Exception as exc:
        logger.error("Failed to list medications: %s", exc)
        return False

    if med_id < 0 or med_id >= len(entries):
        logger.error("med_id out of range: %d (total: %d)", med_id, len(entries))
        return False

    entry = entries[med_id]
    filepath = entry["_path"]

    # Decrement stock
    import re
    stock_str = entry.get("stock", "0")
    match = re.search(r"(\d+)", str(stock_str))
    current_stock = int(match.group(1)) if match else 0

    if current_stock <= 0:
        logger.info("Stock already zero for '%s'", entry.get("name"))
        # Still update the message
        name = entry.get("name", "Неизвестный препарат")
        text = f"✅ <b>Принято:</b> {name} (Остаток: 0 шт.)"
        bot = get_bot()
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="HTML",
            )
        except TelegramAPIError:
            pass
        return True

    new_stock = current_stock - 1
    new_stock_str = re.sub(r"\d+", str(new_stock), str(stock_str), count=1)

    # Update the medicine file
    merged = {k: v for k, v in entry.items() if k != "_path"}
    merged["stock"] = new_stock_str
    store.write(filepath, merged)

    name = entry.get("name", "Неизвестный препарат")
    text = f"✅ <b>Принято:</b> {name} (Остаток: {new_stock} шт.)"

    logger.info("Pill taken: '%s' stock %d → %d", name, current_stock, new_stock)

    # Edit the Telegram message
    bot = get_bot()
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML",
        )
        return True
    except TelegramAPIError as exc:
        logger.error("Failed to edit message: %s", exc)
        return False


async def process_callback(
    callback_data_raw: str,
    message_id: int,
    chat_id: int,
) -> bool:
    """Main entry point for processing incoming callback queries.

    Routes to the appropriate handler by parsing the 'action' parameter
    from callback_data.

    Currently supports:
        action=pill_taken&med_id=N

    Args:
        callback_data_raw: Raw callback_data string from Telegram.
        message_id: Telegram message ID.
        chat_id: Telegram chat ID.

    Returns:
        True if the callback was handled successfully, False otherwise.
    """
    params = parse_callback_data(callback_data_raw)
    action = params.get("action")

    if action == "pill_taken":
        return await handle_pill_taken(params, message_id, chat_id)

    logger.warning("Unknown callback action: %s", action)
    return False
