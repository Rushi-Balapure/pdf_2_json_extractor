"""
End-to-end tests for pdf_2_json_extractor API functions.

These tests use real PDFs, no mocks. If something breaks here, it's actually broken.
"""

import json
from pathlib import Path

import pytest

from pdf_2_json_extractor import extract_pdf_to_dict, extract_pdf_to_json
from pdf_2_json_extractor.exceptions import InvalidPDFError, PDFFileNotFoundError


class TestExtractPdfToDict:
    """E2E tests for extract_pdf_to_dict function."""

    def test_extracts_real_pdf_successfully(self, real_pdf_path: Path):
        """Extract a real PDF and verify the output structure is sane."""
        result = extract_pdf_to_dict(str(real_pdf_path))

        # Verify top-level structure
        assert "title" in result
        assert "sections" in result
        assert "font_histogram" in result
        assert "heading_levels" in result
        assert "stats" in result

        # Verify stats are populated with real values
        stats = result["stats"]
        assert stats["page_count"] > 0
        assert stats["processing_time"] > 0
        assert stats["num_sections"] >= 0
        assert stats["num_paragraphs"] >= 0

        # Verify we actually extracted some content
        assert isinstance(result["sections"], list)
        assert len(result["sections"]) > 0

        # Verify sections have the expected shape
        for section in result["sections"]:
            assert "level" in section
            assert "paragraphs" in section
            assert isinstance(section["paragraphs"], list)

    def test_file_not_found_raises_proper_exception(self, nonexistent_pdf_path: Path):
        """Verify we get a clear error when the file doesn't exist."""
        with pytest.raises(PDFFileNotFoundError) as exc_info:
            extract_pdf_to_dict(str(nonexistent_pdf_path))

        assert "not found" in str(exc_info.value).lower()

    def test_invalid_pdf_raises_proper_exception(self, invalid_pdf_path: Path):
        """Verify garbage files are rejected with a clear error."""
        with pytest.raises(InvalidPDFError):
            extract_pdf_to_dict(str(invalid_pdf_path))

    def test_empty_file_raises_proper_exception(self, empty_file_pdf_path: Path):
        """Verify empty files are rejected."""
        with pytest.raises(InvalidPDFError):
            extract_pdf_to_dict(str(empty_file_pdf_path))


class TestExtractPdfToJson:
    """E2E tests for extract_pdf_to_json function."""

    def test_returns_valid_json_string(self, real_pdf_path: Path):
        """Extract a real PDF and verify the JSON output is parseable."""
        json_str = extract_pdf_to_json(str(real_pdf_path))

        # Must be valid JSON
        result = json.loads(json_str)

        # Same structure checks as dict version
        assert "title" in result
        assert "sections" in result
        assert "stats" in result
        assert result["stats"]["page_count"] > 0

    def test_saves_to_file_when_output_path_provided(
        self, real_pdf_path: Path, temp_json_output_path: Path
    ):
        """Verify JSON is correctly written to file."""
        returned_path = extract_pdf_to_json(
            str(real_pdf_path), str(temp_json_output_path)
        )

        # Should return the output path
        assert returned_path == str(temp_json_output_path)

        # File should exist and contain valid JSON
        assert temp_json_output_path.exists()

        with open(temp_json_output_path, encoding="utf-8") as f:
            saved_result = json.load(f)

        assert "title" in saved_result
        assert "sections" in saved_result
        assert saved_result["stats"]["page_count"] > 0

    def test_json_is_utf8_encoded(self, real_pdf_path: Path, temp_json_output_path: Path):
        """Verify the JSON output handles unicode properly."""
        extract_pdf_to_json(str(real_pdf_path), str(temp_json_output_path))

        # Read as bytes and decode to verify encoding
        content = temp_json_output_path.read_bytes()
        decoded = content.decode("utf-8")

        # Should parse without errors
        json.loads(decoded)

    def test_file_not_found_raises_proper_exception(self, nonexistent_pdf_path: Path):
        """Verify we get a clear error when the file doesn't exist."""
        with pytest.raises(PDFFileNotFoundError):
            extract_pdf_to_json(str(nonexistent_pdf_path))

    def test_invalid_pdf_raises_proper_exception(self, invalid_pdf_path: Path):
        """Verify garbage files are rejected."""
        with pytest.raises(InvalidPDFError):
            extract_pdf_to_json(str(invalid_pdf_path))


class TestApiConsistency:
    """Verify dict and json APIs return equivalent data."""

    def test_dict_and_json_apis_return_same_data(self, real_pdf_path: Path):
        """Both API functions should return structurally identical data."""
        dict_result = extract_pdf_to_dict(str(real_pdf_path))
        json_result = json.loads(extract_pdf_to_json(str(real_pdf_path)))

        # Title and sections should match
        assert dict_result["title"] == json_result["title"]
        assert len(dict_result["sections"]) == len(json_result["sections"])

        # Stats should match (except processing_time which varies)
        assert dict_result["stats"]["page_count"] == json_result["stats"]["page_count"]
        assert dict_result["stats"]["num_sections"] == json_result["stats"]["num_sections"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
