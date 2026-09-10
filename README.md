# lazy-fix

Check and fix Python imports into [PEP 810](https://peps.python.org/pep-0810/) lazy imports.

PEP 810 adds a `lazy` soft keyword to Python 3.15: `lazy import json` and
`lazy from pathlib import Path` defer the import until the name is first
used. lazy-fix is a [LibCST](https://libcst.readthedocs.io/)-based `check`/`fix`
CLI that finds eligible module-level imports and rewrites them to that
syntax.

## Install

```bash
uv add --dev lazy-fix
```

## Usage

```bash
lazy-fix check .   # report non-lazy imports, exit 1 if any are found
lazy-fix fix .      # rewrite them in place
lazy-fix fix . --diff   # preview the changes without writing
```

Recurses by default, considers `.py` files only, and skips dot-prefixed
paths and anything `.gitignore` excludes. Which modules are eligible is
configured via `[tool.lazy-fix]` in `pyproject.toml` or a standalone
`lazy-fix.toml` — see [the docs](https://herogold.github.io/lazy-fix/).

On projects whose `requires-python` doesn't allow 3.15 yet, `fix` inserts a
`__lazy_modules__` marker list instead of the `lazy import` syntax itself —
PEP 810's own documented forward-compatibility mechanism.

## Documentation

<https://herogold.github.io/lazy-fix/>

## License

MIT
