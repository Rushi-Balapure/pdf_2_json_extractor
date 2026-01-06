"""
End-to-end tests for pdf_2_json_extractor CLI.

Tests the actual CLI behavior with real PDFs and real arguments.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run the CLI with the given arguments."""
    cmd = [sys.executable, "-m", "pdf_2_json_extractor.cli", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


class TestCLIBasicUsage:
    """Test basic CLI functionality."""

    def test_extracts_to_stdout(self, real_pdf_path: Path):
        """Running with just a PDF path should output JSON to stdout."""
        result = run_cli(str(real_pdf_path))

        assert result.returncode == 0

        # Should be valid JSON
        output = json.loads(result.stdout)
        assert "title" in output
        assert "sections" in output
        assert "stats" in output

    def test_extracts_to_file(self, real_pdf_path: Path, temp_json_output_path: Path):
        """Using -o should save output to file."""
        result = run_cli(str(real_pdf_path), "-o", str(temp_json_output_path))

        assert result.returncode == 0
        assert temp_json_output_path.exists()

        with open(temp_json_output_path, encoding="utf-8") as f:
            saved = json.load(f)

        assert "title" in saved
        assert "sections" in saved

    def test_compact_output(self, real_pdf_path: Path):
        """--compact should produce minified JSON."""
        result = run_cli(str(real_pdf_path), "--compact")

        assert result.returncode == 0

        # Compact JSON shouldn't have newlines in the main output
        # (there might be newlines in content, but the JSON structure itself is flat)
        output = result.stdout.strip()
        parsed = json.loads(output)

        # Verify it parsed correctly
        assert "title" in parsed

        # Re-encode compact and verify it matches (roughly)
        compact_encoded = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        # The output should be close to compact form
        assert len(output) <= len(compact_encoded) + 100  # Some tolerance


class TestCLIErrorHandling:
    """Test CLI error cases."""

    def test_file_not_found(self, nonexistent_pdf_path: Path):
        """Should exit with error for missing file."""
        result = run_cli(str(nonexistent_pdf_path), check=False)

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_no_arguments(self):
        """Should exit with error when no arguments provided."""
        result = run_cli(check=False)

        assert result.returncode != 0


class TestCLIVersion:
    """Test version flag."""

    def test_version_flag(self):
        """--version should print version and exit."""
        result = run_cli("--version", check=False)

        # argparse exits with 0 for --version
        assert result.returncode == 0
        assert "pdf_2_json_extractor" in result.stdout.lower() or "1." in result.stdout


class TestCLIHelp:
    """Test help output."""

    def test_help_flag(self):
        """--help should print usage and exit."""
        result = run_cli("--help", check=False)

        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "pdf" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
