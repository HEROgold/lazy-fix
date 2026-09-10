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
    assert _rewrite("import os\n", allow=["sys"]) == "import os\n"


def test_deny_overrides_allow() -> None:
    assert _rewrite("import os\n", allow=["os"], deny=["os"]) == "import os\n"


def test_splits_and_rewrites_multi_name_import() -> None:
    result = _rewrite("import os, sys\n", allow=["os", "sys"])

    assert result == "lazy import os\nlazy import sys\n"


def test_splits_multi_name_but_only_rewrites_eligible() -> None:
    result = _rewrite("import os, sys\n", allow=["os"])

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

    result = _rewrite(source, allow=["os", "json"])

    assert result == "lazy import os\nimport sys\nlazy import json\n"


def test_pre_315_target_inserts_lazy_modules_marker() -> None:
    result = _rewrite("import os\nimport sys\n", allow=["os"], target_pep_810=False)

    assert result == 'import os\nimport sys\n__lazy_modules__ = ["os"]\n'


def test_pre_315_target_does_not_touch_import_statements() -> None:
    result = _rewrite("import os\n", allow=["os"], target_pep_810=False)

    assert "import os" in result
    assert "lazy import" not in result


def test_pre_315_target_no_eligible_imports_is_noop() -> None:
    source = "import os\n"

    assert _rewrite(source, allow=["sys"], target_pep_810=False) == source
