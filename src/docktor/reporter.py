from collections import Counter
from typing import List
import json  
import dataclasses 

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .types import Issue

console = Console()

def display_issues(issues: List[Issue], output_format: str = "text") -> None:
    """
    Displays issues in the specified format (text or json).
    """
    if output_format == 'json':
        # Convert the list of Issue dataclass objects to a list of dicts
        issues_as_dicts = [dataclasses.asdict(issue) for issue in issues]
        # Dump the list of dicts to a JSON string and print
        console.print(json.dumps(issues_as_dicts, indent=2))
        return

    if not issues:
        console.print("\n[bold green]✅ No issues found. Well done![/bold green]")
        return

    severity_counts = Counter(issue.severity for issue in issues)
    summary_text = (
        f"⚠️  [yellow]{severity_counts.get('warning', 0)} warnings[/yellow]\n"
        f"ℹ️  [blue]{severity_counts.get('info', 0)} info[/blue]\n"
        f"❌ [red]{severity_counts.get('error', 0)} errors[/red]"
    )
    console.print(Panel(summary_text, title="[bold]Issues Found[/bold]", expand=False))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Line", style="dim", width=5, justify="right")
    table.add_column("Rule ID", style="cyan", width=8)
    table.add_column("Severity", width=10)
    table.add_column("Message")

    for issue in sorted(issues, key=lambda i: i.line_number):
        severity_style = {
            "warning": "[yellow]warning[/yellow]",
            "error": "[bold red]error[/bold red]",
            "info": "[blue]info[/blue]",
        }.get(issue.severity, issue.severity)
        
        table.add_row(
            str(issue.line_number),
            issue.rule_id,
            severity_style,
            issue.message,
        )

    console.print(table)