import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class InstructionType(Enum):
    """Enumeration for all supported Dockerfile instructions."""
    FROM = "FROM"
    RUN = "RUN"
    CMD = "CMD"
    LABEL = "LABEL"
    EXPOSE = "EXPOSE"
    ENV = "ENV"
    ADD = "ADD"
    COPY = "COPY"
    ENTRYPOINT = "ENTRYPOINT"
    VOLUME = "VOLUME"
    USER = "USER"
    WORKDIR = "WORKDIR"
    ARG = "ARG"
    ONBUILD = "ONBUILD"
    STOPSIGNAL = "STOPSIGNAL"
    HEALTHCHECK = "HEALTHCHECK"
    SHELL = "SHELL"
    COMMENT = "#"
    UNKNOWN = "UNKNOWN"

@dataclass
class DockerInstruction:
    """A structured representation of a single Dockerfile instruction."""
    line_number: int
    instruction_type: InstructionType
    original: str
    value: str  
    
    image: Optional[str] = None
    tag: Optional[str] = None
    alias: Optional[str] = None

class DockerfileParser:
    """Parses a Dockerfile's content into a list of structured instructions."""
    FROM_REGEX = re.compile(
        r"^(?P<image>[^:\s]+)(?::(?P<tag>[^\s]+))?(?:\s+as\s+(?P<alias>\S+))?$",
        re.IGNORECASE
    )

    def parse(self, dockerfile_content: str) -> List[DockerInstruction]:
        """
        Parses the full content of a Dockerfile.
        """
        instructions: List[DockerInstruction] = []
        lines = dockerfile_content.splitlines()
        instruction_buffer: List[str] = []
        start_line_number: Optional[int] = None

        for i, line in enumerate(lines):
            line_number = i + 1
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if stripped_line.endswith('\\'):
                if not instruction_buffer:
                    start_line_number = line_number
                instruction_buffer.append(stripped_line[:-1].strip())
                continue
            if instruction_buffer:
                instruction_buffer.append(stripped_line)
                full_instruction_line = " ".join(instruction_buffer)
                instruction_buffer = []
                instructions.append(self._parse_line(
                    full_instruction_line,
                    start_line_number or line_number
                ))
                continue
            instructions.append(self._parse_line(stripped_line, line_number))
        return instructions

    def _parse_line(self, line: str, line_number: int) -> DockerInstruction:
        """Parses a single (potentially merged) line into a DockerInstruction."""
        original_line = line
        
        if line.startswith('#'):
            return DockerInstruction(
                line_number=line_number,
                instruction_type=InstructionType.COMMENT,
                original=original_line,
                value=line[1:].strip()
            )

        parts = line.split(maxsplit=1)
        instruction_str = parts[0].upper()
        value = parts[1] if len(parts) > 1 else ""

        try:
            instruction_type = InstructionType(instruction_str)
        except ValueError:
            instruction_type = InstructionType.UNKNOWN

        instruction = DockerInstruction(
            line_number=line_number,
            instruction_type=instruction_type,
            original=original_line,
            value=value
        )

        if instruction.instruction_type == InstructionType.FROM:
            match = self.FROM_REGEX.match(instruction.value)
            if match:
                instruction.image = match.group("image")
                instruction.tag = match.group("tag")
                instruction.alias = match.group("alias")

        return instruction
