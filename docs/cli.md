# CLI reference

```bash
lazy-fix check [path ...] [options]
lazy-fix fix [path ...] [options]
```

Each `path` is a file or a directory, and directories are recursed into. Only
`.py` files are considered. Dot-prefixed directories/files and
`.gitignore`-matched paths are skipped.

## Project root

With no `path`, lazy-fix scans the whole project from its root. It finds the
root by walking up from the current directory. The first directory holding a
`lazy-fix.toml` or a `pyproject.toml` is the root. With neither, the git root
is used, and with no git repository, the current directory.

Configuration is always read from the project root, including when you pass
explicit paths. Paths only limit what is scanned.

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
