# Configuration reference

Config lives in a `[tool.lazy-fix]` section of `pyproject.toml`, or in a
standalone `lazy-fix.toml`. If both are present, `lazy-fix.toml` wins —
the same precedence rule ruff uses for `ruff.toml` vs `[tool.ruff]`.

## `pyproject.toml`

```toml
[tool.lazy-fix]
allow = ["numpy", "pandas"]
deny = []
```

## `lazy-fix.toml`

```toml
allow = ["numpy", "pandas"]
deny = []
```

## Options

| Key | Type | Description |
| --- | --- | --- |
| `allow` | list of module names | Modules eligible to be made lazy |
| `deny` | list of module names | Modules that must never be made lazy |

Matching is on the source module only: listing `numpy` governs both
`import numpy` and `from numpy import array`, not individual imported names.

## Python version targeting

lazy-fix reads `requires-python` from `pyproject.toml` to decide whether a
file can use real `lazy import` syntax (3.15+) or needs the
`__lazy_modules__` fallback instead — see
[PEP 810 and __lazy_modules__](pep810.md).
