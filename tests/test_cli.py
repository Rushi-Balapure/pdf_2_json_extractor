"""
End-to-end tests for pdf_2_json_extractor CLI.

Tests the actual CLI behavior with real PDFs and real arguments.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pdf_2_json_extractor import cli


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """
    Run the CLI with the given arguments.
    Never raises on non-zero exit. Caller should check returncode and stderr.
    """
    cmd = [sys.executable, "-m", "pdf_2_json_extractor.cli", *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    # Ensure stdout/stderr are never None (defensive for weird Windows/CI edge cases)
    stdout = result.stdout if result.stdout is not None else ""
    stderr = result.stderr if result.stderr is not None else ""
    return subprocess.CompletedProcess(result.args, result.returncode, stdout, stderr)


class TestCLIBasicUsage:
    """Test basic CLI functionality."""

    def test_extracts_to_stdout(self, real_pdf_path: Path):
        """Running with just a PDF path should output JSON to stdout."""
        result = run_cli(str(real_pdf_path))

        # Show stderr on failure for debugging
        assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"
        assert result.stdout, f"CLI returned empty stdout, stderr: {result.stderr}"

        # Should be valid JSON
        output = json.loads(result.stdout)
        assert "title" in output
        assert "sections" in output
        assert "stats" in output

    def test_extracts_to_file(self, real_pdf_path: Path, temp_json_output_path: Path):
        """Using -o should save output to file."""
        result = run_cli(str(real_pdf_path), "-o", str(temp_json_output_path))

        assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"
        assert temp_json_output_path.exists()

        with open(temp_json_output_path, encoding="utf-8") as f:
            saved = json.load(f)

        assert "title" in saved
        assert "sections" in saved

    def test_compact_output(self, real_pdf_path: Path):
        """--compact should produce minified JSON."""
        result = run_cli(str(real_pdf_path), "--compact")

        assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"
        assert result.stdout, f"CLI returned empty stdout, stderr: {result.stderr}"

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
        result = run_cli(str(nonexistent_pdf_path))

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_no_arguments(self):
        """Should exit with error when no arguments provided."""
        result = run_cli()

        assert result.returncode != 0


class TestCLIBatchUsage:
    """Test multiple files and non-recursive directory expansion."""

    def test_processes_multiple_files_in_stable_order(self, real_pdf_path: Path, tmp_path: Path):
        """Multiple explicit PDFs should produce deterministic per-file outputs."""
        second = tmp_path / "zeta.pdf"
        first = tmp_path / "alpha.pdf"
        shutil.copyfile(real_pdf_path, second)
        shutil.copyfile(real_pdf_path, first)
        output_dir = tmp_path / "output"

        result = run_cli(str(second), str(first), "-o", str(output_dir))

        assert result.returncode == 0, result.stderr
        assert (output_dir / "alpha.json").exists()
        assert (output_dir / "zeta.json").exists()
        assert result.stderr.index("alpha.pdf") < result.stderr.index("zeta.pdf")

    def test_expands_directory_case_insensitively_without_recursion(
        self, real_pdf_path: Path, tmp_path: Path
    ):
        """Directory scans should include PDF suffix variants but not nested files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        nested_dir = input_dir / "nested"
        nested_dir.mkdir()
        shutil.copyfile(real_pdf_path, input_dir / "upper.PDF")
        shutil.copyfile(real_pdf_path, input_dir / "lower.pdf")
        shutil.copyfile(real_pdf_path, nested_dir / "ignored.pdf")
        (input_dir / "ignored.txt").write_text("not a PDF", encoding="utf-8")
        output_dir = tmp_path / "output"

        result = run_cli(str(input_dir), "-o", str(output_dir))

        assert result.returncode == 0, result.stderr
        assert sorted(path.name for path in output_dir.iterdir()) == ["lower.json", "upper.json"]
        assert not (output_dir / "ignored.json").exists()

    def test_rejects_empty_directory(self, tmp_path: Path):
        """An input directory without PDFs should fail clearly."""
        input_dir = tmp_path / "empty"
        input_dir.mkdir()

        result = run_cli(str(input_dir))

        assert result.returncode == 1
        assert "no pdf files" in result.stderr.lower()

    def test_rejects_directory_symlinks(self, real_pdf_path: Path, tmp_path: Path):
        """Directory expansion should not follow symlinks implicitly."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        shutil.copyfile(real_pdf_path, input_dir / "document.pdf")
        linked_dir = tmp_path / "linked"
        try:
            linked_dir.symlink_to(input_dir, target_is_directory=True)
        except OSError:
            pytest.skip("Symlink creation is unavailable on this platform")

        result = run_cli(str(linked_dir))

        assert result.returncode == 1
        assert "directory symlinks" in result.stderr.lower()

    def test_requires_output_directory_for_multiple_files(self, real_pdf_path: Path, tmp_path: Path):
        """Batch output should never mix multiple JSON documents on stdout."""
        first = tmp_path / "first.pdf"
        second = tmp_path / "second.pdf"
        shutil.copyfile(real_pdf_path, first)
        shutil.copyfile(real_pdf_path, second)

        result = run_cli(str(first), str(second))

        assert result.returncode == 1
        assert "output directory" in result.stderr.lower()

    def test_continues_after_failure_and_returns_nonzero(
        self, real_pdf_path: Path, invalid_pdf_path: Path, tmp_path: Path
    ):
        """A failed PDF should not prevent valid batch peers from being written."""
        valid = tmp_path / "valid.pdf"
        invalid = tmp_path / "invalid.pdf"
        shutil.copyfile(real_pdf_path, valid)
        shutil.copyfile(invalid_pdf_path, invalid)
        output_dir = tmp_path / "output"

        result = run_cli(str(invalid), str(valid), "-o", str(output_dir))

        assert result.returncode == 1
        assert (output_dir / "valid.json").exists()
        assert not (output_dir / "invalid.json").exists()
        assert "failed" in result.stderr.lower()
        assert "valid.pdf" in result.stderr

    def test_continues_after_missing_input(self, real_pdf_path: Path, tmp_path: Path):
        """Path-resolution failures should not prevent valid peers from running."""
        valid = tmp_path / "valid.pdf"
        missing = tmp_path / "missing.pdf"
        shutil.copyfile(real_pdf_path, valid)
        output_dir = tmp_path / "output"

        result = run_cli(str(missing), str(valid), "-o", str(output_dir))

        assert result.returncode == 1
        assert (output_dir / "valid.json").exists()
        assert f"FAILED {missing}" in result.stderr
        assert f"OK {valid}" in result.stderr

    def test_directory_scan_failure_preserves_valid_peers(
        self, real_pdf_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """An unreadable directory should become a per-input resolution failure."""
        blocked = tmp_path / "blocked"
        blocked.mkdir()
        valid = tmp_path / "valid.pdf"
        shutil.copyfile(real_pdf_path, valid)
        original_iterdir = Path.iterdir

        def guarded_iterdir(path: Path):
            if path == blocked:
                raise PermissionError("access denied")
            return original_iterdir(path)

        monkeypatch.setattr(Path, "iterdir", guarded_iterdir)

        resolved, failures = cli._resolve_pdf_paths([str(blocked), str(valid)])

        assert resolved == [valid]
        assert failures == [(blocked, "cannot scan directory: access denied")]

    def test_refuses_to_overwrite_existing_batch_output(self, real_pdf_path: Path, tmp_path: Path):
        """Batch mode should preserve output files from earlier runs."""
        first = tmp_path / "first.pdf"
        second = tmp_path / "second.pdf"
        shutil.copyfile(real_pdf_path, first)
        shutil.copyfile(real_pdf_path, second)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        existing = output_dir / "first.json"
        existing.write_text("keep me", encoding="utf-8")

        result = run_cli(str(first), str(second), "-o", str(output_dir))

        assert result.returncode == 1
        assert existing.read_text(encoding="utf-8") == "keep me"
        assert (output_dir / "second.json").exists()
        assert "refusing to overwrite" in result.stderr.lower()

    def test_atomic_publish_does_not_clobber_competing_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """A destination created during publication should remain untouched."""
        destination = tmp_path / "result.json"

        def competing_link(source: Path, target: Path) -> None:
            destination.write_text("competitor", encoding="utf-8")
            raise FileExistsError

        monkeypatch.setattr(cli.os, "link", competing_link)

        with pytest.raises(FileExistsError, match="refusing to overwrite"):
            cli._write_json(destination, {"title": "new"}, compact=True)

        assert destination.read_text(encoding="utf-8") == "competitor"
        assert list(tmp_path.iterdir()) == [destination]

    def test_rejects_duplicate_output_stems(self, real_pdf_path: Path, tmp_path: Path):
        """Batch inputs must not silently overwrite the same output name."""
        first_dir = tmp_path / "first"
        second_dir = tmp_path / "second"
        first_dir.mkdir()
        second_dir.mkdir()
        shutil.copyfile(real_pdf_path, first_dir / "report.pdf")
        shutil.copyfile(real_pdf_path, second_dir / "report.pdf")

        result = run_cli(
            str(first_dir / "report.pdf"),
            str(second_dir / "report.pdf"),
            "-o",
            str(tmp_path / "output"),
        )

        assert result.returncode == 1
        assert "duplicate output" in result.stderr.lower()

    def test_compact_batch_writes_minified_json(self, real_pdf_path: Path, tmp_path: Path):
        """Compact formatting should apply to every batch output file."""
        first = tmp_path / "first.pdf"
        second = tmp_path / "second.pdf"
        shutil.copyfile(real_pdf_path, first)
        shutil.copyfile(real_pdf_path, second)
        output_dir = tmp_path / "output"

        result = run_cli(str(first), str(second), "-o", str(output_dir), "--compact")

        assert result.returncode == 0, result.stderr
        assert "\n" not in (output_dir / "first.json").read_text(encoding="utf-8")


class TestCLIVersion:
    """Test version flag."""

    def test_version_flag(self):
        """--version should print version and exit."""
        result = run_cli("--version")

        # argparse exits with 0 for --version
        assert result.returncode == 0
        assert "pdf_2_json_extractor" in result.stdout.lower() or "1." in result.stdout


class TestCLIHelp:
    """Test help output."""

    def test_help_flag(self):
        """--help should print usage and exit."""
        result = run_cli("--help")

        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "pdf" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
