"""Tests for lazy_fix.config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lazy_fix.config import Config, load_config, target_supports_pep_810

if TYPE_CHECKING:
    from pathlib import Path


def test_load_config_empty_when_nothing_present(tmp_path: Path) -> None:
    assert load_config(tmp_path) == Config()


def test_load_config_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [tool.lazy-fix]
        allow = ["numpy"]
        deny = ["os"]
        """,
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config == Config(allow=["numpy"], deny=["os"])


def test_load_config_from_standalone_file(tmp_path: Path) -> None:
    (tmp_path / "lazy-fix.toml").write_text(
        """
        allow = ["pandas"]
        """,
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config == Config(allow=["pandas"], deny=[])


def test_standalone_file_takes_precedence_over_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [tool.lazy-fix]
        allow = ["from-pyproject"]
        """,
        encoding="utf-8",
    )
    (tmp_path / "lazy-fix.toml").write_text(
        """
        allow = ["from-standalone"]
        """,
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.allow == ["from-standalone"]


def test_target_supports_pep_810_true_for_315_plus(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        requires-python = ">=3.15"
        """,
        encoding="utf-8",
    )

    assert target_supports_pep_810(tmp_path) is True


def test_target_supports_pep_810_false_for_older_floor(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        requires-python = ">=3.9"
        """,
        encoding="utf-8",
    )

    assert target_supports_pep_810(tmp_path) is False


def test_target_supports_pep_810_false_when_range_excludes_315(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        requires-python = ">=3.11,<3.14"
        """,
        encoding="utf-8",
    )

    assert target_supports_pep_810(tmp_path) is False


def test_target_supports_pep_810_false_when_no_pyproject(tmp_path: Path) -> None:
    assert target_supports_pep_810(tmp_path) is False


def test_target_supports_pep_810_false_when_no_requires_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        name = "x"
        """,
        encoding="utf-8",
    )

    assert target_supports_pep_810(tmp_path) is False
