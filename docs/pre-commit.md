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

Both hooks only run against `.py` files that pre-commit passes them, on top
of lazy-fix's own dot-prefix and `.gitignore` skipping.
