"""
Pytest configuration and fixtures for pdf_2_json_extractor tests.
"""

import os
import tempfile
from unittest.mock import Mock

import pytest


@pytest.fixture
def sample_pdf():
    """Create a temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Write minimal PDF content (this is not a real PDF, just for testing)
        tmp.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
        tmp_path = tmp.name

    yield tmp_path

    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
def sample_json_output():
    """Sample JSON output for testing."""
    return {
        "title": "Test Document",
        "sections": [
            {
                "level": "H1",
                "title": "Introduction",
                "paragraphs": ["This is the introduction paragraph."]
            },
            {
                "level": "H2",
                "title": "Overview",
                "paragraphs": ["This is the overview section."]
            },
            {
                "level": "content",
                "title": None,
                "paragraphs": ["This is regular content."]
            }
        ],
        "font_histogram": {
            "12.0": 100,
            "14.0": 50,
            "16.0": 25
        },
        "heading_levels": {
            "16.0": "H1",
            "14.0": "H2"
        },
        "stats": {
            "page_count": 1,
            "processing_time": 1.5,
            "num_sections": 3,
            "num_headings": 2,
            "num_paragraphs": 3
        }
    }


@pytest.fixture
def mock_document():
    """Mock PyMuPDF document for testing."""
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
                            {"text": "Title", "size": 16.0, "bbox": [0, 0, 100, 20]},
                            {"text": "Body text", "size": 12.0, "bbox": [0, 25, 100, 35]}
                        ]
                    }
                ]
            }
        ]
    }

    mock_doc.__getitem__ = Mock(return_value=mock_page)
    return mock_doc
