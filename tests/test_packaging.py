"""Regression tests for package metadata and public documentation."""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_no_placeholder_repository_urls():
    """Published metadata and documentation must reference the real repository."""
    for path in ("pyproject.toml", "README.md", "USAGE.md"):
        assert "your-username" not in _read(path)


def test_requires_python_matches_supported_syntax():
    """Package metadata must reject Python versions that cannot parse the source."""
    pyproject = _read("pyproject.toml")

    assert 'requires-python = ">=3.10"' in pyproject
    assert 'python_version = "3.10"' in pyproject


def test_setup_py_is_removed():
    """Pyproject metadata should be the only package metadata source."""
    assert not (ROOT / "setup.py").exists()


def test_documented_environment_variables_are_supported():
    """README must not advertise configuration variables that are ignored."""
    documented = set(re.findall(r"PDF_TO_JSON_[A-Z_]+", _read("README.md")))

    assert documented == {
        "PDF_TO_JSON_DETECT_COLUMNS",
        "PDF_TO_JSON_MAX_HEADING_LEVELS",
        "PDF_TO_JSON_MAX_PAGES_FOR_FONT_ANALYSIS",
        "PDF_TO_JSON_MIN_HEADING_FREQUENCY",
        "PDF_TO_JSON_INCLUDE_PAGE_NUMBERS",
        "PDF_TO_JSON_OCR_LANGUAGE",
        "PDF_TO_JSON_USE_BOLD_AS_HEADING_SIGNAL",
    }


def test_documented_cli_does_not_include_pretty_flag():
    """Pretty output is the default, not a command-line option."""
    assert "--pretty" not in _read("README.md")
    assert "--pretty" not in _read("USAGE.md")


def test_readme_states_python_minimum_and_pymupdf_license():
    """README must disclose runtime and licensing constraints."""
    readme = _read("README.md")

    assert "python-3.10%2B" in readme
    assert "PyMuPDF" in readme
    assert "AGPL" in readme
