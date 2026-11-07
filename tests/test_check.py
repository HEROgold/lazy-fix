"""Tests for lazy_fix.check."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lazy_fix.check import Violation, ViolationKind, check
from lazy_fix.config import Config

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")  # skylos: ignore[SKY-D324] test fixture inside tmp_path
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
    config = Config(deny=["os"])

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
    config = Config(deny=["sys"])

    violations = check([tmp_path], config, target_pep_810=True)

    assert violations[0].line == 4


def test_pre_315_target_violation_when_not_in_lazy_modules(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["os"])

    violations = check([tmp_path], config, target_pep_810=False)

    assert len(violations) == 1
    assert violations[0].module == "os"


def test_pre_315_target_no_violation_when_listed(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", '__lazy_modules__ = ["os"]\nimport os\n')
    config = Config(allow=["os"])

    assert check([tmp_path], config, target_pep_810=False) == []


def test_pre_315_target_flags_misplaced_marker(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", 'import os\n__lazy_modules__ = ["os"]\n')
    config = Config(allow=["os"])

    violations = check([tmp_path], config, target_pep_810=False)

    assert [v.kind for v in violations] == [ViolationKind.MISPLACED]
    assert violations[0].line == 2


def test_checks_multiple_files(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")
    _write(tmp_path / "b.py", "import sys\n")
    config = Config(allow=["os", "sys"])

    violations = check([tmp_path], config, target_pep_810=True)

    assert {v.module for v in violations} == {"os", "sys"}


def test_symlinked_file_is_skipped(tmp_path: Path) -> None:
    real = _write(tmp_path / "real.txt", "import os\n")
    link = tmp_path / "link.py"
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("symlinks unavailable")
    config = Config(allow=["os"])

    results = check([link], config, target_pep_810=True)

    assert results == []


def test_relative_import_is_checked_by_fully_qualified_name(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")  # skylos: ignore[SKY-D324] test fixture inside tmp_path
    (tmp_path / "pkg" / "mod.py").write_text(
        "from .action import Action\n", encoding="utf-8"
    )  # skylos: ignore[SKY-D324] test fixture inside tmp_path

    violations = check([tmp_path], Config(allow=["pkg.action"]), target_pep_810=False)

    assert [v.module for v in violations] == ["pkg.action"]


def test_pre_315_target_flags_stale_marker_entry(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", '__lazy_modules__ = ["os", "gone"]\nimport os\n')

    violations = check([tmp_path], Config(), target_pep_810=False)

    assert [(v.module, v.kind, v.line) for v in violations] == [("gone", ViolationKind.STALE, 1)]


def test_pre_315_target_flags_denied_marker_entry(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", '__lazy_modules__ = ["os"]\nimport os\n')

    violations = check([tmp_path], Config(deny=["os"]), target_pep_810=False)

    assert [(v.module, v.kind) for v in violations] == [("os", ViolationKind.STALE)]


def test_pre_315_target_flags_import_missing_from_marker(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", '__lazy_modules__ = ["os"]\nimport os\nimport sys\n')

    violations = check([tmp_path], Config(), target_pep_810=False)

    assert [(v.module, v.kind, v.line) for v in violations] == [("sys", ViolationKind.MISSING, 3)]


def test_every_module_is_checked_by_default(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")

    assert [v.module for v in check([tmp_path], Config(), target_pep_810=True)] == ["os"]


def test_future_import_is_never_a_violation(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "from __future__ import annotations\n")

    assert check([tmp_path], Config(), target_pep_810=True) == []
    assert check([tmp_path], Config(), target_pep_810=False) == []


def test_excluded_files_are_skipped(tmp_path: Path) -> None:
    _write(tmp_path / "keep.py", "import os\n")
    _write(tmp_path / "build" / "gen.py", "import os\n")

    violations = check([tmp_path], Config(exclude=["build/"]), target_pep_810=True, project_root=tmp_path)

    assert [v.path.name for v in violations] == ["keep.py"]


def test_message_describes_each_kind(tmp_path: Path) -> None:
    missing = Violation(path=tmp_path, line=1, module="os")
    stale = Violation(path=tmp_path, line=1, module="os", kind=ViolationKind.STALE)
    misplaced = Violation(path=tmp_path, line=1, module="__lazy_modules__", kind=ViolationKind.MISPLACED)

    assert missing.message == "os should be lazy"
    assert "not an eligible import" in stale.message
    assert "before the imports it governs" in misplaced.message
