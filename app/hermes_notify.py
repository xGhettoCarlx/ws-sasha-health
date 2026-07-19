"""Utility to notify Hermes by writing notification files to inboxfromhermes/.

Exports:
    notify_hermes(action, details) — writes a YAML-frontmatter .md file
    using an atomic write pattern (tempfile → fsync → os.replace).
"""

import datetime
import fcntl
import os
import tempfile
from pathlib import Path

# Absolute path to the Hermes inbox directory.
INBOX_DIR = Path("/Users/sashak/WorkStation/inboxfromhermes")
"""Target directory for notification files. Overrideable in tests via monkeypatch."""


# ---------------------------------------------------------------------------
# Minimal YAML serializer (stdlib only — no pyyaml dependency)
# ---------------------------------------------------------------------------


def _yaml_value(value, indent: int = 0) -> str:
    """Serialize a single Python value as a YAML inline value."""
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return " {}"
        lines: list[str] = []
        for k, v in value.items():
            lines.append(f"{prefix}{k}:{_yaml_value(v, indent + 2)}")
        return "\n" + "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return " []"
        lines = []
        for item in value:
            lines.append(f"{prefix}-{_yaml_value(item, indent + 2).lstrip()}")
        return "\n" + "\n".join(lines)
    if isinstance(value, bool):
        return f" {str(value).lower()}"
    if isinstance(value, int | float):
        return f" {value}"
    # string (and everything else) — quote if it contains special chars
    sv = str(value)
    _yaml_special = (
        ":",
        "#",
        "{",
        "}",
        "[",
        "]",
        ",",
        "&",
        "*",
        "?",
        "|",
        "-",
        "<",
        ">",
        "=",
        "!",
        "%",
        "@",
        "`",
    )
    if any(c in sv for c in _yaml_special):
        return f" '{sv}'"
    return f" {sv}"


def _yaml_dumps(data: dict) -> str:
    """Serialize a dict as a YAML mapping (no leading ``---``)."""
    return _yaml_value(data, indent=0).lstrip("\n")


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def notify_hermes(action: str, details: dict) -> None:
    """Write a notification file to the Hermes inbox using an atomic write.

    The file is written to ``INBOX_DIR / hermes-sync-{timestamp}.md`` with
    YAML frontmatter containing ``date``, ``action``, ``endpoint``,
    ``details``, and ``source``.

    The write is atomic:
        1. Write to a hidden temporary file in the **same directory**.
        2. ``fcntl.flock(LOCK_EX)`` for concurrent safety.
        3. ``os.fsync`` to flush OS buffers.
        4. ``os.replace`` the temp file over the final path.

    Args:
        action:  HTTP-like verb, e.g. ``"POST"``, ``"PUT"``, ``"DELETE"``.
        details: Payload dict. Must contain an ``"endpoint"`` key.

    Raises:
        KeyError: If ``details`` is missing the ``"endpoint"`` key.
    """
    endpoint = details["endpoint"]  # will raise KeyError if missing

    now = datetime.datetime.now(datetime.timezone.utc)
    # Filesystem-safe ISO timestamp for the filename
    ts_filename = now.strftime("%Y-%m-%dT%H-%M-%S-%f")
    # Human-readable ISO timestamp for the frontmatter
    ts_frontmatter = now.isoformat()

    filepath = INBOX_DIR / f"hermes-sync-{ts_filename}.md"
    dir_path = filepath.parent
    dir_path.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "date": ts_frontmatter,
        "action": action,
        "endpoint": endpoint,
        "details": details,
        "source": "Project5 Mini App",
    }
    serialized = "---\n" + _yaml_dumps(frontmatter) + "\n---\n"

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=dir_path,
        prefix=".tmp." + filepath.name + ".",
        suffix=".md",
        delete=False,
    ) as tmp:
        fcntl.flock(tmp.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write(serialized)
            tmp.flush()
            os.fsync(tmp.fileno())
        finally:
            fcntl.flock(tmp.fileno(), fcntl.LOCK_UN)

    os.replace(tmp.name, filepath)
