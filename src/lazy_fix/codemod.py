"""LibCST codemod that rewrites eligible module-level imports to PEP 810 lazy imports.

Only module-level `import x` and `from x import y` statements are touched.
`from x import *` is left as-is. `import a, b` is split into separate
statements before being made lazy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst

from lazy_fix.imports import is_eligible, iter_top_level_imports, split_multi_name
from lazy_fix.lazy_modules import insert_or_update_lazy_modules

if TYPE_CHECKING:
    from lazy_fix.config import Config


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


def rewrite_module(module: cst.Module, config: Config, *, target_pep_810: bool) -> cst.Module:
    """Rewrite eligible top-level imports to lazy form.

    On a PEP 810 target, eligible imports become `lazy import` / `lazy from
    ... import ...` statements directly. On an older target, the module is
    left untouched and its eligible module names are instead inserted into
    a `__lazy_modules__` marker list (see lazy_modules.py).
    """
    module = _split_lines(module)

    if not target_pep_810:
        eligible = sorted(
            {
                stmt.module
                for stmt in iter_top_level_imports(module)
                if not stmt.is_star and not stmt.is_already_lazy and is_eligible(stmt.module, config)
            }
        )
        if not eligible:
            return module
        return insert_or_update_lazy_modules(module, eligible)

    # Keyed by id(small_stmt), not the small_stmt itself: it's a dataclass
    # with structural equality, so two textually-identical imports (e.g.
    # `import os` appearing twice) would otherwise collide. A line can hold
    # more than one small_stmt (`import os; import sys`), so each is
    # rewritten independently rather than replacing the whole line.
    eligible_ids = {
        id(stmt.small_stmt)
        for stmt in iter_top_level_imports(module)
        if not stmt.is_star and not stmt.is_already_lazy and is_eligible(stmt.module, config)
    }
    if not eligible_ids:
        return module

    new_body = []
    for line in module.body:
        if isinstance(line, cst.SimpleStatementLine) and any(id(small_stmt) in eligible_ids for small_stmt in line.body):
            new_small_stmts = [
                _to_lazy(small_stmt) if id(small_stmt) in eligible_ids else small_stmt for small_stmt in line.body
            ]
            new_body.append(line.with_changes(body=new_small_stmts))
        else:
            new_body.append(line)
    return module.with_changes(body=new_body)
