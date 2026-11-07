"""Tests for lazy_fix.imports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst
import pytest

from lazy_fix.config import Config, ConfigError
from lazy_fix.imports import is_eligible, iter_top_level_imports, split_multi_name

if TYPE_CHECKING:
    from pathlib import Path


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


def test_is_eligible_by_default() -> None:
    assert is_eligible("numpy", Config()) is True


def test_is_eligible_false_when_denied() -> None:
    assert is_eligible("numpy", Config(deny=["numpy"])) is False


def test_deny_covers_submodules_but_not_lookalikes() -> None:
    config = Config(deny=["sqlalchemy"])

    assert is_eligible("sqlalchemy.orm", config) is False
    assert is_eligible("sqlalchemyx", config) is True


def test_more_specific_allow_beats_deny() -> None:
    config = Config(allow=["sqlalchemy.orm"], deny=["sqlalchemy"])

    assert is_eligible("sqlalchemy.orm", config) is True
    assert is_eligible("sqlalchemy.orm.session", config) is True
    assert is_eligible("sqlalchemy.pool", config) is False


def test_more_specific_deny_beats_allow() -> None:
    config = Config(allow=["sqlalchemy"], deny=["sqlalchemy.orm"])

    assert is_eligible("sqlalchemy.pool", config) is True
    assert is_eligible("sqlalchemy.orm", config) is False


def test_future_is_never_eligible() -> None:
    assert is_eligible("__future__", Config(allow=["__future__"])) is False


def test_same_entry_in_allow_and_deny_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="numpy"):
        Config(allow=["numpy"], deny=["numpy"])


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


def _package(tmp_path: Path, *files: str) -> None:
    for name in files:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")  # skylos: ignore[SKY-D324] test fixture inside tmp_path


def _module_of(source: str, path: Path) -> str:
    return iter_top_level_imports(_module(source), path)[0].module


def test_relative_import_resolves_in_src_layout(tmp_path: Path) -> None:
    _package(tmp_path, "src/herogold/__init__.py", "src/herogold/logic/__init__.py", "src/herogold/logic/trigger.py")

    assert _module_of("from .action import X\n", tmp_path / "src/herogold/logic/trigger.py") == "herogold.logic.action"


def test_relative_import_resolves_in_flat_layout(tmp_path: Path) -> None:
    _package(tmp_path, "herogold/__init__.py", "herogold/trigger.py")

    assert _module_of("from .action import X\n", tmp_path / "herogold/trigger.py") == "herogold.action"


def test_parent_relative_import_resolves(tmp_path: Path) -> None:
    _package(tmp_path, "pkg/__init__.py", "pkg/sub/__init__.py", "pkg/sub/mod.py")

    assert _module_of("from ..other import X\n", tmp_path / "pkg/sub/mod.py") == "pkg.other"


def test_bare_parent_import_resolves_to_the_package(tmp_path: Path) -> None:
    _package(tmp_path, "pkg/__init__.py", "pkg/sub/__init__.py", "pkg/sub/mod.py")

    assert _module_of("from .. import y\n", tmp_path / "pkg/sub/mod.py") == "pkg"


def test_bare_dot_import_of_a_submodule_resolves_to_the_submodule(tmp_path: Path) -> None:
    _package(tmp_path, "pkg/__init__.py", "pkg/mod.py", "pkg/z.py")

    assert _module_of("from . import z\n", tmp_path / "pkg/mod.py") == "pkg.z"


def test_bare_dot_import_of_a_name_resolves_to_the_package(tmp_path: Path) -> None:
    _package(tmp_path, "pkg/__init__.py", "pkg/mod.py")

    assert _module_of("from . import z\n", tmp_path / "pkg/mod.py") == "pkg"


def test_relative_import_in_init_resolves_against_its_own_package(tmp_path: Path) -> None:
    _package(tmp_path, "pkg/__init__.py")

    assert _module_of("from .action import X\n", tmp_path / "pkg/__init__.py") == "pkg.action"


def test_relative_import_in_loose_script_is_unresolved(tmp_path: Path) -> None:
    _package(tmp_path, "script.py")

    assert _module_of("from .action import X\n", tmp_path / "script.py") == ""


def test_relative_import_above_the_top_package_is_unresolved(tmp_path: Path) -> None:
    _package(tmp_path, "pkg/__init__.py", "pkg/mod.py")

    assert _module_of("from ..action import X\n", tmp_path / "pkg/mod.py") == ""


def test_unresolved_module_is_never_eligible() -> None:
    assert not is_eligible("", Config(allow=[""]))
