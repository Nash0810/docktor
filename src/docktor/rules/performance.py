from typing import List

from .base import Rule, Issue, DockerInstruction
from ..parser import InstructionType


class CombineRunRule(Rule):
    """
    Rule to check for consecutive RUN commands that can be combined.
    """

    @property
    def id(self) -> str:
        return "PERF001"

    @property
    def description(self) -> str:
        return "Combine consecutive RUN commands to reduce image layers."

    @property
    def explanation(self) -> str:
        return (
            "Each RUN command in a Dockerfile creates a new layer in the Docker image. "
            "Consolidating multiple RUN commands into a single one using '&&' reduces "
            "the number of layers, resulting in a smaller and potentially faster image."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []

        for i in range(len(instructions) - 1):
            current_instruction = instructions[i]
            next_instruction = instructions[i+1]

            # Check if the current and next instructions are both RUN commands
            if (current_instruction.instruction_type == InstructionType.RUN and
                    next_instruction.instruction_type == InstructionType.RUN):
                
                if i > 0 and instructions[i-1].instruction_type == InstructionType.RUN:
                    continue

                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="Multiple consecutive RUN commands can be combined with '&&'.",
                        line_number=current_instruction.line_number,
                        severity="info",
                        explanation=self.explanation,  
                        fix_suggestion="Combine this RUN instruction with the following one(s)."
                    )
                )
        return issues