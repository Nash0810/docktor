
from dataclasses import dataclass
from typing import List, Optional

from .parser import DockerInstruction
from .rules.base import Rule

from .rules import best_practices
from .types import Issue
from .rules import performance
from .rules import security
from .rules import registry

@dataclass
class Issue:
    """A dataclass to represent a single issue found in a Dockerfile."""
    rule_id: str
    message: str
    line_number: int
    severity: str = "warning"  
    explanation: Optional[str] = None
    fix_suggestion: Optional[str] = None

class Analyzer:
    """
    The main analysis engine. It loads rules, runs them against parsed
    Dockerfile instructions, and collects the issues.
    """
    def __init__(self) -> None:
        self._rules: List[Rule] = self._load_rules()

    def _load_rules(self) -> List[Rule]:
        return [subclass() for subclass in Rule.__subclasses__()]

    def run(self, instructions: List[DockerInstruction]) -> List[Issue]:
 
        all_issues: List[Issue] = []
        print(f"🔬 Running {len(self._rules)} rules...")
        for rule in self._rules:
            issues = rule.check(instructions)
            if issues:
                all_issues.extend(issues)
        return all_issues