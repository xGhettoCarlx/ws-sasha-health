"""Application configuration via pydantic-settings.

Loads from .env file in the project root.
All secrets reference GeneralLibrary/secrets/ — never commit real values.
"""

import os
import re
from datetime import datetime
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> str:
    """Return <project_root>/data as default DATA_DIR."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
    )


def _default_static_dir() -> str:
    """Return <project_root>/frontend/dist as default STATIC_DIR."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "dist",
    )


class Settings(BaseSettings):
    """Global application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Required ---
    BOT_TOKEN: str = Field(description="Telegram bot token from @BotFather")

    # --- Optional with defaults ---
    MINI_APP_URL: str = Field(
        default="https://t.me/your_bot/app",
        description="URL of the Telegram Mini App (TMA) for the Open button",
    )
    DATA_DIR: str = Field(
        default_factory=_default_data_dir,
        description="Directory for runtime data files",
    )
    STATIC_DIR: str = Field(
        default_factory=_default_static_dir,
        description="Directory for static frontend files (HTML, JS, CSS)",
    )
    XAI_API_KEY: str | None = Field(
        default=None,
        description="xAI API key (needed for OCR; app works without it)",
    )
    HOST: str = Field(default="127.0.0.1", description="Server bind address")
    PORT: int = Field(default=8000, description="Server port", ge=1, le=65535)
    LOG_LEVEL: str = Field(
        default="info",
        description="Logging level: debug, info, warning, error",
    )
    ALLOWED_TELEGRAM_IDS: str = Field(
        default="",
        description="Comma-separated list of pre-approved Telegram user IDs. "
        "Empty string means no one is pre-approved (registration-only mode). "
        "'*' means all users allowed.",
    )
    TELEGRAM_CHAT_ID: int | None = Field(
        default=None,
        description="Telegram chat ID for cron job notifications. "
        "Required for check_medications and check_visits cron scripts.",
    )

    # ── Belgosstrakh DMS submit (optional; used by tools/belgosstrakh_submit) ──
    BGS_LOGIN: str | None = Field(default=None, description="Belgosstrakh cabinet login")
    BGS_PASSWORD: str | None = Field(default=None, description="Belgosstrakh cabinet password")
    BGS_POLICY_SERIES: str | None = Field(default=None, description="DMS policy series (BSO)")
    BGS_POLICY_NUMBER: str | None = Field(default=None, description="DMS policy number")
    BGS_PHONE: str | None = Field(default=None)
    BGS_EMAIL: str | None = Field(default=None)
    BGS_BIRTHDAY: str | None = Field(default=None, description="DD.MM.YYYY")
    BGS_FULL_NAME: str | None = Field(default=None)
    BGS_CITY: str = Field(default="Могилёв")
    BGS_ENGINE: str = Field(default="http", description="http | playwright")

    @property
    def mini_app_url_with_cache_bust(self) -> str:
        """Return MINI_APP_URL with ?v=YYYYMMDD cache-busting parameter."""
        url = self.MINI_APP_URL
        date_str = datetime.now().strftime("%Y%m%d")
        if "?v=" in url:
            return re.sub(r"\?v=\d+", f"?v={date_str}", url)
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}v={date_str}"


# Global singleton (lazy-loaded — typo-safe)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
