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