from docktor.parser import DockerfileParser, InstructionType


def test_parse_simple_dockerfile():

    dockerfile_content = """
# This is a comment
FROM python:3.11-slim
RUN pip install poetry
"""
    
    
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)

    assert len(instructions) == 3

    assert instructions[0].instruction_type == InstructionType.COMMENT
    assert instructions[0].value == "This is a comment"
    assert instructions[0].line_number == 2 

    assert instructions[1].instruction_type == InstructionType.FROM
    assert instructions[1].value == "python:3.11-slim"
    assert instructions[1].line_number == 3

    assert instructions[2].instruction_type == InstructionType.RUN
    assert instructions[2].value == "pip install poetry"
    assert instructions[2].line_number == 4


def test_parse_multiline_run_command():
    
    dockerfile_content = """
FROM debian
RUN apt-get update && \\
    apt-get install -y git \\
    && echo "hello"
"""

    
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)

    assert len(instructions) == 2

    run_instruction = None
    for inst in instructions:
        if inst.instruction_type == InstructionType.RUN:
            run_instruction = inst
            break
    
    # Assert that a RUN instruction was actually found
    assert run_instruction is not None
    
    # Assert that its line number points to the start of the multi-line block
    assert run_instruction.line_number == 3

    # Assert that the value is the correctly combined string
    expected_value = 'apt-get update && apt-get install -y git && echo "hello"'

    assert run_instruction.value.replace(" ", "") == expected_value.replace(" ", "")
