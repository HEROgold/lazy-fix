# Pre-commit integration

lazy-fix ships two [pre-commit](https://pre-commit.com/) hooks. Add this to
your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/HEROgold/lazy-fix
    rev: v0.1.0 # replace with the latest tag
    hooks:
      - id: lazy-fix-check
```

`lazy-fix-check` fails the commit if it finds non-lazy imports that should
be lazy, without changing anything. To have pre-commit fix them
automatically instead, use `lazy-fix-fix`:

```yaml
repos:
  - repo: https://github.com/HEROgold/lazy-fix
    rev: v0.1.0
    hooks:
      - id: lazy-fix-fix
```

Both hooks only run against the staged `.py` files that pre-commit passes
them, on top of lazy-fix's own dot-prefix and `.gitignore` skipping. They
accept any number of files, and read configuration from the project root.

## Order the hook before your formatter

`lazy-fix-fix` writes valid but unformatted code. List it before your
formatter in `.pre-commit-config.yaml`, so the formatter cleans up its output
in the same run:

```yaml
repos:
  - repo: https://github.com/HEROgold/lazy-fix
    rev: v0.1.0
    hooks:
      - id: lazy-fix-fix
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.0
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

With the hook after the formatter, the formatter has already run, and the
next commit shows long `__lazy_modules__` lists or import order errors that
only a second run fixes.
