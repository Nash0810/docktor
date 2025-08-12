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

- **Comprehensive Linter** – Checks against 19+ rules for performance, security, and best practices.
- **Intelligent Optimizer** – Combines `RUN` commands, cleans up apt-get cache, replaces `ADD` with `COPY`, etc.
- **Educational Explanations** – Understand _why_ a suggestion is made.
- **Empirical Benchmarking** – See image size, build time, and layer count improvements.
- **CI/CD Friendly** – Output in human-readable tables (Rich) or machine-readable JSON.

## 🚀 Quick Start

### Installation

Requires Python **3.8+** and Docker.

```bash
pip install docktor
```

### Usage

#### 1. Lint a Dockerfile

```bash
docktor lint Dockerfile
```

#### 2. See Detailed Explanations

```bash
docktor lint Dockerfile --explain
```

#### 3. Automatically Optimize

```bash
# Pretty summary
docktor optimize Dockerfile

# Copy-pasteable output
docktor optimize Dockerfile --raw

# Save optimized file
docktor optimize Dockerfile --raw > Dockerfile.optimized
```

#### 4. Benchmark Your Changes

```bash
docktor benchmark Dockerfile Dockerfile.optimized
```

## ⚙️ Implemented Rules

| Rule ID | Description                                    | Category      | Auto-Optimized?    |
| ------- | ---------------------------------------------- | ------------- | ------------------ |
| BP001   | FROM uses `:latest` or no tag                  | Best Practice | Yes (for untagged) |
| BP002   | EXPOSE is present without HEALTHCHECK          | Best Practice | No                 |
| BP003   | EXPOSE is missing `/tcp` or `/udp` protocol    | Best Practice | Yes                |
| BP004   | LABEL instruction for metadata is missing      | Best Practice | No                 |
| BP005   | RUN command is used in a scratch image         | Best Practice | No (error)         |
| BP006   | COPY --from refers to a non-existent stage     | Best Practice | No (error)         |
| BP007   | CMD/ENTRYPOINT uses shell form                 | Best Practice | No                 |
| BP008   | WORKDIR path is not absolute                   | Best Practice | No                 |
| PERF001 | Consecutive RUN commands can be merged         | Performance   | Yes                |
| PERF002 | apt-get install is missing cache cleanup       | Performance   | Yes                |
| PERF003 | Broad COPY is used before dependency install   | Performance   | No                 |
| PERF004 | Build-time packages (git, gcc) are installed   | Performance   | No                 |
| PERF005 | Unsafe apt-get upgrade command is used         | Performance   | No                 |
| PERF006 | Broad `COPY . .` pattern is used               | Performance   | No                 |
| PERF007 | Redundant apt-get update command is used       | Performance   | No                 |
| SEC001  | ADD is used instead of COPY                    | Security      | Yes                |
| SEC002  | Container runs as the root user                | Security      | No                 |
| SEC003  | Potential secrets are in ENV variables         | Security      | No                 |
| SEC004  | COPY is used without --chown for non-root user | Security      | No                 |

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Check out the [issues page](https://github.com/Nash0810/docktor/issues) to get started.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
