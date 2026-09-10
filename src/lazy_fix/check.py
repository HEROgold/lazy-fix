"""The `check` command: report imports that are not lazy, without writing changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from lazy_fix.config import Config


@dataclass
class Violation:
    """A single import that should be lazy but is not."""

    path: Path
    line: int
    module: str


def check(paths: list[Path], config: Config) -> list[Violation]:
    """Return every non-lazy import under paths that config says should be lazy."""
    raise NotImplementedError
