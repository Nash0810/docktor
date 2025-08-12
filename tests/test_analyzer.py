from src.docktor.parser import DockerfileParser
from src.docktor.analyzer import Analyzer


def test_analyzer_finds_pinned_version_issue():

    # 1. Arrange: Define a Dockerfile that should trigger rule BP001
    dockerfile_content = "FROM python:latest"

    # 2. Act: Run the full parse-and-analyze pipeline
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # 3. Assert: Check the results
    assert len(issues) == 1
    
    found_issue = issues[0]

    # Check that the details of the issue are correct
    assert found_issue.rule_id == "BP001"
    assert found_issue.line_number == 1
    assert "uses an unpinned version" in found_issue.message


def test_analyzer_finds_no_issues_in_good_file():

    # 1. Arrange: Define a compliant Dockerfile
    dockerfile_content = """
FROM python:3.11-slim
RUN pip install poetry
"""

    # 2. Act
    parser = DockerfileParser()
    instructions = parser.parse(dockerfile_content)
    
    analyzer = Analyzer()
    issues = analyzer.run(instructions)

    # 3. Assert
    assert len(issues) == 0


@pytest.mark.parametrize(
    "dockerfile_content, should_find_issue, expected_message",
    [
        # Case 1: No USER instruction at all
        ("FROM alpine", True, "No 'USER' instruction found."),
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
    if should_find_issue:
        # Find the specific issue we're looking for
        sec002_issues = [issue for issue in issues if issue.rule_id == "SEC002"]
        assert len(sec002_issues) == 1, "Expected to find a SEC002 issue, but didn't."
        assert sec002_issues[0].message == expected_message
    else:
        # Assert that this specific issue was NOT found
        sec002_issues = [issue for issue in issues if issue.rule_id == "SEC002"]
        assert len(sec002_issues) == 0, "Found a SEC002 issue when none was expected."
