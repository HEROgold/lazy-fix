"""LibCST codemod that rewrites eligible module-level imports to PEP 810 lazy imports.

Only module-level `import x` and `from x import y` statements are touched.
`from x import *` is left as-is. `import a, b` is split into separate
statements before being made lazy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst

from lazy_fix.imports import is_eligible, iter_top_level_imports, split_multi_name
from lazy_fix.lazy_modules import is_marker_misplaced, read_lazy_modules, remove_lazy_modules, set_lazy_modules

if TYPE_CHECKING:
    from pathlib import Path

    from lazy_fix.config import Config
    from lazy_fix.imports import ImportStatement


def _to_lazy(small_stmt: cst.Import | cst.ImportFrom) -> cst.LazyImport | cst.LazyImportFrom:
    if isinstance(small_stmt, cst.Import):
        return cst.LazyImport(names=small_stmt.names, semicolon=small_stmt.semicolon)
    return cst.LazyImportFrom(
        module=small_stmt.module,
        names=small_stmt.names,
        relative=small_stmt.relative,
        lpar=small_stmt.lpar,
        rpar=small_stmt.rpar,
        semicolon=small_stmt.semicolon,
    )


def _split_lines(module: cst.Module) -> cst.Module:
    """Split every multi-name `import a, b` into separate statements first.

    Runs as its own pass over module.body so every later step only ever
    deals with one module per statement.
    """
    new_body: list[cst.BaseStatement] = []
    for line in module.body:
        if isinstance(line, cst.SimpleStatementLine):
            new_body.extend(split_multi_name(line))
        else:
            new_body.append(line)
    return module.with_changes(body=new_body)


def _is_rewritable(stmt: ImportStatement, config: Config) -> bool:
    return not stmt.is_star and not stmt.is_already_lazy and is_eligible(stmt.module, config)


def _rewrite_legacy_marker(module: cst.Module, config: Config, path: Path | None) -> cst.Module:
    """Make the `__lazy_modules__` marker list exactly the eligible imports, instead of rewriting them.

    Missing entries are added, and stale or denied ones are removed. Entries that
    are still eligible keep their order, and new ones follow in sorted order.
    """
    eligible = sorted({stmt.module for stmt in iter_top_level_imports(module, path) if _is_rewritable(stmt, config)})
    existing = read_lazy_modules(module)
    if existing is None:
        return set_lazy_modules(module, eligible) if eligible else module
    if not eligible:
        return remove_lazy_modules(module)
    desired = _merge_marker_entries(existing, eligible)
    if desired == existing and not is_marker_misplaced(module):
        return module
    return set_lazy_modules(module, desired)


def _merge_marker_entries(existing: list[str], eligible: list[str]) -> list[str]:
    """Keep the entries that are still eligible in their order, then append the new ones sorted."""
    wanted = set(eligible)
    desired = [name for name in dict.fromkeys(existing) if name in wanted]
    return desired + [name for name in eligible if name not in desired]


def _lazify_line(line: cst.BaseStatement, eligible_ids: set[int]) -> cst.BaseStatement:
    if not isinstance(line, cst.SimpleStatementLine) or not any(id(small_stmt) in eligible_ids for small_stmt in line.body):
        return line
    return line.with_changes(
        body=[
            _to_lazy(small_stmt)
            if isinstance(small_stmt, (cst.Import, cst.ImportFrom)) and id(small_stmt) in eligible_ids
            else small_stmt
            for small_stmt in line.body
        ]
    )


def _rewrite_pep810(module: cst.Module, config: Config, path: Path | None) -> cst.Module:
    """Rewrite eligible imports directly to `lazy import` / `lazy from ... import ...`."""
    # Keyed by id(small_stmt), not the small_stmt itself: it's a dataclass
    # with structural equality, so two textually-identical imports (e.g.
    # `import os` appearing twice) would otherwise collide. A line can hold
    # more than one small_stmt (`import os; import sys`), so each is
    # rewritten independently rather than replacing the whole line.
    eligible_ids = {id(stmt.small_stmt) for stmt in iter_top_level_imports(module, path) if _is_rewritable(stmt, config)}
    if not eligible_ids:
        return module

    return module.with_changes(body=[_lazify_line(line, eligible_ids) for line in module.body])


def rewrite_module(module: cst.Module, config: Config, *, target_pep_810: bool, path: Path | None = None) -> cst.Module:
    """Rewrite eligible top-level imports to lazy form.

    On a PEP 810 target, eligible imports become `lazy import` / `lazy from
    ... import ...` statements directly. On an older target, the module is
    left untouched and its eligible module names are instead inserted into
    a `__lazy_modules__` marker list (see lazy_modules.py). path is the file
    the module came from, used to resolve relative imports.
    """
    module = _split_lines(module)
    if not target_pep_810:
        return _rewrite_legacy_marker(module, config, path)
    return _rewrite_pep810(module, config, path)
