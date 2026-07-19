"""Tests for app/bot.py — notification sender."""

from unittest.mock import AsyncMock, patch

import pytest
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from app import bot as bot_module
from app.bot import get_bot, send_medication_alert, send_reminder, send_verification_prompt, send_visit_reminder


@pytest.fixture
def mock_bot():
    """Mock aiogram Bot with a patched send_message method."""
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=None)
    return bot


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the bot singleton before/after each test for isolation."""
    bot_module._bot = None
    yield
    bot_module._bot = None


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Ensure BOT_TOKEN and MINI_APP_URL are set for all tests."""
    monkeypatch.setenv("BOT_TOKEN", "test_token_123")
    monkeypatch.setenv("MINI_APP_URL", "https://t.me/test_bot/app")


class TestSendReminder:
    """Tests for send_reminder()."""

    async def test_sends_correct_text(self, mock_bot):
        """send_reminder passes text and HTML parse mode to send_message."""
        with patch.object(bot_module, "_bot", mock_bot):
            result = await send_reminder(chat_id=42, text="Hello <b>World</b>")

        assert result is True
        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 42
        assert call_kwargs["text"] == "Hello <b>World</b>"
        assert call_kwargs["parse_mode"] == "HTML"
        assert call_kwargs["reply_markup"] is None

    async def test_with_inline_buttons(self, mock_bot):
        """send_reminder attaches InlineKeyboardMarkup when buttons provided."""
        from aiogram.types import InlineKeyboardButton

        buttons = [[InlineKeyboardButton(text="Click", callback_data="cb")]]

        with patch.object(bot_module, "_bot", mock_bot):
            await send_reminder(chat_id=1, text="Pick one", buttons=buttons)

        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert isinstance(call_kwargs["reply_markup"], InlineKeyboardMarkup)
        markup = call_kwargs["reply_markup"]
        assert len(markup.inline_keyboard) == 1
        assert markup.inline_keyboard[0][0].text == "Click"

    async def test_handles_telegram_api_error(self, mock_bot):
        """send_reminder returns False on TelegramAPIError (no crash)."""
        mock_bot.send_message = AsyncMock(
            side_effect=TelegramAPIError(method="sendMessage", message="Forbidden")
        )
        with patch.object(bot_module, "_bot", mock_bot):
            result = await send_reminder(chat_id=99, text="test")

        assert result is False


class TestSendVerificationPrompt:
    """Tests for send_verification_prompt()."""

    async def test_mini_app_button_present(self, mock_bot):
        """Verification prompt includes an inline keyboard with a WebAppInfo button."""
        with patch.object(bot_module, "_bot", mock_bot):
            result = await send_verification_prompt(chat_id=10, filename="report.pdf")

        assert result is True
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "report.pdf" in call_kwargs["text"]

        markup = call_kwargs["reply_markup"]
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard) == 1
        button = markup.inline_keyboard[0][0]
        assert button.text == "Open"
        assert button.web_app is not None
        assert button.web_app.url == "https://t.me/test_bot/app"

    async def test_handles_api_error(self, mock_bot):
        """Verification prompt returns False on TelegramAPIError."""
        mock_bot.send_message = AsyncMock(
            side_effect=TelegramAPIError(method="sendMessage", message="Blocked")
        )
        with patch.object(bot_module, "_bot", mock_bot):
            result = await send_verification_prompt(chat_id=5, filename="scan.png")

        assert result is False


class TestSendVisitReminder:
    """Tests for send_visit_reminder()."""

    async def test_formats_doctor_date_time(self, mock_bot):
        """Visit reminder includes doctor, date, and time in HTML."""
        visit = {"doctor": "Dr. Smith", "date": "2026-07-15", "time": "14:00"}

        with patch.object(bot_module, "_bot", mock_bot):
            result = await send_visit_reminder(chat_id=3, visit_info=visit)

        assert result is True
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "<b>Dr. Smith</b>" in text
        assert "2026-07-15" in text
        assert "14:00" in text

    async def test_includes_location_and_notes(self, mock_bot):
        """Visit reminder includes optional location and notes fields."""
        visit = {
            "doctor": "Dr. Jones",
            "date": "2026-08-01",
            "time": "10:30",
            "location": "Room 302",
            "notes": "Bring test results",
        }

        with patch.object(bot_module, "_bot", mock_bot):
            await send_visit_reminder(chat_id=7, visit_info=visit)

        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "Room 302" in text
        assert "Bring test results" in text

    async def test_missing_fields_use_na(self, mock_bot):
        """Missing doctor/date/time fall back to 'N/A'."""
        with patch.object(bot_module, "_bot", mock_bot):
            await send_visit_reminder(chat_id=9, visit_info={})

        text = mock_bot.send_message.call_args.kwargs["text"]
        assert text.count("N/A") == 3  # doctor, date, time


class TestSendMedicationAlert:
    """Tests for send_medication_alert()."""

    async def test_low_stock_warning(self, mock_bot):
        """Medication alert with 5 days left shows 🟡 and 'low' urgency."""
        with patch.object(bot_module, "_bot", mock_bot):
            result = await send_medication_alert(chat_id=11, medicine_name="Aspirin", days_left=5)

        assert result is True
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "Aspirin" in text
        assert "5" in text
        assert "🟡" in text
        assert "low" in text

    async def test_critical_urgency_at_zero_days(self, mock_bot):
        """Medication alert with 0 days left shows 🔴 and 'critical'."""
        with patch.object(bot_module, "_bot", mock_bot):
            result = await send_medication_alert(chat_id=8, medicine_name="Insulin", days_left=0)

        assert result is True
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "🔴" in text
        assert "critical" in text

    async def test_critical_urgency_at_two_days(self, mock_bot):
        """Medication alert with 2 days left is still critical (threshold: <=2)."""
        with patch.object(bot_module, "_bot", mock_bot):
            await send_medication_alert(chat_id=6, medicine_name="Ibuprofen", days_left=2)

        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "🔴" in text
        assert "critical" in text

    async def test_day_one_uses_singular_form(self, mock_bot):
        """Medication alert shows '1 day' (not '1 days')."""
        with patch.object(bot_module, "_bot", mock_bot):
            await send_medication_alert(chat_id=4, medicine_name="Paracetamol", days_left=1)

        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "<b>1</b> day" in text


class TestGetBot:
    """Tests for get_bot() singleton."""

    def test_returns_singleton(self, monkeypatch):
        """get_bot() returns the same instance on repeated calls."""
        # Use a valid-format token (aiogram validates <int>:<hash>)
        monkeypatch.setenv("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        # Reset settings singleton so it picks up the new env var
        import app.config as _cfg
        _cfg._settings = None
        bot_module._bot = None

        b1 = get_bot()
        b2 = get_bot()
        assert b1 is b2
        assert b1.token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
