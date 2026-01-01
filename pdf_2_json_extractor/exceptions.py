"""
Custom exceptions for pdf_2_json_extractor library.
"""

from typing import Any, Optional

class PdfToJsonError(Exception):
    """Base exception for pdf_2_json_extractor library."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class PDFProcessingError(PdfToJsonError):
    """Raised when PDF processing fails."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None, details: Optional[dict[str, Any]] = None):
        super().__init__(message, details)
        self.original_expection = original_exception

class InvalidPDFError(PdfToJsonError):
    """Raised when the PDF file is invalid or corrupted."""
    def __init__(self, message: str, path: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        super().__init__(message, details)
        self.path = path

class PDFFileNotFoundError(PdfToJsonError):
    """Raised when the PDF file is not found."""
    def __init__(self, path: str, message: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        if message is None:
            message = f"PDF file not found: {path}"
        super().__init__(message, details)
        self.path = path
