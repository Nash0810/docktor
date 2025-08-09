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

@dataclass
class BenchmarkResult:

    image_tag: str
    image_size_mb: float = 0.0
    layer_count: int = 0
    build_time_seconds: float = 0.0
    error_message: Optional[str] = None