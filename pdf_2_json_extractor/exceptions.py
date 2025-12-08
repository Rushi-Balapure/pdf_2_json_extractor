"""
Custom exceptions for pdf_2_json_extractor library.
"""

class PdfToJsonError(Exception):
    """Base exception for pdf_2_json_extractor library."""

class PDFProcessingError(PdfToJsonError):
    """Raised when PDF processing fails."""

class InvalidPDFError(PdfToJsonError):
    """Raised when the PDF file is invalid or corrupted."""

class PDFFileNotFoundError(PdfToJsonError):
    """Raised when the PDF file is not found."""
