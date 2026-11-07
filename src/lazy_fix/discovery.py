"""Find the .py files a check/fix run should consider."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pathspec

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from pathlib import Path

type _Specs = list[tuple[Path, pathspec.PathSpec]]


def _load_gitignore(directory: Path) -> pathspec.PathSpec | None:
    gitignore = directory / ".gitignore"
    if not gitignore.is_file():
        return None
    lines = gitignore.read_text(encoding="utf-8").splitlines()
    return pathspec.PathSpec.from_lines("gitignore", lines)


def _is_ignored(path: Path, *, is_dir: bool, specs: _Specs) -> bool:
    for directory, spec in specs:
        relative = path.relative_to(directory).as_posix()
        if is_dir:
            relative += "/"
        if spec.match_file(relative):
            return True
    return False


def _walk(directory: Path, specs: _Specs, excluded: Callable[[Path], bool]) -> Iterator[Path]:
    spec = _load_gitignore(directory)
    local_specs = [*specs, (directory, spec)] if spec is not None else specs

    for entry in sorted(directory.iterdir()):
        if entry.name.startswith("."):
            continue
        is_dir = entry.is_dir()
        if _is_ignored(entry, is_dir=is_dir, specs=local_specs) or excluded(entry):
            continue
        if is_dir:
            yield from _walk(entry, local_specs, excluded)
        elif entry.suffix == ".py":
            yield entry


def iter_python_files(root: Path, *, exclude: Sequence[str] = (), project_root: Path | None = None) -> Iterator[Path]:
    """Recursively list .py files under root, skipping dot-prefixed, gitignored and excluded paths.

    exclude holds gitignore-style patterns, matched against paths relative to
    project_root (default: root itself). They also apply to a file given directly.
    """
    base = (project_root or (root if root.is_dir() else root.parent)).resolve()
    spec = pathspec.PathSpec.from_lines("gitignore", exclude)

    def excluded(path: Path) -> bool:
        if not exclude:
            return False
        try:
            relative = path.resolve().relative_to(base).as_posix()
        except ValueError:
            return False
        return spec.match_file(f"{relative}/" if path.is_dir() else relative)

    if root.is_file():
        if root.suffix == ".py" and not excluded(root):
            yield root
        return
    yield from _walk(root.resolve(), [], excluded)
