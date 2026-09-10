"""The `fix` command: rewrite non-lazy imports in place, or show a diff."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import libcst as cst

from lazy_fix.codemod import rewrite_module
from lazy_fix.discovery import iter_python_files

if TYPE_CHECKING:
    from pathlib import Path

    from lazy_fix.config import Config


@dataclass
class FixResult:
    """The outcome of fixing a single file."""

    path: Path
    changed: bool
    diff: str


def _fix_file(path: Path, config: Config, *, target_pep_810: bool, dry_run: bool) -> FixResult:
    original = path.read_text(encoding="utf-8")
    module = cst.parse_module(original)
    updated = module.code_for_node(rewrite_module(module, config, target_pep_810=target_pep_810))

    if updated == original:
        return FixResult(path=path, changed=False, diff="")

    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )

    if not dry_run:
        path.write_text(updated, encoding="utf-8")

    return FixResult(path=path, changed=True, diff=diff)


def fix(
    paths: list[Path],
    config: Config,
    *,
    target_pep_810: bool,
    dry_run: bool = False,
) -> list[FixResult]:
    """Rewrite eligible imports under paths to lazy form.

    On Python 3.15+ targets this emits real `lazy import` syntax; on older
    targets it inserts/updates a __lazy_modules__ marker list instead.
    When dry_run is True, files are not written and only the diff is returned.
    """
    results: list[FixResult] = []
    for path in paths:
        results.extend(
            _fix_file(file, config, target_pep_810=target_pep_810, dry_run=dry_run) for file in iter_python_files(path)
        )
    return results
