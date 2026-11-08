"""Find the project root that lazy-fix reads its configuration from."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_CONFIG_FILENAMES = ("lazy-fix.toml", "pyproject.toml")


def find_project_root(start: Path) -> Path:
    """Return the project root for a run started in start.

    Walks up from start through its parents. The first directory holding a
    `lazy-fix.toml` or a `pyproject.toml` is the root. With no such file, the
    git root is used, and with no git repository either, start itself.
    """
    start = start.resolve()
    for directory in (start, *start.parents):
        if any((directory / name).is_file() for name in _CONFIG_FILENAMES):
            return directory
    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            return directory
    return start
