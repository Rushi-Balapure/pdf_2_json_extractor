"""
PDF structure extractor with layout-aware text extraction.
"""

import logging
import os
import time
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pymupdf as fitz  # PyMuPDF

from .config import Config
from .exceptions import InvalidPDFError, PDFFileNotFoundError, PDFProcessingError

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
    level: str | None = None

class PDFStructureExtractor:
    """
    High-performance PDF structure extractor optimized for CPU processing.
    Supports multilingual text extraction and heading detection based on font analysis.
    """

    def __init__(self, config: Config | None = None):
        """
        Initialize the PDF structure extractor.

        Args:
            config (Config, optional): Configuration object. If None, uses default config.
        """
        self.config = config or Config()
        self.font_size_histogram: defaultdict[float, int] = defaultdict(int)
        self.heading_levels: dict[float, str] = {}

    def analyze_font_sizes(self, doc: fitz.Document) -> tuple[dict[float, int], dict[float, str]]:
        """Analyze font sizes across the document to determine heading levels."""
        font_histogram: defaultdict[float, int] = defaultdict(int)
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
        if font_histogram and total_chars > 0:
            sorted_fonts_desc = sorted(font_histogram.items(), key=lambda x: x[0], reverse=True)
            main_font_size = max(font_histogram.items(), key=lambda x: x[1])[0]
            level_index = 1
            for font_size, count in sorted_fonts_desc:
                if font_size > main_font_size and count > total_chars * self.config.MIN_HEADING_FREQUENCY:
                    heading_levels[font_size] = f"H{min(level_index, self.config.MAX_HEADING_LEVELS)}"
                    level_index += 1

        return font_histogram, heading_levels

    def _iter_lines(self, doc: fitz.Document) -> Iterator[dict[str, Any]]:
        """Yield lines with their concatenated text, max font size, and y-position bounds."""
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict").get("blocks", [])
            lines = list(self._iter_lines_from_blocks(page_num, blocks))
            if not lines:
                lines = list(self._iter_page_ocr(page_num, page))
            yield from self._order_page_lines(lines, page.rect.width)

    def _iter_lines_from_blocks(
        self, page_num: int, blocks: list[dict[str, Any]]
    ) -> Iterator[dict[str, Any]]:
        """Yield normalized line items from block dictionaries."""
        for block in blocks:
            lines = block.get("lines")
            if not lines:
                continue
            for line in lines:
                text_parts: list[str] = []
                max_size = 0.0
                bold_chars = 0
                total_chars = 0
                top_y = None
                bottom_y = None
                left_x = None
                right_x = None
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text or not text.strip():
                        continue
                    text_parts.append(text)
                    char_count = len(text.strip())
                    total_chars += char_count
                    if int(span.get("flags", 0)) & fitz.TEXT_FONT_BOLD:
                        bold_chars += char_count
                    size = float(span.get("size", 0.0))
                    if size > max_size:
                        max_size = size
                    bbox = span.get("bbox")
                    if bbox:
                        span_left, span_top, span_right, span_bottom = bbox
                        left_x = span_left if left_x is None else min(left_x, span_left)
                        right_x = span_right if right_x is None else max(right_x, span_right)
                        top_y = span_top if top_y is None else min(top_y, span_top)
                        bottom_y = span_bottom if bottom_y is None else max(bottom_y, span_bottom)
                if not text_parts:
                    continue
                bold_ratio = bold_chars / total_chars if total_chars else 0.0
                yield {
                    "page": page_num,
                    "text": "".join(text_parts).strip(),
                    "font_size": round(max_size, 1),
                    "is_bold": bold_ratio >= 0.8,
                    "bold_ratio": bold_ratio,
                    "left": left_x,
                    "right": right_x,
                    "top": top_y,
                    "bottom": bottom_y,
                }

    def _order_page_lines(
        self,
        lines: list[dict[str, Any]],
        page_width: float,
    ) -> list[dict[str, Any]]:
        """Return lines in visual reading order with paragraph flow markers."""
        if not lines:
            return []
        if not self.config.DETECT_COLUMNS:
            return [dict(line, flow_region=0) for line in lines]

        clusters = self._cluster_line_starts(lines, page_width)
        columns = self._select_column_clusters(clusters)
        if len(columns) < 2:
            return [dict(line, flow_region=0) for line in sorted(lines, key=self._line_position)]

        centers = [sum(float(line["left"]) for line in column) / len(column) for column in columns]
        boundaries = []
        for index in range(len(columns) - 1):
            next_left = min(float(line["left"]) for line in columns[index + 1])
            rights = sorted(
                float(line.get("right") or line["left"])
                for line in columns[index]
                if float(line.get("right") or line["left"]) < next_left
            )
            right_edge = rights[(len(rights) - 1) // 2] if rights else centers[index]
            boundaries.append((right_edge + next_left) / 2)
        column_line_ids = {id(line) for column in columns for line in column}
        rejected_line_ids = {
            id(line) for cluster in clusters if cluster not in columns and len(cluster) >= 2 for line in cluster
        }
        column_top = min(float(line.get("top") or 0.0) for column in columns for line in column)
        column_bottom = max(float(line.get("bottom") or 0.0) for column in columns for line in column)
        full_width: list[dict[str, Any]] = []
        column_lines: list[tuple[int, dict[str, Any]]] = []
        for line in lines:
            left = float(line.get("left") or 0.0)
            right = float(line.get("right") or left)
            top = float(line.get("top") or 0.0)
            outside_columns = id(line) not in column_line_ids and (top < column_top or top > column_bottom)
            if id(line) in rejected_line_ids or outside_columns or any(left < boundary < right for boundary in boundaries):
                full_width.append(line)
                continue
            column = min(range(len(centers)), key=lambda index: abs(left - centers[index]))
            column_lines.append((column, line))

        return self._order_flow_regions(column_lines, full_width)

    def _select_column_clusters(
        self, clusters: list[list[dict[str, Any]]]
    ) -> list[list[dict[str, Any]]]:
        """Select dense vertical flows whose page ranges overlap."""
        candidates = [
            cluster
            for index, cluster in enumerate(clusters)
            if len(cluster) >= 2
            and self._vertical_density(cluster) >= 0.15
            and not self._interior_cluster_spans_right(index, cluster, clusters)
        ]
        return [
            cluster
            for cluster in candidates
            if any(
                other is not cluster and self._vertical_overlap(cluster, other) >= 10.0
                for other in candidates
            )
        ]

    @staticmethod
    def _interior_cluster_spans_right(
        index: int,
        cluster: list[dict[str, Any]],
        clusters: list[list[dict[str, Any]]],
    ) -> bool:
        """Identify centered blocks that cross into the next text flow."""
        if index == 0 or index == len(clusters) - 1:
            return False
        rights = sorted(float(line.get("right") or line["left"]) for line in cluster)
        typical_right = rights[(len(rights) - 1) // 2]
        next_left = min(float(line["left"]) for line in clusters[index + 1])
        return typical_right >= next_left

    @staticmethod
    def _vertical_density(lines: list[dict[str, Any]]) -> float:
        """Measure how much of a cluster's vertical range contains text."""
        top = min(float(line.get("top") or 0.0) for line in lines)
        bottom = max(float(line.get("bottom") or top) for line in lines)
        occupied = sum(
            max(float(line.get("bottom") or 0.0) - float(line.get("top") or 0.0), 0.0)
            for line in lines
        )
        return occupied / (bottom - top) if bottom > top else 0.0

    @staticmethod
    def _vertical_overlap(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> float:
        """Return the shared vertical range between two candidate flows."""
        left_top = min(float(line.get("top") or 0.0) for line in left)
        left_bottom = max(float(line.get("bottom") or left_top) for line in left)
        right_top = min(float(line.get("top") or 0.0) for line in right)
        right_bottom = max(float(line.get("bottom") or right_top) for line in right)
        return max(min(left_bottom, right_bottom) - max(left_top, right_top), 0.0)

    @staticmethod
    def _cluster_line_starts(
        lines: list[dict[str, Any]], page_width: float
    ) -> list[list[dict[str, Any]]]:
        """Cluster lines by horizontal start using a page-relative gutter."""
        positioned = [line for line in lines if line.get("left") is not None]
        positioned.sort(key=lambda line: float(line["left"]))
        if not positioned:
            return []

        threshold = max(page_width * 0.18, 36.0)
        clusters = [[positioned[0]]]
        for line in positioned[1:]:
            previous_left = float(clusters[-1][-1]["left"])
            if float(line["left"]) - previous_left > threshold:
                clusters.append([line])
            else:
                clusters[-1].append(line)
        return clusters

    def _order_flow_regions(
        self,
        column_lines: list[tuple[int, dict[str, Any]]],
        full_width: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Order column bands around full-width separator lines."""
        ordered: list[dict[str, Any]] = []
        remaining = list(column_lines)
        band = 0
        for separator_group in self._group_separator_lines(full_width):
            separator_top = float(separator_group[0].get("top") or 0.0)
            before: list[tuple[int, dict[str, Any]]] = []
            after: list[tuple[int, dict[str, Any]]] = []
            for item in remaining:
                target = before if float(item[1].get("top") or 0.0) < separator_top else after
                target.append(item)
            remaining = after
            ordered.extend(self._sort_column_band(before, band))
            ordered.extend(dict(line, flow_region=f"separator-{band}") for line in separator_group)
            band += 1
        ordered.extend(self._sort_column_band(remaining, band))
        return ordered

    def _group_separator_lines(self, lines: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Keep adjacent full-width lines in the same paragraph flow."""
        groups: list[list[dict[str, Any]]] = []
        for line in sorted(lines, key=self._line_position):
            if not groups:
                groups.append([line])
                continue
            previous = groups[-1][-1]
            gap = float(line.get("top") or 0.0) - float(previous.get("bottom") or 0.0)
            threshold = max(float(line.get("font_size") or 10.0), 10.0) * 0.8
            if gap > threshold:
                groups.append([line])
            else:
                groups[-1].append(line)
        return groups

    def _sort_column_band(
        self, lines: list[tuple[int, dict[str, Any]]], band: int
    ) -> list[dict[str, Any]]:
        """Sort one horizontal band by column and vertical position."""
        return [
            dict(line, flow_region=f"{band}-{column}")
            for column, line in sorted(lines, key=lambda item: (item[0], *self._line_position(item[1])))
        ]

    @staticmethod
    def _line_position(line: dict[str, Any]) -> tuple[float, float]:
        """Return a stable top-left sort key for a normalized line."""
        return float(line.get("top") or 0.0), float(line.get("left") or 0.0)

    def _iter_lines_ocr(self, doc: fitz.Document) -> Iterator[dict[str, Any]]:
        """Yield OCR lines for every page in a document."""
        for page_num in range(len(doc)):
            page = doc[page_num]
            lines = list(self._iter_page_ocr(page_num, page))
            yield from self._order_page_lines(lines, page.rect.width)

    def _iter_page_ocr(self, page_num: int, page: fitz.Page) -> Iterator[dict[str, Any]]:
        """Yield normalized OCR lines for one page with actionable failures."""
        try:
            textpage = page.get_textpage_ocr(language=self.config.OCR_LANGUAGE)
        except RuntimeError as exc:
            language = self.config.OCR_LANGUAGE
            raise PDFProcessingError(
                f"OCR failed on page {page_num + 1} using language '{language}'. "
                "Ensure Tesseract and the requested language packs are installed."
            ) from exc
        blocks = page.get_text("dict", textpage=textpage).get("blocks", [])
        yield from self._iter_lines_from_blocks(page_num, blocks)

    def _classify_level(self, line_font_size: float, heading_levels: dict[float, str]) -> str | None:
        """Return heading level like 'H1'..'H6' if font size matches, else None."""
        return heading_levels.get(round(line_font_size, 1))

    def _classify_line(
        self,
        line: dict[str, Any],
        heading_levels: dict[float, str],
        previous_line: dict[str, Any] | None = None,
    ) -> str | None:
        """Classify a line using size first and optional font-weight evidence."""
        size_level = self._classify_level(float(line.get("font_size") or 0.0), heading_levels)
        if size_level or not self.config.USE_BOLD_AS_HEADING_SIGNAL:
            return size_level
        if not line.get("is_bold") or float(line.get("bold_ratio") or 0.0) < 0.8:
            return None

        text = " ".join(str(line.get("text") or "").split())
        if not text or len(text) > 80 or len(text.split()) > 12 or text.endswith((".", ",", ";")):
            return None
        if previous_line is not None and not self._has_heading_spacing(line, previous_line):
            return None

        used_levels = [int(level[1:]) for level in heading_levels.values() if level.startswith("H")]
        return f"H{min(max(used_levels, default=0) + 1, self.config.MAX_HEADING_LEVELS)}"

    @staticmethod
    def _has_heading_spacing(line: dict[str, Any], previous_line: dict[str, Any]) -> bool:
        """Return whether a bold line begins a new visual text region."""
        if line.get("page") != previous_line.get("page"):
            return True
        top = line.get("top")
        previous_bottom = previous_line.get("bottom")
        if top is None or previous_bottom is None:
            return False
        minimum_gap = float(line.get("font_size") or 10.0) * 0.5
        return float(top) - float(previous_bottom) >= minimum_gap

    def _group_paragraphs(self, lines: list[dict[str, Any]], gap_multiplier: float = 0.8) -> list[list[dict[str, Any]]]:
        """Group consecutive lines into paragraphs based on vertical gaps."""
        paragraphs: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []

        prev_bottom = None
        prev_page = None
        prev_flow_region = None
        for ln in lines:
            if prev_bottom is None:
                current = [ln]
                prev_bottom = ln.get("bottom")
                prev_page = ln.get("page")
                prev_flow_region = ln.get("flow_region")
                continue

            top = ln.get("top")
            font_size = ln.get("font_size") or 0.0
            # Heuristic threshold: if the gap is larger than k * font_size, start a new paragraph
            threshold = (font_size or 10.0) * gap_multiplier
            gap = (top - prev_bottom) if (top is not None and prev_bottom is not None) else threshold + 1

            flow_changed = ln.get("page") != prev_page or ln.get("flow_region") != prev_flow_region
            if flow_changed or (gap is not None and gap > threshold):
                if current:
                    paragraphs.append(current)
                current = [ln]
            else:
                current.append(ln)
            prev_bottom = ln.get("bottom")
            prev_page = ln.get("page")
            prev_flow_region = ln.get("flow_region")

        if current:
            paragraphs.append(current)

        return paragraphs

    def extract_text_with_structure(self, pdf_path: str) -> dict[str, Any]:
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

        doc: fitz.Document | None = None
        try:
            doc = fitz.open(pdf_path)

            # Validate that document has content
            if len(doc) == 0:
                raise InvalidPDFError("PDF document is empty")

            # Analyze font sizes for heading detection
            font_histogram, heading_levels = self.analyze_font_sizes(doc)

            # Extract document title (usually from first page, largest non-body font)
            title = self._extract_title(doc, heading_levels)

            # Extract structured content
            sections: list[dict[str, Any]] = []
            current_section: dict[str, Any] | None = None

            # Collect all non-empty lines first with layout info
            all_lines: list[dict[str, Any]] = list(self._iter_lines(doc))

            # Split by headings and group non-heading lines into paragraphs per section
            buffer_non_heading: list[dict[str, Any]] = []
            previous_line: dict[str, Any] | None = None
            for ln in all_lines:
                level = self._classify_line(ln, heading_levels, previous_line)
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
                previous_line = ln

            # Flush remaining buffer into the last/current section
            if buffer_non_heading:
                paragraphs = self._group_paragraphs(buffer_non_heading)
                if current_section is None:
                    current_section = {"level": "content", "title": None, "paragraphs": []}
                    sections.append(current_section)
                current_section["paragraphs"].extend([" ".join(p_i["text"] for p_i in para) for para in paragraphs])

            page_count = len(doc)

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
            raise InvalidPDFError(f"Invalid or corrupted PDF file: {e}")
        except PDFProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise PDFProcessingError(f"Failed to process PDF: {e}")
        finally:
            if doc is not None:
                doc.close()

    def _extract_title(self, doc: fitz.Document, heading_levels: dict[float, str]) -> str:
        """Extract document title from first page."""
        if len(doc) == 0:
            return "Untitled Document"

        metadata_title = self._metadata_title(doc)
        if metadata_title:
            return metadata_title

        candidates = self._title_candidates(doc[0])
        if not candidates:
            return "Untitled Document"
        return max(candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]

    @staticmethod
    def _metadata_title(doc: fitz.Document) -> str | None:
        """Return useful normalized title metadata, if present."""
        title = " ".join(str((doc.metadata or {}).get("title") or "").split())
        normalized = title.casefold()
        placeholders = {"untitled", "untitled document", "document", "microsoft word"}
        if not title or normalized in placeholders or normalized.startswith("microsoft word -"):
            return None
        return title

    def _title_candidates(self, page: fitz.Page) -> list[tuple[float, float, str]]:
        """Build scored title candidates from complete first-page lines."""
        candidates: list[tuple[float, float, str]] = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                candidate = self._score_title_line(line, page.rect)
                if candidate:
                    candidates.append(candidate)
        return candidates

    @staticmethod
    def _score_title_line(
        line: dict[str, Any], page_rect: fitz.Rect
    ) -> tuple[float, float, str] | None:
        """Score a plausible title line using prominence, position, and width."""
        spans = [span for span in line.get("spans", []) if str(span.get("text") or "").strip()]
        if not spans:
            return None
        text = " ".join("".join(str(span.get("text") or "") for span in spans).split())
        if not text or (text.isdigit() and len(text) <= 4):
            return None

        font_size = max(float(span.get("size") or 0.0) for span in spans)
        boxes = [span.get("bbox") for span in spans if span.get("bbox")]
        left = min(float(box[0]) for box in boxes) if boxes else 0.0
        top = min(float(box[1]) for box in boxes) if boxes else 0.0
        right = max(float(box[2]) for box in boxes) if boxes else left
        width_ratio = min(max((right - left) / max(page_rect.width, 1.0), 0.0), 1.0)
        upper_page_bonus = 3.0 if top <= page_rect.height * 0.5 else 0.0
        tie_break_score = width_ratio * 8.0 + min(len(text) / 40.0, 1.0) * 4.0 + upper_page_bonus
        return font_size, tie_break_score, text
