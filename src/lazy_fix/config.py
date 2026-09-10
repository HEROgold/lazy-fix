"""Load lazy-fix configuration from lazy-fix.toml or pyproject.toml.

lazy-fix.toml takes precedence over a [tool.lazy-fix] section in
pyproject.toml when both are present, matching ruff's convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Config:
    """Resolved lazy-fix configuration for a project."""

    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)


def load_config(root: Path) -> Config:
    """Resolve configuration for the project rooted at root."""
    raise NotImplementedError


def target_supports_pep_810(root: Path) -> bool:
    """Whether requires-python in pyproject.toml allows Python 3.15+."""
    raise NotImplementedError
