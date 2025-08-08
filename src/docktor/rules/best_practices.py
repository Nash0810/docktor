from typing import List

from .base import Rule, Issue, DockerInstruction
from ..parser import InstructionType


class PinnedVersionRule(Rule):
    """
    Rule to check for unpinned base image versions (i.e., 'latest' tag or no tag).
    """

    @property
    def id(self) -> str:
        return "BP001"

    @property
    def description(self) -> str:
        return "Base image should have a pinned version, not 'latest' or no tag."

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.FROM:
                image_name = instruction.value
                # Check if it uses the 'latest' tag or has no tag at all
                if ":" not in image_name or image_name.endswith(":latest"):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Base image '{image_name}' uses an unpinned version.",
                            line_number=instruction.line_number,
                            severity="warning",
                            fix_suggestion=f"Pin the image to a specific version. E.g., '{image_name.split(':')[0]}:3.11-slim'."
                        )
                    )
        return issues