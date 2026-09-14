"""Tests for lazy_fix.imports."""

import libcst as cst

from lazy_fix.config import Config
from lazy_fix.imports import is_eligible, iter_top_level_imports, split_multi_name


def _module(source: str) -> cst.Module:
    return cst.parse_module(source)


def test_plain_import_single_name() -> None:
    stmts = iter_top_level_imports(_module("import os\n"))

    assert len(stmts) == 1
    assert stmts[0].module == "os"
    assert stmts[0].is_star is False
    assert stmts[0].is_already_lazy is False


def test_plain_import_multi_name_yields_one_entry_per_module() -> None:
    stmts = iter_top_level_imports(_module("import os, sys\n"))

    assert [s.module for s in stmts] == ["os", "sys"]


def test_dotted_import() -> None:
    stmts = iter_top_level_imports(_module("import xml.etree.ElementTree\n"))

    assert stmts[0].module == "xml.etree.ElementTree"


def test_from_import() -> None:
    stmts = iter_top_level_imports(_module("from numpy import array\n"))

    assert len(stmts) == 1
    assert stmts[0].module == "numpy"


def test_dotted_from_import() -> None:
    stmts = iter_top_level_imports(_module("from a.b import c\n"))

    assert stmts[0].module == "a.b"


def test_from_import_multiple_names_is_one_statement() -> None:
    stmts = iter_top_level_imports(_module("from numpy import array, zeros\n"))

    assert len(stmts) == 1
    assert stmts[0].module == "numpy"


def test_star_import_flagged() -> None:
    stmts = iter_top_level_imports(_module("from os import *\n"))

    assert stmts[0].is_star is True


def test_relative_import_has_empty_module() -> None:
    stmts = iter_top_level_imports(_module("from . import x\n"))

    assert stmts[0].module == ""


def test_already_lazy_import_flagged() -> None:
    stmts = iter_top_level_imports(_module("lazy import os\n"))

    assert stmts[0].is_already_lazy is True
    assert stmts[0].module == "os"


def test_already_lazy_from_import_flagged() -> None:
    stmts = iter_top_level_imports(_module("lazy from pathlib import Path\n"))

    assert stmts[0].is_already_lazy is True
    assert stmts[0].module == "pathlib"


def test_nested_import_not_returned() -> None:
    source = """
def f():
    import os
    return os
"""
    stmts = iter_top_level_imports(_module(source))

    assert stmts == []


def test_import_inside_if_not_returned() -> None:
    source = """
if True:
    import os
"""
    stmts = iter_top_level_imports(_module(source))

    assert stmts == []


def test_is_eligible_requires_allow_listing() -> None:
    config = Config(allow=["numpy"], deny=[])

    assert is_eligible("numpy", config) is True
    assert is_eligible("pandas", config) is False


def test_is_eligible_deny_overrides_allow() -> None:
    config = Config(allow=["numpy"], deny=["numpy"])

    assert is_eligible("numpy", config) is False


def test_split_multi_name_splits_import() -> None:
    module = _module("import os, sys\n")
    (line,) = module.body
    assert isinstance(line, cst.SimpleStatementLine)

    result = split_multi_name(line)

    assert [module.code_for_node(r) for r in result] == ["import os\n", "import sys\n"]


def test_split_multi_name_three_names() -> None:
    module = _module("import a, b, c\n")
    (line,) = module.body
    assert isinstance(line, cst.SimpleStatementLine)

    result = split_multi_name(line)

    assert [module.code_for_node(r) for r in result] == ["import a\n", "import b\n", "import c\n"]


def test_split_multi_name_leaves_single_name_unchanged() -> None:
    module = _module("import os\n")
    (line,) = module.body
    assert isinstance(line, cst.SimpleStatementLine)

    result = split_multi_name(line)

    assert result == [line]


def test_split_multi_name_leaves_from_import_unchanged() -> None:
    module = _module("from numpy import array, zeros\n")
    (line,) = module.body
    assert isinstance(line, cst.SimpleStatementLine)

    result = split_multi_name(line)

    assert result == [line]
