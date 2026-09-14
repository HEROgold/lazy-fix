"""Find the .py files a check/fix run should consider."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pathspec

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def _load_gitignore(directory: Path) -> pathspec.PathSpec | None:
    gitignore = directory / ".gitignore"
    if not gitignore.is_file():
        return None
    lines = gitignore.read_text(encoding="utf-8").splitlines()
    return pathspec.PathSpec.from_lines("gitignore", lines)


def _is_ignored(path: Path, *, is_dir: bool, specs: list[tuple[Path, pathspec.PathSpec]]) -> bool:
    for directory, spec in specs:
        relative = path.relative_to(directory).as_posix()
        if is_dir:
            relative += "/"
        if spec.match_file(relative):
            return True
    return False


def _walk(directory: Path, specs: list[tuple[Path, pathspec.PathSpec]]) -> Iterator[Path]:
    spec = _load_gitignore(directory)
    local_specs = [*specs, (directory, spec)] if spec is not None else specs

    for entry in sorted(directory.iterdir()):
        if entry.name.startswith("."):
            continue
        is_dir = entry.is_dir()
        if _is_ignored(entry, is_dir=is_dir, specs=local_specs):
            continue
        if is_dir:
            yield from _walk(entry, local_specs)
        elif entry.suffix == ".py":
            yield entry


def iter_python_files(root: Path) -> Iterator[Path]:
    """Recursively list .py files under root, skipping dot-prefixed and gitignored paths."""
    if root.is_file():
        if root.suffix == ".py":
            yield root
        return
    yield from _walk(root.resolve(), [])
