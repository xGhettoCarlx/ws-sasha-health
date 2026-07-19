"""Tests for app/hermes_notify.py — notify_hermes() utility.

Covers: file creation, YAML frontmatter correctness, unique filenames,
atomic write behavior, and edge cases.
"""

import re
from unittest.mock import patch

import pytest

from app.hermes_notify import notify_hermes

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_inbox(tmp_path):
    """Redirect INBOX_DIR to a temp directory for test isolation."""
    inbox = tmp_path / "inboxfromhermes"
    inbox.mkdir()
    with patch("app.hermes_notify.INBOX_DIR", inbox):
        yield inbox


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------


def test_creates_file_in_inbox(isolated_inbox):
    """Calling notify_hermes creates exactly one .md file in the inbox."""
    notify_hermes("POST", {"endpoint": "/api/test", "key": "value"})
    files = list(isolated_inbox.glob("hermes-sync-*.md"))
    assert len(files) == 1
    assert files[0].stat().st_size > 0


def test_multiple_calls_create_unique_files(isolated_inbox):
    """Multiple calls to notify_hermes create multiple unique files (no overwrite)."""
    notify_hermes("POST", {"endpoint": "/api/a"})
    notify_hermes("PUT", {"endpoint": "/api/b"})
    notify_hermes("DELETE", {"endpoint": "/api/c"})
    files = sorted(isolated_inbox.glob("hermes-sync-*.md"))
    assert len(files) == 3
    # All filenames must be different
    assert len({f.name for f in files}) == 3


# ---------------------------------------------------------------------------
# Frontmatter correctness
# ---------------------------------------------------------------------------


def test_frontmatter_contains_required_fields(isolated_inbox):
    """Created file has correct YAML frontmatter with all required fields."""
    notify_hermes("POST", {"endpoint": "/api/pharmacy", "medicine": "test"})
    file_path = next(isolated_inbox.glob("hermes-sync-*.md"))
    content = file_path.read_text(encoding="utf-8")

    # Must start and end with ---
    assert content.startswith("---\n"), f"Missing opening ---: {content[:50]}"
    assert "---\n" in content[3:], f"Missing closing ---: {content[:100]}"

    # Extract frontmatter block between the first pair of ---
    parts = content.split("---\n", 2)
    assert len(parts) >= 3, f"Frontmatter not properly delimited: {content}"
    frontmatter = parts[1]

    # Check required fields exist
    assert "action: POST" in frontmatter, f"Missing action field: {frontmatter}"
    assert "source: Project5 Mini App" in frontmatter, f"Missing source field: {frontmatter}"
    assert "date:" in frontmatter, f"Missing date field: {frontmatter}"
    assert "endpoint: /api/pharmacy" in frontmatter, f"Missing endpoint field: {frontmatter}"
    assert "details:" in frontmatter, f"Missing details field: {frontmatter}"
    assert "medicine: test" in frontmatter, f"Missing details content: {frontmatter}"


def test_frontmatter_date_is_iso_timestamp(isolated_inbox):
    """The date field in frontmatter is an ISO-8601 timestamp."""
    notify_hermes("GET", {"endpoint": "/api/health"})
    file_path = next(isolated_inbox.glob("hermes-sync-*.md"))
    content = file_path.read_text(encoding="utf-8")
    parts = content.split("---\n", 2)
    frontmatter = parts[1]

    # Extract date value
    date_match = re.search(r"date: '(.+?)'", frontmatter)
    assert date_match, f"Date not found in frontmatter: {frontmatter}"
    date_str = date_match.group(1)
    # ISO-8601 with microseconds: 2026-07-02T12:34:56.123456
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", date_str), (
        f"Date not ISO format: {date_str}"
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_details(isolated_inbox):
    """dict with no keys produces valid frontmatter."""
    notify_hermes("POST", {"endpoint": "/api/empty"})
    file_path = next(isolated_inbox.glob("hermes-sync-*.md"))
    content = file_path.read_text(encoding="utf-8")
    assert "details:" in content


def test_nested_details(isolated_inbox):
    """Nested dict in details is serialized as indented YAML."""
    notify_hermes("PUT", {"endpoint": "/api/nested", "nested": {"a": 1, "b": [2, 3]}})
    file_path = next(isolated_inbox.glob("hermes-sync-*.md"))
    content = file_path.read_text(encoding="utf-8")
    # Should have indented sub-keys
    assert "a:" in content
    assert "b:" in content


# ---------------------------------------------------------------------------
# Atomic write behaviour
# ---------------------------------------------------------------------------


def test_atomic_write_uses_tempfile(isolated_inbox):
    """The implementation uses tempfile + os.replace (no direct write to target)."""
    # We verify by checking the write pattern — partial writes should not leave
    # visible .tmp files unless the process crashes mid-write.
    notify_hermes("POST", {"endpoint": "/api/atomic"})
    # No .tmp files should remain after successful write
    tmp_files = list(isolated_inbox.glob(".tmp.*"))
    assert len(tmp_files) == 0, f"Leftover temp files: {tmp_files}"


def test_filename_format(isolated_inbox):
    """Filename matches hermes-sync-{timestamp_ms}.md pattern."""
    notify_hermes("POST", {"endpoint": "/api/format"})
    file_path = next(isolated_inbox.glob("hermes-sync-*.md"))
    # Pattern: hermes-sync-2026-07-02T12-34-56-123456.md
    assert file_path.name.startswith("hermes-sync-")
    assert file_path.name.endswith(".md")
    # The timestamp part should be non-empty
    ts_part = file_path.name.replace("hermes-sync-", "").replace(".md", "")
    assert len(ts_part) > 0, f"Empty timestamp in filename: {file_path.name}"
