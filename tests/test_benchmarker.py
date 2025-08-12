import pytest
import docker
from docktor.benchmarker import DockerBenchmarker

DOCKER_UNAVAILABLE = False
try:
    docker.from_env().ping()
except Exception:
    DOCKER_UNAVAILABLE = True


@pytest.mark.skipif(DOCKER_UNAVAILABLE, reason="Docker daemon is not running or accessible.")
def test_benchmarker_builds_image_successfully():
    """
    Integration test to verify that the benchmarker can build a simple
    image and return valid metrics.
    """
    # 1. Arrange: Define a simple, valid Dockerfile
    dockerfile_content = "FROM alpine\nRUN echo 'hello'"
    
    # 2. Act: Run the benchmark
    benchmarker = DockerBenchmarker()
    result = benchmarker.benchmark(dockerfile_content, "docktor-test-image")

    # 3. Assert: Check that the results are realistic
 
    assert result.error_message is None
    assert result.image_size_mb > 0
    assert result.layer_count > 0
    assert result.build_time_seconds >= 0