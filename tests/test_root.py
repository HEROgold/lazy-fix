"""Tests for lazy_fix.root."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lazy_fix.root import find_project_root

if TYPE_CHECKING:
    from pathlib import Path


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")  # skylos: ignore[SKY-D324] test fixture inside tmp_path
    return path


def test_nearest_pyproject_is_the_root(tmp_path: Path) -> None:
    _touch(tmp_path / "pyproject.toml")
    start = tmp_path / "src" / "pkg"
    start.mkdir(parents=True)

    assert find_project_root(start) == tmp_path.resolve()


def test_lazy_fix_toml_is_the_root(tmp_path: Path) -> None:
    _touch(tmp_path / "lazy-fix.toml")
    start = tmp_path / "a"
    start.mkdir()

    assert find_project_root(start) == tmp_path.resolve()


def test_nearest_config_wins_over_a_farther_one(tmp_path: Path) -> None:
    _touch(tmp_path / "pyproject.toml")
    _touch(tmp_path / "sub" / "pyproject.toml")
    start = tmp_path / "sub" / "deep"
    start.mkdir()

    assert find_project_root(start) == (tmp_path / "sub").resolve()


def test_config_in_the_same_directory_counts(tmp_path: Path) -> None:
    _touch(tmp_path / "pyproject.toml")

    assert find_project_root(tmp_path) == tmp_path.resolve()


def test_git_root_when_there_is_no_config(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    start = tmp_path / "src"
    start.mkdir()

    assert find_project_root(start) == tmp_path.resolve()


def test_config_beats_a_git_root_above_it(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    _touch(tmp_path / "sub" / "pyproject.toml")
    start = tmp_path / "sub" / "x"
    start.mkdir()

    assert find_project_root(start) == (tmp_path / "sub").resolve()
