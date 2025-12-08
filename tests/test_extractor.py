"""
Unit tests for pdf_2_json_extractor extractor.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from pdf_2_json_extractor.config import Config
from pdf_2_json_extractor.exceptions import PDFFileNotFoundError, PDFProcessingError
from pdf_2_json_extractor.extractor import PDFStructureExtractor


class TestPDFStructureExtractor:
    """Test cases for PDFStructureExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.extractor = PDFStructureExtractor(self.config)

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        extractor = PDFStructureExtractor()
        assert extractor.config is not None
        assert isinstance(extractor.config, Config)

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        custom_config = Config()
        custom_config.MAX_PAGES_FOR_FONT_ANALYSIS = 5
        extractor = PDFStructureExtractor(custom_config)
        assert extractor.config == custom_config

    def test_extract_text_with_structure_file_not_found(self):
        """Test error handling for non-existent file."""
        with pytest.raises(PDFFileNotFoundError):
            self.extractor.extract_text_with_structure("nonexistent.pdf")

    @patch('pdf_2_json_extractor.extractor.fitz.open')
    def test_extract_text_with_structure_invalid_pdf(self, mock_fitz_open):
        """Test error handling for invalid PDF."""
        mock_fitz_open.side_effect = Exception("Invalid PDF")

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"invalid pdf content")
            tmp_path = tmp.name

        try:
            with pytest.raises(PDFProcessingError):
                self.extractor.extract_text_with_structure(tmp_path)
        finally:
            os.unlink(tmp_path)

    @patch('pdf_2_json_extractor.extractor.fitz.open')
    def test_extract_text_with_structure_success(self, mock_fitz_open):
        """Test successful PDF extraction."""
        # Mock document
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=2)

        # Mock page
        mock_page = Mock()
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {"text": "Title", "size": 16.0, "bbox": [0, 0, 100, 20]}
                            ]
                        }
                    ]
                }
            ]
        }

        # Set up the document to return the mock page
        def get_page(self, index):
            return mock_page

        mock_doc.__getitem__ = get_page

        mock_fitz_open.return_value = mock_doc

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"valid pdf content")
            tmp_path = tmp.name

        try:
            result = self.extractor.extract_text_with_structure(tmp_path)

            assert "title" in result
            assert "sections" in result
            assert "font_histogram" in result
            assert "heading_levels" in result
            assert "stats" in result
            assert result["stats"]["page_count"] == 2

        finally:
            os.unlink(tmp_path)

    def test_analyze_font_sizes(self):
        """Test font size analysis."""
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=1)

        mock_page = Mock()
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {"text": "Heading", "size": 16.0},
                                {"text": "Body text", "size": 12.0}
                            ]
                        }
                    ]
                }
            ]
        }
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        font_histogram, heading_levels = self.extractor.analyze_font_sizes(mock_doc)

        assert isinstance(font_histogram, dict)
        assert isinstance(heading_levels, dict)
        assert 16.0 in font_histogram
        assert 12.0 in font_histogram

    def test_classify_level(self):
        """Test heading level classification."""
        heading_levels = {16.0: "H1", 14.0: "H2", 12.0: "H3"}

        assert self.extractor._classify_level(16.0, heading_levels) == "H1"
        assert self.extractor._classify_level(14.0, heading_levels) == "H2"
        assert self.extractor._classify_level(12.0, heading_levels) == "H3"
        assert self.extractor._classify_level(10.0, heading_levels) is None

    def test_group_paragraphs(self):
        """Test paragraph grouping."""
        lines = [
            {"text": "Line 1", "font_size": 12.0, "top": 100, "bottom": 110},
            {"text": "Line 2", "font_size": 12.0, "top": 115, "bottom": 125},
            {"text": "Line 3", "font_size": 12.0, "top": 200, "bottom": 210},  # Large gap
            {"text": "Line 4", "font_size": 12.0, "top": 215, "bottom": 225}
        ]

        paragraphs = self.extractor._group_paragraphs(lines)

        assert len(paragraphs) == 2  # Should be grouped into 2 paragraphs
        assert len(paragraphs[0]) == 2  # First paragraph has 2 lines
        assert len(paragraphs[1]) == 2  # Second paragraph has 2 lines

    def test_extract_title(self):
        """Test title extraction."""
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=1)

        mock_page = Mock()
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {"text": "Small text", "size": 10.0},
                                {"text": "Large Title", "size": 18.0}
                            ]
                        }
                    ]
                }
            ]
        }
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        title = self.extractor._extract_title(mock_doc, {})
        assert title == "Large Title"

    def test_extract_title_empty_document(self):
        """Test title extraction from empty document."""
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=0)

        title = self.extractor._extract_title(mock_doc, {})
        assert title == "Untitled Document"

    def test_extract_title_no_text(self):
        """Test title extraction when no text is found."""
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=1)

        mock_page = Mock()
        mock_page.get_text.return_value = {"blocks": []}
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        title = self.extractor._extract_title(mock_doc, {})
        assert title == "Untitled Document"


class TestConfig:
    """Test cases for Config class."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()

        assert config.MAX_PAGES_FOR_FONT_ANALYSIS == 10
        assert config.FONT_SIZE_PRECISION == 0.1
        assert config.MIN_HEADING_FREQUENCY == 0.001
        assert config.MIN_TEXT_LENGTH == 3
        assert config.MAX_HEADING_LEVELS == 6
        assert config.COMBINE_CONSECUTIVE_TEXT is True
        assert config.MULTILINGUAL_SUPPORT is True
        assert config.DEFAULT_ENCODING == "utf-8"
        assert config.PROCESS_PAGES_IN_CHUNKS is False
        assert config.CHUNK_SIZE == 10
        assert config.DEBUG_MODE is False
        assert config.LOG_LEVEL == "INFO"

    def test_get_config(self):
        """Test get_config method."""
        config = Config()
        config_dict = config.get_config()

        assert isinstance(config_dict, dict)
        assert "max_pages_for_font_analysis" in config_dict
        assert "font_size_precision" in config_dict
        assert "min_heading_frequency" in config_dict
        assert config_dict["max_pages_for_font_analysis"] == 10


if __name__ == "__main__":
    pytest.main([__file__])
