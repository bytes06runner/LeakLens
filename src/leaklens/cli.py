"""Command-line entry point (docs/SPEC.md sections 2, 7 and 8).

`leaklens scan` runs the static analyser and never executes the analysed code. `--dynamic` and `--impact`
execute it, instrumented, and therefore need `--trust-code`: untrusted notebooks may only be run through
`leaklens.sandbox` inside an offline Kaggle session (CLAUDE.md Integrity Rule 7).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from leaklens import LEAKAGE_TYPES, __version__

console = Console()

# Exit codes: docs/SPEC.md section 7.
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_UNANALYSABLE = 3


def _commit() -> str | None:
    try:
        root = Path(__file__).resolve().parents[2]
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                             timeout=5)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


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
    console.print("Status: static analyser, dynamic confirmation and impact estimation implemented; results so far "
                  "are on the DEV split only (see README).")


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["terminal", "json", "sarif"]), default="terminal")
@click.option("--output", "-o", type=click.Path(dir_okay=False), help="Write the report to this file.")
@click.option("--fail-on", type=click.Choice(["never", "low", "medium", "high"]), default="high", show_default=True)
@click.option("--min-confidence", type=click.Choice(["low", "medium", "high"]), default="medium", show_default=True)
@click.option("--strict", is_flag=True, help="Exit 3 when any input could not be analysed.")
@click.option("--dynamic", is_flag=True, help="Also run each file, instrumented, to confirm or refute findings.")
@click.option("--impact", is_flag=True, help="Also re-run each file with the canonical fix and report the metric change.")
@click.option("--trust-code", is_flag=True, help="Required with --dynamic/--impact: the code is yours and safe to run.")
@click.option("--timeout", type=int, default=600, show_default=True, help="Seconds per run in dynamic/impact mode.")
@click.option("-v", "--verbose", is_flag=True)
def scan(paths: tuple[str, ...], fmt: str, output: str | None, fail_on: str, min_confidence: str, strict: bool,
         dynamic: bool, impact: bool, trust_code: bool, timeout: int, verbose: bool) -> None:
    """Scan .py / .ipynb files or directories for data leakage."""
    from leaklens.config import load_config
    from leaklens.ingest import collect, load
    from leaklens.report.findings import passes
    from leaklens.report.output import envelope, terminal_lines, to_sarif
    from leaklens.static.analyzer import analyze

    if not paths:
        console.print("[red]No path given.[/red] Usage: leaklens scan PATH...")
        sys.exit(EXIT_USAGE)
    if (dynamic or impact) and not trust_code:
        console.print("[red]--dynamic and --impact execute the analysed code.[/red] Pass --trust-code for your own "
                      "code. Notebooks from the internet must only be run inside an offline Kaggle session through "
                      "leaklens.sandbox (see README).")
        sys.exit(EXIT_UNANALYSABLE)
    files = collect(list(paths))
    sources, findings = [], []
    for p in files:
        src = load(p)
        sources.append(src)
        if src.status != "ok":
            continue
        fs, truncated = analyze(src)
        if truncated:
            src.skipped_cells.append({"cell": None, "reason": "analysis stopped at the statement budget"})
        if dynamic or impact:
            from leaklens.dynamic.confirm import confirm_file

            fs = confirm_file(Path(p), src, fs, with_impact=impact, timeout=timeout)
        findings += fs
    mode = "impact" if impact else "dynamic" if dynamic else "static"
    report = envelope(str(Path.cwd()), mode, sources, findings, load_config("static"), _commit())
    if fmt == "terminal":
        text = None
        for line in terminal_lines(report, min_confidence, verbose):
            console.print(line, highlight=False)
    else:
        text = json.dumps(to_sarif(report) if fmt == "sarif" else report, indent=2)
        if not output:
            click.echo(text)
    if output:
        Path(output).write_text(text if text is not None else json.dumps(report, indent=2))
    analysed = [s for s in sources if s.status == "ok"]
    if any(passes(f, fail_on, min_confidence) for f in findings):
        sys.exit(EXIT_FINDINGS)
    if not analysed or (strict and len(analysed) < len(sources)):
        sys.exit(EXIT_UNANALYSABLE)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
