"""Command-line entry point.

Phase 0 ships only `leaklens info`. `leaklens scan` exists so the interface is visible, but it refuses to
produce findings until the analyser is built (Phase 4); it never prints a fake "no leakage found".
"""

import sys

import click
from rich.console import Console

from leaklens import LEAKAGE_TYPES, __version__

console = Console()

# Exit codes are specified in docs/SPEC.md (Phase 1). 3 = tool cannot analyse the input.
EXIT_NOT_IMPLEMENTED = 3


@click.group()
@click.version_option(__version__, prog_name="leaklens")
def main() -> None:
    """LeakLens: find data leakage in ML scripts and notebooks."""


@main.command()
def info() -> None:
    """Show version, supported leakage types and build status."""
    console.print(f"[bold]LeakLens[/bold] {__version__}")
    console.print(f"Python {sys.version.split()[0]}")
    console.print("Leakage types (docs/TAXONOMY.md): " + ", ".join(LEAKAGE_TYPES))
    console.print("Status: Phase 0 (setup and novelty check). No detector is implemented yet.")


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def scan(paths: tuple[str, ...]) -> None:
    """Scan .py / .ipynb files for leakage (available from Phase 4)."""
    console.print("[yellow]leaklens scan is not implemented yet (Phase 4).[/yellow] No analysis was run.")
    sys.exit(EXIT_NOT_IMPLEMENTED)


if __name__ == "__main__":
    main()
