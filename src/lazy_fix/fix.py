"""The `fix` command: rewrite non-lazy imports in place, or show a diff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from lazy_fix.config import Config


@dataclass
class FixResult:
    """The outcome of fixing a single file."""

    path: Path
    changed: bool
    diff: str


def fix(paths: list[Path], config: Config, *, dry_run: bool = False) -> list[FixResult]:
    """Rewrite eligible imports under paths to lazy form.

    On Python 3.15+ targets this emits real `lazy import` syntax; on older
    targets it inserts/updates a __lazy_modules__ marker list instead.
    When dry_run is True, files are not written and only the diff is returned.
    """
    raise NotImplementedError
