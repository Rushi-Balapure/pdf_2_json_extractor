"""
End-to-end tests for PDFStructureExtractor.

Real PDFs, real extraction, real results.
"""

from pathlib import Path

import pymupdf as fitz
import pytest

from pdf_2_json_extractor.config import Config
from pdf_2_json_extractor.exceptions import InvalidPDFError, PDFFileNotFoundError
from pdf_2_json_extractor.extractor import PDFStructureExtractor


class TestPDFStructureExtractorInit:
    """Test extractor initialization."""

    def test_init_with_default_config(self):
        """Extractor should work with default config."""
        extractor = PDFStructureExtractor()
        assert extractor.config is not None
        assert isinstance(extractor.config, Config)

    def test_init_with_custom_config(self):
        """Extractor should accept custom config."""
        custom_config = Config()
        custom_config.MAX_PAGES_FOR_FONT_ANALYSIS = 5
        extractor = PDFStructureExtractor(custom_config)
        assert extractor.config.MAX_PAGES_FOR_FONT_ANALYSIS == 5


class TestExtractTextWithStructure:
    """E2E tests for the main extraction method."""

    def test_extracts_real_pdf(self, real_pdf_path: Path):
        """Extract a real PDF and verify the structure."""
        extractor = PDFStructureExtractor()
        result = extractor.extract_text_with_structure(str(real_pdf_path))

        # Verify complete output structure
        assert "title" in result
        assert "sections" in result
        assert "font_histogram" in result
        assert "heading_levels" in result
        assert "stats" in result

        # Verify we got actual content
        assert len(result["sections"]) > 0
        assert result["stats"]["page_count"] > 0
        assert result["stats"]["processing_time"] > 0

    def test_file_not_found(self, nonexistent_pdf_path: Path):
        """Should raise PDFFileNotFoundError for missing files."""
        extractor = PDFStructureExtractor()
        with pytest.raises(PDFFileNotFoundError):
            extractor.extract_text_with_structure(str(nonexistent_pdf_path))

    def test_invalid_pdf(self, invalid_pdf_path: Path):
        """Should raise InvalidPDFError for garbage files."""
        extractor = PDFStructureExtractor()
        with pytest.raises(InvalidPDFError):
            extractor.extract_text_with_structure(str(invalid_pdf_path))

    def test_empty_file(self, empty_file_pdf_path: Path):
        """Should raise InvalidPDFError for empty files."""
        extractor = PDFStructureExtractor()
        with pytest.raises(InvalidPDFError):
            extractor.extract_text_with_structure(str(empty_file_pdf_path))


class TestFontAnalysis:
    """Test font size analysis on real documents."""

    def test_analyze_font_sizes_on_real_pdf(self, real_pdf_path: Path):
        """Font analysis should return sensible histogram and heading levels."""
        extractor = PDFStructureExtractor()

        with fitz.open(str(real_pdf_path)) as doc:
            font_histogram, heading_levels = extractor.analyze_font_sizes(doc)

        # Should have found some fonts
        assert len(font_histogram) > 0

        # All font sizes should be positive
        for size, count in font_histogram.items():
            assert size > 0
            assert count > 0

        # If heading levels were detected, they should be valid
        for size, level in heading_levels.items():
            assert level.startswith("H")
            level_num = int(level[1:])
            assert 1 <= level_num <= 6


class TestParagraphGrouping:
    """Test paragraph grouping logic."""

    def test_groups_close_lines_together(self):
        """Lines close together should be grouped into one paragraph."""
        extractor = PDFStructureExtractor()
        lines = [
            {"text": "Line 1", "font_size": 12.0, "top": 100, "bottom": 112},
            {"text": "Line 2", "font_size": 12.0, "top": 114, "bottom": 126},
            {"text": "Line 3", "font_size": 12.0, "top": 128, "bottom": 140},
        ]

        paragraphs = extractor._group_paragraphs(lines)

        # All lines are close, should be one paragraph
        assert len(paragraphs) == 1
        assert len(paragraphs[0]) == 3

    def test_splits_on_large_gaps(self):
        """Lines with large vertical gaps should be split into separate paragraphs."""
        extractor = PDFStructureExtractor()
        lines = [
            {"text": "Para 1 Line 1", "font_size": 12.0, "top": 100, "bottom": 112},
            {"text": "Para 1 Line 2", "font_size": 12.0, "top": 114, "bottom": 126},
            # Big gap here
            {"text": "Para 2 Line 1", "font_size": 12.0, "top": 200, "bottom": 212},
            {"text": "Para 2 Line 2", "font_size": 12.0, "top": 214, "bottom": 226},
        ]

        paragraphs = extractor._group_paragraphs(lines)

        assert len(paragraphs) == 2
        assert len(paragraphs[0]) == 2
        assert len(paragraphs[1]) == 2

    def test_handles_empty_input(self):
        """Empty input should return empty output."""
        extractor = PDFStructureExtractor()
        paragraphs = extractor._group_paragraphs([])
        assert paragraphs == []

    def test_handles_single_line(self):
        """Single line should be its own paragraph."""
        extractor = PDFStructureExtractor()
        lines = [{"text": "Solo line", "font_size": 12.0, "top": 100, "bottom": 112}]

        paragraphs = extractor._group_paragraphs(lines)

        assert len(paragraphs) == 1
        assert len(paragraphs[0]) == 1


class TestHeadingClassification:
    """Test heading level classification."""

    def test_classifies_known_sizes(self):
        """Known heading sizes should return correct levels."""
        extractor = PDFStructureExtractor()
        heading_levels = {18.0: "H1", 16.0: "H2", 14.0: "H3"}

        assert extractor._classify_level(18.0, heading_levels) == "H1"
        assert extractor._classify_level(16.0, heading_levels) == "H2"
        assert extractor._classify_level(14.0, heading_levels) == "H3"

    def test_returns_none_for_body_text(self):
        """Body text sizes should return None."""
        extractor = PDFStructureExtractor()
        heading_levels = {18.0: "H1", 16.0: "H2"}

        assert extractor._classify_level(12.0, heading_levels) is None
        assert extractor._classify_level(10.0, heading_levels) is None

    def test_handles_rounding(self):
        """Font sizes should be rounded for comparison."""
        extractor = PDFStructureExtractor()
        heading_levels = {16.0: "H1"}

        # 16.04 rounds to 16.0
        assert extractor._classify_level(16.04, heading_levels) == "H1"


class TestTitleExtraction:
    """Test title extraction from documents."""

    def test_extracts_title_from_real_pdf(self, real_pdf_path: Path):
        """Should extract a non-empty title from a real PDF."""
        extractor = PDFStructureExtractor()

        with fitz.open(str(real_pdf_path)) as doc:
            title = extractor._extract_title(doc, {})

        assert title is not None
        assert len(title) > 0
        assert title != "Untitled Document"


class TestConfig:
    """Test Config class."""

    def test_config_defaults(self):
        """Default config values should be sensible."""
        config = Config()

        assert config.MAX_PAGES_FOR_FONT_ANALYSIS == 10
        assert config.MIN_HEADING_FREQUENCY == 0.001
        assert config.MAX_HEADING_LEVELS == 6

    def test_get_config_returns_dict(self):
        """get_config should return a dictionary representation."""
        config = Config()
        config_dict = config.get_config()

        assert isinstance(config_dict, dict)
        assert "max_pages_for_font_analysis" in config_dict
        assert config_dict["max_pages_for_font_analysis"] == 10

    def test_instances_are_independent(self):
        """Modifying one Config instance should not affect others."""
        config1 = Config()
        config2 = Config()

        # Modify config1
        config1.MAX_PAGES_FOR_FONT_ANALYSIS = 99

        # config2 should be unchanged
        assert config2.MAX_PAGES_FOR_FONT_ANALYSIS == 10
        assert config1.MAX_PAGES_FOR_FONT_ANALYSIS == 99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
