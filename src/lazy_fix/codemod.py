"""LibCST codemod that rewrites eligible module-level imports to PEP 810 lazy imports.

Only module-level `import x` and `from x import y` statements are touched.
`from x import *` is left as-is. `import a, b` is split into separate
statements before being made lazy.
"""

import libcst as cst


class LazyImportTransformer(cst.CSTTransformer):
    """Rewrite eligible imports to `lazy import` / `lazy from ... import ...`."""

    def __init__(self, allow: list[str], deny: list[str]) -> None:
        """Store the allow/deny module lists used to decide what to rewrite."""
        self.allow = allow
        self.deny = deny
