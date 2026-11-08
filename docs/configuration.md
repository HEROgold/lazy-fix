# Configuration reference

Config lives in a `[tool.lazy-fix]` table. lazy-fix reads it from the project
root, from `lazy-fix.toml` if that exists and from `pyproject.toml` otherwise.
Both files use the same `[tool.lazy-fix]` table and keys. See
[CLI reference](cli.md#project-root) for how the root is found.

```toml
[tool.lazy-fix]
deny = ["sqlalchemy"]
allow = ["sqlalchemy.orm"]
exclude = ["build/", "migrations/"]
```

lazy-fix only reads these files. It never creates or rewrites them.

!!! warning "Breaking change in 0.2.0"
    Every module is now eligible by default, where before only modules listed
    in `allow` were. A `lazy-fix.toml` with top-level keys (`allow = [...]`)
    must move them under `[tool.lazy-fix]`. Top-level keys are ignored, and
    lazy-fix logs a warning when it finds them.

## Options

| Key | Type | Description |
| --- | --- | --- |
| `deny` | list of module names | Modules that are never made lazy |
| `allow` | list of module names | Modules made lazy even when a broader `deny` entry covers them |
| `exclude` | list of glob patterns | Files and directories to skip |

## Which modules are eligible

Every module is eligible unless `deny` covers it. `__future__` is never
eligible, because a lazy future import is invalid.

An entry covers the module itself and every module below it. `sqlalchemy`
covers `sqlalchemy` and `sqlalchemy.orm`, but not `sqlalchemyx`.

When both `deny` and `allow` cover a module, the most specific entry wins.
With `deny = ["sqlalchemy"]` and `allow = ["sqlalchemy.orm"]`,
`sqlalchemy.orm` is lazy and `sqlalchemy.pool` is not. Listing the same entry
in both `deny` and `allow` is a configuration error, and lazy-fix exits with
code `2`.

Matching uses the module's fully qualified name. A relative import such as
`from .action import Action` in `src/herogold/logic/trigger.py` is matched as
`herogold.logic.action`. lazy-fix works out the package by following
`__init__.py` files up from the file. A relative import in a file that is not
inside a package is skipped.

`from . import x` is matched as the package itself, or as `package.x` when
`x` is a submodule.

## Excluding files

`exclude` takes gitignore-style patterns, matched against paths relative to
the project root. They apply on top of `.gitignore` and dot-prefix skipping,
and also to files passed on the command line, so they work in pre-commit.

## Invalid values

A value of the wrong type logs a warning and falls back to the default for
that key.

## `__lazy_modules__` sync

On a project that can't use `lazy import` syntax yet, `fix` makes the
`__lazy_modules__` list in each file match the eligible imports exactly. It
adds missing entries and removes stale or denied ones, and it deletes the
list when no import is eligible. `check` reports a missing entry, a stale
entry, and a marker placed below the imports it governs.

## Python version targeting

lazy-fix reads `requires-python` from `pyproject.toml` to decide whether a
file can use real `lazy import` syntax (3.15+) or needs the
`__lazy_modules__` fallback instead. See
[PEP 810 and __lazy_modules__](pep810.md).
