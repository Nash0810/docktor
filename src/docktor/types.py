from dataclasses import dataclass
from typing import Optional

@dataclass
class Issue:
    rule_id: str
    message: str
    line_number: int
    severity: str = "warning"
    explanation: Optional[str] = None
    fix_suggestion: Optional[str] = None