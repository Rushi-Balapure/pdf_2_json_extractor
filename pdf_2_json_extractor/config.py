"""
Configuration for pdf_2_json_extractor library.
"""

import os
from dataclasses import dataclass, field
from typing import Any

from .exceptions import ConfigError


def _env_int(key: str, default: int) -> int:
    """Read an integer from environment variable with fallback."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {key} must be an integer, got {raw!r}") from exc


def _env_float(key: str, default: float) -> float:
    """Read a float from environment variable with fallback."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {key} must be a number, got {raw!r}") from exc


def _env_bool(key: str, default: bool) -> bool:
    """Read a boolean from an environment variable with fallback."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_str(key: str, default: str) -> str:
    """Read a non-empty string from an environment variable with fallback."""
    value = os.getenv(key, "").strip()
    return value or default


@dataclass
class Config:
    """
    Configuration for pdf_2_json_extractor.

    Each instance has its own settings. Modify instance attributes freely
    without affecting other instances or the defaults.

    Environment variables are read at instance creation time as defaults.
    """

    # How many pages to analyze when detecting heading font sizes
    MAX_PAGES_FOR_FONT_ANALYSIS: int = field(
        default_factory=lambda: _env_int("PDF_TO_JSON_MAX_PAGES_FOR_FONT_ANALYSIS", 10)
    )

    # Minimum frequency (as fraction of total chars) for a font size to be considered a heading
    MIN_HEADING_FREQUENCY: float = field(
        default_factory=lambda: _env_float("PDF_TO_JSON_MIN_HEADING_FREQUENCY", 0.001)
    )

    # Maximum heading level to assign (H1 through H{MAX_HEADING_LEVELS})
    MAX_HEADING_LEVELS: int = field(
        default_factory=lambda: _env_int("PDF_TO_JSON_MAX_HEADING_LEVELS", 6)
    )

    # Detect and order text in columns instead of trusting PDF block order
    DETECT_COLUMNS: bool = field(
        default_factory=lambda: _env_bool("PDF_TO_JSON_DETECT_COLUMNS", True)
    )

    # Promote short, separated bold lines to headings when size alone is insufficient
    USE_BOLD_AS_HEADING_SIGNAL: bool = field(
        default_factory=lambda: _env_bool("PDF_TO_JSON_USE_BOLD_AS_HEADING_SIGNAL", False)
    )

    # Tesseract language expression used for image-only pages, such as eng+fra
    OCR_LANGUAGE: str = field(
        default_factory=lambda: _env_str("PDF_TO_JSON_OCR_LANGUAGE", "eng")
    )

    # Include one-based source page numbers in headings and paragraph objects
    INCLUDE_PAGE_NUMBERS: bool = field(
        default_factory=lambda: _env_bool("PDF_TO_JSON_INCLUDE_PAGE_NUMBERS", False)
    )

    def __post_init__(self) -> None:
        """Validate numeric ranges after construction."""
        self.validate()

    def validate(self) -> None:
        """Raise ConfigError when numeric settings are outside supported ranges."""
        if self.MAX_PAGES_FOR_FONT_ANALYSIS < 1:
            raise ConfigError("MAX_PAGES_FOR_FONT_ANALYSIS must be at least 1")
        if not 0.0 <= self.MIN_HEADING_FREQUENCY <= 1.0:
            raise ConfigError("MIN_HEADING_FREQUENCY must be between 0 and 1")
        if not 1 <= self.MAX_HEADING_LEVELS <= 6:
            raise ConfigError("MAX_HEADING_LEVELS must be between 1 and 6")

    def get_config(self) -> dict[str, Any]:
        """Return configuration as dictionary."""
        return {
            "max_pages_for_font_analysis": self.MAX_PAGES_FOR_FONT_ANALYSIS,
            "min_heading_frequency": self.MIN_HEADING_FREQUENCY,
            "max_heading_levels": self.MAX_HEADING_LEVELS,
            "detect_columns": self.DETECT_COLUMNS,
            "use_bold_as_heading_signal": self.USE_BOLD_AS_HEADING_SIGNAL,
            "ocr_language": self.OCR_LANGUAGE,
            "include_page_numbers": self.INCLUDE_PAGE_NUMBERS,
        }
