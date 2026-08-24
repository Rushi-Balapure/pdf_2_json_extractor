"""
Pytest configuration and fixtures for pdf_2_json_extractor tests.
"""

import os
import shutil
from pathlib import Path

import pymupdf as fitz
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
def scanned_pdf_path(tmp_path: Path) -> Path:
    """Create a scanned-like PDF page (image only, no text layer)."""
    if shutil.which("tesseract") is None:
        pytest.skip("tesseract is required for OCR fallback tests")

    source_pdf = tmp_path / "source_text.pdf"
    scanned_pdf = tmp_path / "scanned_like.pdf"

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Scanned OCR Test Heading", fontsize=24)
    page.insert_text((72, 120), "This is body text for OCR fallback.", fontsize=12)
    doc.save(str(source_pdf))
    doc.close()

    with fitz.open(str(source_pdf)) as src:
        pix = src[0].get_pixmap(matrix=fitz.Matrix(2, 2))

    out = fitz.open()
    image_page = out.new_page(width=pix.width, height=pix.height)
    image_page.insert_image(image_page.rect, stream=pix.tobytes("png"))
    out.save(str(scanned_pdf))
    out.close()

    return scanned_pdf


@pytest.fixture
def two_column_pdf_path(tmp_path: Path) -> Path:
    """Create a PDF whose insertion order conflicts with visual reading order."""
    pdf_path = tmp_path / "two_columns.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    page.insert_text((72, 60), "COLUMN READING ORDER", fontsize=18)
    page.insert_textbox(
        fitz.Rect(330, 100, 550, 300),
        "RIGHT-1 first right line\nRIGHT-2 second right line\nRIGHT-3 third right line",
        fontsize=11,
    )
    page.insert_textbox(
        fitz.Rect(50, 100, 270, 300),
        "LEFT-1 first left line\nLEFT-2 second left line\nLEFT-3 third left line",
        fontsize=11,
    )
    doc.save(str(pdf_path))
    doc.close()
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
