"""Find the .py files a check/fix run should consider."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def iter_python_files(root: Path) -> list[Path]:
    """Recursively list .py files under root, skipping dot-prefixed and gitignored paths."""
    raise NotImplementedError
