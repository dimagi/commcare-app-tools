"""Output formatters for CLI commands -- JSON, table, and CSV."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

import click
from rich.console import Console
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


def format_output(
    data: Any,
    fmt: str = "json",
    columns: list[str] | None = None,
    title: str | None = None,
    output_file: str | None = None,
) -> None:
    """Format and print data in the requested format.

    Args:
        data: The data to format. Can be a dict, list of dicts, or any JSON-serializable value.
        fmt: Output format -- "json", "table", or "csv".
        columns: Column names for table/CSV output. If None, inferred from data keys.
        title: Optional title for table output.
        output_file: If provided, write to this file instead of stdout.
    """
    if fmt == "json":
        _output_json(data, output_file)
    elif fmt == "table":
        _output_table(data, columns, title, output_file)
    elif fmt == "csv":
        _output_csv(data, columns, output_file)
    else:
        raise click.BadParameter(f"Unknown format: {fmt}. Use json, table, or csv.")


def _output_json(data: Any, output_file: str | None) -> None:
    text = json.dumps(data, indent=2, default=str)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        console.print_json(data=data)


def _output_table(
    data: Any,
    columns: list[str] | None,
    title: str | None,
    output_file: str | None,
) -> None:
    rows = _normalize_to_rows(data)
    if not rows:
        console.print("[dim]No results.[/dim]")
        return

    if columns is None:
        columns = list(rows[0].keys())

    table = Table(title=title, show_lines=False)
    for col in columns:
        table.add_column(col, overflow="fold")

    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    if output_file:
        file_console = Console(file=open(output_file, "w", encoding="utf-8"))
        file_console.print(table)
    else:
        console.print(table)


def _output_csv(
    data: Any,
    columns: list[str] | None,
    output_file: str | None,
) -> None:
    rows = _normalize_to_rows(data)
    if not rows:
        click.echo("No results.")
        return

    if columns is None:
        columns = list(rows[0].keys())

    if output_file:
        f = open(output_file, "w", encoding="utf-8", newline="")
    else:
        f = io.StringIO()

    writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col, "") for col in columns})

    if output_file:
        f.close()
    else:
        click.echo(f.getvalue(), nl=False)


def _normalize_to_rows(data: Any) -> list[dict]:
    """Normalize data into a list of dicts for table/CSV output."""
    if isinstance(data, list):
        return [row if isinstance(row, dict) else {"value": row} for row in data]
    if isinstance(data, dict):
        # If it looks like a paginated response with "objects" key
        if "objects" in data and isinstance(data["objects"], list):
            return data["objects"]
        # If it looks like a paginated response with "results" key
        if "results" in data and isinstance(data["results"], list):
            return data["results"]
        # Single object -- wrap in a list
        return [data]
    return [{"value": data}]


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    error_console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_info(message: str) -> None:
    """Print an informational message."""
    console.print(f"[dim]{message}[/dim]")
