
import sys
from typing import Literal

import click
from rich.console import Console

# We'll instantiate Console here to use it across the module
# This is a common pattern for Rich-based CLIs
console = Console(stderr=True)


@click.group()
@click.version_option(package_name="docktor")
def cli() -> None:
    """
    Docktor: The smart Dockerfile analysis and optimization tool.

    Docktor helps you build smaller, faster, and more secure Docker images
    by analyzing your Dockerfile and suggesting improvements.
    """
    pass


@cli.command()
@click.argument("dockerfile_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--explain", is_flag=True, default=False, help="Show detailed explanations for each issue found.")
@click.option("--format", type=click.Choice(['text', 'json']), default='text', help="Choose the output format.")
def lint(dockerfile_path: str, explain: bool, format: Literal['text', 'json']) -> None:
    """Analyze a Dockerfile for issues and optimizations."""
    console.print(f"🔍 Analyzing Dockerfile at: [cyan]{dockerfile_path}[/cyan]")
    console.print(f"   Explanations: {'On' if explain else 'Off'}")
    console.print(f"   Output Format: {format}")


    issues_found = True
    if issues_found:
        # As per spec, exit with 1 if issues are found
        sys.exit(1)
    
    # Exit with 0 on success
    sys.exit(0)


if __name__ == "__main__":
    cli()