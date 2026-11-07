"""Tests for lazy_fix.codemod."""

import libcst as cst

from lazy_fix.codemod import rewrite_module
from lazy_fix.config import Config


def _rewrite(source: str, *, allow: list[str], deny: list[str] | None = None, target_pep_810: bool = True) -> str:
    module = cst.parse_module(source)
    config = Config(allow=allow, deny=deny or [])
    result = rewrite_module(module, config, target_pep_810=target_pep_810)
    return module.code_for_node(result)


def test_rewrites_eligible_plain_import() -> None:
    assert _rewrite("import os\n", allow=["os"]) == "lazy import os\n"


def test_rewrites_eligible_from_import() -> None:
    assert _rewrite("from pathlib import Path\n", allow=["pathlib"]) == "lazy from pathlib import Path\n"


def test_leaves_ineligible_import_untouched() -> None:
    assert _rewrite("import os\n", allow=[], deny=["os"]) == "import os\n"


def test_every_module_is_eligible_by_default() -> None:
    assert _rewrite("import os\n", allow=[]) == "lazy import os\n"


def test_deny_covers_submodules() -> None:
    assert _rewrite("import sqlalchemy.pool\n", allow=[], deny=["sqlalchemy"]) == "import sqlalchemy.pool\n"


def test_more_specific_allow_overrides_deny() -> None:
    source = "import sqlalchemy.orm\nimport sqlalchemy.pool\n"

    assert _rewrite(source, allow=["sqlalchemy.orm"], deny=["sqlalchemy"]) == (
        "lazy import sqlalchemy.orm\nimport sqlalchemy.pool\n"
    )


def test_future_import_is_never_rewritten() -> None:
    source = "from __future__ import annotations\n"

    assert _rewrite(source, allow=["__future__"]) == source


def test_splits_and_rewrites_multi_name_import() -> None:
    result = _rewrite("import os, sys\n", allow=["os", "sys"])

    assert result == "lazy import os\nlazy import sys\n"


def test_splits_multi_name_but_only_rewrites_eligible() -> None:
    result = _rewrite("import os, sys\n", allow=[], deny=["sys"])

    assert result == "lazy import os\nimport sys\n"


def test_skips_star_import() -> None:
    assert _rewrite("from os import *\n", allow=["os"]) == "from os import *\n"


def test_already_lazy_import_is_idempotent() -> None:
    assert _rewrite("lazy import os\n", allow=["os"]) == "lazy import os\n"


def test_leaves_nested_import_untouched() -> None:
    source = "def f():\n    import os\n    return os\n"

    assert _rewrite(source, allow=["os"]) == source


def test_multiple_eligible_imports() -> None:
    source = "import os\nimport sys\nimport json\n"

    result = _rewrite(source, allow=[], deny=["sys"])

    assert result == "lazy import os\nimport sys\nlazy import json\n"


def test_pre_315_target_inserts_lazy_modules_marker() -> None:
    result = _rewrite("import os\nimport sys\n", allow=[], deny=["sys"], target_pep_810=False)

    assert result == '__lazy_modules__ = ["os"]\nimport os\nimport sys\n'


def test_pre_315_target_does_not_touch_import_statements() -> None:
    result = _rewrite("import os\n", allow=["os"], target_pep_810=False)

    assert "import os" in result
    assert "lazy import" not in result


def test_pre_315_target_no_eligible_imports_is_noop() -> None:
    source = "import os\n"

    assert _rewrite(source, allow=[], deny=["os"], target_pep_810=False) == source


def test_pre_315_target_removes_stale_and_denied_marker_entries() -> None:
    source = '__lazy_modules__ = ["os", "sys", "gone"]\nimport os\nimport sys\n'

    result = _rewrite(source, allow=[], deny=["sys"], target_pep_810=False)

    assert result == '__lazy_modules__ = ["os"]\nimport os\nimport sys\n'


def test_pre_315_target_adds_missing_marker_entries_after_existing_ones() -> None:
    source = '__lazy_modules__ = ["sys"]\nimport os\nimport sys\nimport json\n'

    result = _rewrite(source, allow=[], target_pep_810=False)

    assert result == '__lazy_modules__ = ["sys", "json", "os"]\nimport os\nimport sys\nimport json\n'


def test_pre_315_target_removes_marker_when_nothing_is_eligible() -> None:
    source = '__lazy_modules__ = ["os"]\n\nimport os\n'

    result = _rewrite(source, allow=[], deny=["os"], target_pep_810=False)

    assert result == "\nimport os\n"


def test_pre_315_target_in_sync_marker_is_untouched() -> None:
    source = 'from __future__ import annotations\n\n__lazy_modules__ = ["os"]  # keep\n\nimport os\n'

    assert _rewrite(source, allow=[], target_pep_810=False) == source
