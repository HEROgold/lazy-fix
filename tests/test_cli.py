"""Tests for lazy_fix.cli."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from lazy_fix.cli import build_parser, main

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")  # skylos: ignore[SKY-D324] test fixture inside tmp_path
    return path


def _project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, requires_python: str = ">=3.15") -> Path:
    monkeypatch.chdir(tmp_path)
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


def test_check_exits_zero_with_no_violations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    _write(project / "a.py", "lazy import os\n")

    assert main(["check", str(project)]) == 0


def test_check_exits_one_with_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path, monkeypatch)
    _write(project / "a.py", "import os\n")

    exit_code = main(["check", str(project)])

    assert exit_code == 1
    assert "os" in capsys.readouterr().out


def test_fix_exits_zero_and_rewrites_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    target = _write(project / "a.py", "import os\n")

    assert main(["fix", str(project)]) == 0
    assert target.read_text(encoding="utf-8") == "lazy import os\n"


def test_fix_dry_run_does_not_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    target = _write(project / "a.py", "import os\n")

    assert main(["fix", str(project), "--diff"]) == 0
    assert target.read_text(encoding="utf-8") == "import os\n"


def test_fix_pre_315_target_uses_lazy_modules_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch, requires_python=">=3.9")
    target = _write(project / "a.py", "import os\n")

    main(["fix", str(project)])

    assert target.read_text(encoding="utf-8") == '__lazy_modules__ = ["os"]\nimport os\n'


def test_check_path_defaults_to_the_project_root() -> None:
    args = build_parser().parse_args(["check"])

    assert args.paths == []


def test_fix_dry_run_defaults_to_false() -> None:
    args = build_parser().parse_args(["fix", "."])

    assert args.dry_run is False


def test_requires_a_subcommand() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_check_from_a_subdirectory_scans_the_whole_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    _write(project / "top.py", "import os\n")
    monkeypatch.chdir(_write(project / "pkg" / "inner.py", "lazy import os\n").parent)

    assert main(["check"]) == 1


def test_explicit_path_limits_the_scan_but_not_the_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    _write(project / "top.py", "import os\n")
    clean = _write(project / "pkg" / "inner.py", "lazy import os\n")
    monkeypatch.chdir(clean.parent)

    assert main(["check", str(clean)]) == 0


def test_check_accepts_several_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    first = _write(project / "a.py", "lazy import os\n")
    second = _write(project / "b.py", "lazy import os\n")

    assert main(["check", str(first), str(second)]) == 0


def test_check_reports_violations_across_several_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path, monkeypatch)
    first = _write(project / "a.py", "import os\n")
    second = _write(project / "b.py", "import os\n")

    assert main(["check", str(first), str(second)]) == 1
    assert "2 violation(s) found." in capsys.readouterr().out


def test_fix_accepts_several_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    first = _write(project / "a.py", "import os\n")
    second = _write(project / "b.py", "import os\n")

    assert main(["fix", str(first), str(second)]) == 0
    assert first.read_text(encoding="utf-8") == "lazy import os\n"
    assert second.read_text(encoding="utf-8") == "lazy import os\n"


def test_config_comes_from_the_project_root_for_nested_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _project(tmp_path, monkeypatch)
    nested = _write(project / "src" / "pkg" / "mod.py", "import os\n")

    assert main(["check", str(nested)]) == 1


def test_same_entry_in_allow_and_deny_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "pyproject.toml", '[tool.lazy-fix]\nallow = ["os"]\ndeny = ["os"]\n')
    _write(tmp_path / "a.py", "import os\n")

    assert main(["check"]) == 2
    assert "invalid configuration" in capsys.readouterr().out


def test_exclude_setting_skips_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "pyproject.toml", '[project]\nrequires-python = ">=3.15"\n\n[tool.lazy-fix]\nexclude = ["build/"]\n')
    _write(tmp_path / "build" / "gen.py", "import os\n")

    assert main(["check"]) == 0
