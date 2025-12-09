<!-- Project Title -->
<h1 align="center">🐳 Docktor</h1>
<p align="center">
  <strong>A Dockerfile Linter and Optimizer Built on AST Parsing</strong><br>
  Static analysis and transformation of Dockerfile instructions using structured syntax trees.
</p>

<!-- Badges -->
<p align="center">
  <a href="https://pypi.org/project/docktor/"><img src="https://img.shields.io/pypi/v/docktor.svg" alt="PyPI version"></a>
  <a href="https://github.com/Nash0810/docktor/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://github.com/Nash0810/docktor/actions"><img src="https://github.com/Nash0810/docktor/workflows/CI/badge.svg" alt="Build Status"></a>
  <a href="https://pypi.org/project/docktor/"><img src="https://img.shields.io/pypi/pyversions/docktor" alt="Python Versions"></a>
</p>

## Overview

Docktor is a static analysis tool for Dockerfiles that uses **Abstract Syntax Tree (AST) parsing** to identify issues and apply optimizations. Unlike regex-based approaches, Docktor constructs a structured representation of Dockerfile instructions, enabling reliable pattern matching and safe transformations.

The project demonstrates end-to-end architecture design: recursive descent parsing → plugin-based rule engine → automated optimization → Docker SDK benchmarking.

## ✨ Key Technical Features

- **AST-Based Parsing** – Recursive descent parser with multi-line continuation handling (`\`), not regex-based pattern matching
- **Extensible Rule Engine** – Plugin architecture using Python decorators for linting rules (best practices, performance, security, registry checks)
- **Safe Optimization Pipeline** – 8-stage transformation pipeline with isolated optimization passes and change tracking
- **Benchmarking Harness** – Direct Docker SDK integration to measure real build metrics (image size, layer count, build duration) in isolated temp environments
- **Structured Output** – Both human-readable (Rich) and machine-readable (JSON) formats for CI/CD integration

## 📦 What's New in v0.2.0

- **Registry Rule (REG001)** – Docker Hub API integration to detect newer patch versions of base images
- **GitHub Actions Composite Action** – Pre-built workflow for CI/CD automation
- **Improved CLI** – Encoding auto-detection (chardet) for non-UTF-8 Dockerfiles, better error handling

## 🚀 Quick Start

### Requirements

- Python 3.8+
- Docker (for benchmarking feature; linting works without it)

### Installation

```bash
pip install docktor-py
```

### Usage

#### 1. Lint a Dockerfile

Run static analysis against 21 rules:

```bash
docktor lint Dockerfile
```

#### 2. View Detailed Explanations

Each rule includes a structured explanation of the issue and suggested fix:

```bash
docktor lint Dockerfile --explain
```

#### 3. Generate Optimized Dockerfile

Apply automated transformations (RUN merging, layer reduction, cache cleanup):

```bash
# View transformations with change summary
docktor optimize Dockerfile

# Output clean Dockerfile without pretty printing (for piping)
docktor optimize Dockerfile --raw > Dockerfile.optimized
```

#### 4. Benchmark Optimization Impact

Build both images in isolated temp environments and compare metrics:

```bash
# Must run from directory containing all COPY/ADD source files
docktor benchmark Dockerfile Dockerfile.optimized
```

#### 5. Export Results as JSON

For CI/CD integration:

```bash
docktor lint Dockerfile --format json
```

## ⚙️ Linting Rules Reference

Docktor enforces **20 rules** across four categories. Each rule is implemented as a plugin with explicit checks against the AST:

### Best Practice Rules (BP)

| Rule ID | Description                              | Auto-Optimized? |
| ------- | ---------------------------------------- | --------------- |
| BP001   | FROM uses `:latest` or no tag            | Yes             |
| BP002   | EXPOSE present without HEALTHCHECK       | No              |
| BP003   | EXPOSE missing `/tcp` or `/udp` protocol | Yes             |
| BP004   | LABEL instruction missing for metadata   | No              |
| BP005   | RUN command used in scratch image        | No (error)      |
| BP006   | COPY --from refers to non-existent stage | No (error)      |
| BP007   | CMD/ENTRYPOINT uses shell form           | No              |
| BP008   | WORKDIR path is not absolute             | No              |
| BP009   | apt-get install missing apt-get update   | No (error)      |

### Performance Rules (PERF)

| Rule ID | Description                                  | Auto-Optimized? |
| ------- | -------------------------------------------- | --------------- |
| PERF001 | Consecutive RUN commands can be merged       | Yes             |
| PERF002 | apt-get install missing cache cleanup        | Yes             |
| PERF003 | Broad COPY before dependency install         | No              |
| PERF004 | Build-time packages installed in final image | No              |
| PERF005 | Unsafe apt-get upgrade command used          | No              |
| PERF006 | Broad `COPY . .` pattern used                | No              |
| PERF007 | Redundant apt-get update command             | No              |

### Security Rules (SEC)

| Rule ID | Description                            | Auto-Optimized? |
| ------- | -------------------------------------- | --------------- |
| SEC001  | ADD used instead of COPY               | Yes             |
| SEC002  | Container runs as root user            | No              |
| SEC003  | Potential secrets in ENV variables     | No              |
| SEC004  | COPY missing --chown for non-root user | No              |

### Registry Rules (REG) - _New in v0.2.0_

| Rule ID | Description                                 | Auto-Optimized? |
| ------- | ------------------------------------------- | --------------- |
| REG001  | Newer patch version available on Docker Hub | No              |

## How It Works

### 1. Parsing Phase

The `DockerfileParser` uses recursive descent with regex anchors to tokenize and structure Dockerfile content:

- Strips and normalizes lines
- Handles line continuations (backslash escape)
- Constructs `DockerInstruction` objects with metadata (line number, type, value, image/tag/alias)
- Tolerates malformed input gracefully

### 2. Analysis Phase

The `Analyzer` loads all rule implementations as plugins (via `Rule.__subclasses__()`) and runs them:

- Each rule performs AST traversal over instructions
- Rules check for specific patterns (e.g., `instruction.instruction_type == InstructionType.RUN`)
- Issues are collected with severity, explanation, and fix suggestions

### 3. Optimization Phase

The `DockerfileOptimizer` applies 8 sequential transformations:

1. **RUN Merging** – Combines consecutive RUN commands with `&&`
2. **FROM Pinning** – Tags untagged base images with `:latest`
3. **apt-get Cache Cleanup** – Appends `rm -rf /var/lib/apt/lists/*`
4. **EXPOSE Protocol** – Adds `/tcp` suffix to port numbers
5. **ADD → COPY** – Security-motivated instruction replacement
6. **Metadata Combining** – Merges consecutive LABEL/ENV/ARG instructions
7. **sudo Removal** – Strips unnecessary sudo from RUN commands
8. **apt-get Update** – Prepends `apt-get update` where required

Each pass is isolated and order-dependent. Changes are tracked and reported.

### 4. Benchmarking Phase

The `DockerBenchmarker` uses Docker SDK to build images in ephemeral containers:

- Creates temp directory with Dockerfile
- Calls `docker.client.api.build()` to measure build duration
- Captures final image size and layer count from image metadata
- Cleans up images after measurement
- Computes % improvement across metrics

**Scope Note:** Benchmarking metrics are measured in **local test environments** (validated on 8GB RAM, Docker daemon on host). No multi-machine or cluster testing.

## CI/CD Integration

### GitHub Actions

Automate linting in workflows:

```yaml
name: Dockerfile Quality Check
on: [push, pull_request]

jobs:
  docktor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Docktor Linter
        uses: nash0810/docktor@v0.2.0
        with:
          dockerfile: "./Dockerfile"
          explain: "true"
```

**Inputs:**

- `dockerfile` (optional, default: `Dockerfile`)
- `explain` (optional, default: `false`)
- `format` (optional, default: `text`, accepts `json`)

### Other Platforms

Any CI/CD system supporting Python and Docker:

```bash
pip install docktor-py
docktor lint Dockerfile --format json
```

---

## Benchmarking Methodology

The `docktor benchmark` command measures real Docker builds using the Docker SDK:

- Builds each Dockerfile in an isolated temporary directory
- Extracts image size (bytes), layer count, and build duration from Docker metadata
- Computes percentage improvements (`(original - optimized) / original * 100`)
- Cleans up images after measurement

**Requirements:**

- Docker daemon must be running
- Must run from directory containing all source files referenced in COPY/ADD instructions
- Builds are not cached between runs (fresh builds each time)

**Tested Scenario:** Reduced image size by ~40% in sample Python/Node.js multi-stage build scenarios with aggressive layer merging.

---

## Development

Clone and install in editable mode:

```bash
git clone https://github.com/Nash0810/docktor.git
cd docktor
pip install -e ".[dev]"
pytest
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
