# Docktor Linting Rules

This document describes all 20 linting rules in Docktor, their implementation, and when they apply.

## Best Practice Rules (BP)

### BP001: Pinned Version Required

**ID:** `BP001`  
**Category:** Best Practice  
**Severity:** Warning  
**Auto-Optimized:** Yes

**Description:** Base image (FROM instruction) should use a pinned version tag, not `latest` or untagged.

**Why:** Using `latest` or no tag makes builds non-deterministic. A new version of the base image could be released at any time, introducing breaking changes or vulnerabilities into your application without your knowledge.

**Example (Bad):**

```dockerfile
FROM python
FROM node:latest
```

**Example (Good):**

```dockerfile
FROM python:3.11-slim
FROM node:18.16.0-alpine
```

**Implementation:**

```python
if ":" not in image_name or image_name.endswith(":latest"):
    issues.append(Issue(...))
```

**Optimization:** Optimizer automatically appends `:latest` tag to untagged images (conservative approach; pins to latest release).

---

### BP002: Missing HEALTHCHECK with EXPOSE

**ID:** `BP002`  
**Category:** Best Practice  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** When a port is exposed via EXPOSE, a HEALTHCHECK should be defined.

**Why:** EXPOSE indicates a service is listening on that port. Without a HEALTHCHECK, orchestrators (Kubernetes, Docker Swarm) can only know if the container is running, not if the service inside is healthy. This affects traffic routing, restart policies, and rolling deployments.

**Example (Bad):**

```dockerfile
FROM python:3.11
EXPOSE 5000
# No HEALTHCHECK
```

**Example (Good):**

```dockerfile
FROM python:3.11
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s CMD curl -f http://localhost:5000/health || exit 1
```

**Implementation:**

```python
expose_instruction = next((inst for inst in instructions if inst.instruction_type == InstructionType.EXPOSE), None)
has_healthcheck = any(inst.instruction_type == InstructionType.HEALTHCHECK for inst in instructions)
if expose_instruction and not has_healthcheck:
    issues.append(Issue(...))
```

---

### BP003: EXPOSE Protocol Specification

**ID:** `BP003`  
**Category:** Best Practice  
**Severity:** Info  
**Auto-Optimized:** Yes

**Description:** EXPOSE instructions should explicitly specify protocol (TCP or UDP).

**Why:** While Docker defaults to TCP, explicitly stating the protocol (e.g., `80/tcp` or `53/udp`) makes the Dockerfile unambiguous and serves as clearer documentation for developers.

**Example (Bad):**

```dockerfile
EXPOSE 3000
EXPOSE 53
```

**Example (Good):**

```dockerfile
EXPOSE 3000/tcp
EXPOSE 53/udp
```

**Implementation:**

```python
if "/tcp" not in port_value and "/udp" not in port_value:
    issues.append(Issue(...))
```

**Optimization:** Optimizer appends `/tcp` suffix (Docker's default protocol).

---

### BP004: Missing LABEL Metadata

**ID:** `BP004`  
**Category:** Best Practice  
**Severity:** Info  
**Auto-Optimized:** No

**Description:** Dockerfile should contain a LABEL instruction for image metadata.

**Why:** The LABEL instruction adds key-value metadata to your image (maintainer, version, source repo, etc.). This metadata is useful for managing images in automated environments and tools like Docker registries.

**Example (Bad):**

```dockerfile
FROM python:3.11
RUN apt-get update && apt-get install -y curl
# No LABEL
```

**Example (Good):**

```dockerfile
FROM python:3.11
LABEL maintainer="dev@example.com"
LABEL version="1.0.0"
RUN apt-get update && apt-get install -y curl
```

**Implementation:**

```python
has_label = any(inst.instruction_type == InstructionType.LABEL for inst in instructions)
if not has_label:
    issues.append(Issue(...))
```

---

### BP005: RUN in Scratch Image

**ID:** `BP005`  
**Category:** Best Practice  
**Severity:** Error  
**Auto-Optimized:** No

**Description:** RUN commands cannot be executed in a scratch image.

**Why:** The `FROM scratch` instruction creates a completely empty image with no shell or binaries. Any RUN command will fail because there is no `/bin/sh` to execute it.

**Example (Bad):**

```dockerfile
FROM scratch
RUN echo "This will fail"
```

**Example (Good):**

```dockerfile
FROM scratch
COPY app /app
CMD ["/app"]
```

**Implementation:**

```python
first_from = next((inst for inst in instructions if inst.instruction_type == InstructionType.FROM), None)
if first_from and "scratch" in first_from.value:
    for inst in instructions[1:]:
        if inst.instruction_type == InstructionType.RUN:
            issues.append(Issue(...))
```

---

### BP006: Invalid Multi-Stage Reference

**ID:** `BP006`  
**Category:** Best Practice  
**Severity:** Error  
**Auto-Optimized:** No

**Description:** COPY --from references an undefined build stage.

**Why:** Multi-stage builds require that referenced stages (via `COPY --from=stagename`) are defined earlier in the Dockerfile.

**Example (Bad):**

```dockerfile
FROM alpine:latest AS stage1
...
COPY --from=undefined_stage /app /app
```

**Example (Good):**

```dockerfile
FROM golang:1.19 AS builder
RUN go build -o app .

FROM alpine:latest
COPY --from=builder /app /app
```

**Implementation:**

```python
defined_stages = {inst.alias for inst in instructions if inst.instruction_type == InstructionType.FROM and inst.alias}
for inst in instructions:
    if inst.instruction_type == InstructionType.COPY and "--from=" in inst.value:
        referenced_stage = extract_stage_name(inst.value)
        if referenced_stage not in defined_stages:
            issues.append(Issue(...))
```

---

### BP007: Shell Form CMD/ENTRYPOINT

**ID:** `BP007`  
**Category:** Best Practice  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** CMD and ENTRYPOINT should use exec form, not shell form.

**Why:** Exec form (`["executable", "param1"]`) allows the process to receive signals (SIGTERM, SIGKILL) correctly. Shell form (`command param`) runs the command in a shell, which may not forward signals properly, causing graceful shutdown issues.

**Example (Bad):**

```dockerfile
CMD python app.py
ENTRYPOINT /bin/sh -c "python app.py"
```

**Example (Good):**

```dockerfile
CMD ["python", "app.py"]
ENTRYPOINT ["/bin/sh", "-c", "python app.py"]
```

**Implementation:**

```python
if inst.instruction_type in (InstructionType.CMD, InstructionType.ENTRYPOINT):
    if not inst.value.startswith("["):  # Not JSON array form
        issues.append(Issue(...))
```

---

### BP008: Non-Absolute WORKDIR

**ID:** `BP008`  
**Category:** Best Practice  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** WORKDIR path should be absolute.

**Why:** Relative WORKDIR paths can cause confusion about where subsequent COPY/RUN commands execute. Absolute paths are explicit and reduce ambiguity.

**Example (Bad):**

```dockerfile
WORKDIR app
RUN npm install
```

**Example (Good):**

```dockerfile
WORKDIR /app
RUN npm install
```

**Implementation:**

```python
if inst.instruction_type == InstructionType.WORKDIR:
    if not inst.value.startswith("/"):
        issues.append(Issue(...))
```

---

### BP009: apt-get install Without apt-get update

**ID:** `BP009`  
**Category:** Best Practice  
**Severity:** Error  
**Auto-Optimized:** No (reported as critical)

**Description:** `apt-get install` without preceding `apt-get update` may use stale package lists.

**Why:** `apt-get update` refreshes the package metadata from repositories. Without it, `apt-get install` may fail or install outdated packages with known vulnerabilities.

**Example (Bad):**

```dockerfile
RUN apt-get install -y curl
```

**Example (Good):**

```dockerfile
RUN apt-get update && apt-get install -y curl
```

**Implementation:**

```python
for i, inst in enumerate(instructions):
    if "apt-get install" in inst.value:
        # Check if any previous RUN contains apt-get update
        has_update = any("apt-get update" in prev.value for prev in instructions[:i])
        if not has_update:
            issues.append(Issue(...))
```

---

## Performance Rules (PERF)

### PERF001: Consecutive RUN Commands

**ID:** `PERF001`  
**Category:** Performance  
**Severity:** Info  
**Auto-Optimized:** Yes

**Description:** Consecutive RUN commands can be merged to reduce image layers.

**Why:** Each Dockerfile instruction creates a new layer in the image. Merging RUN commands with `&&` reduces the number of layers, which decreases image size and improves caching efficiency.

**Example (Bad):**

```dockerfile
RUN apt-get update
RUN apt-get install -y curl
RUN curl https://example.com/script.sh | bash
```

**Example (Good):**

```dockerfile
RUN apt-get update && \
    apt-get install -y curl && \
    curl https://example.com/script.sh | bash
```

**Optimization:** Merges consecutive RUN commands with `&&` chain operator.

---

### PERF002: apt-get Cache Not Cleaned

**ID:** `PERF002`  
**Category:** Performance  
**Severity:** Info  
**Auto-Optimized:** Yes

**Description:** `apt-get install` should clean up cache to reduce image size.

**Why:** `apt-get` downloads .deb files and stores metadata in `/var/lib/apt/lists/`. These are not needed in the final image and can be safely removed.

**Example (Bad):**

```dockerfile
RUN apt-get update && apt-get install -y curl
```

**Example (Good):**

```dockerfile
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
```

**Optimization:** Appends `rm -rf /var/lib/apt/lists/*` to RUN commands containing `apt-get install`.

---

### PERF003: Broad COPY Before Dependency Install

**ID:** `PERF003`  
**Category:** Performance  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** Copying application files before installing dependencies breaks Docker layer caching.

**Why:** Docker caches layers based on instruction content. If you COPY source code early, then install dependencies, any source code change invalidates the dependency layer cache, forcing a full rebuild.

**Example (Bad):**

```dockerfile
COPY . /app
RUN pip install -r requirements.txt
```

**Example (Good):**

```dockerfile
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt
COPY . /app
```

**Implementation:**

```python
# Detect COPY . pattern before RUN install patterns
copy_all_found = False
for inst in instructions:
    if inst.instruction_type == InstructionType.COPY and ". " in inst.value:
        copy_all_found = True
    if copy_all_found and "apt-get install" in inst.value or "pip install" in inst.value:
        issues.append(Issue(...))
        break
```

---

### PERF004: Build-Time Packages in Final Image

**ID:** `PERF004`  
**Category:** Performance  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** Build-time dependencies should be removed or isolated to build stage.

**Why:** Build tools (gcc, make, git) are needed to compile code but not to run it. Keeping them increases image size. Use multi-stage builds to separate build and runtime.

**Example (Bad):**

```dockerfile
FROM ubuntu:latest
RUN apt-get install -y build-essential git
RUN git clone https://repo && make
# Image now contains build-essential and git
```

**Example (Good):**

```dockerfile
FROM ubuntu:latest AS builder
RUN apt-get install -y build-essential git
RUN git clone https://repo && make

FROM ubuntu:latest
COPY --from=builder /app /app
# Runtime image is much smaller
```

**Implementation:**

```python
# Heuristic: detect build tool installations without multi-stage pattern
build_tools = ["build-essential", "gcc", "make", "git"]
for inst in instructions:
    if "apt-get install" in inst.value and any(tool in inst.value for tool in build_tools):
        # Check if this is in a builder stage
        preceding_from = last(inst for inst in instructions[:i] if inst.type == FROM)
        if not preceding_from.alias:  # Not in a named stage
            issues.append(Issue(...))
```

---

### PERF005: Unsafe apt-get upgrade

**ID:** `PERF005`  
**Category:** Performance  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** `apt-get upgrade` or `apt-get dist-upgrade` in Dockerfiles can introduce unexpected changes.

**Why:** Upgrading packages may break compatibility with your application. Use pinned versions instead to ensure reproducibility.

**Example (Bad):**

```dockerfile
RUN apt-get update && apt-get upgrade -y
```

**Example (Good):**

```dockerfile
RUN apt-get update && apt-get install -y curl=7.68.0-1ubuntu1
```

**Implementation:**

```python
if inst.instruction_type == InstructionType.RUN:
    if "apt-get upgrade" in inst.value or "apt-get dist-upgrade" in inst.value:
        issues.append(Issue(...))
```

---

### PERF006: Broad COPY Pattern

**ID:** `PERF006`  
**Category:** Performance  
**Severity:** Info  
**Auto-Optimized:** No

**Description:** Using `COPY . .` pattern copies everything, including build artifacts and cache directories.

**Why:** Copying unnecessary files (node_modules, .git, **pycache**, .env) increases image size and can expose secrets.

**Example (Bad):**

```dockerfile
WORKDIR /app
COPY . .
```

**Example (Good):**

```dockerfile
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY src ./src
```

**Implementation:**

```python
if inst.instruction_type == InstructionType.COPY:
    if ". ." in inst.value or ("." in inst.value and inst.value.count(".") == 2):
        issues.append(Issue(...))
```

---

### PERF007: Redundant apt-get update

**ID:** `PERF007`  
**Category:** Performance  
**Severity:** Info  
**Auto-Optimized:** No

**Description:** Multiple `apt-get update` calls are redundant.

**Why:** Each `apt-get update` takes time and creates a new layer. Run it once per RUN instruction (merged with install commands via `&&`).

**Example (Bad):**

```dockerfile
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get update
RUN apt-get install -y wget
```

**Example (Good):**

```dockerfile
RUN apt-get update && apt-get install -y curl wget
```

**Implementation:**

```python
update_count = 0
for inst in instructions:
    if inst.instruction_type == InstructionType.RUN:
        if "apt-get update" in inst.value:
            update_count += 1
if update_count > 1:
    issues.append(Issue(...))
```

---

## Security Rules (SEC)

### SEC001: ADD Used Instead of COPY

**ID:** `SEC001`  
**Category:** Security  
**Severity:** Warning  
**Auto-Optimized:** Yes

**Description:** Use COPY instead of ADD unless tar extraction is required.

**Why:** ADD has special behavior: it automatically extracts tar files and fetches URLs. This implicit behavior can be confusing and introduce security risks (e.g., tar bombs). COPY is explicit and safer.

**Example (Bad):**

```dockerfile
ADD app.tar.gz /app
ADD https://example.com/script.sh /tmp/
```

**Example (Good):**

```dockerfile
# If you need tar extraction, be explicit
RUN tar -xzf /tmp/app.tar.gz -C /app

# For local files, always use COPY
COPY app /app
COPY config.json /app/
```

**Implementation:**

```python
if inst.instruction_type == InstructionType.ADD:
    issues.append(Issue(...))
```

**Optimization:** Replaces ADD with COPY.

---

### SEC002: Container Runs as Root

**ID:** `SEC002`  
**Category:** Security  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** Container should run as a non-root user.

**Why:** Running as root grants unnecessary privileges. If a container is compromised, the attacker has root access to the entire system. Best practice is to create a dedicated user.

**Example (Bad):**

```dockerfile
FROM python:3.11
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
# Runs as root (UID 0)
```

**Example (Good):**

```dockerfile
FROM python:3.11
RUN useradd -m appuser
RUN pip install -r requirements.txt
USER appuser
CMD ["python", "app.py"]
```

**Implementation:**

```python
has_user = any(inst.instruction_type == InstructionType.USER for inst in instructions)
if not has_user:
    issues.append(Issue(...))
```

---

### SEC003: Potential Secrets in ENV Variables

**ID:** `SEC003`  
**Category:** Security  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** ENV variables containing "secret," "key," "token," or "password" may expose sensitive data.

**Why:** ENV variables are baked into the image and visible in image history (`docker history`). Never store secrets in ENV; use runtime secrets (Docker Secrets, Kubernetes Secrets) instead.

**Example (Bad):**

```dockerfile
ENV API_KEY=abc123def456
ENV DATABASE_PASSWORD=secret123
```

**Example (Good):**

```dockerfile
# Use docker secrets or environment passed at runtime
# docker run -e API_KEY=$API_KEY
# OR
# docker run --secret api_key
```

**Implementation:**

```python
secret_keywords = ["secret", "key", "token", "password", "apikey"]
if inst.instruction_type == InstructionType.ENV:
    if any(keyword in inst.value.lower() for keyword in secret_keywords):
        issues.append(Issue(...))
```

---

### SEC004: COPY --chown Missing for Non-Root User

**ID:** `SEC004`  
**Category:** Security  
**Severity:** Warning  
**Auto-Optimized:** No

**Description:** When running as non-root, ensure copied files have correct ownership.

**Why:** If you COPY files as root but then switch to a non-root user, the non-root user cannot modify those files. Use `COPY --chown=user:group` to set correct ownership.

**Example (Bad):**

```dockerfile
COPY app /app
RUN useradd -m appuser
USER appuser
# appuser cannot write to /app (owned by root)
```

**Example (Good):**

```dockerfile
RUN useradd -m appuser
COPY --chown=appuser:appuser app /app
USER appuser
```

**Implementation:**

```python
has_user = any(inst.instruction_type == InstructionType.USER for inst in instructions)
if has_user:
    for inst in instructions:
        if inst.instruction_type == InstructionType.COPY:
            if "--chown" not in inst.value:
                issues.append(Issue(...))
```

---

## Registry Rules (REG)

### REG001: Newer Patch Version Available

**ID:** `REG001`  
**Category:** Registry  
**Severity:** Info  
**Auto-Optimized:** No

**Description:** Docker Hub has a newer patch version of the base image.

**Why:** Newer patch versions include security fixes and bug patches. Staying up-to-date ensures your base image has the latest stability and security improvements.

**Example (Bad):**

```dockerfile
FROM python:3.11.0
# Newer version available: 3.11.5
```

**Example (Good):**

```dockerfile
FROM python:3.11.5
```

**Implementation:**

```python
def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
    issues = []
    for inst in instructions:
        if inst.instruction_type == InstructionType.FROM:
            image_name = inst.image
            current_tag = inst.tag

            # Query Docker Hub API
            response = requests.get(f"https://hub.docker.com/v2/repositories/{image_name}/tags")
            available_tags = [tag['name'] for tag in response.json()['results']]

            # Find newer patch versions
            current_version = self._parse_leading_version(current_tag)
            newer_versions = [tag for tag in available_tags if self._is_higher(self._parse_leading_version(tag), current_version)]

            if newer_versions:
                issues.append(Issue(...))
    return issues
```

**Trade-offs:**

- ✅ Encourages staying up-to-date
- ❌ Requires internet access (Docker Hub API)
- ❌ Subject to API rate limits
- ❌ Does not apply to private registries

---

## Summary Table

| Rule ID | Category      | Severity | Auto-Optimized | Purpose                         |
| ------- | ------------- | -------- | -------------- | ------------------------------- |
| BP001   | Best Practice | Warning  | Yes            | Pin base image versions         |
| BP002   | Best Practice | Warning  | No             | Add HEALTHCHECK with EXPOSE     |
| BP003   | Best Practice | Info     | Yes            | Specify EXPOSE protocol         |
| BP004   | Best Practice | Info     | No             | Add LABEL metadata              |
| BP005   | Best Practice | Error    | No             | Prevent RUN in scratch          |
| BP006   | Best Practice | Error    | No             | Validate multi-stage references |
| BP007   | Best Practice | Warning  | No             | Use exec form CMD/ENTRYPOINT    |
| BP008   | Best Practice | Warning  | No             | Use absolute WORKDIR            |
| BP009   | Best Practice | Error    | No             | apt-get update before install   |
| PERF001 | Performance   | Info     | Yes            | Merge consecutive RUN           |
| PERF002 | Performance   | Info     | Yes            | Clean apt-get cache             |
| PERF003 | Performance   | Warning  | No             | COPY dependencies before app    |
| PERF004 | Performance   | Warning  | No             | Remove build-time deps          |
| PERF005 | Performance   | Warning  | No             | Avoid apt-get upgrade           |
| PERF006 | Performance   | Info     | No             | Avoid broad COPY pattern        |
| PERF007 | Performance   | Info     | No             | Avoid redundant apt-get update  |
| SEC001  | Security      | Warning  | Yes            | Use COPY instead of ADD         |
| SEC002  | Security      | Warning  | No             | Run as non-root user            |
| SEC003  | Security      | Warning  | No             | Never hardcode secrets          |
| SEC004  | Security      | Warning  | No             | Set correct file ownership      |
| REG001  | Registry      | Info     | No             | Check Docker Hub for updates    |
