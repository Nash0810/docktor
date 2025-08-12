import sys
from typing import Literal, Optional

import click
import chardet  
from rich.console import Console
from rich.pretty import pprint
from rich.panel import Panel
from rich.table import Table

from .parser import DockerfileParser
from .reporter import display_issues, console
from .analyzer import Analyzer

from .benchmarker import DockerBenchmarker

from .optimizer import DockerfileOptimizer

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
    
    console.print(f"🔍 Analyzing Dockerfile at: [cyan]{dockerfile_path}[/cyan]")
    content = read_file_with_autodetect(dockerfile_path)
    if content is None:
        sys.exit(2)

    try:
        parser = DockerfileParser()
        instructions = parser.parse(content)

        # 1. Instantiate the analyzer
        analyzer = Analyzer()
        
        # 2. Run the analysis
        issues = analyzer.run(instructions)
        # 3. Print the results
        display_issues(issues, output_format=format, show_explanations=explain)

        sys.exit(1 if issues else 0)

    except IOError as e:

        console.print("[bold red]Error:[/bold red] Could not read file:", e)
        sys.exit(2)
    except Exception as e:
        console.print("[bold red]An unexpected error occurred during analysis:[/bold red]", e)
        sys.exit(2)

@cli.command()
@click.argument("dockerfile_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--raw", is_flag=True, default=False, help="Print the raw, clean Dockerfile content to the terminal.")
def optimize(dockerfile_path: str, raw: bool) -> None:
    """Optimizes a Dockerfile and prints the new version."""

    content = read_file_with_autodetect(dockerfile_path)
    if content is None:
        sys.exit(2)

    if sys.stdout.isatty() and not raw:
        console.print(f"🛠️  Optimizing Dockerfile at: [cyan]{dockerfile_path}[/cyan]")
    
    parser = DockerfileParser()
    instructions = parser.parse(content)

    optimizer = DockerfileOptimizer()
    result = optimizer.optimize(instructions)

    new_dockerfile_content = "\n".join([ins.original for ins in result.optimized_instructions])

    
    if sys.stdout.isatty() and not raw:
        if not result.applied_optimizations:
            console.print("\n[bold green]✅ No optimizable issues found.[/bold green]")
        else:
            console.print("\n[bold]✨ Optimizations applied:[/bold]")
            for change in result.applied_optimizations:
                console.print(f"  - {change}")
            
            console.print("\n[bold]New Optimized Dockerfile:[/bold]")
            console.print(Panel(new_dockerfile_content, border_style="green"))
    else:
        print(new_dockerfile_content)

    sys.exit(0)
@cli.command()
@click.argument("original_dockerfile", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.argument("optimized_dockerfile", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def benchmark(original_dockerfile: str, optimized_dockerfile: str):
    """Benchmarks an original and an optimized Dockerfile."""
    console.print("🚀 Starting Dockerfile benchmark...")
    
    try:
        benchmarker = DockerBenchmarker()
        results = []

        # --- Benchmark Original ---
        original_content = read_file_with_autodetect(original_dockerfile)
        if original_content:
            results.append(benchmarker.benchmark(original_content, "docktor-benchmark:original"))
        
        # --- Benchmark Optimized ---
        optimized_content = read_file_with_autodetect(optimized_dockerfile)
        if optimized_content:
            results.append(benchmarker.benchmark(optimized_content, "docktor-benchmark:optimized"))

        # --- Display Results Table ---
        table = Table(title="Benchmark Comparison")
        table.add_column("Metric", style="cyan")
        table.add_column("Original", style="magenta")
        table.add_column("Optimized", style="green")
        table.add_column("Improvement")

        if len(results) == 2:
            original_res, optimized_res = results[0], results[1]
            
            
            def get_improvement(original, optimized):
                if original == 0 or optimized == 0:
                    return "N/A"
                
                change = ((original - optimized) / original) * 100
                
                if change > 0.01: 
                    return f"[green]{change:.1f}%[/green]"
                elif change < -0.01: 
                    return f"+[red]{-change:.1f}%[/red]"
                else: 
                    return "0.0%"

            table.add_row("Image Size (MB)", f"{original_res.image_size_mb}", f"{optimized_res.image_size_mb}", get_improvement(original_res.image_size_mb, optimized_res.image_size_mb))
            table.add_row("Layer Count", f"{original_res.layer_count}", f"{optimized_res.layer_count}", get_improvement(original_res.layer_count, optimized_res.layer_count))
            table.add_row("Build Time (s)", f"{original_res.build_time_seconds}", f"{optimized_res.build_time_seconds}", get_improvement(original_res.build_time_seconds, optimized_res.build_time_seconds))

        console.print(table)


    except RuntimeError as e:
        console.print(f"[bold red]Benchmark Error:[/bold red] {e}")
        sys.exit(2)

if __name__ == "__main__":
    cli()