"""Pre-3.15 fallback: manage the `__lazy_modules__` marker list.

PEP 810 defines `__lazy_modules__` as a forward-compatibility escape hatch:
on interpreters older than 3.15 it is inert (imports still run eagerly), but
it declares intent so the file is ready to adopt real `lazy import` syntax
once the project's requires-python allows 3.15+.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import libcst as cst


def read_lazy_modules(module: cst.Module) -> list[str]:
    """Return the module names currently listed in __lazy_modules__, if present."""
    raise NotImplementedError


def insert_or_update_lazy_modules(module: cst.Module, names: list[str]) -> cst.Module:
    """Insert a __lazy_modules__ list under the imports, or update an existing one."""
    raise NotImplementedError
