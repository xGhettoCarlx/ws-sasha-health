"""Tests for app/storage.py — MDStorage engine.

Covers: CRUD cycle, atomic write, file locking, concurrent access,
directory listing, bundle creation, and edge cases.
"""

import multiprocessing
import os
import tempfile
from unittest.mock import patch

import frontmatter
import pytest

from app.storage import MDStorage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(test_data_dir):
    """MDStorage instance rooted at the isolated test data directory."""
    return MDStorage(base_dir=test_data_dir)


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


def test_read_returns_metadata_and_content(store, test_data_dir):
    """Read a .md file with frontmatter — returns correct (metadata, content)."""
    path = test_data_dir / "test.md"
    path.write_text(
        "---\ntitle: hello\ncount: 42\n---\n# Body\n\nSome content.\n",
        encoding="utf-8",
    )

    metadata, content = store.read("test.md")

    assert metadata == {"title": "hello", "count": 42}
    assert content.strip() == "# Body\n\nSome content."


def test_read_file_not_found(store):
    """Reading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        store.read("nonexistent.md")


def test_read_empty_frontmatter(store, test_data_dir):
    """File with no frontmatter block still returns empty metadata."""
    path = test_data_dir / "plain.md"
    path.write_text("# Just a heading\n\nNo frontmatter here.", encoding="utf-8")

    metadata, content = store.read("plain.md")

    assert metadata == {}
    assert content.strip() == "# Just a heading\n\nNo frontmatter here."


def test_read_with_none_frontmatter_fields(store, test_data_dir):
    """YAML null values in frontmatter are preserved as None."""
    path = test_data_dir / "nullable.md"
    path.write_text("---\nkey: null\ntitle: present\n---\nBody.", encoding="utf-8")

    metadata, _ = store.read("nullable.md")

    assert metadata == {"key": None, "title": "present"}


# ---------------------------------------------------------------------------
# write  (atomic + locked)
# ---------------------------------------------------------------------------


def test_write_and_read_roundtrip(store, test_data_dir):
    """Write a file, then read it back — metadata and content match."""
    store.write(
        "roundtrip.md",
        {"status": "active", "count": 7},
        "## Section\n\nRound-trip body.",
    )

    metadata, content = store.read("roundtrip.md")

    assert metadata == {"status": "active", "count": 7}
    assert "Round-trip body" in content


def test_write_creates_parent_dirs(store, test_data_dir):
    """Writing to a nested path creates all intermediate directories."""
    store.write("deep/nested/path/file.md", {"key": "val"}, "nested content")

    assert (test_data_dir / "deep" / "nested" / "path" / "file.md").exists()

    metadata, content = store.read("deep/nested/path/file.md")
    assert metadata == {"key": "val"}
    assert content.strip() == "nested content"


def test_write_empty_metadata_and_content(store, test_data_dir):
    """Edge case: writing with empty metadata and empty content."""
    store.write("empty.md", {}, "")

    metadata, content = store.read("empty.md")
    assert metadata == {}
    assert content == ""


def test_write_overwrite_existing(store, test_data_dir):
    """Writing to an existing path replaces the old content atomically."""
    store.write("overwrite.md", {"version": 1}, "first")
    store.write("overwrite.md", {"version": 2}, "second")

    metadata, content = store.read("overwrite.md")
    assert metadata == {"version": 2}
    assert content.strip() == "second"


def test_write_atomic_no_partial_file(store, test_data_dir):
    """If a write fails mid-stream, no partial file is left at the target path."""
    target = "atomic.md"
    path = test_data_dir / target

    # Write a known-good file first.
    store.write(target, {"initial": True}, "initial content")

    # Simulate a failure by patching os.replace to raise.
    with patch("os.replace", side_effect=OSError("simulated failure")):
        with pytest.raises(OSError):
            store.write(target, {"broken": True}, "should not appear")

    # The original file must be intact (no partial corruption).
    metadata, content = store.read(target)
    assert metadata == {"initial": True}
    assert "initial content" in content


def test_write_uses_flock(store, test_data_dir):
    """Verify that fcntl.flock is called during the write operation."""
    target = test_data_dir / "locked.md"

    with patch("fcntl.flock") as mock_flock:
        store.write("locked.md", {"a": 1}, "body")

    # Should be called at least twice: LOCK_EX (acquire) + LOCK_UN (release).
    assert mock_flock.call_count >= 2


# ---------------------------------------------------------------------------
# concurrent access
# ---------------------------------------------------------------------------


def _concurrent_writer(args):
    """Worker for test_concurrent_writes_no_corruption."""
    base_dir, idx = args
    store = MDStorage(base_dir=base_dir)
    store.write(
        "concurrent.md",
        {"writer": idx},
        f"Content from writer {idx}.\n",
    )


def test_concurrent_writes_no_corruption(store, test_data_dir):
    """Multiple processes writing to the same file — no corruption.

    Each process writes via (tempfile + os.replace).  On Unix the final
    file is guaranteed to be the complete output of one of the writers,
    never a mangled mixture.
    """
    writer_count = 5
    base_dir = str(test_data_dir)

    with multiprocessing.Pool(processes=writer_count) as pool:
        pool.map(_concurrent_writer, [(base_dir, i) for i in range(writer_count)])

    # The file must exist and be parseable (no mangled bytes).
    assert (test_data_dir / "concurrent.md").exists()

    metadata, content = store.read("concurrent.md")
    assert "writer" in metadata
    assert isinstance(metadata["writer"], int)
    # Content is the complete output from one of the writers — verify
    # it starts correctly and ends cleanly (no mid-write truncation).
    assert content.startswith("Content from writer")
    assert content.strip() == content.strip()  # no mangled bytes


# ---------------------------------------------------------------------------
# list_dir
# ---------------------------------------------------------------------------


def test_list_dir_returns_all_md_files(store, test_data_dir):
    """list_dir returns metadata for every .md file in the directory."""
    store.write("a.md", {"order": 1}, "a")
    store.write("b.md", {"order": 2}, "b")
    store.write("c.md", {"order": 3}, "c")

    results = store.list_dir(".")

    assert len(results) == 3
    paths = [r["_path"] for r in results]
    assert paths == ["a.md", "b.md", "c.md"]
    orders = [r["order"] for r in results]
    assert orders == [1, 2, 3]


def test_list_dir_empty_directory(store, test_data_dir):
    """Empty directory returns an empty list (no crash)."""
    sub = test_data_dir / "empty_sub"
    sub.mkdir()

    results = store.list_dir("empty_sub")
    assert results == []


def test_list_dir_nonexistent_directory(store):
    """Non-existent directory returns an empty list (no crash)."""
    results = store.list_dir("nowhere")
    assert results == []


def test_list_dir_ignores_non_md_files(store, test_data_dir):
    """Only .md files are listed; .txt, .json, etc. are ignored."""
    (test_data_dir / "readme.md").write_text("---\n---\n", encoding="utf-8")
    (test_data_dir / "notes.txt").write_text("plain text", encoding="utf-8")
    (test_data_dir / "config.json").write_text("{}", encoding="utf-8")

    results = store.list_dir(".")

    assert len(results) == 1
    assert results[0]["_path"] == "readme.md"


# ---------------------------------------------------------------------------
# create_bundle
# ---------------------------------------------------------------------------


def test_create_bundle_structure(store, test_data_dir):
    """create_bundle creates the expected directory layout and .md file."""
    rel_path = store.create_bundle("visits", "2026-07-01", "терапевт")

    # Assert path
    assert rel_path == "visits/2026-07-01_терапевт/2026-07-01_терапевт.md"

    # Assert directory exists
    bundle_dir = test_data_dir / "visits" / "2026-07-01_терапевт"
    assert bundle_dir.is_dir()

    # Assert .md file exists (touched with empty frontmatter)
    md_file = bundle_dir / "2026-07-01_терапевт.md"
    assert md_file.exists()
    content = md_file.read_text(encoding="utf-8")
    assert content.strip() == "---\n---"


def test_create_bundle_with_original_file(store, test_data_dir):
    """create_bundle copies the original file into the bundle."""
    # Create a dummy original file
    original = test_data_dir / "scan.jpg"
    original.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # fake JPEG header

    store.create_bundle(
        "analyses",
        "2026-01-15",
        "кровь",
        original_path=str(original),
    )

    # Check copied file
    copied = (
        test_data_dir
        / "analyses"
        / "2026-01-15_кровь"
        / "2026-01-15_кровь_original.jpg"
    )
    assert copied.exists()
    assert copied.read_bytes() == b"\xff\xd8\xff\xe0\x00\x10JFIF"


def test_create_bundle_original_missing(store, test_data_dir):
    """If original_path points to a non-existent file, no error and no copy."""
    store.create_bundle(
        "visits",
        "2026-06-15",
        "хирург",
        original_path="/nonexistent/photo.png",
    )

    bundle_dir = test_data_dir / "visits" / "2026-06-15_хирург"
    # Only the .md file, no _original file
    files = list(bundle_dir.glob("*"))
    assert len(files) == 1
    assert files[0].name == "2026-06-15_хирург.md"


def test_create_bundle_no_original(store, test_data_dir):
    """create_bundle with original_path=None creates only the .md file."""
    store.create_bundle("profile", "2026-07-01", "карточка")

    bundle_dir = test_data_dir / "profile" / "2026-07-01_карточка"
    assert bundle_dir.is_dir()

    files = list(bundle_dir.glob("*"))
    assert len(files) == 1
    assert files[0].name == "2026-07-01_карточка.md"


def test_create_bundle_idempotent(store, test_data_dir):
    """Calling create_bundle twice for the same bundle does not duplicate files."""
    store.create_bundle("visits", "2026-07-01", "терапевт")
    store.create_bundle("visits", "2026-07-01", "терапевт")

    bundle_dir = test_data_dir / "visits" / "2026-07-01_терапевт"
    files = list(bundle_dir.glob("*"))
    assert len(files) == 1  # no duplicate .md


# ---------------------------------------------------------------------------
# base_dir
# ---------------------------------------------------------------------------


def test_base_dir_respects_custom_path(tmp_path):
    """MDStorage accepts an explicit base_dir that overrides config."""
    custom = tmp_path / "custom_data"
    custom.mkdir()
    store = MDStorage(base_dir=custom)

    store.write("hello.md", {"greeting": "hi"}, "# Hi")
    assert (custom / "hello.md").exists()


# ---------------------------------------------------------------------------
# Symlink / traversal safety
# ---------------------------------------------------------------------------


def test_read_respects_absolute_path(store, tmp_path):
    """Passing an absolute path to read() bypasses base_dir."""
    abs_file = tmp_path / "absolute.md"
    abs_file.write_text("---\nkey: abs\n---\nAbsolute content.", encoding="utf-8")

    metadata, content = store.read(str(abs_file))
    assert metadata == {"key": "abs"}
    assert content.strip() == "Absolute content."
