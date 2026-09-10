"""The `lazy-fix` entry point: check and fix subcommands.

This is a temporary stdlib-argparse implementation. herogold.argparse's
`Argument` descriptor currently has no subcommand support (an unimplemented
TODO in that package - it registers everything onto one shared global
parser), so this is meant to be swapped for `herogold.argparse` once that
lands, not the long-term implementation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from lazy_fix.check import check
from lazy_fix.config import load_config, target_supports_pep_810
from lazy_fix.fix import fix


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with 'check' and 'fix' subcommands."""
    parser = argparse.ArgumentParser(prog="lazy-fix")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Report non-lazy imports")
    check_parser.add_argument("path", nargs="?", default=".")

    fix_parser = subparsers.add_parser("fix", help="Rewrite non-lazy imports")
    fix_parser.add_argument("path", nargs="?", default=".")
    fix_parser.add_argument(
        "--diff",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Show the changes without writing them",
    )

    return parser


def _config_root(path: Path) -> Path:
    return path if path.is_dir() else path.parent


def _run_check(console: Console, path: Path) -> int:
    root = _config_root(path)
    config = load_config(root)
    target_pep_810 = target_supports_pep_810(root)

    violations = check([path], config, target_pep_810=target_pep_810)
    if not violations:
        console.print("[green]No violations found.[/green]")
        return 0

    for violation in sorted(violations, key=lambda v: (str(v.path), v.line)):
        console.print(f"[yellow]{violation.path}:{violation.line}[/yellow] {violation.module} should be lazy")
    console.print(f"[red]{len(violations)} violation(s) found.[/red]")
    return 1


def _run_fix(console: Console, path: Path, *, dry_run: bool) -> int:
    root = _config_root(path)
    config = load_config(root)
    target_pep_810 = target_supports_pep_810(root)

    results = fix([path], config, target_pep_810=target_pep_810, dry_run=dry_run)
    changed = [result for result in results if result.changed]

    if dry_run:
        for result in changed:
            console.print(result.diff)
    else:
        for result in changed:
            console.print(f"[green]fixed[/green] {result.path}")

    console.print(f"{len(changed)} file(s) changed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse argv and dispatch to check or fix."""
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()
    path = Path(args.path).resolve()

    if args.command == "check":
        return _run_check(console, path)
    return _run_fix(console, path, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
