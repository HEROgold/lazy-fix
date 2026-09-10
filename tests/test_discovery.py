"""Tests for lazy_fix.discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lazy_fix.discovery import iter_python_files

if TYPE_CHECKING:
    from pathlib import Path


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_finds_py_files_recursively(tmp_path: Path) -> None:
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "pkg" / "b.py")
    _touch(tmp_path / "pkg" / "sub" / "c.py")

    found = {p.relative_to(tmp_path).as_posix() for p in iter_python_files(tmp_path)}

    assert found == {"a.py", "pkg/b.py", "pkg/sub/c.py"}


def test_ignores_non_py_files(tmp_path: Path) -> None:
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "README.md")
    _touch(tmp_path / "data.json")

    found = {p.name for p in iter_python_files(tmp_path)}

    assert found == {"a.py"}


def test_skips_dot_prefixed_directories(tmp_path: Path) -> None:
    _touch(tmp_path / "a.py")
    _touch(tmp_path / ".venv" / "b.py")
    _touch(tmp_path / ".git" / "c.py")

    found = {p.name for p in iter_python_files(tmp_path)}

    assert found == {"a.py"}


def test_skips_dot_prefixed_files(tmp_path: Path) -> None:
    _touch(tmp_path / "a.py")
    _touch(tmp_path / ".hidden.py")

    found = {p.name for p in iter_python_files(tmp_path)}

    assert found == {"a.py"}


def test_respects_root_gitignore(tmp_path: Path) -> None:
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "build" / "b.py")
    (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")

    found = {p.name for p in iter_python_files(tmp_path)}

    assert found == {"a.py"}


def test_respects_nested_gitignore(tmp_path: Path) -> None:
    _touch(tmp_path / "pkg" / "keep.py")
    _touch(tmp_path / "pkg" / "generated.py")
    (tmp_path / "pkg" / ".gitignore").write_text("generated.py\n", encoding="utf-8")

    found = {p.name for p in iter_python_files(tmp_path)}

    assert found == {"keep.py"}


def test_gitignore_negation(tmp_path: Path) -> None:
    _touch(tmp_path / "vendor" / "a.py")
    _touch(tmp_path / "vendor" / "keep.py")
    (tmp_path / ".gitignore").write_text("vendor/*\n!vendor/keep.py\n", encoding="utf-8")

    found = {p.name for p in iter_python_files(tmp_path)}

    assert found == {"keep.py"}


def test_single_file_root(tmp_path: Path) -> None:
    target = tmp_path / "only.py"
    _touch(target)

    found = list(iter_python_files(target))

    assert found == [target]


def test_single_file_root_non_python(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    _touch(target)

    assert list(iter_python_files(target)) == []
