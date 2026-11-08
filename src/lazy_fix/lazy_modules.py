"""Pre-3.15 fallback: manage the `__lazy_modules__` marker list.

PEP 810 defines `__lazy_modules__` as a forward-compatibility escape hatch:
on interpreters older than 3.15 it is inert (imports still run eagerly), but
it declares intent so the file is ready to adopt real `lazy import` syntax
once the project's requires-python allows 3.15+.
"""

from __future__ import annotations

from typing import cast

import libcst as cst

_MARKER = "__lazy_modules__"


def _find_marker_index(module: cst.Module) -> int | None:
    for index, line in enumerate(module.body):
        if not isinstance(line, cst.SimpleStatementLine) or len(line.body) != 1:
            continue
        (small_stmt,) = line.body
        if (
            isinstance(small_stmt, cst.Assign)
            and len(small_stmt.targets) == 1
            and isinstance(small_stmt.targets[0].target, cst.Name)
            and small_stmt.targets[0].target.value == _MARKER
        ):
            return index
    return None


def _string_values(value: cst.BaseExpression) -> list[str]:
    if not isinstance(value, (cst.List, cst.Tuple)):
        return []
    values = []
    for element in value.elements:
        if not isinstance(element.value, cst.SimpleString):
            continue
        evaluated = element.value.evaluated_value
        if isinstance(evaluated, str):
            values.append(evaluated)
    return values


def read_lazy_modules(module: cst.Module) -> list[str] | None:
    """Return the module names currently listed in __lazy_modules__, or None if absent."""
    index = _find_marker_index(module)
    if index is None:
        return None
    line = cast("cst.SimpleStatementLine", module.body[index])
    (assign,) = line.body
    return _string_values(cast("cst.Assign", assign).value)


_IMPORT_TYPES = (cst.Import, cst.ImportFrom, cst.LazyImport, cst.LazyImportFrom)


def _is_import_line(line: cst.BaseStatement) -> bool:
    return isinstance(line, cst.SimpleStatementLine) and any(isinstance(s, _IMPORT_TYPES) for s in line.body)


def _is_future_import(line: cst.BaseStatement) -> bool:
    if not isinstance(line, cst.SimpleStatementLine):
        return False
    return any(
        isinstance(s, cst.ImportFrom) and isinstance(s.module, cst.Name) and s.module.value == "__future__" for s in line.body
    )


def _is_docstring(line: cst.BaseStatement) -> bool:
    if not isinstance(line, cst.SimpleStatementLine) or len(line.body) != 1:
        return False
    expr = line.body[0]
    return isinstance(expr, cst.Expr) and isinstance(expr.value, (cst.SimpleString, cst.ConcatenatedString))


def _first_governed_import_index(module: cst.Module) -> int | None:
    """Index of the first import that is not a `from __future__` import."""
    for index, line in enumerate(module.body):
        if _is_import_line(line) and not _is_future_import(line):
            return index
    return None


def _header_end_index(module: cst.Module) -> int:
    """Index just past the module docstring and any `from __future__` imports."""
    index = 0
    if module.body and _is_docstring(module.body[0]):
        index = 1
    while index < len(module.body) and _is_future_import(module.body[index]):
        index += 1
    return index


def is_marker_misplaced(module: cst.Module) -> bool:
    """Return True if __lazy_modules__ sits below an import it should govern."""
    marker = _find_marker_index(module)
    if marker is None:
        return False
    first = _first_governed_import_index(module)
    return first is not None and first < marker


def _marker_list(names: list[str]) -> cst.List:
    return cst.List(elements=[cst.Element(value=cst.SimpleString(f'"{name}"')) for name in names])


def _build_assignment(names: list[str]) -> cst.SimpleStatementLine:
    return cst.SimpleStatementLine(
        body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name(_MARKER))], value=_marker_list(names))]
    )


def _with_names(line: cst.SimpleStatementLine, names: list[str]) -> cst.SimpleStatementLine:
    """Replace the marker's list, keeping its blank lines, comments and trailing whitespace."""
    (assign,) = line.body
    return line.with_changes(body=[cast("cst.Assign", assign).with_changes(value=_marker_list(names))])


def insert_or_update_lazy_modules(module: cst.Module, names: list[str]) -> cst.Module:
    """Place __lazy_modules__ before the first non-`__future__` import, merging in names.

    An existing marker is updated in place when it is already above every
    governed import, and moved up otherwise.
    """
    names = [name for name in names if name != "__future__"]
    existing_index = _find_marker_index(module)
    if existing_index is not None:
        existing = read_lazy_modules(module) or []
        names = existing + [name for name in names if name not in existing]
        if not is_marker_misplaced(module):
            new_body = list(module.body)
            new_body[existing_index] = _with_names(cast("cst.SimpleStatementLine", module.body[existing_index]), names)
            return module.with_changes(body=new_body)
        body = [line for index, line in enumerate(module.body) if index != existing_index]
        module = module.with_changes(body=body)

    insert_at = _first_governed_import_index(module)
    if insert_at is None:
        insert_at = _header_end_index(module)
    new_line = _build_assignment(names)
    body = list(module.body)
    if insert_at < len(body):
        target = body[insert_at]
        leading = list(getattr(target, "leading_lines", ()))
        blanks = 0
        while blanks < len(leading) and leading[blanks].comment is None:
            blanks += 1
        if blanks:
            new_line = new_line.with_changes(leading_lines=leading[:blanks])
            body[insert_at] = target.with_changes(leading_lines=leading[blanks:])
    return module.with_changes(body=[*body[:insert_at], new_line, *body[insert_at:]])
