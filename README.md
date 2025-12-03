<!-- Project Title -->
<h1 align="center">🐳 Docktor</h1>
<p align="center">
  <strong>A Smart Dockerfile Linter & Optimizer</strong><br>
  Build smaller, faster, and more secure Docker images with ease.
</p>

<!-- Badges -->
<p align="center">
  <a href="https://pypi.org/project/docktor/"><img src="https://img.shields.io/pypi/v/docktor.svg" alt="PyPI version"></a>
  <a href="https://github.com/Nash0810/docktor/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://github.com/Nash0810/docktor/actions"><img src="https://github.com/Nash0810/docktor/workflows/CI/badge.svg" alt="Build Status"></a>
  <a href="https://pypi.org/project/docktor/"><img src="https://img.shields.io/pypi/pyversions/docktor" alt="Python Versions"></a>
</p>

## ✨ Features

- **Comprehensive Linter** – Checks against 21 rules for performance, security, and best practices.
- **Intelligent Optimizer** – Combines `RUN` commands, cleans up apt-get cache, replaces `ADD` with `COPY`, etc.
- **Educational Explanations** – Understand _why_ a suggestion is made.
- **Empirical Benchmarking** – See image size, build time, and layer count improvements.
- **CI/CD Friendly** – Output in human-readable tables (Rich) or machine-readable JSON.
- **Registry Awareness** – Detects newer patch versions on Docker Hub (REG001).

## 📦 What's New in v0.2.0

- ✨ **Registry Rule (REG001)** – Automatically checks Docker Hub for newer patch versions of base images
- 🚀 **GitHub Actions Integration** – Official composite action for CI/CD workflows
- 📖 **Enhanced Documentation** – Comprehensive guides for all use cases
- 🔧 **Improved CLI** – Better error handling and output formatting

## 🚀 Quick Start

### Requirements

- **Python** 3.8 or higher
- **Docker** (for linting and benchmarking features)

### Installation

Install Docktor from PyPI:

```bash
pip install docktor-py
```

### Usage

#### 1. Lint a Dockerfile

Analyze your Dockerfile against 21 best practice rules:

```bash
docktor lint Dockerfile
```

#### 2. Get Detailed Explanations

Understand why each issue matters:

```bash
docktor lint Dockerfile --explain
```

#### 3. Automatically Optimize

Generate an optimized version of your Dockerfile:

```bash
# View optimizations in a pretty format
docktor optimize Dockerfile

# Output raw Dockerfile (copy-pasteable)
docktor optimize Dockerfile --raw

# Save optimized Dockerfile
docktor optimize Dockerfile --raw > Dockerfile.optimized
```

#### 4. Benchmark Your Changes

Compare image metrics before and after optimization:

```bash
# Must run from directory containing all COPY/ADD source files
docktor benchmark Dockerfile Dockerfile.optimized
```

#### 5. Output as JSON

Export results for CI/CD integration:

```bash
docktor lint Dockerfile --format json
```

## ⚙️ Implemented Rules

Docktor enforces **21 rules** across four categories:

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

## 🔌 CI/CD Integration

### GitHub Actions

Automate Dockerfile linting in your GitHub workflows:

```yaml
name: Docker Quality Check

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

**Action Inputs:**

- `dockerfile` (optional, default: `Dockerfile`) – Path to the Dockerfile to lint
- `explain` (optional, default: `false`) – Show detailed explanations for each issue
- `format` (optional, default: `text`) – Output format: `text` or `json`

### Local Development

Run Docktor locally before pushing:

```bash
# Lint your Dockerfile
docktor lint Dockerfile

# Get detailed explanations
docktor lint Dockerfile --explain

# Optimize and save
docktor optimize Dockerfile --raw > Dockerfile.optimized

# Compare before/after (run from directory containing all COPY/ADD files)
docktor benchmark Dockerfile Dockerfile.optimized
```

### Integration with Other CI/CD Platforms

Docktor works with any CI/CD system supporting Python and Docker:

```bash
# GitLab CI, Jenkins, CircleCI, etc.
pip install docktor-py
docktor lint Dockerfile
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. **Report Issues** – Use the [issues page](https://github.com/Nash0810/docktor/issues)
2. **Submit PRs** – Fork the repo and create a pull request
3. **Improve Documentation** – Help us make Docktor more accessible

For development setup:

```bash
git clone https://github.com/Nash0810/docktor.git
cd docktor
pip install -e ".[dev]"
pytest
```

---

## 📊 Benchmarking Tips

When using the `docktor benchmark` command:

- **Run from the correct directory** – Must be where your `COPY`/`ADD` source files exist
- **Compare Dockerfiles** – Always benchmark against an original to measure improvements
- **Docker must be running** – Benchmarking builds real images using Docker daemon

Example:

```bash
cd /path/to/project  # Ensure all COPY/ADD sources are accessible
docktor benchmark Dockerfile Dockerfile.optimized
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
