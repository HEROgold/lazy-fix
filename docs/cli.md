# CLI reference

```bash
lazy-fix check <path> [options]
lazy-fix fix <path> [options]
```

`<path>` is recursed into by default; only `.py` files are considered.
Dot-prefixed directories/files and `.gitignore`-matched paths are skipped.

## `check`

Reports non-lazy imports that should be lazy, per your configuration.
Writes nothing. Exits `1` if any violations are found, `0` otherwise —
suitable as a CI gate.

## `fix`

Rewrites eligible imports to lazy form and exits `0` once done.

| Flag | Description |
| --- | --- |
| `--diff` / `--dry-run` | Print the changes without writing them |

## Exit codes

| Command | Exit code | Meaning |
| --- | --- | --- |
| `check` | `0` | No violations found |
| `check` | `1` | One or more non-lazy imports found |
| `fix` | `0` | Fix ran (whether or not it changed anything) |
