"""
Storage engine — python-frontmatter CRUD for .md file database.

Mirrors the Hermes directory layout:
    {category}/{YYYY-MM-DD}_{type_name}/{date}_{type}.md

Multi-tenant (HEALTH-MULTI-TENANT-ROUTING):
    Default base_dir = {DATA_DIR}/users/<telegram_id>/
    via request-scoped tenant context (app.tenant).

Atomic writes via tempfile + os.replace(), file locking via fcntl.flock.
"""

import fcntl
import os
import shutil
import tempfile
from pathlib import Path

import frontmatter

from app.config import get_settings


class MDStorage:
    """File-based storage engine for .md files with YAML frontmatter.

    All paths are relative to base_dir unless absolute.  Each .md file
    carries a YAML frontmatter block (parsed by python-frontmatter)
    followed by markdown body content.

    Usage:
        store = MDStorage()               # current tenant (data/users/<id>/)
        store = MDStorage.for_user(80101636)
        md, body = store.read("карточка.md")
        store.write("profile.md", {"name": "Sasha"}, "# Profile")
        results = store.list_dir("visits")
        store.create_bundle("visits", "2026-07-01", "терапевт", "/tmp/scan.jpg")
    """

    def __init__(
        self,
        base_dir: str | Path | None = None,
        *,
        user_id: int | str | None = None,
        shared: bool = False,
    ) -> None:
        """Init storage root.

        Args:
            base_dir: Explicit root (tests / migration). Highest priority.
            user_id:  Scope to ``data/users/<user_id>/``.
            shared:   If True and no base_dir/user_id, use raw DATA_DIR
                      (legacy global — avoid in HTTP handlers).
        """
        if base_dir is not None:
            self.base_dir = Path(base_dir)
            self.user_id = user_id
            return

        if user_id is not None:
            from app.tenant import ensure_user_data_dir

            self.user_id = int(user_id)
            self.base_dir = ensure_user_data_dir(self.user_id)
            return

        if shared:
            self.user_id = None
            self.base_dir = Path(get_settings().DATA_DIR)
            return

        # Request-scoped tenant from auth dependency
        from app.tenant import (
            ensure_user_data_dir,
            peek_current_user_id,
            default_tenant_id,
        )

        uid = peek_current_user_id()
        if uid is None:
            # Cron / CLI without auth: default tenant (Sasha)
            uid = default_tenant_id()
        self.user_id = int(uid)
        self.base_dir = ensure_user_data_dir(self.user_id)

    @classmethod
    def for_user(cls, user_id: int | str) -> "MDStorage":
        """Explicit tenant storage (agents: sasha-health / dasha-health)."""
        return cls(user_id=user_id)

    @classmethod
    def shared_root(cls) -> "MDStorage":
        """Raw DATA_DIR (only for migration / healthcheck / admin shared files)."""
        return cls(shared=True)

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------

    def read(self, path: str | Path) -> tuple[dict, str]:
        """Read a .md file and return (metadata dict, content string).

        Uses python-frontmatter to parse the YAML block between the
        opening ``---`` and closing ``---`` markers.  Everything after
        the second ``---`` is treated as the markdown body.

        Args:
            path: Relative path (from base_dir) or absolute path to the .md file.

        Returns:
            A 2-tuple of (metadata: dict, content: str).

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        filepath = self._resolve(path)
        with open(filepath, encoding="utf-8") as fh:
            post = frontmatter.load(fh)
        return dict(post.metadata), post.content or ""

    # ------------------------------------------------------------------
    # write  (atomic + locked)
    # ------------------------------------------------------------------

    def write(self, path: str | Path, metadata: dict, content: str = "") -> None:
        """Write (or overwrite) a .md file atomically.

        The operation uses the classic atomic-write pattern:

        1. Serialise metadata + content via ``frontmatter.dumps``.
        2. Write to a hidden temporary file in the **same directory**
           as the target (so ``os.replace`` is a same-filesystem rename).
        3. ``flock(LOCK_EX)`` the temp file during write for concurrent safety.
        4. ``os.fsync`` to flush OS buffers before the atomic rename.
        5. ``os.replace`` the temp file over the real path.

        Parent directories are created automatically if they do not exist.

        Args:
            path:    Relative or absolute path for the .md file.
            metadata: Key-value pairs to serialise as YAML frontmatter.
            content:  Markdown body text (empty string by default).
        """
        filepath = self._resolve(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        post = frontmatter.Post(content, **metadata)
        serialized = frontmatter.dumps(post)

        dir_path = filepath.parent
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

    # ------------------------------------------------------------------
    # list_dir
    # ------------------------------------------------------------------

    def list_dir(self, dir_path: str | Path) -> list[dict]:
        """List all .md files in a directory, returning their metadata.

        Only files matching ``*.md`` are considered.  Each entry in the
        returned list is the **metadata dict** from that file's frontmatter
        plus an extra ``_path`` key holding the relative path.

        Subdirectories are **not** recursed — this is a flat listing.

        Args:
            dir_path: Directory to scan, relative to base_dir or absolute.

        Returns:
            List of metadata dicts (one per .md file).  Empty list if the
            directory does not exist or contains no .md files.
        """
        directory = self._resolve(dir_path)
        if not directory.is_dir():
            return []

        results: list[dict] = []
        for md_file in sorted(directory.glob("*.md")):
            metadata, _ = self.read(str(md_file.relative_to(self.base_dir)))
            metadata["_path"] = str(md_file.relative_to(self.base_dir))
            results.append(metadata)
        return results

    # ------------------------------------------------------------------
    # create_bundle
    # ------------------------------------------------------------------

    def create_bundle(
        self,
        category: str,
        date_str: str,
        type_name: str,
        original_path: str | None = None,
    ) -> str:
        """Create a Hermes-style bundle directory.

        Layout::

            {base_dir}/{category}/{date_str}_{type_name}/
                {date_str}_{type_name}.md
                {date_str}_{type_name}_original{ext}   (if original_path given)

        The directory and .md file are created but the file is left empty.
        The caller is expected to ``write()`` content into the .md file
        afterwards.

        If *original_path* points to an existing file it is **copied**
        (not moved) into the bundle with the ``_original`` suffix,
        preserving its extension.

        Args:
            category:       Top-level category name (e.g. "visits", "analyses").
            date_str:       ISO-8601 date string (YYYY-MM-DD).
            type_name:      Human-readable type slug (e.g. "терапевт").
            original_path:  Optional path to an original attachment file.

        Returns:
            Relative path (from base_dir) of the created .md file.
        """
        bundle_dir = self.base_dir / category / f"{date_str}_{type_name}"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        md_filename = f"{date_str}_{type_name}.md"
        md_filepath = bundle_dir / md_filename

        # Touch the .md file so it exists (empty frontmatter + empty body).
        if not md_filepath.exists():
            md_filepath.write_text("---\n---\n", encoding="utf-8")

        # Copy original attachment if provided.
        if original_path:
            orig = Path(original_path)
            if orig.exists() and orig.is_file():
                ext = orig.suffix or ".jpg"
                dest = bundle_dir / f"{date_str}_{type_name}_original{ext}"
                shutil.copy2(orig, dest)

        return str(md_filepath.relative_to(self.base_dir))

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str | Path) -> Path:
        """Resolve a path: if absolute use as-is, else prepend base_dir."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_dir / p
