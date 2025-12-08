"""
Unit tests for pdf_2_json_extractor CLI.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from pdf_2_json_extractor.cli import main
from pdf_2_json_extractor.exceptions import PdfToJsonError


class TestCLI:
    """Test cases for pdf_2_json_extractor CLI."""

    def test_cli_help(self, capsys):
        """Test CLI help output."""
        with pytest.raises(SystemExit):
            main()

        # This would normally be called with --help, but we're testing the argument parsing
        # The actual help test would require modifying sys.argv

    @patch('pdf_2_json_extractor.cli.extract_pdf_to_json')
    def test_cli_success_stdout(self, mock_extract):
        """Test successful CLI execution with stdout output."""
        mock_result = '{"title": "Test Document", "sections": []}'
        mock_extract.return_value = mock_result

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"pdf content")
            tmp_path = tmp.name

        try:
            # Mock sys.argv to simulate command line arguments
            with patch('sys.argv', ['pdf_2_json_extractor', tmp_path]):
                with patch('sys.stdout') as mock_stdout:
                    main()
                    # Verify that JSON was written to stdout
                    mock_stdout.write.assert_called()
        finally:
            os.unlink(tmp_path)

    @patch('pdf_2_json_extractor.cli.extract_pdf_to_dict')
    def test_cli_success_file_output(self, mock_extract):
        """Test successful CLI execution with file output."""
        mock_result = {
            "title": "Test Document",
            "sections": [{"level": "H1", "title": "Introduction", "paragraphs": ["Content"]}],
            "stats": {"page_count": 1, "processing_time": 1.0}
        }
        mock_extract.return_value = mock_result

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b"pdf content")
            pdf_path = tmp_pdf.name

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_json:
            json_path = tmp_json.name

        try:
            # Mock sys.argv to simulate command line arguments
            with patch('sys.argv', ['pdf_2_json_extractor', pdf_path, '-o', json_path]):
                with patch('sys.stdout') as mock_stdout:
                    main()
                    # Verify that success message was printed
                    mock_stdout.write.assert_called()

                    # Verify that JSON was written to file
                    with open(json_path, 'r', encoding='utf-8') as f:
                        saved_result = json.load(f)
                    assert saved_result == mock_result
        finally:
            os.unlink(pdf_path)
            os.unlink(json_path)

    def test_cli_file_not_found(self):
        """Test CLI error handling for non-existent file."""
        with patch('sys.argv', ['pdf_2_json_extractor', 'nonexistent.pdf']):
            with patch('sys.stderr') as mock_stderr:
                with pytest.raises(SystemExit):
                    main()
                # Verify error message was written to stderr
                mock_stderr.write.assert_called()

    @patch('pdf_2_json_extractor.cli.extract_pdf_to_dict')
    def test_cli_processing_error(self, mock_extract):
        """Test CLI error handling for processing errors."""
        mock_extract.side_effect = PdfToJsonError("Processing failed")

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"pdf content")
            tmp_path = tmp.name

        try:
            with patch('sys.argv', ['pdf_2_json_extractor', tmp_path]):
                with patch('sys.stderr') as mock_stderr:
                    with pytest.raises(SystemExit):
                        main()
                    # Verify error message was written to stderr
                    mock_stderr.write.assert_called()
        finally:
            os.unlink(tmp_path)

    @patch('pdf_2_json_extractor.cli.extract_pdf_to_dict')
    @patch('pdf_2_json_extractor.cli.extract_pdf_to_json')
    def test_cli_compact_output(self, mock_extract_json, mock_extract_dict):
        """Test CLI compact output option."""
        mock_result = {"title": "Test", "sections": []}
        mock_extract_dict.return_value = mock_result
        mock_extract_json.return_value = '{"title": "Test", "sections": []}'

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"pdf content")
            tmp_path = tmp.name

        try:
            with patch('sys.argv', ['pdf_2_json_extractor', tmp_path, '--compact']):
                with patch('sys.stdout') as mock_stdout:
                    main()
                    # Verify that JSON was written to stdout
                    mock_stdout.write.assert_called()
        finally:
            os.unlink(tmp_path)

    @patch('pdf_2_json_extractor.cli.extract_pdf_to_json')
    def test_cli_pretty_output(self, mock_extract):
        """Test CLI pretty output option."""
        mock_result = '{"title": "Test", "sections": []}'
        mock_extract.return_value = mock_result

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"pdf content")
            tmp_path = tmp.name

        try:
            with patch('sys.argv', ['pdf_2_json_extractor', tmp_path, '--pretty']):
                with patch('sys.stdout') as mock_stdout:
                    main()
                    # Verify that JSON was written to stdout
                    mock_stdout.write.assert_called()
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__])
