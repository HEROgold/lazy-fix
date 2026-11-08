"""The `check` command: report imports that are not lazy, without writing changes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from lazy_fix.discovery import iter_python_files
from lazy_fix.imports import is_eligible, iter_top_level_imports
from lazy_fix.lazy_modules import find_marker_index, is_marker_misplaced, read_lazy_modules

if TYPE_CHECKING:
    from pathlib import Path

    from lazy_fix.config import Config
    from lazy_fix.imports import ImportStatement


class ViolationKind(StrEnum):
    """Why a violation was reported."""

    MISSING = "missing"
    """An eligible import is not lazy (or not listed in `__lazy_modules__`)."""
    STALE = "stale"
    """`__lazy_modules__` lists a module that is not an eligible import in the file."""
    MISPLACED = "misplaced"
    """`__lazy_modules__` sits below an import it should govern."""


@dataclass
class Violation:
    """A single place where a file does not match what lazy-fix would write."""

    path: Path
    line: int
    module: str
    kind: ViolationKind = ViolationKind.MISSING

    @property
    def message(self) -> str:
        """A one-line description for the report."""
        if self.kind is ViolationKind.STALE:
            return f"{self.module} is listed in __lazy_modules__ but is not an eligible import"
        if self.kind is ViolationKind.MISPLACED:
            return "__lazy_modules__ must come before the imports it governs"
        return f"{self.module} should be lazy"


def _eligible_imports(module: cst.Module, path: Path, config: Config) -> list[ImportStatement]:
    return [
        stmt
        for stmt in iter_top_level_imports(module, path)
        if not stmt.is_star and not stmt.is_already_lazy and is_eligible(stmt.module, config)
    ]


def _marker_violations(
    path: Path,
    module: cst.Module,
    listed: list[str] | None,
    marker_line: int,
    eligible_modules: set[str],
) -> list[Violation]:
    """Misplaced and stale findings for a `__lazy_modules__` marker found on marker_line."""
    violations: list[Violation] = []
    if is_marker_misplaced(module):
        violations.append(Violation(path=path, line=marker_line, module="__lazy_modules__", kind=ViolationKind.MISPLACED))
    violations.extend(
        Violation(path=path, line=marker_line, module=name, kind=ViolationKind.STALE)
        for name in dict.fromkeys(listed or [])
        if name not in eligible_modules
    )
    return violations


def _legacy_violations(path: Path, wrapper: MetadataWrapper, config: Config) -> list[Violation]:
    """Drift between the file's `__lazy_modules__` marker and the eligible imports it should list."""
    module = wrapper.module
    positions = wrapper.resolve(PositionProvider)
    listed = read_lazy_modules(module)
    marker_index = find_marker_index(module)

    eligible = _eligible_imports(module, path, config)
    violations = [
        Violation(path=path, line=positions[stmt.line].start.line, module=stmt.module)
        for stmt in eligible
        if stmt.module not in (listed or [])
    ]
    if marker_index is None:
        return violations

    marker_line = positions[module.body[marker_index]].start.line
    return violations + _marker_violations(path, module, listed, marker_line, {stmt.module for stmt in eligible})


def _check_file(path: Path, config: Config, *, target_pep_810: bool) -> list[Violation]:
    if path.is_symlink() or not path.is_file():
        return []

    source = path.read_text(encoding="utf-8")
    wrapper = MetadataWrapper(cst.parse_module(source))

    if not target_pep_810:
        return _legacy_violations(path, wrapper, config)

    positions = wrapper.resolve(PositionProvider)
    return [
        Violation(path=path, line=positions[stmt.line].start.line, module=stmt.module)
        for stmt in _eligible_imports(wrapper.module, path, config)
    ]


def check(
    paths: list[Path],
    config: Config,
    *,
    target_pep_810: bool,
    project_root: Path | None = None,
) -> list[Violation]:
    """Return every place under paths where a file differs from what `fix` would write.

    On a PEP 810 target, a violation is an eligible import that isn't
    already `lazy import`/`lazy from ... import ...`. On an older target, the
    file's `__lazy_modules__` marker must list exactly the eligible imports
    and sit above them: a missing entry, a stale entry and a misplaced marker
    each count. Files matching `exclude` in config are skipped.
    """
    violations: list[Violation] = []
    for path in paths:
        for file in iter_python_files(path, exclude=config.exclude, project_root=project_root):
            violations.extend(_check_file(file, config, target_pep_810=target_pep_810))
    return violations
