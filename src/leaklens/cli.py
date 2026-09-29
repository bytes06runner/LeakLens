"""Command-line entry point.

Until the analyser is built (Phase 4), `leaklens scan` refuses with exit code 3 ("mode unavailable", SPEC §7);
it never prints a fake "no leakage found".
"""

import sys

import click
from rich.console import Console

from leaklens import LEAKAGE_TYPES, __version__

console = Console()

# Exit codes: docs/SPEC.md §7.
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_UNANALYSABLE = 3
EXIT_NOT_IMPLEMENTED = EXIT_UNANALYSABLE


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
    console.print("Status: Phase 1 (taxonomy and specification). No detector is implemented yet.")


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def scan(paths: tuple[str, ...]) -> None:
    """Scan .py / .ipynb files for leakage (available from Phase 4)."""
    console.print("[yellow]leaklens scan is not implemented yet (Phase 4).[/yellow] No analysis was run.")
    sys.exit(EXIT_NOT_IMPLEMENTED)


if __name__ == "__main__":
    main()
