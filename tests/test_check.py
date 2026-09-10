"""Tests for lazy_fix.check."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lazy_fix.check import check
from lazy_fix.config import Config

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_finds_violation_for_eligible_import(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["os"])

    violations = check([tmp_path], config, target_pep_810=True)

    assert len(violations) == 1
    assert violations[0].module == "os"
    assert violations[0].line == 1


def test_no_violation_when_not_eligible(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["sys"])

    assert check([tmp_path], config, target_pep_810=True) == []


def test_no_violation_when_already_lazy(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "lazy import os\n")
    config = Config(allow=["os"])

    assert check([tmp_path], config, target_pep_810=True) == []


def test_no_violation_for_star_import(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "from os import *\n")
    config = Config(allow=["os"])

    assert check([tmp_path], config, target_pep_810=True) == []


def test_violation_line_number_with_preceding_code(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", '"""Docstring."""\n\nimport sys\nimport os\n')
    config = Config(allow=["os"])

    violations = check([tmp_path], config, target_pep_810=True)

    assert violations[0].line == 4


def test_pre_315_target_violation_when_not_in_lazy_modules(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["os"])

    violations = check([tmp_path], config, target_pep_810=False)

    assert len(violations) == 1
    assert violations[0].module == "os"


def test_pre_315_target_no_violation_when_listed(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", 'import os\n__lazy_modules__ = ["os"]\n')
    config = Config(allow=["os"])

    assert check([tmp_path], config, target_pep_810=False) == []


def test_checks_multiple_files(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")
    _write(tmp_path / "b.py", "import sys\n")
    config = Config(allow=["os", "sys"])

    violations = check([tmp_path], config, target_pep_810=True)

    assert {v.module for v in violations} == {"os", "sys"}
