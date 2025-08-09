import time
import tempfile
import pathlib
import docker
from docker.errors import BuildError, APIError

from .types import BenchmarkResult

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

            try:
       
                start_time = time.monotonic()
                print(f"Building image '{image_tag}'... (this may take a moment)")
                
                image, build_logs = self.client.images.build(
                    path=str(temp_dir),
                    tag=image_tag,
                    rm=True,  
                    forcerm=True
                )
                end_time = time.monotonic()
                result.build_time_seconds = round(end_time - start_time, 2)
                
            
                result.image_size_mb = round(image.attrs['Size'] / (1024 * 1024), 2)
     
                result.layer_count = len(image.history())

                print(f"✅ Build successful for '{image_tag}'.")

            except BuildError as e:
                # If the Docker build fails, record the error.
                print(f"❌ Build failed for '{image_tag}'.")
                result.error_message = str(e)
            
            finally:
                if image:
                    try:
                        self.client.images.remove(image.id, force=True)
                        print(f"🧹 Cleaned up image '{image_tag}'.")
                    except APIError as e:
                        print(f"Could not remove image '{image_tag}'. Error: {e}")
            
            return result