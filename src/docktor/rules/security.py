from docktor.rules.base import Rule
from docktor.analyzer import Issue
from docktor.parser import DockerInstruction
from typing import List

class PinnedBaseImageRule(Rule):
    id = "SEC001"
    description = "Base images should be pinned to specific versions"

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues = []
        for instr in instructions:
            if instr.type.name == "FROM" and 'latest' in ' '.join(instr.arguments).lower():
                issues.append(Issue(
                    rule_id=self.id,
                    severity="warning",
                    line_number=instr.line_number,
                    message=f"Base image is not pinned: {' '.join(instr.arguments)}",
                    explanation="Unpinned base images can lead to non-reproducible builds.",
                    fix_suggestion="Use a specific tag like python:3.8-slim",
                    fix_confidence=0.9
                ))
        return issues
