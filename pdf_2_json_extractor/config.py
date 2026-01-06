"""
Configuration for pdf_2_json_extractor library.
"""

import os
from typing import Any


class Config:
    """Configuration class for pdf_2_json_extractor library."""

    # How many pages to analyze when detecting heading font sizes
    MAX_PAGES_FOR_FONT_ANALYSIS = int(os.getenv("PDF_TO_JSON_MAX_PAGES_FOR_FONT_ANALYSIS", "10"))

    # Minimum frequency (as fraction of total chars) for a font size to be considered a heading
    MIN_HEADING_FREQUENCY = float(os.getenv("PDF_TO_JSON_MIN_HEADING_FREQUENCY", "0.001"))

    # Maximum heading level to assign (H1 through H{MAX_HEADING_LEVELS})
    MAX_HEADING_LEVELS = int(os.getenv("PDF_TO_JSON_MAX_HEADING_LEVELS", "6"))

    @classmethod
    def get_config(cls) -> dict[str, Any]:
        """Return configuration as dictionary."""
        return {
            "max_pages_for_font_analysis": cls.MAX_PAGES_FOR_FONT_ANALYSIS,
            "min_heading_frequency": cls.MIN_HEADING_FREQUENCY,
            "max_heading_levels": cls.MAX_HEADING_LEVELS,
        }
