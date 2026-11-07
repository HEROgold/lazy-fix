"""Load lazy-fix configuration from lazy-fix.toml or pyproject.toml.

Configuration is read with confkit from `lazy-fix.toml` (preferred) or, as a
fallback, `pyproject.toml`. Both files use the same `[tool.lazy-fix]` table and
keys. The values resolve into one immutable :class:`Config`.

Every setting is declared once, as a :class:`Config` field created with
:func:`option`. The field carries its confkit data type, and :func:`load_config`
turns the fields into confkit descriptors, so adding a setting never means
touching a parallel schema or the loader.

lazy-fix never writes to the user's config: confkit only points at a file that
exists, with `write_on_edit` off.
"""
# ruff: noqa: RUF009  # option() returns a dataclasses.field(); it is not a shared mutable default

from __future__ import annotations

import ast
import logging
import tomllib
from collections.abc import Iterable
from copy import copy
from dataclasses import Field, dataclass, field, fields
from typing import TYPE_CHECKING, Any, cast, overload, override

from confkit import BaseDataType
from confkit import Config as ConfkitConfig
from packaging.specifiers import SpecifierSet

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_ENCODING = "utf-8"
_CONFIG_FILENAMES = ("lazy-fix.toml", "pyproject.toml")
_SECTION = "tool.lazy-fix"
_DATA_TYPE = "confkit_data_type"
"""Field-metadata key holding the confkit data type an :func:`option` reads with."""


class ConfigError(ValueError):
    """The configuration is contradictory and lazy-fix cannot guess what was meant."""


class StringList(BaseDataType[list[str]]):
    """A TOML array of strings, read as a list (a bare comma-separated string also works).

    confkit stores a value natively only when `str(native) == str(value)` and always
    hands `convert` the stringified form on read. A TOML array stringifies as a Python
    literal, so this type parses its input with :func:`ast.literal_eval`.
    """

    def __init__(self, default: Iterable[str] = ()) -> None:
        """Initialise with a default list (empty when omitted)."""
        super().__init__(list(default))

    @override
    def __str__(self) -> str:
        """Return a Python literal so confkit stores the value as a native TOML array."""
        return repr(self.value)

    @override
    def convert(self, value: Any) -> list[str]:
        """Parse a stored value (native, or its stringified literal) into a list of strings."""
        if not isinstance(value, str):
            return self._parse(value)
        try:
            return self._parse(ast.literal_eval(value))
        except (ValueError, SyntaxError):
            return self._parse(value)

    @staticmethod
    def _parse(raw: object) -> list[str]:
        if isinstance(raw, str):
            return [item.strip() for item in raw.split(",") if item.strip()]
        if isinstance(raw, Iterable):
            return [str(item) for item in cast("Iterable[object]", raw)]
        return [str(raw)]


@overload
def option[T](default: BaseDataType[T]) -> T: ...
@overload
def option[T](default: T) -> T: ...
def option[T](default: T | BaseDataType[T]) -> T:
    """Declare one setting as a :class:`Config` field.

    `default` is anything confkit's descriptor accepts: a plain value or a custom
    :class:`~confkit.BaseDataType`. The field's own default is what confkit reads
    back for an unset option, so a missing file and an empty table resolve the same.
    """
    data_type = BaseDataType.cast(default)
    return cast("T", field(default_factory=lambda: _unset_value(data_type), metadata={_DATA_TYPE: data_type}))


@dataclass(frozen=True)
class Config:
    """Resolved lazy-fix configuration for a project.

    Each field is read from the `[tool.lazy-fix]` key of the same name.
    """

    allow: list[str] = option(StringList())
    """Modules (and every module below them) that are made lazy even when a broader `deny` entry covers them."""
    deny: list[str] = option(StringList())
    """Modules (and every module below them) that are never made lazy."""
    exclude: list[str] = option(StringList())
    """Glob patterns of files and directories to skip, on top of `.gitignore`."""

    def __post_init__(self) -> None:
        """Reject an entry listed in both `allow` and `deny`."""
        both = sorted(set(self.allow) & set(self.deny))
        if both:
            msg = f"listed in both allow and deny: {', '.join(both)}"
            raise ConfigError(msg)


def find_config_file(root: Path) -> Path | None:
    """Return `lazy-fix.toml` (preferred) or `pyproject.toml` in root, if either exists."""
    for filename in _CONFIG_FILENAMES:
        candidate = root / filename
        if candidate.is_file():
            return candidate
    return None


def load_config(root: Path) -> Config:
    """Resolve configuration for the project rooted at root.

    Falls back to the built-in defaults when no config file or section is
    present. An invalid value is reported and replaced by that option's default.
    """
    path = find_config_file(root)
    if path is None:
        return Config()
    _warn_about_top_level_keys(path)

    class _Cfg(ConfkitConfig[Any]): ...

    _Cfg.write_on_edit = False
    _Cfg.set_file(path)

    # confkit derives the section from the container's qualname, so naming it
    # `tool.lazy-fix` addresses `[tool.lazy-fix]`. Each descriptor gets its own
    # copy of the data type: confkit stores the last read value on it.
    options = fields(Config)
    container = type(
        "lazy-fix",
        (),
        {"__qualname__": _SECTION, **{entry.name: _Cfg(copy(_data_type(entry))) for entry in options}},
    )
    values: dict[str, Any] = {}
    for entry in options:
        try:
            values[entry.name] = getattr(container, entry.name)
        except ValueError as exc:
            logger.warning("Invalid %s in %s: %s. Using the default.", entry.name, path, exc)
    return Config(**values)


def _warn_about_top_level_keys(path: Path) -> None:
    """Point out a `lazy-fix.toml` still written with top-level keys, which are now ignored."""
    if path.name != "lazy-fix.toml":
        return
    data = tomllib.loads(path.read_text(encoding=_ENCODING))
    stale = sorted(entry.name for entry in fields(Config) if entry.name in data)
    if stale:
        logger.warning(
            "%s has top-level %s. Move them under a [tool.lazy-fix] table; top-level keys are ignored.",
            path,
            ", ".join(stale),
        )


def _data_type(entry: Field[Any]) -> BaseDataType[Any]:
    """Return the confkit data type an :func:`option` field was declared with."""
    return entry.metadata[_DATA_TYPE]


def _unset_value[T](data_type: BaseDataType[T]) -> T:
    """Return what confkit reads back for an option that is absent from the file."""
    return data_type.convert(str(data_type))


def target_supports_pep_810(root: Path) -> bool:
    """Whether requires-python in pyproject.toml allows Python 3.15+."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False

    data = tomllib.loads(pyproject.read_text(encoding=_ENCODING))
    requires_python = data.get("project", {}).get("requires-python")
    if not requires_python:
        return False

    specifier = SpecifierSet(requires_python)
    # requires-python allows 3.15+ only if 3.15 itself is allowed and nothing
    # just below it is - e.g. ">=3.11,<3.14" must not count even though it
    # never contains 3.14 outright.
    return specifier.contains("3.15", prereleases=True) and not specifier.contains("3.14.99", prereleases=True)
