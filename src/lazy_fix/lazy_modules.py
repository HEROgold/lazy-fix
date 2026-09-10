"""Pre-3.15 fallback: manage the `__lazy_modules__` marker list.

PEP 810 defines `__lazy_modules__` as a forward-compatibility escape hatch:
on interpreters older than 3.15 it is inert (imports still run eagerly), but
it declares intent so the file is ready to adopt real `lazy import` syntax
once the project's requires-python allows 3.15+.
"""

from __future__ import annotations

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
    return [element.value.evaluated_value for element in value.elements if isinstance(element.value, cst.SimpleString)]


def read_lazy_modules(module: cst.Module) -> list[str] | None:
    """Return the module names currently listed in __lazy_modules__, or None if absent."""
    index = _find_marker_index(module)
    if index is None:
        return None
    (assign,) = module.body[index].body
    return _string_values(assign.value)


def _last_import_index(module: cst.Module) -> int:
    last = -1
    for index, line in enumerate(module.body):
        if not isinstance(line, cst.SimpleStatementLine):
            continue
        if any(isinstance(s, (cst.Import, cst.ImportFrom, cst.LazyImport, cst.LazyImportFrom)) for s in line.body):
            last = index
    return last


def _build_assignment(names: list[str]) -> cst.SimpleStatementLine:
    elements = [cst.Element(value=cst.SimpleString(f'"{name}"')) for name in names]
    return cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(_MARKER))],
                value=cst.List(elements=elements),
            )
        ]
    )


def insert_or_update_lazy_modules(module: cst.Module, names: list[str]) -> cst.Module:
    """Insert a __lazy_modules__ list under the imports, or update an existing one."""
    existing_index = _find_marker_index(module)
    if existing_index is not None:
        existing = read_lazy_modules(module) or []
        merged = existing + [name for name in names if name not in existing]
        new_line = _build_assignment(merged)
        new_body = list(module.body)
        new_body[existing_index] = new_line
        return module.with_changes(body=new_body)

    insert_at = _last_import_index(module) + 1
    new_body = [*module.body[:insert_at], _build_assignment(names), *module.body[insert_at:]]
    return module.with_changes(body=new_body)
