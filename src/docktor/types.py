from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import DockerInstruction
@dataclass
class Issue:
    rule_id: str
    message: str
    line_number: int
    severity: str = "warning"
    explanation: Optional[str] = None
    fix_suggestion: Optional[str] = None

@dataclass
class OptimizationResult:
    optimized_instructions: List['DockerInstruction'] 
    applied_optimizations: List[str]
