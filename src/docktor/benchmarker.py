# src/docktor/benchmarker.py

import time
import tempfile
import pathlib
import json
import docker
from docker.errors import BuildError, APIError
from rich.console import Console

from .types import BenchmarkResult

console = Console()

class DockerBenchmarker:
    """
    Handles building Docker images and collecting benchmark metrics.
    """
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"Docker daemon is not running or accessible. Please start Docker. Error: {e}")

    def benchmark(self, dockerfile_content: str, image_tag: str) -> BenchmarkResult:
        """
        Builds a Docker image from a string and measures its metrics.
        """
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = pathlib.Path(temp_dir_str)
            dockerfile_path = temp_dir / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            image = None
            result = BenchmarkResult(image_tag=image_tag)
            
            console.print(f"Building image [cyan]'{image_tag}'[/cyan]...")
            start_time = time.monotonic()
            
            try:
                stream = self.client.api.build(
                    path=str(temp_dir),
                    tag=image_tag,
                    rm=True,
                    forcerm=True,
                    decode=True
                )
                
                for chunk in stream:
                    if 'stream' in chunk:
                        print(chunk['stream'].strip())
                    elif 'error' in chunk:
                        raise BuildError(chunk['error'], build_log=stream)
                
                image = self.client.images.get(image_tag)
                
                end_time = time.monotonic()
                result.build_time_seconds = round(end_time - start_time, 2)
                result.image_size_mb = round(image.attrs['Size'] / (1024 * 1024), 2)
                result.layer_count = len(image.history())

                console.print(f"\n✅ Build successful for [cyan]'{image_tag}'[/cyan].")

            except BuildError as e:
                console.print(f"\n❌ Build failed for [cyan]'{image_tag}'[/cyan].")
                
                full_log = "".join([json.dumps(line) for line in e.build_log])
                result.error_message = f"Build failed with error: {e.msg}\nFull log: {full_log}"
                
                console.print(f"[bold red]Error Details:[/bold red] {result.error_message}")

            finally:
                if image:
                    try:
                        self.client.images.remove(image.id, force=True)
                        console.print(f"🧹 Cleaned up image [cyan]'{image_tag}'[/cyan].")
                    except APIError as e:
                        console.print(f"[yellow]Warning:[/yellow] Could not remove image '{image_tag}'. Error: {e}")
            
            return result
