"""
pdf_2_json_extractor - A high-performance PDF to JSON extraction library.

This library extracts structured content from PDF documents while preserving
document layout semantics such as headings (H1-H6) and body text, outputting
the extracted content as JSON.

Features:
- Layout-aware extraction with heading detection
- Multilingual support for various scripts
- High performance CPU-only processing
- Small footprint with minimal dependencies
- Offline operation with no internet required
"""

__version__ = "1.0.0"
__author__ = "Rushi Balapure"
__email__ = "rishibalapure12@gmail.com"

import json

from .config import Config
from .exceptions import InvalidPDFError, PDFProcessingError, PdfToJsonError
from .extractor import PDFStructureExtractor

__all__ = [
    "PDFStructureExtractor",
    "Config",
    "PdfToJsonError",
    "PDFProcessingError",
    "InvalidPDFError",
    "extract_pdf_to_json",
    "extract_pdf_to_dict"
]

def extract_pdf_to_json(pdf_path: str, output_path: str = None) -> str:
    """
    Extract PDF content to JSON string.

    Args:
        pdf_path (str): Path to the PDF file
        output_path (str, optional): Path to save JSON output. If None, returns JSON string.

    Returns:
        str: JSON string if output_path is None, otherwise saves to file and returns path

    Raises:
        PdfToJsonError: If PDF processing fails
    """
    extractor = PDFStructureExtractor()
    result = extractor.extract_text_with_structure(pdf_path)

    json_str = json.dumps(result, ensure_ascii = False, indent = 2)

    if output_path:
        with open(output_path, 'w', encoding = 'utf-8') as f:
            f.write(json_str)
        return output_path
    return json_str

def extract_pdf_to_dict(pdf_path: str) -> dict:
    """
    Extract PDF content to Python dictionary.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        dict: Dictionary containing extracted PDF structure

    Raises:
        PdfToJsonError: If PDF processing fails
    """
    extractor = PDFStructureExtractor()
    return extractor.extract_text_with_structure(pdf_path)
