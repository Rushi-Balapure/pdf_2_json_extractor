"""
PDF structure extractor with layout-aware text extraction.
"""

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pymupdf as fitz  # PyMuPDF

from .config import Config
from .exceptions import InvalidPDFError, PDFFileNotFoundError, PDFProcessingError

# Configure logging
logging.basicConfig(level = getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

@dataclass
class FontInfo:
    """Font information for text spans."""
    size: float
    name: str
    flags: int

@dataclass
class TextSpan:
    """Text span with font and layout information."""
    text: str
    font_info: FontInfo
    bbox: tuple
    level: Optional[str] = None

class PDFStructureExtractor:
    """
    High-performance PDF structure extractor optimized for CPU processing.
    Supports multilingual text extraction and heading detection based on font analysis.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the PDF structure extractor.

        Args:
            config (Config, optional): Configuration object. If None, uses default config.
        """
        self.config = config or Config()
        self.font_size_histogram = defaultdict(int)
        self.heading_levels = {}

    def analyze_font_sizes(self, doc: fitz.Document) -> tuple[Dict[float, int], Dict[float, str]]:
        """Analyze font sizes across the document to determine heading levels."""
        font_histogram = defaultdict(int)
        total_chars = 0

        max_pages = min(len(doc), self.config.MAX_PAGES_FOR_FONT_ANALYSIS)

        for page_num in range(max_pages):
            blocks = doc[page_num].get_text("dict").get("blocks", [])
            for block in blocks:
                lines = block.get("lines")
                if not lines:
                    continue
                for line in lines:
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        if not text or not text.strip():
                            continue
                        size = span.get("size", 0)
                        font_size = round(float(size), 1)
                        char_count = len(text)
                        font_histogram[font_size] += char_count
                        total_chars += char_count

        # Determine heading levels based on frequency and size
        heading_levels = {}
        if font_histogram:
            sorted_fonts_desc = sorted(font_histogram.items(), key=lambda x: x[0], reverse=True)
            main_font_size = max(font_histogram.items(), key=lambda x: x[1])[0]
            level_index = 1
            for font_size, count in sorted_fonts_desc:
                if font_size > main_font_size and count > total_chars * self.config.MIN_HEADING_FREQUENCY:
                    heading_levels[font_size] = f"H{min(level_index, self.config.MAX_HEADING_LEVELS)}"
                    level_index += 1

        return font_histogram, heading_levels

    def _iter_lines(self, doc: fitz.Document):
        """Yield lines with their concatenated text, max font size, and y-position bounds."""
        for page_num in range(len(doc)):
            blocks = doc[page_num].get_text("dict").get("blocks", [])
            for block in blocks:
                lines = block.get("lines")
                if not lines:
                    continue
                for line in lines:
                    text_parts: List[str] = []
                    max_size = 0.0
                    top_y = None
                    bottom_y = None
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        if not text or not text.strip():
                            continue
                        text_parts.append(text)
                        size = float(span.get("size", 0.0))
                        if size > max_size:
                            max_size = size
                        bbox = span.get("bbox")
                        if bbox:
                            span_top, span_bottom = bbox[1], bbox[3]
                            top_y = span_top if top_y is None else min(top_y, span_top)
                            bottom_y = span_bottom if bottom_y is None else max(bottom_y, span_bottom)
                    if not text_parts:
                        continue
                    yield {
                        "page": page_num,
                        "text": "".join(text_parts).strip(),
                        "font_size": round(max_size, 1),
                        "top": top_y,
                        "bottom": bottom_y,
                    }

    def _classify_level(self, line_font_size: float, heading_levels: Dict[float, str]) -> Optional[str]:
        """Return heading level like 'H1'..'H6' if font size matches, else None."""
        return heading_levels.get(round(line_font_size, 1))

    def _group_paragraphs(self, lines: List[Dict[str, Any]], gap_multiplier: float = 0.8) -> List[List[Dict[str, Any]]]:
        """Group consecutive lines into paragraphs based on vertical gaps."""
        paragraphs: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = []

        prev_bottom = None
        for ln in lines:
            if prev_bottom is None:
                current = [ln]
                prev_bottom = ln.get("bottom")
                continue

            top = ln.get("top")
            font_size = ln.get("font_size") or 0.0
            # Heuristic threshold: if the gap is larger than k * font_size, start a new paragraph
            threshold = (font_size or 10.0) * gap_multiplier
            gap = (top - prev_bottom) if (top is not None and prev_bottom is not None) else threshold + 1

            if gap is not None and gap > threshold:
                if current:
                    paragraphs.append(current)
                current = [ln]
            else:
                current.append(ln)
            prev_bottom = ln.get("bottom")

        if current:
            paragraphs.append(current)

        return paragraphs

    def extract_text_with_structure(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text with hierarchical structure from PDF.
        Returns JSON format with title and outline.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            Dict[str, Any]: Dictionary containing extracted PDF structure

        Raises:
            PDFFileNotFoundError: If PDF file doesn't exist
            InvalidPDFError: If PDF file is corrupted
            PDFProcessingError: If processing fails
        """
        start_time = time.time()

        if not os.path.exists(pdf_path):
            raise PDFFileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)

            # Analyze font sizes for heading detection
            font_histogram, heading_levels = self.analyze_font_sizes(doc)

            # Extract document title (usually from first page, largest non-body font)
            title = self._extract_title(doc, heading_levels)

            # Extract structured content
            sections: List[Dict[str, Any]] = []
            current_section: Optional[Dict[str, Any]] = None

            # Collect all non-empty lines first with layout info
            all_lines: List[Dict[str, Any]] = list(self._iter_lines(doc))

            # Split by headings and group non-heading lines into paragraphs per section
            buffer_non_heading: List[Dict[str, Any]] = []
            for ln in all_lines:
                level = self._classify_level(ln["font_size"], heading_levels)
                if level:
                    # Flush any buffered content as a paragraph section if present
                    if buffer_non_heading:
                        paragraphs = self._group_paragraphs(buffer_non_heading)
                        if current_section is None:
                            current_section = {"level": "content", "title": None, "paragraphs": []}
                            sections.append(current_section)
                        current_section["paragraphs"].extend([" ".join(p_i["text"] for p_i in para) for para in paragraphs])
                        buffer_non_heading = []

                    # Start a new heading section
                    current_section = {"level": level, "title": ln["text"], "paragraphs": []}
                    sections.append(current_section)
                else:
                    buffer_non_heading.append(ln)

            # Flush remaining buffer into the last/current section
            if buffer_non_heading:
                paragraphs = self._group_paragraphs(buffer_non_heading)
                if current_section is None:
                    current_section = {"level": "content", "title": None, "paragraphs": []}
                    sections.append(current_section)
                current_section["paragraphs"].extend([" ".join(p_i["text"] for p_i in para) for para in paragraphs])

            page_count = len(doc)
            doc.close()

            processing_time = time.time() - start_time
            logger.info(f"Processing completed in {processing_time:.2f} seconds")

            # Prepare enriched output
            num_headings = sum(1 for s in sections if s.get("level", "").startswith("H"))
            num_paragraphs = sum(len(s.get("paragraphs", [])) for s in sections)

            return {
                "title": title,
                "sections": sections,
                "font_histogram": {str(k): v for k, v in sorted(font_histogram.items())},
                "heading_levels": {str(k): v for k, v in heading_levels.items()},
                "stats": {
                    "page_count": page_count,
                    "processing_time": processing_time,
                    "num_sections": len(sections),
                    "num_headings": num_headings,
                    "num_paragraphs": num_paragraphs
                }
            }

        except fitz.FileDataError as e:
            raise InvalidPDFError(f"Invalid or corrupted PDF file: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise PDFProcessingError(f"Failed to process PDF: {str(e)}")

    def _extract_title(self, doc: fitz.Document, heading_levels: Dict[float, str]) -> str:
        """Extract document title from first page."""
        if len(doc) == 0:
            return "Untitled Document"

        first_page = doc[0]
        blocks = first_page.get_text("dict")["blocks"]

        # Look for the largest text on the first page
        largest_text = ""
        largest_size = 0

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    if span["text"].strip() and span["size"] > largest_size:
                        largest_size = span["size"]
                        largest_text = span["text"].strip()

        return largest_text if largest_text else "Untitled Document"
