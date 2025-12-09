# Docktor Architecture

This document explains the design decisions, data flow, and component interactions in Docktor.

## Philosophy

Docktor demonstrates **pragmatic engineering trade-offs**:

- **Clarity over speed:** AST parsing is slower than regex but enables reliable transformations
- **Extensibility over minimalism:** Plugin architecture adds setup overhead but allows custom rules
- **Safety over aggression:** Optimization pipeline is conservative (no unsafe transformations like stripping HEALTHCHECK)

## System Overview

```
Input (Dockerfile)
    ↓
Parser (DockerfileParser)
    ↓
Instructions (List[DockerInstruction])
    ↓
[Analyzer] ─→ Issues
    ↓
[Optimizer] ─→ Optimized Instructions
    ↓
[Benchmarker] ─→ Metrics (size, time, layers)
    ↓
Output (JSON or Rich Table)
```

## Core Components

### 1. Parser (`src/docktor/parser.py`)

**Purpose:** Convert raw Dockerfile text into a structured AST.

**Key Classes:**

- `InstructionType` (Enum) – 18 Docker instruction types
- `DockerInstruction` (dataclass) – Parsed representation with metadata
- `DockerfileParser` – Recursive descent parser

**Design Decisions:**

- **Line Continuation Handling:** Buffers lines ending with `\` before tokenizing
- **Regex Only for FROM:** Uses regex anchors only to extract image/tag/alias from FROM values
- **Tolerates Malformed Input:** Missing instructions default to `UNKNOWN` type
- **Preserves Original:** Stores both parsed value and original line for lossless round-trip

**Example Flow:**

```python
input = "FROM python:3.11\nRUN apt-get update \\\n    && apt-get install -y curl"
instructions = parser.parse(input)
# Result:
# [
#   DockerInstruction(line=1, type=FROM, value="python:3.11", image="python", tag="3.11"),
#   DockerInstruction(line=2, type=RUN, value="apt-get update && apt-get install -y curl")
# ]
```

**Trade-offs:**

- ✅ Handles multi-line instructions correctly
- ✅ Preserves line numbers for error reporting
- ❌ Slower than single-pass regex (extra string operations per line)

---

### 2. Analyzer (`src/docktor/analyzer.py`)

**Purpose:** Load rules as plugins and run linting checks.

**Key Classes:**

- `Rule` (ABC) – Base class with `id`, `description`, `explanation`, `check()`
- `Analyzer` – Rule loader and orchestrator
- `Issue` – Result dataclass (rule_id, message, line_number, severity, explanation, fix_suggestion)

**Rule Plugin System:**

```python
# Automatic discovery via subclasses
self._rules: List[Rule] = [subclass() for subclass in Rule.__subclasses__()]
```

**Execution Flow:**

1. Load all Rule subclasses (best_practices, performance, security, registry)
2. For each rule, call `rule.check(instructions)`
3. Collect issues with severity levels (error, warning, info)
4. Return sorted list

**Rule Categories:**

| Category      | Count | Example Rules                                        |
| ------------- | ----- | ---------------------------------------------------- |
| Best Practice | 9     | BP001 (unpinned versions), BP002 (no HEALTHCHECK)    |
| Performance   | 7     | PERF001 (mergeable RUN), PERF002 (apt cache cleanup) |
| Security      | 4     | SEC001 (ADD vs COPY), SEC002 (root user)             |
| Registry      | 1     | REG001 (Docker Hub version check)                    |

**Trade-offs:**

- ✅ Extensible: Add new rules without modifying Analyzer
- ✅ Isolated: Each rule is independent (no cross-rule state)
- ❌ No pruning: All rules run even if not requested
- ❌ No caching: Rules recompute patterns on each invocation

---

### 3. Optimizer (`src/docktor/optimizer.py`)

**Purpose:** Apply safe, deterministic transformations to reduce image size and complexity.

**Architecture: Sequential Pipeline**

```
Instructions
    ↓ (Pass 1: Combine RUN commands)
    ↓ (Pass 2: Pin untagged FROM)
    ↓ (Pass 3: Add apt-get cleanup)
    ↓ (Pass 4: Add EXPOSE protocol)
    ↓ (Pass 5: Replace ADD with COPY)
    ↓ (Pass 6: Combine metadata instructions)
    ↓ (Pass 7: Remove unnecessary sudo)
    ↓ (Pass 8: Prepend apt-get update)
Optimized Instructions + Change Log
```

**Each Pass:**

- Takes list of instructions
- Returns (new list, list of changes applied)
- **Order matters:** Pass 1 must run before Pass 3 (apt cleanup depends on RUN structure)

**Example: RUN Merging (Pass 1)**

```python
Input:
  RUN apt-get update
  RUN apt-get install -y curl
  COPY app /app

Output:
  RUN apt-get update && apt-get install -y curl
  COPY app /app

Change: "Combined 2 RUN commands starting at line 1"
```

**Design Decisions:**

| Pass                | Type            | Risk Level | Rationale                                                      |
| ------------------- | --------------- | ---------- | -------------------------------------------------------------- |
| 1. Combine RUN      | Layer reduction | Low        | Explicitly merges consecutive RUNs                             |
| 2. Pin FROM         | Reproducibility | Low        | Adds `:latest` tag only; doesn't change semantics              |
| 3. apt cleanup      | Size reduction  | Low        | Removes cache dir after install (idempotent)                   |
| 4. EXPOSE protocol  | Clarity         | Very Low   | Adds `/tcp` suffix; Docker defaults to TCP anyway              |
| 5. ADD → COPY       | Security        | Low        | COPY is preferred; ADD only needed for tar extraction          |
| 6. Combine metadata | Layer reduction | Very Low   | ENV/LABEL/ARG can be combined without side effects             |
| 7. Remove sudo      | Clarity         | Medium     | Assumes container runs as non-root; may break some Dockerfiles |
| 8. apt-get update   | Correctness     | Medium     | Ensures cache is fresh; may be redundant if already present    |

**Trade-offs:**

- ✅ Conservative: Avoids dangerous transformations (e.g., reordering COPY/RUN)
- ✅ Traceable: Each change is logged for audit
- ❌ Opinionated: Cannot disable individual passes
- ❌ Order-dependent: Changing pass order can produce different results

---

### 4. Benchmarker (`src/docktor/benchmarker.py`)

**Purpose:** Build Docker images and measure real metrics.

**Key Classes:**

- `DockerBenchmarker` – Docker SDK wrapper
- `BenchmarkResult` – Metrics dataclass (image_size_mb, layer_count, build_time_seconds, error_message)

**Execution Flow:**

1. Create temp directory
2. Write Dockerfile to temp location
3. Call `docker.client.api.build(path=temp_dir, tag=tag, rm=True, forcerm=True)`
4. Stream build output to console
5. Retrieve image metadata: `image.attrs['Size']` (bytes), `len(image.history())` (layers)
6. Calculate build duration from start_time to end_time
7. Clean up image
8. Return BenchmarkResult

**Example Metrics:**

```
Image Size:      250 MB
Layer Count:     15
Build Time:      8.3 seconds
```

**Design Decisions:**

- **Ephemeral Builds:** Each image is built in a fresh temp dir (no cache reuse)
- **Real Docker:** Uses Docker daemon, not a simulator or mock
- **Size from Image Attrs:** Queries actual layer sizes, not Dockerfile analysis
- **Layer Count from History:** Uses Docker image history (== number of RUN/ADD/COPY/etc. instructions)

**Error Handling:**

```python
try:
    # Build image
except BuildError as e:
    result.error_message = f"Build failed: {e.msg}"
finally:
    # Always clean up image, even on error
    self.client.images.remove(image.id, force=True)
```

**Trade-offs:**

- ✅ Accurate: Measures real Docker builds
- ✅ Observable: Streams build log for debugging
- ❌ Slow: Full Docker builds can take minutes
- ❌ Requires Docker:\*\* Cannot run without Docker daemon
- ❌ Not Cached:\*\* No layer caching between benchmarks (always fresh build)

---

## Data Structures

### DockerInstruction

```python
@dataclass
class DockerInstruction:
    line_number: int              # Original line in Dockerfile
    instruction_type: InstructionType  # FROM, RUN, COPY, etc.
    original: str                 # Original instruction string
    value: str                    # Parsed argument value
    image: Optional[str]          # FROM-specific: image name
    tag: Optional[str]            # FROM-specific: tag
    alias: Optional[str]          # FROM-specific: multi-stage alias (AS)
```

### Issue

```python
@dataclass
class Issue:
    rule_id: str                  # BP001, PERF001, etc.
    message: str                  # Human-readable finding
    line_number: int              # Where in Dockerfile
    severity: str                 # "error", "warning", "info"
    explanation: Optional[str]    # Why this matters
    fix_suggestion: Optional[str] # How to fix
```

### OptimizationResult

```python
@dataclass
class OptimizationResult:
    optimized_instructions: List[DockerInstruction]
    applied_optimizations: List[str]  # Change log
```

### BenchmarkResult

```python
@dataclass
class BenchmarkResult:
    image_tag: str
    image_size_mb: float = 0.0
    layer_count: int = 0
    build_time_seconds: float = 0.0
    error_message: Optional[str] = None
```

---

## CLI Architecture (`src/docktor/cli.py`)

Uses Click framework for command structure:

```
docktor
  ├── lint
  │   ├── --explain       (show detailed issue explanations)
  │   └── --format        (text or json)
  ├── optimize
  │   └── --raw           (skip pretty printing)
  └── benchmark
      ├── original_dockerfile
      └── optimized_dockerfile
```

**Shared Utilities:**

- `read_file_with_autodetect()` – Uses chardet to detect encoding (not ASCII-only)
- `display_issues()` – Renders Issue list as Rich table or JSON
- `console` – Rich Console for styled output

---

## Extension Points

### Add a New Linting Rule

1. Create class in `src/docktor/rules/{category}.py`:

```python
from .base import Rule
from ..types import Issue

class MyCustomRule(Rule):
    @property
    def id(self) -> str:
        return "CUSTOM001"

    @property
    def description(self) -> str:
        return "Description of the rule"

    @property
    def explanation(self) -> str:
        return "Why this matters and how to fix it"

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues = []
        for inst in instructions:
            if <condition>:
                issues.append(Issue(
                    rule_id=self.id,
                    message="...",
                    line_number=inst.line_number,
                    explanation=self.explanation,
                    fix_suggestion="..."
                ))
        return issues
```

2. Analyzer automatically discovers via `Rule.__subclasses__()`

### Add a New Optimization Pass

1. Add method to `DockerfileOptimizer`:

```python
def _my_transformation(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
    new_instructions = []
    changes = []
    for inst in instructions:
        if <condition>:
            new_instructions.append(<transformed>)
            changes.append("Transformation applied at line X")
        else:
            new_instructions.append(inst)
    return new_instructions, changes
```

2. Call in `optimize()` method in correct order

---

## Known Limitations

1. **No Semantic Analysis:** Rules check syntax, not runtime behavior (e.g., cannot verify if a COPY source actually exists)
2. **No Dockerfile Validation:** Invalid instructions are silently passed through
3. **Single-Stage Optimization:** Some optimizations assume single-stage builds
4. **Limited ADD Detection:** Rule SEC001 only checks `instruction.instruction_type == InstructionType.ADD`, not content-based heuristics
5. **No Compose Support:** Only single Dockerfiles, not docker-compose.yml
6. **Docker Hub Rate Limiting:** REG001 may hit rate limits on public Docker Hub API

---

## Testing Strategy

Test files in `tests/`:

- `test_parser.py` – Multi-line continuation, all instruction types
- `test_analyzer.py` – Rule discovery, issue collection
- `test_optimizer.py` – Each optimization pass in isolation
- `test_benchmarker.py` – Docker integration (requires Docker daemon)
- `test_cli.py` – Command structure and output formats

Run tests:

```bash
pytest -v
```

Coverage:

```bash
pytest --cov=src/docktor
```

---

## Performance Characteristics

| Operation              | Time Complexity | Space Complexity | Notes                           |
| ---------------------- | --------------- | ---------------- | ------------------------------- |
| Parse small Dockerfile | O(n)            | O(n)             | Linear scan + buffer            |
| Analyze with 20 rules  | O(20n)          | O(n)             | Rules run independently         |
| Optimize               | O(8n)           | O(n)             | 8 passes, each O(n)             |
| Benchmark              | O(m)            | O(m)             | m = Docker build time (minutes) |

Where n = number of instructions.

---

## Future Considerations

- **Caching:** Cache rule results to avoid recomputation
- **Parallel Rule Execution:** Run independent rules concurrently
- **Custom Rule Loading:** Allow rules from external packages
- **Diff Output:** Show before/after diffs instead of changelogs
- **Multi-Stage Awareness:** Dedicated logic for multi-stage builds
- **Dockerfile Generation:** Create optimized Dockerfile from scratch (not just modify)
