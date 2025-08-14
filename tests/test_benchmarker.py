import pytest
import docker
from docktor.benchmarker import DockerBenchmarker

DOCKER_UNAVAILABLE = False
try:

    client = docker.from_env(timeout=5)
    client.ping()
except Exception:
    DOCKER_UNAVAILABLE = True

@pytest.mark.skipif(DOCKER_UNAVAILABLE, reason="Docker daemon is not running or accessible.")
def test_benchmarker_builds_image_successfully():
    """
    Integration test to verify that the benchmarker can build a simple
    image and return valid metrics.
    """
    # 1. Arrange: Use a multi-platform image that works on both Linux and Windows.
    dockerfile_content = "FROM hello-world"
    
    # 2. Act: Run the benchmark
    benchmarker = DockerBenchmarker()
    # Use a unique tag to avoid conflicts in CI runners
    result = benchmarker.benchmark(dockerfile_content, "docktor-test-image-ci")

    # 3. Assert: Check that the results are realistic
    assert result.error_message is None, f"Benchmark failed with an unexpected error: {result.error_message}"
    assert result.image_size_mb > 0
    assert result.layer_count > 0
    assert result.build_time_seconds >= 0
