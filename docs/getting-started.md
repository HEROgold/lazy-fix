# Getting started

## Install

```bash
uv add --dev lazy-fix
```

Requires Python 3.15+ to run.

## Check a repository

```bash
lazy-fix check .
```

Recurses from the given path, considers `.py` files only, and skips
dot-prefixed directories/files and anything matched by `.gitignore`. Reports
every eligible import that isn't lazy yet and exits non-zero if it finds any.

## Fix a repository

```bash
lazy-fix fix .
```

Rewrites eligible imports in place. Add `--diff` to preview the changes
without writing them:

```bash
lazy-fix fix . --diff
```

## What counts as "eligible"

An import is only rewritten if its source module is listed in your
project's `allow` list (or not in `deny`, depending on how you've
configured it) — see the [configuration reference](configuration.md).
lazy-fix never touches `from x import *`, and only rewrites module-level
imports (not ones already inside a function body or conditional block).
