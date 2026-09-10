"""Tests for lazy_fix.cli."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lazy_fix.cli import build_parser, main

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _project(tmp_path: Path, *, requires_python: str = ">=3.15") -> Path:
    _write(
        tmp_path / "pyproject.toml",
        f"""
        [project]
        requires-python = "{requires_python}"

        [tool.lazy-fix]
        allow = ["os"]
        """,
    )
    return tmp_path


def test_check_exits_zero_with_no_violations(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write(project / "a.py", "lazy import os\n")

    assert main(["check", str(project)]) == 0


def test_check_exits_one_with_violations(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = _project(tmp_path)
    _write(project / "a.py", "import os\n")

    exit_code = main(["check", str(project)])

    assert exit_code == 1
    assert "os" in capsys.readouterr().out


def test_fix_exits_zero_and_rewrites_file(tmp_path: Path) -> None:
    project = _project(tmp_path)
    target = _write(project / "a.py", "import os\n")

    assert main(["fix", str(project)]) == 0
    assert target.read_text(encoding="utf-8") == "lazy import os\n"


def test_fix_dry_run_does_not_write(tmp_path: Path) -> None:
    project = _project(tmp_path)
    target = _write(project / "a.py", "import os\n")

    assert main(["fix", str(project), "--diff"]) == 0
    assert target.read_text(encoding="utf-8") == "import os\n"


def test_fix_pre_315_target_uses_lazy_modules_fallback(tmp_path: Path) -> None:
    project = _project(tmp_path, requires_python=">=3.9")
    target = _write(project / "a.py", "import os\n")

    main(["fix", str(project)])

    assert target.read_text(encoding="utf-8") == 'import os\n__lazy_modules__ = ["os"]\n'


def test_check_path_defaults_to_current_directory() -> None:
    args = build_parser().parse_args(["check"])

    assert args.path == "."


def test_fix_dry_run_defaults_to_false() -> None:
    args = build_parser().parse_args(["fix", "."])

    assert args.dry_run is False


def test_requires_a_subcommand() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
