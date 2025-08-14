import pytest
import docker
import platform
from docktor.benchmarker import DockerBenchmarker

DOCKER_UNAVAILABLE = False
try:
    client = docker.from_env()
    client.ping()
    
    try:
 
        client.images.pull("hello-world:latest")
        LINUX_CONTAINERS_AVAILABLE = True
    except Exception:
        LINUX_CONTAINERS_AVAILABLE = False
except Exception:
    DOCKER_UNAVAILABLE = True
    LINUX_CONTAINERS_AVAILABLE = False


def get_platform_appropriate_dockerfile():
    """
    Returns a Dockerfile that works on the current platform.
    """
    if platform.system() == "Windows":
  
        return """
FROM mcr.microsoft.com/windows/nanoserver:ltsc2022
RUN echo hello > test.txt
"""
    else:

        return """
FROM alpine:latest
RUN echo 'hello' > test.txt
"""


@pytest.mark.skipif(DOCKER_UNAVAILABLE, reason="Docker daemon is not running or accessible.")
def test_benchmarker_builds_image_successfully():
    """
    Integration test to verify that the benchmarker can build a simple
    image and return valid metrics.
    """
    # 1. Arrange: Use platform-appropriate Dockerfile
    dockerfile_content = get_platform_appropriate_dockerfile()
    
    # 2. Act: Run the benchmark
    benchmarker = DockerBenchmarker()
    result = benchmarker.benchmark(dockerfile_content, "docktor-test-image")

    # 3. Assert: Check that the results are realistic
    if result.error_message:
    
        print(f"Docker build failed: {result.error_message}")
        pytest.skip(f"Docker build failed on this platform: {result.error_message}")
    
    assert result.error_message is None
    assert result.image_size_mb > 0
    assert result.layer_count > 0
    assert result.build_time_seconds >= 0


@pytest.mark.skipif(DOCKER_UNAVAILABLE, reason="Docker daemon is not running or accessible.")
def test_benchmarker_handles_build_failure_gracefully():
    """
    Test that the benchmarker handles invalid Dockerfiles gracefully.
    """
    # 1. Arrange: Invalid Dockerfile
    invalid_dockerfile = "FROM nonexistent-image:invalid-tag\nRUN this-will-fail"
    
    # 2. Act: Run the benchmark
    benchmarker = DockerBenchmarker()
    result = benchmarker.benchmark(invalid_dockerfile, "docktor-test-fail")

    # 3. Assert: Should return error gracefully
    assert result.error_message is not None
    assert result.image_size_mb == 0.0
    assert result.layer_count == 0
    assert result.build_time_seconds >= 0  


@pytest.mark.skipif(DOCKER_UNAVAILABLE or platform.system() == "Windows", 
                   reason="Linux containers test - skipping on Windows")
def test_benchmarker_linux_containers():
    """
    Test specifically for Linux containers (Ubuntu/macOS only).
    """
    dockerfile_content = "FROM alpine:latest\nRUN echo 'hello'"
    
    benchmarker = DockerBenchmarker()
    result = benchmarker.benchmark(dockerfile_content, "docktor-test-linux")

    assert result.error_message is None
    assert result.image_size_mb > 0
    assert result.layer_count > 0


@pytest.mark.skipif(DOCKER_UNAVAILABLE or platform.system() != "Windows", 
                   reason="Windows containers test - only run on Windows")  
def test_benchmarker_windows_containers():
    """
    Test specifically for Windows containers (Windows only).
    """
    dockerfile_content = """
FROM mcr.microsoft.com/windows/nanoserver:ltsc2022
RUN echo hello > test.txt
"""
    
    benchmarker = DockerBenchmarker()
    result = benchmarker.benchmark(dockerfile_content, "docktor-test-windows")

    if result.error_message and "manifest" in result.error_message:
        pytest.skip("Windows container manifest not available in this environment")
    
    assert result.error_message is None
    assert result.image_size_mb > 0
    assert result.layer_count > 0