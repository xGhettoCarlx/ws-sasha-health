"""Tests for app.config — Settings loading, validation, defaults."""

import os

import pytest
from pydantic import ValidationError

from app.config import Settings, _default_data_dir, get_settings


class TestSettingsFromEnvFile:
    """Settings loaded from a .env file."""

    def test_load_from_env(self, tmp_path):
        """Settings reads values from an env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "BOT_TOKEN=test:token\n"
            "XAI_API_KEY=xai-key-123\n"
            "DATA_DIR=/custom/data\n"
            "HOST=0.0.0.0\n"
            "PORT=9000\n"
            "LOG_LEVEL=debug\n"
        )

        settings = Settings(_env_file=str(env_file))
        assert settings.BOT_TOKEN == "test:token"
        assert settings.XAI_API_KEY == "xai-key-123"
        assert settings.DATA_DIR == "/custom/data"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 9000
        assert settings.LOG_LEVEL == "debug"

    def test_missing_bot_token_raises_error(self, tmp_path):
        """Missing BOT_TOKEN raises ValidationError."""
        env_file = tmp_path / ".env"
        env_file.write_text("XAI_API_KEY=some-key\n")

        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=str(env_file))
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "BOT_TOKEN" in field_names

    def test_default_values_applied(self, tmp_path):
        """Default values for optional fields when not in env."""
        env_file = tmp_path / ".env"
        env_file.write_text("BOT_TOKEN=my-token\n")

        settings = Settings(_env_file=str(env_file))
        assert settings.BOT_TOKEN == "my-token"
        # XAI_API_KEY is optional — None by default
        assert settings.XAI_API_KEY is None
        # DATA_DIR defaults to <project_root>/data
        assert settings.DATA_DIR == _default_data_dir()
        # Other defaults
        assert settings.HOST == "127.0.0.1"
        assert settings.PORT == 8000
        assert settings.LOG_LEVEL == "info"


class TestGetSettings:
    """get_settings() singleton — needs BOT_TOKEN in env since no .env exists."""

    def test_singleton_returns_settings(self, monkeypatch):
        """get_settings() returns a Settings instance."""
        monkeypatch.setenv("BOT_TOKEN", "test-token")
        import app.config as _cfg

        _cfg._settings = None  # reset singleton
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_singleton_cached(self, monkeypatch):
        """get_settings() returns the same instance on second call."""
        monkeypatch.setenv("BOT_TOKEN", "test-token")
        import app.config as _cfg

        _cfg._settings = None
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
