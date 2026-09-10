"""Load lazy-fix configuration from lazy-fix.toml or pyproject.toml.

lazy-fix.toml takes precedence over a [tool.lazy-fix] section in
pyproject.toml when both are present, matching ruff's convention.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from packaging.specifiers import SpecifierSet

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Config:
    """Resolved lazy-fix configuration for a project."""

    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)


def load_config(root: Path) -> Config:
    """Resolve configuration for the project rooted at root."""
    standalone = root / "lazy-fix.toml"
    if standalone.is_file():
        data = tomllib.loads(standalone.read_text(encoding="utf-8"))
        return Config(allow=data.get("allow", []), deny=data.get("deny", []))

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        tool_config = data.get("tool", {}).get("lazy-fix", {})
        return Config(allow=tool_config.get("allow", []), deny=tool_config.get("deny", []))

    return Config()


def target_supports_pep_810(root: Path) -> bool:
    """Whether requires-python in pyproject.toml allows Python 3.15+."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    requires_python = data.get("project", {}).get("requires-python")
    if not requires_python:
        return False

    specifier = SpecifierSet(requires_python)
    # requires-python allows 3.15+ only if 3.15 itself is allowed and nothing
    # just below it is - e.g. ">=3.11,<3.14" must not count even though it
    # never contains 3.14 outright.
    return specifier.contains("3.15", prereleases=True) and not specifier.contains("3.14.99", prereleases=True)
