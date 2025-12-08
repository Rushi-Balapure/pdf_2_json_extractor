"""
Unit tests for pdf_2_json_extractor API functions.
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from pdf_2_json_extractor import extract_pdf_to_dict, extract_pdf_to_json
from pdf_2_json_extractor.exceptions import PDFFileNotFoundError, PDFProcessingError


class TestAPI:
    """Test cases for pdf_2_json_extractor API functions."""

    def test_extract_pdf_to_dict_success(self):
        """Test successful PDF extraction to dictionary."""
        mock_result = {
            "title": "Test Document",
            "sections": [
                {"level": "H1", "title": "Introduction", "paragraphs": ["Content"]}
            ],
            "stats": {"page_count": 1, "processing_time": 1.0}
        }

        with patch('pdf_2_json_extractor.PDFStructureExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_text_with_structure.return_value = mock_result
            mock_extractor_class.return_value = mock_extractor

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(b"pdf content")
                tmp_path = tmp.name

            try:
                result = extract_pdf_to_dict(tmp_path)
                assert result == mock_result
                mock_extractor.extract_text_with_structure.assert_called_once_with(tmp_path)
            finally:
                os.unlink(tmp_path)

    def test_extract_pdf_to_dict_file_not_found(self):
        """Test error handling for non-existent file."""
        with pytest.raises(PDFFileNotFoundError):
            extract_pdf_to_dict("nonexistent.pdf")

    def test_extract_pdf_to_dict_processing_error(self):
        """Test error handling for processing errors."""
        with patch('pdf_2_json_extractor.PDFStructureExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_text_with_structure.side_effect = PDFProcessingError("Processing failed")
            mock_extractor_class.return_value = mock_extractor

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(b"pdf content")
                tmp_path = tmp.name

            try:
                with pytest.raises(PDFProcessingError):
                    extract_pdf_to_dict(tmp_path)
            finally:
                os.unlink(tmp_path)

    def test_extract_pdf_to_json_success(self):
        """Test successful PDF extraction to JSON string."""
        mock_result = {
            "title": "Test Document",
            "sections": [{"level": "H1", "title": "Introduction", "paragraphs": ["Content"]}],
            "stats": {"page_count": 1, "processing_time": 1.0}
        }

        with patch('pdf_2_json_extractor.PDFStructureExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_text_with_structure.return_value = mock_result
            mock_extractor_class.return_value = mock_extractor

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(b"pdf content")
                tmp_path = tmp.name

            try:
                json_str = extract_pdf_to_json(tmp_path)
                result = json.loads(json_str)
                assert result == mock_result
            finally:
                os.unlink(tmp_path)

    def test_extract_pdf_to_json_save_to_file(self):
        """Test saving JSON output to file."""
        mock_result = {
            "title": "Test Document",
            "sections": [{"level": "H1", "title": "Introduction", "paragraphs": ["Content"]}],
            "stats": {"page_count": 1, "processing_time": 1.0}
        }

        with patch('pdf_2_json_extractor.PDFStructureExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_text_with_structure.return_value = mock_result
            mock_extractor_class.return_value = mock_extractor

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                tmp_pdf.write(b"pdf content")
                pdf_path = tmp_pdf.name

            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_json:
                json_path = tmp_json.name

            try:
                result_path = extract_pdf_to_json(pdf_path, json_path)
                assert result_path == json_path

                # Verify file was written
                with open(json_path, 'r', encoding='utf-8') as f:
                    saved_result = json.load(f)
                assert saved_result == mock_result
            finally:
                os.unlink(pdf_path)
                os.unlink(json_path)

    def test_extract_pdf_to_json_processing_error(self):
        """Test error handling for processing errors in JSON extraction."""
        with patch('pdf_2_json_extractor.PDFStructureExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_text_with_structure.side_effect = PDFProcessingError("Processing failed")
            mock_extractor_class.return_value = mock_extractor

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(b"pdf content")
                tmp_path = tmp.name

            try:
                with pytest.raises(PDFProcessingError):
                    extract_pdf_to_json(tmp_path)
            finally:
                os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__])
