from docktor.parser import DockerfileParser, InstructionType
from docktor.optimizer import DockerfileOptimizer


def test_optimizer_combines_run_and_adds_cleanup():
    """
    Tests that the optimizer correctly merges consecutive RUN commands
    AND adds the apt-get cleanup.
    """
    # Arrange: Define input with consecutive RUNs that need cleanup
    dockerfile_content = """
FROM python:3.11-slim
RUN apt-get update
RUN apt-get install -y git
COPY . /app
"""
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)

    # Act: Run the optimizer
    optimizer = DockerfileOptimizer()
    result = optimizer.optimize(instructions)

    # Assert: Check the optimization results
    # We now expect TWO optimizations to be applied
    assert len(result.applied_optimizations) == 2
    assert any("Combined 2 RUN commands" in change for change in result.applied_optimizations)
    assert any("Appended apt-get cache cleanup" in change for change in result.applied_optimizations)

    # Find the single, combined RUN instruction
    run_instructions = [
        inst for inst in result.optimized_instructions
        if inst.instruction_type == InstructionType.RUN
    ]
    assert len(run_instructions) == 1
    combined_run = run_instructions[0]

    # Check that the final command has both the install and the cleanup
    assert "apt-get install -y git" in combined_run.value
    assert "rm -rf /var/lib/apt/lists/*" in combined_run.value


def test_optimizer_replaces_add_with_copy():
    """
    Tests that the optimizer correctly replaces ADD with COPY.
    """
    # 1. Arrange: Define input with an ADD instruction
    dockerfile_content = "FROM alpine\nADD . /app"
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)

    # 2. Act: Run the optimizer
    optimizer = DockerfileOptimizer()
    result = optimizer.optimize(instructions)

    # 3. Assert: Check the optimization results
    # Check that the specific optimization was applied
    assert any("Replaced 'ADD' with 'COPY'" in change for change in result.applied_optimizations)

    # Check that there are no ADD instructions left
    has_add = any(inst.instruction_type == InstructionType.ADD for inst in result.optimized_instructions)
    assert not has_add, "Optimizer failed to remove ADD instruction."

    # Check that a COPY instruction now exists
    has_copy = any(inst.instruction_type == InstructionType.COPY for inst in result.optimized_instructions)
    assert has_copy, "Optimizer failed to add COPY instruction."


def test_optimizer_combines_metadata():
    """
    Tests that the optimizer correctly combines consecutive ENV and LABEL instructions.
    """
    # 1. Arrange: Define input with consecutive metadata and an untagged image
    dockerfile_content = """
FROM alpine
ENV APP_VERSION="1.2.3"
ENV APP_PORT="8080"
RUN echo "hello"
LABEL maintainer="test"
LABEL version="1.0"
"""
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)

    # 2. Act: Run the optimizer
    optimizer = DockerfileOptimizer()
    result = optimizer.optimize(instructions)

    # 3. Assert: Check the optimization results

    assert len(result.applied_optimizations) == 3

    assert any("Pinned untagged base image 'alpine'" in change for change in result.applied_optimizations)
    assert any("Combined 2 consecutive 'ENV' instructions" in change for change in result.applied_optimizations)
    assert any("Combined 2 consecutive 'LABEL' instructions" in change for change in result.applied_optimizations)

    
    assert len(result.optimized_instructions) == 4

    
    env_instructions = [inst for inst in result.optimized_instructions if inst.instruction_type == InstructionType.ENV]
    assert len(env_instructions) == 1
    assert 'APP_VERSION="1.2.3"' in env_instructions[0].value
    assert 'APP_PORT="8080"' in env_instructions[0].value



def test_optimizer_removes_unnecessary_sudo():
    """
    Tests that the optimizer correctly removes 'sudo' from RUN commands.
    """
    # 1. Arrange: Define input with 'sudo'
    dockerfile_content = "FROM alpine\nRUN sudo apk update && sudo apk add git"
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)

    # 2. Act: Run the optimizer
    optimizer = DockerfileOptimizer()
    result = optimizer.optimize(instructions)

    # 3. Assert: Check the optimization results

    assert len(result.applied_optimizations) == 2
    assert any("Removed unnecessary 'sudo'" in change for change in result.applied_optimizations)

    # Find the RUN instruction
    run_instruction = next(inst for inst in result.optimized_instructions if inst.instruction_type == InstructionType.RUN)
    
    # Check that 'sudo' is no longer in the command
    assert "sudo" not in run_instruction.value