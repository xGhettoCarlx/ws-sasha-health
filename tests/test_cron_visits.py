"""Tests for app/cron/check_visits.py.

Covers: 4 time windows, deduplication logic, time parsing helpers,
state file CRUD, edge cases (missing fields, no chat_id, past visits,
cancelled/completed status, unparseable time).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.cron import check_visits as cv

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


# ---------------------------------------------------------------------------
# _parse_time
# ---------------------------------------------------------------------------


class TestParseTime:
    """Tests for _parse_time helper."""

    def test_colon_format(self):
        assert cv._parse_time("14:30") == (14, 30)

    def test_dot_format(self):
        assert cv._parse_time("09.05") == (9, 5)

    def test_none_input(self):
        assert cv._parse_time(None) is None

    def test_empty_string(self):
        assert cv._parse_time("") is None

    def test_garbage_input(self):
        assert cv._parse_time("afternoon") is None


# ---------------------------------------------------------------------------
# _absolute_at_time
# ---------------------------------------------------------------------------


class TestAbsoluteAtTime:
    """Tests for _absolute_at_time window-opening calculation."""

    def test_3d_before_window(self):
        """3 days before visit, at 10:00."""
        visit_date = date(2026, 7, 5)
        result = cv._absolute_at_time(visit_date, timedelta(days=-3), (10, 0))
        assert result == datetime(2026, 7, 2, 10, 0)

    def test_eve_before_window(self):
        """Evening before visit, at 21:10."""
        visit_date = date(2026, 7, 5)
        result = cv._absolute_at_time(visit_date, timedelta(days=-1), (21, 10))
        assert result == datetime(2026, 7, 4, 21, 10)

    def test_2h_before_window(self):
        """2 hours before visit time, relative calculation."""
        visit_date = date(2026, 7, 5)
        result = cv._absolute_at_time(visit_date, timedelta(hours=-2), None, (14, 0))
        assert result == datetime(2026, 7, 5, 12, 0)

    def test_2h_after_window(self):
        """2 hours after visit time, relative calculation."""
        visit_date = date(2026, 7, 5)
        result = cv._absolute_at_time(visit_date, timedelta(hours=2), None, (9, 30))
        assert result == datetime(2026, 7, 5, 11, 30)

    def test_relative_without_time_returns_none(self):
        """Relative window without visit time returns None (graceful skip)."""
        visit_date = date(2026, 7, 5)
        result = cv._absolute_at_time(visit_date, timedelta(hours=-2), None, None)
        assert result is None


# ---------------------------------------------------------------------------
# state file helpers
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """Tests for _load_state / _save_state cycle."""

    def test_load_empty_when_missing(self, tmp_path):
        sp = tmp_path / "cron_visits_state.json"
        with patch.object(cv, "_state_path", return_value=sp):
            assert cv._load_state() == {}

    def test_save_and_reload_roundtrip(self, tmp_path):
        sp = tmp_path / "cron_visits_state.json"
        with patch.object(cv, "_state_path", return_value=sp):
            cv._save_state({"visits": {"abc": {"3d_before": True}}})
            reloaded = cv._load_state()
            assert reloaded["visits"]["abc"]["3d_before"] is True


# ---------------------------------------------------------------------------
# _window_done / _mark_window_done
# ---------------------------------------------------------------------------


class TestWindowDone:
    """Tests for _window_done / _mark_window_done dedup logic."""

    def test_window_not_done_initially(self):
        assert cv._window_done("v1", "3d_before", {}) is False

    def test_window_done_after_mark(self):
        state: dict = {}
        cv._mark_window_done("v1", "3d_before", state)
        assert cv._window_done("v1", "3d_before", state) is True

    def test_mark_does_not_affect_other_windows(self):
        state: dict = {}
        cv._mark_window_done("v1", "3d_before", state)
        assert cv._window_done("v1", "eve_before", state) is False

    def test_mark_does_not_affect_other_visits(self):
        state: dict = {}
        cv._mark_window_done("v1", "3d_before", state)
        assert cv._window_done("v2", "3d_before", state) is False


# ---------------------------------------------------------------------------
# _check_visit integration
# ---------------------------------------------------------------------------


class TestCheckVisit:
    """Integration tests for _check_visit with time mocking."""

    def _make_visit(self, visit_id: str, visit_date: date, time_str: str = "14:00",
                    doctor: str = "Dr. Test", status: str = "planned"):
        return {
            "id": visit_id,
            "date": visit_date.isoformat(),
            "time": time_str,
            "doctor": doctor,
            "institution": "Clinic A",
            "notes": "",
            "status": status,
        }

    async def test_3d_before_window_triggers(self):
        """When 'now' is 3 days before at 11:00, 3d_before window fires."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 2, 11, 0)  # 3 days before, after 10:00
        visit = self._make_visit("v1", visit_date)

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, {}, 999)
                mock_send.assert_awaited_once()

    async def test_3d_before_window_too_early(self):
        """At 09:00 (before 10:00), 3d_before window does NOT fire."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 2, 9, 0)  # 3 days before but too early
        visit = self._make_visit("v2", visit_date)

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, {}, 999)
                mock_send.assert_not_awaited()

    async def test_eve_before_window_triggers(self):
        """When 'now' is day before at 22:00, eve_before fires."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 4, 22, 0)
        visit = self._make_visit("v3", visit_date)
        state = {"visits": {"v3": {"3d_before": True}}}  # earlier window already done

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, state, 999)
                mock_send.assert_awaited_once()

    async def test_2h_before_window_triggers(self):
        """1.5h before visit — 2h_before window fires."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 5, 12, 30)  # 1.5h before 14:00
        visit = self._make_visit("v4", visit_date, time_str="14:00")
        state = {"visits": {"v4": {"3d_before": True, "eve_before": True}}}

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, state, 999)
                mock_send.assert_awaited_once()

    async def test_2h_after_window_triggers(self):
        """2.5h after visit — 2h_after window fires (opens at visit+2h)."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 5, 16, 30)  # 2.5h after 14:00, past window open at 16:00
        visit = self._make_visit("v5", visit_date, time_str="14:00")
        state = {"visits": {"v5": {"3d_before": True, "eve_before": True, "2h_before": True}}}

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, state, 999)
                mock_send.assert_awaited_once()

    async def test_window_already_done_skips(self):
        """If 3d_before is already marked, it does not fire again."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 2, 11, 0)
        visit = self._make_visit("v6", visit_date)
        state = {"visits": {"v6": {"3d_before": True}}}

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, state, 999)
                mock_send.assert_not_awaited()

    async def test_cancelled_visit_skipped(self):
        """Cancelled visits are ignored completely."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 2, 11, 0)
        visit = self._make_visit("v7", visit_date, status="cancelled")

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, {}, 999)
                mock_send.assert_not_awaited()

    async def test_completed_visit_skipped(self):
        """Completed visits are ignored completely."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 2, 11, 0)
        visit = self._make_visit("v8", visit_date, status="completed")

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, {}, 999)
                mock_send.assert_not_awaited()

    async def test_no_id_skipped(self):
        """Visit without ID is skipped gracefully."""
        visit_date = date(2026, 7, 5)
        now = datetime(2026, 7, 2, 11, 0)
        visit = {"date": visit_date.isoformat(), "doctor": "X", "status": "planned"}

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, {}, 999)
                mock_send.assert_not_awaited()

    async def test_no_date_skipped(self):
        """Visit without date is skipped gracefully."""
        now = datetime(2026, 7, 2, 11, 0)
        visit = {"id": "v99", "doctor": "X", "status": "planned"}

        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv._check_visit(visit, {}, 999)
                mock_send.assert_not_awaited()


# ---------------------------------------------------------------------------
# run() integration tests
# ---------------------------------------------------------------------------


class TestRunVisits:
    """Integration tests for check_visits.run()."""

    @pytest.fixture(autouse=True)
    def _setup_dir(self, tmp_path):
        self.tmp = tmp_path

    def _write_visit(self, filename: str, visit_id: str, visit_date: date,
                     time_str: str = "14:00", doctor: str = "Dr. T",
                     status: str = "planned"):
        """Write a visit .md file into the test schedule dir."""
        sched = self.tmp / "schedule"
        sched.mkdir(exist_ok=True)
        lines = [
            "---",
            f"id: {visit_id}",
            f"date: '{visit_date.isoformat()}'",
            f"time: '{time_str}'",
            f"doctor: {doctor}",
            f"status: {status}",
            "---",
            f"# Visit {visit_id}",
        ]
        (sched / filename).write_text("\n".join(lines), encoding="utf-8")

    async def test_run_sends_alert_for_3d_window(self):
        """run() scans schedule and fires 3d_before when applicable."""
        visit_date = date.today() + timedelta(days=3)
        self._write_visit("v1.md", "v1", visit_date)
        cv._state_path = lambda: self.tmp / "cron_visits_state.json"  # type: ignore[method-assign]

        now = datetime.combine(date.today(), datetime.strptime("10:05", "%H:%M").time())
        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv.run()
                mock_send.assert_awaited_once()

    async def test_run_dedup_no_duplicate_on_second_call(self):
        """Second run() with state does not re-alert the same window."""
        visit_date = date.today() + timedelta(days=3)
        self._write_visit("v2.md", "v2", visit_date)
        cv._state_path = lambda: self.tmp / "cron_visits_state.json"  # type: ignore[method-assign]

        now = datetime.combine(date.today(), datetime.strptime("10:30", "%H:%M").time())
        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv.run()
                await cv.run()
                assert mock_send.await_count == 1

    async def test_run_no_chat_id_skips(self, monkeypatch):
        """run() is a no-op without TELEGRAM_CHAT_ID."""
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        import app.config as _cfg
        _cfg._settings = None
        visit_date = date.today() + timedelta(days=3)
        self._write_visit("v3.md", "v3", visit_date)

        now = datetime.combine(date.today(), datetime.strptime("10:05", "%H:%M").time())
        with patch.object(cv, "_now", return_value=now):
            with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock) as mock_send:
                await cv.run()
                mock_send.assert_not_awaited()

    async def test_run_empty_schedule_no_crash(self):
        """run() handles empty schedule directory gracefully."""
        cv._state_path = lambda: self.tmp / "cron_visits_state.json"  # type: ignore[method-assign]

        with patch("app.cron.check_visits.send_reminder", new_callable=AsyncMock):
            await cv.run()  # should not crash
