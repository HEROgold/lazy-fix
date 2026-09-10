"""Tests for lazy_fix.fix."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lazy_fix.config import Config
from lazy_fix.fix import fix

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_writes_rewritten_file(tmp_path: Path) -> None:
    target = _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["os"])

    results = fix([tmp_path], config, target_pep_810=True)

    assert len(results) == 1
    assert results[0].changed is True
    assert target.read_text(encoding="utf-8") == "lazy import os\n"


def test_unchanged_file_reports_no_change(tmp_path: Path) -> None:
    target = _write(tmp_path / "a.py", "import os\n")
    original = target.read_text(encoding="utf-8")
    config = Config(allow=["sys"])

    results = fix([tmp_path], config, target_pep_810=True)

    assert results[0].changed is False
    assert results[0].diff == ""
    assert target.read_text(encoding="utf-8") == original


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    target = _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["os"])

    results = fix([tmp_path], config, target_pep_810=True, dry_run=True)

    assert results[0].changed is True
    assert target.read_text(encoding="utf-8") == "import os\n"


def test_dry_run_diff_contains_before_and_after(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["os"])

    results = fix([tmp_path], config, target_pep_810=True, dry_run=True)

    assert "-import os" in results[0].diff
    assert "+lazy import os" in results[0].diff


def test_pre_315_target_inserts_marker(tmp_path: Path) -> None:
    target = _write(tmp_path / "a.py", "import os\n")
    config = Config(allow=["os"])

    fix([tmp_path], config, target_pep_810=False)

    assert target.read_text(encoding="utf-8") == 'import os\n__lazy_modules__ = ["os"]\n'


def test_fixes_multiple_files(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.py", "import os\n")
    b = _write(tmp_path / "b.py", "import sys\n")
    config = Config(allow=["os", "sys"])

    fix([tmp_path], config, target_pep_810=True)

    assert a.read_text(encoding="utf-8") == "lazy import os\n"
    assert b.read_text(encoding="utf-8") == "lazy import sys\n"
