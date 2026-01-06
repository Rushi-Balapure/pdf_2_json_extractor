"""
Configuration for pdf_2_json_extractor library.
"""

import os
from dataclasses import dataclass, field
from typing import Any


def _env_int(key: str, default: int) -> int:
    """Read an integer from environment variable with fallback."""
    return int(os.getenv(key, str(default)))


def _env_float(key: str, default: float) -> float:
    """Read a float from environment variable with fallback."""
    return float(os.getenv(key, str(default)))


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

    def get_config(self) -> dict[str, Any]:
        """Return configuration as dictionary."""
        return {
            "max_pages_for_font_analysis": self.MAX_PAGES_FOR_FONT_ANALYSIS,
            "min_heading_frequency": self.MIN_HEADING_FREQUENCY,
            "max_heading_levels": self.MAX_HEADING_LEVELS,
        }
