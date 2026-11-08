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
    from pathlib import Path

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


def _dotted_name(node: cst.BaseExpression) -> str:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return f"{_dotted_name(node.value)}.{node.attr.value}"
    msg = f"unexpected node in dotted name: {type(node).__name__}"
    raise TypeError(msg)


def package_of(path: Path) -> str | None:
    """Dotted name of the package that holds the file at path, or None for a loose script.

    Follows `__init__.py` files upward from the file's directory, which works for
    src and flat layouts alike. For an `__init__.py` this is the package itself.
    """
    parts: list[str] = []
    directory = path.resolve().parent
    while (directory / "__init__.py").is_file():
        parts.append(directory.name)
        directory = directory.parent
    return ".".join(reversed(parts)) or None


def _is_submodule(directory: Path, name: str) -> bool:
    return (directory / f"{name}.py").is_file() or (directory / name / "__init__.py").is_file()


def _relative_base(small_stmt: cst.ImportFrom | cst.LazyImportFrom, path: Path) -> list[str] | None:
    """Package parts a relative import starts from, or None when it climbs past the top package."""
    package = package_of(path)
    parts = package.split(".") if package else []
    up = len(small_stmt.relative) - 1
    if not parts or up >= len(parts):
        return None
    return parts[: len(parts) - up]


def _single_imported_name(small_stmt: cst.ImportFrom | cst.LazyImportFrom) -> str | None:
    names = small_stmt.names
    if isinstance(names, cst.ImportStar) or len(names) != 1 or not isinstance(names[0].name, cst.Name):
        return None
    return names[0].name.value


def _resolve_relative(small_stmt: cst.ImportFrom | cst.LazyImportFrom, path: Path | None) -> str:
    """Fully qualified module a relative `from` import names, or "" when it can't be worked out."""
    if path is None:
        return ""
    base = _relative_base(small_stmt, path)
    if base is None:
        return ""
    if small_stmt.module is not None:
        return ".".join([*base, _dotted_name(small_stmt.module)])
    directory = path.resolve().parent
    for _ in range(len(small_stmt.relative) - 1):
        directory = directory.parent
    name = _single_imported_name(small_stmt)
    return ".".join([*base, name]) if name is not None and _is_submodule(directory, name) else ".".join(base)


def _from_import_statements(
    line: cst.SimpleStatementLine,
    small_stmt: cst.ImportFrom | cst.LazyImportFrom,
    path: Path | None,
) -> list[ImportStatement]:
    # PEP 810 matches __lazy_modules__ against the fully qualified module name,
    # so a relative import is recorded under the name it resolves to. One whose
    # package can't be worked out gets "" and is never eligible.
    if small_stmt.relative:
        module = _resolve_relative(small_stmt, path)
    else:
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


def iter_top_level_imports(module: cst.Module, path: Path | None = None) -> list[ImportStatement]:
    """List every import in module, one entry per named module.

    path is the file the module came from; it is needed to resolve relative imports.

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
                statements.extend(_from_import_statements(line, small_stmt, path))
    return statements


def _match_depth(module_name: str, entries: list[str]) -> int:
    """Count the dotted parts of the most specific entry covering module_name, or 0 for none.

    An entry covers itself and every module below it: `sqlalchemy` covers
    `sqlalchemy` and `sqlalchemy.orm`, but not `sqlalchemyx`.
    """
    depth = 0
    for entry in entries:
        if module_name == entry or module_name.startswith(f"{entry}."):
            depth = max(depth, entry.count(".") + 1)
    return depth


def is_eligible(module_name: str, config: Config) -> bool:
    """Whether module_name should be made lazy.

    Every module is eligible unless `deny` covers it. When both `allow` and
    `deny` cover it, the more specific entry wins, so `deny = ["sqlalchemy"]`
    with `allow = ["sqlalchemy.orm"]` makes `sqlalchemy.orm` lazy and
    `sqlalchemy.pool` not. `__future__` is never eligible, because a lazy
    future import is invalid, and neither is a module that could not be named.
    """
    if not module_name or module_name == "__future__":
        return False
    denied = _match_depth(module_name, config.deny)
    return not denied or _match_depth(module_name, config.allow) > denied


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
