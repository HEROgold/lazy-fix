"""Tests for lazy_fix.lazy_modules."""

import libcst as cst

from lazy_fix.lazy_modules import insert_or_update_lazy_modules, is_marker_misplaced, read_lazy_modules


def _module(source: str) -> cst.Module:
    return cst.parse_module(source)


def test_read_lazy_modules_absent() -> None:
    assert read_lazy_modules(_module("import os\n")) is None


def test_read_lazy_modules_present() -> None:
    source = 'import os\n__lazy_modules__ = ["os", "sys"]\n'

    assert read_lazy_modules(_module(source)) == ["os", "sys"]


def _insert(source: str, names: list[str]) -> str:
    module = _module(source)
    return module.code_for_node(insert_or_update_lazy_modules(module, names))


def test_insert_fresh_before_imports() -> None:
    assert _insert("import os\nimport sys\n\nprint(os, sys)\n", ["os"]) == (
        '__lazy_modules__ = ["os"]\nimport os\nimport sys\n\nprint(os, sys)\n'
    )


def test_insert_after_docstring() -> None:
    assert _insert('"""Doc."""\nimport os\n', ["os"]) == '"""Doc."""\n__lazy_modules__ = ["os"]\nimport os\n'


def test_insert_after_future_import() -> None:
    source = "from __future__ import annotations\nimport os\n"

    assert _insert(source, ["os"]) == 'from __future__ import annotations\n__lazy_modules__ = ["os"]\nimport os\n'


def test_insert_after_docstring_and_future_import() -> None:
    source = '"""Doc."""\n\nfrom __future__ import annotations\n\nimport os\n'

    assert _insert(source, ["os"]) == (
        '"""Doc."""\n\nfrom __future__ import annotations\n\n__lazy_modules__ = ["os"]\nimport os\n'
    )


def test_future_never_in_marker() -> None:
    module = _module("from __future__ import annotations\nimport os\n")

    result = insert_or_update_lazy_modules(module, ["__future__", "os"])

    assert read_lazy_modules(result) == ["os"]


def test_misplaced_marker_is_moved_up_and_merged() -> None:
    source = '"""Doc."""\nfrom __future__ import annotations\nimport os\nimport sys\n__lazy_modules__ = ["os"]\n'

    assert _insert(source, ["sys", "os"]) == (
        '"""Doc."""\nfrom __future__ import annotations\n__lazy_modules__ = ["os", "sys"]\nimport os\nimport sys\n'
    )


def test_is_marker_misplaced() -> None:
    assert is_marker_misplaced(_module('import os\n__lazy_modules__ = ["os"]\n'))
    assert not is_marker_misplaced(_module('__lazy_modules__ = ["os"]\nimport os\n'))
    assert not is_marker_misplaced(_module("import os\n"))


def test_insert_fresh_with_no_imports() -> None:
    module = _module("print('hi')\n")

    result = insert_or_update_lazy_modules(module, ["os"])

    assert module.code_for_node(result) == "__lazy_modules__ = [\"os\"]\nprint('hi')\n"


def test_update_existing_merges_new_names() -> None:
    module = _module('__lazy_modules__ = ["os"]\nimport os\n')

    result = insert_or_update_lazy_modules(module, ["sys"])

    assert read_lazy_modules(result) == ["os", "sys"]


def test_update_existing_dedupes() -> None:
    module = _module('__lazy_modules__ = ["os"]\nimport os\n')

    result = insert_or_update_lazy_modules(module, ["os"])

    assert read_lazy_modules(result) == ["os"]


def test_update_preserves_existing_order() -> None:
    module = _module('__lazy_modules__ = ["sys", "os"]\nimport os\n')

    result = insert_or_update_lazy_modules(module, ["json"])

    assert read_lazy_modules(result) == ["sys", "os", "json"]
