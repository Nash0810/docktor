from src.docktor.parser import DockerfileParser, InstructionType
from src.docktor.optimizer import DockerfileOptimizer


def test_optimizer_combines_run_commands():

    # 1. Arrange: Define input with consecutive RUNs
    dockerfile_content = """
FROM python:3.11-slim
RUN apt-get update
RUN apt-get install -y git
COPY . /app
"""
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)

    # 2. Act: Run the optimizer
    optimizer = DockerfileOptimizer()
    result = optimizer.optimize(instructions)

    # 3. Assert: Check the optimization results
    # Check that one optimization was applied
    assert len(result.applied_optimizations) == 1
    assert "Combined 2 RUN commands" in result.applied_optimizations[0]

    # Check that the number of instructions was reduced
    assert len(result.optimized_instructions) < len(instructions)
    assert len(result.optimized_instructions) == 3 # FROM, combined RUN, COPY

    # Check that there is now only one RUN instruction
    run_instructions = [
        inst for inst in result.optimized_instructions 
        if inst.instruction_type == InstructionType.RUN
    ]
    assert len(run_instructions) == 1

    # Check that the value of the combined RUN is correct
    combined_run = run_instructions[0]
    assert "apt-get update" in combined_run.value
    assert "&&" in combined_run.value
    assert "apt-get install -y git" in combined_run.value