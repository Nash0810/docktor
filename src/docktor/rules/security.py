from typing import List

from .base import Rule, Issue, DockerInstruction
from ..parser import InstructionType


class AddInsteadOfCopyRule(Rule):

    @property
    def id(self) -> str:
        return "SEC001"

    @property
    def description(self) -> str:
        return "Use COPY instead of ADD unless you need ADD's specific features."

    @property
    def explanation(self) -> str:
        return (
            "The 'ADD' instruction has magic features like remote URL downloads and "
            "automatic tarball extraction. This can introduce security vulnerabilities "
            "if the source is compromised. 'COPY' is more transparent and safer as it "
            "only copies local files."
        )


    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.ADD:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="ADD is used. Prefer COPY for clarity and security.",
                        line_number=instruction.line_number,
                        severity="warning",
                        explanation=self.explanation,  # <-- Pass the explanation
                        fix_suggestion="Replace 'ADD' with 'COPY' if you are only copying local files."
                    )
                )

        return issues