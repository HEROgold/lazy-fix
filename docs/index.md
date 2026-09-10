# lazy-fix

Check and fix Python imports into [PEP 810](https://peps.python.org/pep-0810/) lazy imports.

PEP 810 adds a `lazy` soft keyword to Python 3.15: `lazy import json` and
`lazy from pathlib import Path` defer the actual import until the name is
first used. lazy-fix is a CST-based (LibCST) tool that finds eligible
module-level imports in your codebase and rewrites them to that syntax,
so you don't have to do it by hand.

## Install

```bash
uv add --dev lazy-fix
```

## Quickstart

```bash
lazy-fix check .
lazy-fix fix .
```

`check` reports imports that should be lazy but aren't, and exits with a
non-zero status if it finds any — use it as a CI gate. `fix` rewrites them
in place; pass `--diff` to preview the changes without writing.

## Targeting pre-3.15 projects

If a project's `requires-python` doesn't allow 3.15 yet, lazy-fix falls back
to PEP 810's own forward-compatibility mechanism: a `__lazy_modules__` list
declared under the imports, rather than the `lazy import` syntax itself. See
[PEP 810 and __lazy_modules__](pep810.md).

## Next

- [Getting started](getting-started.md)
- [CLI reference](cli.md)
- [Configuration reference](configuration.md)
- [Pre-commit integration](pre-commit.md)
