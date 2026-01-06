"""
Pytest configuration and fixtures for pdf_2_json_extractor tests.
"""

import os
from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return get_project_root()


@pytest.fixture
def papers_dir(project_root: Path) -> Path:
    """Return the papers directory containing real PDFs for testing."""
    return project_root / "papers"


@pytest.fixture
def real_pdf_path(papers_dir: Path) -> Path:
    """
    Return the path to a real PDF file for e2e testing.
    This is the good stuff. An actual PDF, not some fake mock bullshit.
    """
    pdf_path = papers_dir / "1751-0473-7-7.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found at {pdf_path}")
    return pdf_path


@pytest.fixture
def nonexistent_pdf_path(tmp_path: Path) -> Path:
    """Return a path to a PDF file that definitely does not exist."""
    return tmp_path / "this_file_does_not_exist.pdf"


@pytest.fixture
def invalid_pdf_path(tmp_path: Path) -> Path:
    """
    Create a file with .pdf extension but garbage content.
    For testing that the extractor properly rejects invalid PDFs.
    """
    invalid_pdf = tmp_path / "not_a_real_pdf.pdf"
    invalid_pdf.write_bytes(b"This is definitely not a PDF file, just random text.")
    return invalid_pdf


@pytest.fixture
def empty_file_pdf_path(tmp_path: Path) -> Path:
    """Create an empty file with .pdf extension."""
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")
    return empty_pdf


@pytest.fixture
def temp_json_output_path(tmp_path: Path) -> Path:
    """Return a temporary path for JSON output."""
    return tmp_path / "output.json"
