

import pathlib
from click.testing import CliRunner
from docktor.cli import cli

def test_cli_lint_good_file_exits_successfully(tmp_path: pathlib.Path):
    """
    Tests that 'docktor lint' on a compliant file exits with code 0.
    """
    good_dockerfile = tmp_path / "Dockerfile"
    good_dockerfile.write_text(
        'LABEL maintainer="test"\nFROM python:3.11-slim\nUSER 1001'
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", str(good_dockerfile)])
    assert result.exit_code == 0
    assert "No issues found" in result.output

def test_cli_lint_bad_file_exits_with_error(tmp_path: pathlib.Path):
    """
    Tests that 'docktor lint' on a non-compliant file exits with code 1.
    """
    bad_dockerfile = tmp_path / "Dockerfile"
    bad_dockerfile.write_text("FROM python:latest")
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", str(bad_dockerfile)])
    assert result.exit_code == 1
    assert "Issues Found" in result.output
    assert "BP001" in result.output

def test_cli_optimize_command_shows_summary(tmp_path: pathlib.Path, monkeypatch):
    """
    Tests that 'docktor optimize' shows the pretty summary by forcing it
    with an environment variable.
    """
    # 1. Arrange: Create a temporary Dockerfile
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM alpine\nRUN sudo apt-get update")


    monkeypatch.setenv("DOCKTOR_FORCE_PRETTY", "1")

    # 2. Act: Run the 'optimize' command
    runner = CliRunner()
    result = runner.invoke(cli, ["optimize", str(dockerfile)])

    # 3. Assert: Check the results
    assert result.exit_code == 0
    assert "Optimizations applied" in result.output
    assert "Removed unnecessary 'sudo'" in result.output

def test_cli_optimize_command_shows_raw_output(tmp_path: pathlib.Path):
    """
    Tests that 'docktor optimize --raw' shows the clean, raw output.
    """
    # 1. Arrange: Create a temporary Dockerfile
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM alpine\nRUN sudo apt-get update")

    # 2. Act: Run the 'optimize' command with the --raw flag
    runner = CliRunner()
    result = runner.invoke(cli, ["optimize", "--raw", str(dockerfile)])

    # 3. Assert: Check the results
    assert result.exit_code == 0
    
    assert "Optimizations applied" not in result.output
    
    expected_output = "FROM alpine:latest\nRUN apt-get update"
    assert expected_output in result.output
