import sys
from typing import Literal, Optional

import click
import chardet  
from rich.console import Console
from rich.pretty import pprint

from .parser import DockerfileParser

from .analyzer import Analyzer

console = Console(stderr=True)


def read_file_with_autodetect(file_path: str) -> Optional[str]:

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()

        # Detect encoding
        detection = chardet.detect(raw_data)
        encoding = detection['encoding']
        confidence = detection['confidence']
        
        console.print(f"📝 Detected encoding: [yellow]{encoding}[/yellow] with {confidence:.0%} confidence.")

        if encoding is None:
            console.print(f"[bold red]Error:[/bold red] Could not detect file encoding.")
            return None

        # Decode using the detected encoding
        return raw_data.decode(encoding)

    except IOError as e:
        console.print(f"[bold red]Error:[/bold red] Could not read file: {e}")
        return None
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during file reading:[/bold red] {e}")
        return None


@click.group()
@click.version_option(package_name="docktor")
def cli() -> None:
    pass


@cli.command()
@click.argument("dockerfile_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--explain", is_flag=True, default=False, help="Show detailed explanations for each issue found.")
@click.option("--format", type=click.Choice(['text', 'json']), default='text', help="Choose the output format.")
def lint(dockerfile_path: str, explain: bool, format: str) -> None:
    """Analyze a Dockerfile for issues and optimizations."""
    # ... (The first part of the function remains the same) ...
    console.print(f"🔍 Analyzing Dockerfile at: [cyan]{dockerfile_path}[/cyan]")
    content = read_file_with_autodetect(dockerfile_path)
    if content is None:
        sys.exit(2)

    try:
        # --- This is the part we are changing ---
        parser = DockerfileParser()
        instructions = parser.parse(content)

        # 1. Instantiate the analyzer
        analyzer = Analyzer()
        
        # 2. Run the analysis
        issues = analyzer.run(instructions)

        # 3. Print the results
        if not issues:
            console.print("\n[bold green]✅ No issues found. Well done![/bold green]")
        else:
            console.print("\n[bold red]🚨 Issues Found:[/bold red]")
            pprint(issues)
        
        # Exit with 1 if issues were found, 0 otherwise
        sys.exit(1 if issues else 0)

    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during analysis:[/bold red] {e}")
        sys.exit(2)


if __name__ == "__main__":
    cli()