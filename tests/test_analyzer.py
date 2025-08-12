import pytest
from docktor.parser import DockerfileParser
from docktor.analyzer import Analyzer


def test_analyzer_finds_specific_issue():
    """
    Tests that the Analyzer can find a specific issue (BP001)
    while ignoring others that might also be present.
    """
    # Arrange: This file has multiple issues (no user, no label, latest tag)
    dockerfile_content = "FROM python:latest"

    # Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert: Check that the specific BP001 issue exists
    assert any(issue.rule_id == "BP001" for issue in issues)


def test_analyzer_finds_no_issues_in_truly_good_file():
    """
    Tests that the Analyzer returns no issues for a Dockerfile
    that complies with all our current rules.
    """
    # Arrange: A compliant Dockerfile with a pinned version, a label, and a non-root user
    dockerfile_content = """
LABEL maintainer="test"
FROM python:3.11-slim
RUN useradd -m myappuser
USER myappuser
RUN pip install poetry
"""

    # Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert: We expect zero issues
    assert len(issues) == 0, f"Expected 0 issues, but found {len(issues)}: {issues}"


@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue, expected_message",
    [
        # Case 1: No USER instruction at all (Corrected Message)
        ("FROM alpine", True, "No 'USER' instruction found. Container will run as root."),
        # Case 2: Last USER is explicitly root
        ("FROM alpine\nUSER root", True, "Container is explicitly set to run as 'root' user."),
        # Case 3: A non-root user is set (good case)
        ("FROM alpine\nUSER myappuser", False, None),
        # Case 4: Multiple USER instructions, last one is non-root (good case)
        ("FROM alpine\nUSER root\nUSER myappuser", False, None),
    ],
)
def test_analyzer_non_root_user_rule(dockerfile_content, should_find_issue, expected_message):
    """
    Tests the NonRootUserRule (SEC002) across multiple scenarios.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    sec002_issues = [issue for issue in issues if issue.rule_id == "SEC002"]
    if should_find_issue:
        assert len(sec002_issues) == 1, "Expected to find a SEC002 issue, but didn't."
        assert sec002_issues[0].message == expected_message
    else:
        assert len(sec002_issues) == 0, "Found a SEC002 issue when none was expected."

@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: EXPOSE is present, but HEALTHCHECK is missing (Bad case)
        ("FROM alpine\nEXPOSE 80", True),
        # Case 2: Both EXPOSE and HEALTHCHECK are present (Good case)
        ("FROM alpine\nEXPOSE 80\nHEALTHCHECK CMD curl http://localhost/", False),
        # Case 3: No EXPOSE instruction (Good case)
        ("FROM alpine\nCMD echo 'hello'", False),
    ],
)
def test_analyzer_missing_healthcheck_rule(dockerfile_content, should_find_issue):
    """
    Tests the MissingHealthcheckRule (BP002) for various scenarios.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    # We specifically look for the BP002 issue
    bp002_issues = [issue for issue in issues if issue.rule_id == "BP002"]
    
    if should_find_issue:
        assert len(bp002_issues) == 1, "Expected to find a BP002 issue, but didn't."
    else:
        assert len(bp002_issues) == 0, "Found a BP002 issue when none was expected."

@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: A clear secret keyword is used (Bad case)
        ("FROM alpine\nENV DATABASE_PASSWORD=secret", True),
        # Case 2: Another secret keyword (API_KEY)
        ("FROM alpine\nENV MY_API_KEY=12345", True),
        # Case 3: A safe, non-secret environment variable (Good case)
        ("FROM alpine\nENV APP_VERSION=1.2.3", False),
        # Case 4: No ENV instructions at all (Good case)
        ("FROM alpine\nRUN echo 'hello'", False),
    ],
)
def test_analyzer_env_var_secrets_rule(dockerfile_content, should_find_issue):
    """
    Tests the EnvVarSecretsRule (SEC003) for various scenarios.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    sec003_issues = [issue for issue in issues if issue.rule_id == "SEC003"]
    
    if should_find_issue:
        assert len(sec003_issues) >= 1, "Expected to find a SEC003 issue, but didn't."
    else:
        assert len(sec003_issues) == 0, "Found a SEC003 issue when none was expected."


@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: The classic cache-busting anti-pattern (Bad case)
        ("FROM python:3.11\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt", True),
        # Case 2: The correct, optimized pattern (Good case)
        ("FROM python:3.11\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .", False),
        # Case 3: A Dockerfile with no install command (Good case)
        ("FROM python:3.11\nCOPY . .", False),
    ],
)
def test_analyzer_cache_busting_copy_rule(dockerfile_content, should_find_issue):
    """
    Tests the CacheBustingCopyRule (PERF003) for various ordering scenarios.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    perf003_issues = [issue for issue in issues if issue.rule_id == "PERF003"]
    
    if should_find_issue:
        assert len(perf003_issues) == 1, "Expected to find a PERF003 issue, but didn't."
    else:
        assert len(perf003_issues) == 0, "Found a PERF003 issue when none was expected."


@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: Installs an unnecessary package (git) - Bad case
        ("FROM alpine\nRUN apt-get install -y git", True),
        # Case 2: Installs another unnecessary package (curl)
        ("FROM alpine\nRUN apk add curl", True),
        # Case 3: Installs a safe, necessary package (Good case)
        ("FROM alpine\nRUN apt-get install -y my-app-dependency", False),
        # Case 4: A RUN command without an install (Good case)
        ("FROM alpine\nRUN echo 'hello'", False),
    ],
)
def test_analyzer_unnecessary_packages_rule(dockerfile_content, should_find_issue):
    """
    Tests the UnnecessaryPackagesRule (PERF004) for various packages.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    perf004_issues = [issue for issue in issues if issue.rule_id == "PERF004"]
    
    if should_find_issue:
        assert len(perf004_issues) >= 1, "Expected to find a PERF004 issue, but didn't."
    else:
        assert len(perf004_issues) == 0, "Found a PERF004 issue when none was expected."


@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: Contains 'apt-get upgrade' (Bad case)
        ("FROM debian\nRUN apt-get update && apt-get upgrade -y", True),
        # Case 2: Contains 'apt-get dist-upgrade' (Bad case)
        ("FROM debian\nRUN apt-get dist-upgrade", True),
        # Case 3: Contains a safe install command (Good case)
        ("FROM debian\nRUN apt-get install -y git", False),
    ],
)
def test_analyzer_apt_get_upgrade_rule(dockerfile_content, should_find_issue):
    """
    Tests the AptGetUpgradeRule (PERF005) for forbidden commands.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    perf005_issues = [issue for issue in issues if issue.rule_id == "PERF005"]
    
    if should_find_issue:
        assert len(perf005_issues) == 1, "Expected to find a PERF005 issue, but didn't."
    else:
        assert len(perf005_issues) == 0, "Found a PERF005 issue when none was expected."


@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: Non-root user is set, but COPY is missing --chown (Bad case)
        ("FROM alpine\nUSER myapp\nCOPY . /app", True),
        # Case 2: Non-root user is set, and COPY has --chown (Good case)
        ("FROM alpine\nUSER myapp\nCOPY --chown=myapp . /app", False),
        # Case 3: User is root, so --chown is not required (Good case)
        ("FROM alpine\nUSER root\nCOPY . /app", False),
        # Case 4: No USER is set (defaults to root), so --chown is not required (Good case)
        ("FROM alpine\nCOPY . /app", False),
    ],
)
def test_analyzer_copy_chown_rule(dockerfile_content, should_find_issue):
    """
    Tests the CopyChownRule (SEC004) for various user states.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    sec004_issues = [issue for issue in issues if issue.rule_id == "SEC004"]
    
    if should_find_issue:
        assert len(sec004_issues) == 1, "Expected to find a SEC004 issue, but didn't."
    else:
        assert len(sec004_issues) == 0, "Found a SEC004 issue when none was expected."

@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: Two 'apt-get update' commands, the second should be flagged (Bad case)
        ("FROM debian\nRUN apt-get update\nRUN apt-get update", True),
        # Case 2: Only one 'apt-get update' command (Good case)
        ("FROM debian\nRUN apt-get update && apt-get install -y git", False),
        # Case 3: No 'apt-get update' commands at all (Good case)
        ("FROM debian\nRUN apt-get install -y git", False),
    ],
)
def test_analyzer_redundant_update_rule(dockerfile_content, should_find_issue):
    """
    Tests the RedundantUpdateRule (PERF007) for repeated commands.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    perf007_issues = [issue for issue in issues if issue.rule_id == "PERF007"]
    
    if should_find_issue:
        assert len(perf007_issues) == 1, "Expected to find a PERF007 issue, but didn't."
    else:
        assert len(perf007_issues) == 0, "Found a PERF007 issue when none was expected."

@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: CMD in shell form (Bad case)
        ("FROM alpine\nCMD echo 'hello'", True),
        # Case 2: ENTRYPOINT in shell form (Bad case)
        ("FROM alpine\nENTRYPOINT /app/start.sh", True),
        # Case 3: CMD in exec form (Good case)
        ('FROM alpine\nCMD ["echo", "hello"]', False),
        # Case 4: ENTRYPOINT in exec form (Good case)
        ('FROM alpine\nENTRYPOINT ["/app/start.sh"]', False),
    ],
)
def test_analyzer_shell_form_command_rule(dockerfile_content, should_find_issue):
    """
    Tests the ShellFormCommandRule (BP007) for CMD and ENTRYPOINT.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    bp007_issues = [issue for issue in issues if issue.rule_id == "BP007"]
    
    if should_find_issue:
        assert len(bp007_issues) == 1, "Expected to find a BP007 issue, but didn't."
    else:
        assert len(bp007_issues) == 0, "Found a BP007 issue when none was expected."


@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue",
    [
        # Case 1: WORKDIR with a relative path (Bad case)
        ("FROM alpine\nWORKDIR app", True),
        # Case 2: WORKDIR with an absolute path (Good case)
        ("FROM alpine\nWORKDIR /app", False),
        # Case 3: WORKDIR using a build argument (Good case, should be ignored)
        ("FROM alpine\nARG APP_DIR=/app\nWORKDIR $APP_DIR", False),
    ],
)
def test_analyzer_workdir_absolute_rule(dockerfile_content, should_find_issue):
    """
    Tests the WorkdirAbsoluteRule (BP008) for relative and absolute paths.
    """
    # Arrange & Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # Assert
    bp008_issues = [issue for issue in issues if issue.rule_id == "BP008"]
    
    if should_find_issue:
        assert len(bp008_issues) == 1, "Expected to find a BP008 issue, but didn't."
    else:
        assert len(bp008_issues) == 0, "Found a BP008 issue when none was expected."

