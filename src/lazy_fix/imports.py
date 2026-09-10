"""Shared analysis of top-level import statements.

check.py and codemod.py both need to answer "is this import eligible to be
made lazy, and what module does it name?" - keeping that logic in one place
is what keeps check and fix from ever disagreeing about what counts as a
violation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from lazy_fix.config import Config


@dataclass(frozen=True)
class ImportStatement:
    """One module named by a top-level import statement."""

    line: cst.SimpleStatementLine
    small_stmt: cst.Import | cst.ImportFrom | cst.LazyImport | cst.LazyImportFrom
    alias: cst.ImportAlias | None  # set only for one entry of a multi-name `import a, b`
    module: str
    is_star: bool
    is_already_lazy: bool


def _dotted_name(node: cst.Attribute | cst.Name) -> str:
    if isinstance(node, cst.Name):
        return node.value
    return f"{_dotted_name(node.value)}.{node.attr.value}"


def _from_import_statements(
    line: cst.SimpleStatementLine,
    small_stmt: cst.ImportFrom | cst.LazyImportFrom,
) -> list[ImportStatement]:
    # `from . import x` / `from .. import x` have no absolute module name;
    # such statements can never match a configured module name, so they're
    # simply never eligible.
    module = _dotted_name(small_stmt.module) if small_stmt.module is not None else ""
    return [
        ImportStatement(
            line=line,
            small_stmt=small_stmt,
            alias=None,
            module=module,
            is_star=isinstance(small_stmt.names, cst.ImportStar),
            is_already_lazy=isinstance(small_stmt, cst.LazyImportFrom),
        )
    ]


def _import_statements(
    line: cst.SimpleStatementLine,
    small_stmt: cst.Import | cst.LazyImport,
) -> list[ImportStatement]:
    is_already_lazy = isinstance(small_stmt, cst.LazyImport)
    return [
        ImportStatement(
            line=line,
            small_stmt=small_stmt,
            alias=alias,
            module=_dotted_name(alias.name),
            is_star=False,
            is_already_lazy=is_already_lazy,
        )
        for alias in small_stmt.names
    ]


def iter_top_level_imports(module: cst.Module) -> list[ImportStatement]:
    """List every import in module, one entry per named module.

    Only walks module.body directly - never recurses into FunctionDef, If,
    Try, etc. - which is what keeps this module-level-only.
    """
    statements: list[ImportStatement] = []
    for line in module.body:
        if not isinstance(line, cst.SimpleStatementLine):
            continue
        for small_stmt in line.body:
            if isinstance(small_stmt, (cst.Import, cst.LazyImport)):
                statements.extend(_import_statements(line, small_stmt))
            elif isinstance(small_stmt, (cst.ImportFrom, cst.LazyImportFrom)):
                statements.extend(_from_import_statements(line, small_stmt))
    return statements


def is_eligible(module_name: str, config: Config) -> bool:
    """Whether module_name should be made lazy: allow-listed and not denied."""
    if module_name in config.deny:
        return False
    return module_name in config.allow


def split_multi_name(line: cst.SimpleStatementLine) -> list[cst.SimpleStatementLine]:
    """`import a, b` -> two separate Import statements.

    Anything that isn't a multi-name plain Import/LazyImport (an ImportFrom,
    or an Import/LazyImport with only one name) is returned unchanged as a
    single-element list.
    """
    if len(line.body) != 1:
        return [line]
    (small_stmt,) = line.body
    if not isinstance(small_stmt, (cst.Import, cst.LazyImport)) or len(small_stmt.names) <= 1:
        return [line]

    return [
        line.with_changes(body=[small_stmt.with_changes(names=[alias.with_changes(comma=cst.MaybeSentinel.DEFAULT)])])
        for alias in small_stmt.names
    ]
