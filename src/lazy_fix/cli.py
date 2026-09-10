"""The `lazy-fix` entry point: check and fix subcommands.

Blocked on herogold gaining subparser support (its `Argument` descriptor
currently registers onto one shared global parser with no subcommand
concept — see https://github.com/HEROgold/HeroPy). Until that lands,
`check`/`fix` cannot be wired up here.
"""


def main() -> None:
    """Parse argv and dispatch to check or fix."""
    raise NotImplementedError
