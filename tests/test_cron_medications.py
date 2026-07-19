"""Tests for app/cron/check_medications.py.

Covers: stock alert (<7d), prescription alert (<30d), deduplication,
state file CRUD, edge cases (missing fields, corrupt state, no chat_id).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.cron import check_medications as cm

# Short aliases for long mock paths (ruff E501 line length)
_MED_ALERT = "app.cron.check_medications.send_medication_alert"
_MED_REMINDER = "app.cron.check_medications.send_reminder"

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch, tmp_path):
    """Set environment and reset app.config singleton so ALL modules see test DATA_DIR."""
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Reset the global _settings singleton so get_settings() rebuilds from env.
    import app.config as _cfg
    _cfg._settings = None


@pytest.fixture
def cron_store(tmp_path):
    """Return an MDStorage instance pointed at the test data dir."""
    from app.storage import MDStorage
    return MDStorage(base_dir=tmp_path)


@pytest.fixture
def today_str():
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# state file helpers
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """Tests for _load_state / _save_state cycle."""

    def test_load_empty_when_missing(self, tmp_path):
        """_load_state returns {} when no state file exists."""
        with patch.object(cm, "_state_path", return_value=tmp_path / "cron_state.json"):
            assert cm._load_state() == {}

    def test_load_existing_state(self, tmp_path):
        """_load_state correctly reads a valid JSON state file."""
        sp = tmp_path / "cron_state.json"
        sp.write_text(json.dumps({"medications": {"Aspirin": {"stock_alerted_at": "2026-07-01"}}}))
        with patch.object(cm, "_state_path", return_value=sp):
            state = cm._load_state()
            assert state["medications"]["Aspirin"]["stock_alerted_at"] == "2026-07-01"

    def test_load_corrupt_state_resets(self, tmp_path):
        """_load_state returns {} when JSON is corrupt."""
        sp = tmp_path / "cron_state.json"
        sp.write_text("not json")
        with patch.object(cm, "_state_path", return_value=sp):
            assert cm._load_state() == {}

    def test_save_and_reload_roundtrip(self, tmp_path):
        """_save_state writes state that _load_state can read back."""
        sp = tmp_path / "cron_state.json"
        with patch.object(cm, "_state_path", return_value=sp):
            cm._save_state({"medications": {"X": {"stock_alerted_at": "today"}}})
            reloaded = cm._load_state()
            assert reloaded["medications"]["X"]["stock_alerted_at"] == "today"


# ---------------------------------------------------------------------------
# _should_alert / _mark_alerted
# ---------------------------------------------------------------------------


class TestDedupLogic:
    """Tests for _should_alert and _mark_alerted deduplication."""

    def test_should_alert_when_no_prior(self):
        """Alert when no prior alert recorded for this med+type."""
        assert cm._should_alert("MedX", "stock_alerted_at", {}, "2026-07-01") is True

    def test_should_alert_when_prior_is_different_day(self):
        """Alert when prior alert was on a different day."""
        state = {"medications": {"MedX": {"stock_alerted_at": "2026-06-30"}}}
        assert cm._should_alert("MedX", "stock_alerted_at", state, "2026-07-01") is True

    def test_should_not_alert_when_prior_is_same_day(self):
        """Do NOT alert when prior alert was on the same day."""
        state = {"medications": {"MedX": {"stock_alerted_at": "2026-07-01"}}}
        assert cm._should_alert("MedX", "stock_alerted_at", state, "2026-07-01") is False

    def test_mark_alerted_sets_value(self):
        """_mark_alerted records the alert date."""
        state: dict = {}
        cm._mark_alerted("MedX", "stock_alerted_at", state, "2026-07-01")
        assert state["medications"]["MedX"]["stock_alerted_at"] == "2026-07-01"

    def test_mark_alerted_does_not_clobber_other_types(self):
        """_mark_alerted for one type doesn't overwrite another type's alert date."""
        state = {"medications": {"MedX": {"rx_alerted_at": "2026-07-01"}}}
        cm._mark_alerted("MedX", "stock_alerted_at", state, "2026-07-02")
        assert state["medications"]["MedX"]["rx_alerted_at"] == "2026-07-01"
        assert state["medications"]["MedX"]["stock_alerted_at"] == "2026-07-02"


# ---------------------------------------------------------------------------
# _stock_check
# ---------------------------------------------------------------------------


class TestStockCheck:
    """Tests for _stock_check threshold and alerting."""

    async def test_alerts_when_below_threshold(self, today_str):
        """Stock of 2 days (<7) triggers send_medication_alert."""
        with patch(_MED_ALERT, new_callable=AsyncMock) as mock_alert:
            await cm._stock_check("TestMed", 2, {}, today_str, 999)
            mock_alert.assert_awaited_once_with(999, "TestMed", 2)

    async def test_no_alert_above_threshold(self, today_str):
        """Stock of 10 days (>=7) does NOT trigger alert."""
        with patch(_MED_ALERT, new_callable=AsyncMock) as mock_alert:
            await cm._stock_check("TestMed", 10, {}, today_str, 999)
            mock_alert.assert_not_awaited()

    async def test_no_alert_at_boundary(self, today_str):
        """Stock of exactly 7 days (threshold boundary) does NOT trigger."""
        with patch(_MED_ALERT, new_callable=AsyncMock) as mock_alert:
            await cm._stock_check("TestMed", 7, {}, today_str, 999)
            mock_alert.assert_not_awaited()

    async def test_dedup_prevents_duplicate(self):
        """Already alerted today — no second alert."""
        today = date.today().isoformat()
        state = {"medications": {"TestMed": {"stock_alerted_at": today}}}
        with patch(_MED_ALERT, new_callable=AsyncMock) as mock_alert:
            await cm._stock_check("TestMed", 2, state, today, 999)
            mock_alert.assert_not_awaited()


# ---------------------------------------------------------------------------
# _rx_check
# ---------------------------------------------------------------------------


class TestRxCheck:
    """Tests for _rx_check threshold and alerting."""

    async def test_alerts_when_expires_soon(self):
        """Prescription expiring in 15 days (<30) triggers alert."""
        today = date.today()
        expiry = (today + timedelta(days=15)).isoformat()
        today_str = today.isoformat()

        with patch(_MED_REMINDER, new_callable=AsyncMock) as mock_alert:
            await cm._rx_check("TestMed", expiry, {}, today_str, today, 999)
            mock_alert.assert_awaited_once()
            args_text = mock_alert.call_args.args[1]
            assert "15" in args_text and "days" in args_text

    async def test_no_alert_when_far_future(self):
        """Prescription expiring in 60 days (>30) does NOT trigger."""
        today = date.today()
        expiry = (today + timedelta(days=60)).isoformat()
        today_str = today.isoformat()

        with patch(_MED_REMINDER, new_callable=AsyncMock) as mock_alert:
            await cm._rx_check("TestMed", expiry, {}, today_str, today, 999)
            mock_alert.assert_not_awaited()

    async def test_no_alert_when_expiry_is_none(self):
        """Missing prescription_expiry — no alert."""
        today = date.today()
        with patch(_MED_REMINDER, new_callable=AsyncMock) as mock_alert:
            await cm._rx_check("TestMed", None, {}, today.isoformat(), today, 999)
            mock_alert.assert_not_awaited()

    async def test_no_alert_when_already_expired(self, caplog):
        """Past expiry date — no alert."""
        today = date.today()
        expiry = (today - timedelta(days=5)).isoformat()
        with patch(_MED_REMINDER, new_callable=AsyncMock) as mock_alert:
            await cm._rx_check("TestMed", expiry, {}, today.isoformat(), today, 999)
            mock_alert.assert_not_awaited()

    async def test_bad_expiry_date_no_crash(self, caplog):
        """Unparseable expiry date — logs warning, no alert."""
        today = date.today()
        with patch(_MED_REMINDER, new_callable=AsyncMock) as mock_alert:
            await cm._rx_check("TestMed", "bad-date", {}, today.isoformat(), today, 999)
            mock_alert.assert_not_awaited()

    async def test_dedup_prevents_duplicate_rx_alert(self):
        """Already alerted today for rx — no second alert."""
        today = date.today()
        today_str = today.isoformat()
        expiry = (today + timedelta(days=10)).isoformat()
        state = {"medications": {"TestMed": {"rx_alerted_at": today_str}}}
        with patch(_MED_REMINDER, new_callable=AsyncMock) as mock_alert:
            await cm._rx_check("TestMed", expiry, state, today_str, today, 999)
            mock_alert.assert_not_awaited()


# ---------------------------------------------------------------------------
# run() integration tests
# ---------------------------------------------------------------------------


class TestRunMedications:
    """Integration tests for check_medications.run()."""

    @pytest.fixture(autouse=True)
    def _setup_state(self, tmp_path):
        """Ensure clean state and medication files for run tests."""
        self.tmp = tmp_path

    def _write_med(self, filename: str, name: str, days_left: int, rx_expiry: str | None = None):
        """Write a medication .md file into the test лекарства dir."""
        med_dir = self.tmp / "лекарства"
        med_dir.mkdir(exist_ok=True)
        lines = [
            "---",
            f"name: {name}",
            "dose: 100 мг",
            "frequency: daily",
            f"days_left: {days_left}",
        ]
        if rx_expiry:
            lines.append(f"prescription_expiry: '{rx_expiry}'")
        lines.append("---")
        lines.append(f"# {name}")
        (med_dir / filename).write_text("\n".join(lines), encoding="utf-8")

    async def test_run_with_low_stock_sends_alert(self):
        """Medication with 2 days_left triggers stock alert via run()."""
        self._write_med("low.md", "LowMed", 2)
        cm._state_path = lambda: self.tmp / "cron_state.json"  # type: ignore[method-assign]

        with patch(_MED_ALERT, new_callable=AsyncMock) as mock_alert:
            with patch(_MED_REMINDER, new_callable=AsyncMock):
                await cm.run()
                mock_alert.assert_awaited_once()
                assert mock_alert.call_args.args[1] == "LowMed"

    async def test_run_dedup_second_call_no_duplicate(self):
        """Second run() on the same day does not send duplicate alerts."""
        self._write_med("dup.md", "DupMed", 3)
        cm._state_path = lambda: self.tmp / "cron_state.json"  # type: ignore[method-assign]

        with patch(_MED_ALERT, new_callable=AsyncMock) as mock_alert:
            with patch(_MED_REMINDER, new_callable=AsyncMock):
                await cm.run()
                await cm.run()
                assert mock_alert.await_count == 1  # only first call sent

    async def test_run_saves_state_after_scan(self):
        """run() persists the state file after scanning medications."""
        self._write_med("savable.md", "SavableMed", 1)
        sp = self.tmp / "cron_state.json"
        cm._state_path = lambda: sp  # type: ignore[method-assign]

        with patch(_MED_ALERT, new_callable=AsyncMock):
            with patch(_MED_REMINDER, new_callable=AsyncMock):
                await cm.run()

        assert sp.exists()
        state = json.loads(sp.read_text(encoding="utf-8"))
        assert "SavableMed" in state["medications"]

    async def test_run_no_chat_id_skips(self, monkeypatch):
        """run() is a no-op when TELEGRAM_CHAT_ID is not set."""
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        import app.config as _cfg
        _cfg._settings = None
        self._write_med("nochat.md", "NoChatMed", 1)

        with patch(_MED_ALERT, new_callable=AsyncMock) as mock_alert:
            await cm.run()
            mock_alert.assert_not_awaited()

    async def test_run_no_medication_files(self):
        """run() handles empty лекарства directory gracefully."""
        cm._state_path = lambda: self.tmp / "cron_state.json"  # type: ignore[method-assign]

        with patch(_MED_ALERT, new_callable=AsyncMock):
            with patch(_MED_REMINDER, new_callable=AsyncMock):
                # Should not crash
                await cm.run()

    async def test_run_with_rx_expiring_soon(self):
        """Medication with rx expiring in 5 days triggers prescription alert."""
        today = date.today()
        rx = (today + timedelta(days=5)).isoformat()
        self._write_med("rx.md", "RxMed", 30, rx_expiry=rx)  # stock ok, rx expiring
        cm._state_path = lambda: self.tmp / "cron_state.json"  # type: ignore[method-assign]

        with patch(_MED_REMINDER, new_callable=AsyncMock) as mock_rx:
            with patch(_MED_ALERT, new_callable=AsyncMock):
                await cm.run()
                mock_rx.assert_awaited_once()
                args_text = mock_rx.call_args.args[1]
                assert "RxMed" in args_text
