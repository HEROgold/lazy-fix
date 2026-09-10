"""Tests for lazy_fix.lazy_modules."""

import libcst as cst

from lazy_fix.lazy_modules import insert_or_update_lazy_modules, read_lazy_modules


def _module(source: str) -> cst.Module:
    return cst.parse_module(source)


def test_read_lazy_modules_absent() -> None:
    assert read_lazy_modules(_module("import os\n")) is None


def test_read_lazy_modules_present() -> None:
    source = 'import os\n__lazy_modules__ = ["os", "sys"]\n'

    assert read_lazy_modules(_module(source)) == ["os", "sys"]


def test_insert_fresh_after_imports() -> None:
    module = _module("import os\nimport sys\n\nprint(os, sys)\n")

    result = insert_or_update_lazy_modules(module, ["os"])

    assert module.code_for_node(result) == ('import os\nimport sys\n__lazy_modules__ = ["os"]\n\nprint(os, sys)\n')


def test_insert_fresh_with_no_imports() -> None:
    module = _module("print('hi')\n")

    result = insert_or_update_lazy_modules(module, ["os"])

    assert module.code_for_node(result) == "__lazy_modules__ = [\"os\"]\nprint('hi')\n"


def test_update_existing_merges_new_names() -> None:
    module = _module('import os\n__lazy_modules__ = ["os"]\n')

    result = insert_or_update_lazy_modules(module, ["sys"])

    assert read_lazy_modules(result) == ["os", "sys"]


def test_update_existing_dedupes() -> None:
    module = _module('import os\n__lazy_modules__ = ["os"]\n')

    result = insert_or_update_lazy_modules(module, ["os"])

    assert read_lazy_modules(result) == ["os"]


def test_update_preserves_existing_order() -> None:
    module = _module('import os\n__lazy_modules__ = ["sys", "os"]\n')

    result = insert_or_update_lazy_modules(module, ["json"])

    assert read_lazy_modules(result) == ["sys", "os", "json"]
