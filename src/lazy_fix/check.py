"""The `check` command: report imports that are not lazy, without writing changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from lazy_fix.discovery import iter_python_files
from lazy_fix.imports import is_eligible, iter_top_level_imports
from lazy_fix.lazy_modules import read_lazy_modules

if TYPE_CHECKING:
    from pathlib import Path

    from lazy_fix.config import Config


@dataclass
class Violation:
    """A single import that should be lazy but is not."""

    path: Path
    line: int
    module: str


def _check_file(path: Path, config: Config, *, target_pep_810: bool) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    wrapper = MetadataWrapper(cst.parse_module(source))
    positions = wrapper.resolve(PositionProvider)
    module = wrapper.module

    lazy_modules = set(read_lazy_modules(module) or [])

    violations = []
    for stmt in iter_top_level_imports(module):
        if stmt.is_star or not is_eligible(stmt.module, config):
            continue
        already_handled = stmt.is_already_lazy if target_pep_810 else stmt.module in lazy_modules
        if already_handled:
            continue
        line = positions[stmt.line].start.line
        violations.append(Violation(path=path, line=line, module=stmt.module))
    return violations


def check(paths: list[Path], config: Config, *, target_pep_810: bool) -> list[Violation]:
    """Return every non-lazy import under paths that config says should be lazy.

    On a PEP 810 target, a violation is an eligible import that isn't
    already `lazy import`/`lazy from ... import ...`. On an older target,
    it's an eligible import whose module isn't already listed in
    __lazy_modules__.
    """
    violations: list[Violation] = []
    for path in paths:
        for file in iter_python_files(path):
            violations.extend(_check_file(file, config, target_pep_810=target_pep_810))
    return violations
