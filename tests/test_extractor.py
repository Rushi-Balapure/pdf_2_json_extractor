"""
End-to-end tests for PDFStructureExtractor.

Real PDFs, real extraction, real results.
"""

from pathlib import Path

import pymupdf as fitz
import pytest

from pdf_2_json_extractor.config import Config
from pdf_2_json_extractor.exceptions import InvalidPDFError, PDFFileNotFoundError, PDFProcessingError
from pdf_2_json_extractor.extractor import PDFStructureExtractor


class TestPDFStructureExtractorInit:
    """Test extractor initialization."""

    def test_init_with_default_config(self):
        """Extractor should work with default config."""
        extractor = PDFStructureExtractor()
        assert extractor.config is not None
        assert isinstance(extractor.config, Config)

    def test_init_with_custom_config(self):
        """Extractor should accept custom config."""
        custom_config = Config()
        custom_config.MAX_PAGES_FOR_FONT_ANALYSIS = 5
        extractor = PDFStructureExtractor(custom_config)
        assert extractor.config.MAX_PAGES_FOR_FONT_ANALYSIS == 5


class TestExtractTextWithStructure:
    """E2E tests for the main extraction method."""

    def test_extracts_real_pdf(self, real_pdf_path: Path):
        """Extract a real PDF and verify the structure."""
        extractor = PDFStructureExtractor()
        result = extractor.extract_text_with_structure(str(real_pdf_path))

        # Verify complete output structure
        assert "title" in result
        assert "sections" in result
        assert "font_histogram" in result
        assert "heading_levels" in result
        assert "stats" in result

        # Verify we got actual content
        assert len(result["sections"]) > 0
        assert result["stats"]["page_count"] > 0
        assert result["stats"]["processing_time"] > 0

    def test_file_not_found(self, nonexistent_pdf_path: Path):
        """Should raise PDFFileNotFoundError for missing files."""
        extractor = PDFStructureExtractor()
        with pytest.raises(PDFFileNotFoundError):
            extractor.extract_text_with_structure(str(nonexistent_pdf_path))

    def test_invalid_pdf(self, invalid_pdf_path: Path):
        """Should raise InvalidPDFError for garbage files."""
        extractor = PDFStructureExtractor()
        with pytest.raises(InvalidPDFError):
            extractor.extract_text_with_structure(str(invalid_pdf_path))

    def test_empty_file(self, empty_file_pdf_path: Path):
        """Should raise InvalidPDFError for empty files."""
        extractor = PDFStructureExtractor()
        with pytest.raises(InvalidPDFError):
            extractor.extract_text_with_structure(str(empty_file_pdf_path))


class TestMultiColumnOrdering:
    """Test visual reading order for multi-column documents."""

    def test_left_column_precedes_right_column(self, two_column_pdf_path: Path):
        """Columns should be read left-to-right regardless of PDF block order."""
        result = PDFStructureExtractor().extract_text_with_structure(str(two_column_pdf_path))
        paragraphs = [paragraph for section in result["sections"] for paragraph in section["paragraphs"]]
        text = " ".join(paragraphs)

        assert text.index("LEFT-1") < text.index("LEFT-3") < text.index("RIGHT-1")

    def test_columns_are_separate_paragraphs(self, two_column_pdf_path: Path):
        """A transition between columns should force a paragraph boundary."""
        result = PDFStructureExtractor().extract_text_with_structure(str(two_column_pdf_path))
        paragraphs = [paragraph for section in result["sections"] for paragraph in section["paragraphs"]]

        assert any("LEFT-1" in paragraph and "LEFT-3" in paragraph for paragraph in paragraphs)
        assert any("RIGHT-1" in paragraph and "RIGHT-3" in paragraph for paragraph in paragraphs)
        assert not any("LEFT-1" in paragraph and "RIGHT-1" in paragraph for paragraph in paragraphs)

    @staticmethod
    def _line(text: str, left: float, top: float, right: float | None = None) -> dict:
        return {
            "page": 0,
            "text": text,
            "font_size": 11.0,
            "left": left,
            "right": right if right is not None else left + 100,
            "top": top,
            "bottom": top + 12,
        }

    def test_single_column_is_sorted_top_to_bottom(self):
        """Source order should not override vertical order on one-column pages."""
        extractor = PDFStructureExtractor()
        lines = [self._line("second", 50, 120), self._line("first", 50, 100)]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == ["first", "second"]

    def test_indentation_does_not_create_columns(self):
        """Overlapping indented text should remain one top-to-bottom flow."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("base-1", 50, 100, 300),
            self._line("indent-1", 130, 120, 300),
            self._line("base-2", 50, 140, 300),
            self._line("indent-2", 130, 160, 300),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == ["base-1", "indent-1", "base-2", "indent-2"]

    def test_orders_three_columns_left_to_right(self):
        """Three detected columns should each retain top-to-bottom order."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("right-1", 410, 100, 520),
            self._line("middle-2", 230, 120, 340),
            self._line("left-2", 50, 120, 160),
            self._line("right-2", 410, 120, 520),
            self._line("left-1", 50, 100, 160),
            self._line("middle-1", 230, 100, 340),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == [
            "left-1",
            "left-2",
            "middle-1",
            "middle-2",
            "right-1",
            "right-2",
        ]

    def test_full_width_line_separates_column_bands(self):
        """A gutter-crossing line should retain its vertical position."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("right-above", 330, 100, 500),
            self._line("left-below", 50, 220, 180),
            self._line("separator", 50, 180, 500),
            self._line("right-below", 330, 220, 500),
            self._line("left-above", 50, 100, 180),
            self._line("right-above-2", 330, 120, 500),
            self._line("left-above-2", 50, 120, 180),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == [
            "left-above",
            "left-above-2",
            "right-above",
            "right-above-2",
            "separator",
            "left-below",
            "right-below",
        ]

    def test_hanging_indent_does_not_create_columns(self):
        """Short list labels and wrapped text should remain in row order."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("label-1", 50, 100, 95),
            self._line("continuation-1", 130, 100, 300),
            self._line("label-2", 50, 140, 95),
            self._line("continuation-2", 130, 140, 300),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == [
            "label-1",
            "continuation-1",
            "label-2",
            "continuation-2",
        ]

    def test_margin_header_and_footer_do_not_create_a_column(self):
        """Centered running text should surround, not disrupt, body columns."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("right-1", 330, 100, 500),
            self._line("footer", 180, 730, 420),
            self._line("left-2", 50, 120, 220),
            self._line("header", 180, 50, 420),
            self._line("right-2", 330, 120, 500),
            self._line("left-1", 50, 100, 220),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == [
            "header",
            "left-1",
            "left-2",
            "right-1",
            "right-2",
            "footer",
        ]

    def test_narrow_columns_still_use_column_order(self):
        """A wide gutter should distinguish narrow columns from indentation."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("right-1", 330, 100, 370),
            self._line("left-2", 50, 120, 90),
            self._line("right-2", 330, 120, 370),
            self._line("left-1", 50, 100, 90),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == ["left-1", "left-2", "right-1", "right-2"]

    def test_staggered_columns_still_use_column_order(self):
        """Columns need not share matching line baselines."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("right-1", 330, 130, 500),
            self._line("left-2", 50, 160, 220),
            self._line("right-2", 330, 190, 500),
            self._line("left-1", 50, 100, 220),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == ["left-1", "left-2", "right-1", "right-2"]

    def test_centered_multiline_separator_is_not_a_column(self):
        """A centered block between column bands should remain full-width."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("right-above-1", 330, 100, 500),
            self._line("heading-2", 180, 200, 500),
            self._line("left-below-2", 50, 300, 220),
            self._line("right-below-1", 330, 280, 500),
            self._line("left-above-2", 50, 120, 220),
            self._line("heading-1", 180, 180, 500),
            self._line("right-above-2", 330, 120, 500),
            self._line("left-below-1", 50, 280, 220),
            self._line("right-below-2", 330, 300, 500),
            self._line("left-above-1", 50, 100, 220),
        ]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == [
            "left-above-1",
            "left-above-2",
            "right-above-1",
            "right-above-2",
            "heading-1",
            "heading-2",
            "left-below-1",
            "left-below-2",
            "right-below-1",
            "right-below-2",
        ]

    def test_adjacent_full_width_lines_share_a_flow(self):
        """A multi-line full-width block should remain one paragraph."""
        extractor = PDFStructureExtractor()
        lines = [
            self._line("left-1", 50, 180, 220),
            self._line("full-2", 50, 120, 500),
            self._line("right-2", 330, 200, 500),
            self._line("full-1", 50, 100, 500),
            self._line("left-2", 50, 200, 220),
            self._line("right-1", 330, 180, 500),
        ]

        ordered = extractor._order_page_lines(lines, 600)
        paragraphs = extractor._group_paragraphs(ordered)

        assert [line["text"] for line in ordered] == [
            "full-1",
            "full-2",
            "left-1",
            "left-2",
            "right-1",
            "right-2",
        ]
        assert [line["text"] for line in paragraphs[0]] == ["full-1", "full-2"]

    def test_column_detection_can_be_disabled(self):
        """Disabling detection should preserve source block order."""
        config = Config()
        config.DETECT_COLUMNS = False
        extractor = PDFStructureExtractor(config)
        lines = [self._line("right", 330, 100), self._line("left", 50, 100)]

        ordered = extractor._order_page_lines(lines, 600)

        assert [line["text"] for line in ordered] == ["right", "left"]


class TestOCRFallback:
    """Test OCR fallback behavior for scanned PDFs."""

    @staticmethod
    def _blocks(text: str) -> list[dict]:
        return [
            {
                "lines": [
                    {
                        "spans": [
                            {
                                "text": text,
                                "size": 12.0,
                                "flags": 0,
                                "bbox": (50.0, 100.0, 200.0, 112.0),
                            }
                        ]
                    }
                ]
            }
        ]

    class FakePage:
        rect = fitz.Rect(0, 0, 600, 800)

        def __init__(self, native_text: str | None, ocr_text: str = "OCR text") -> None:
            self.native_text = native_text
            self.ocr_text = ocr_text
            self.ocr_languages: list[str] = []
            self.textpage = object()

        def get_text(self, output: str, textpage: object | None = None) -> dict:
            assert output == "dict"
            if textpage is self.textpage:
                return {"blocks": TestOCRFallback._blocks(self.ocr_text)}
            blocks = TestOCRFallback._blocks(self.native_text) if self.native_text else []
            return {"blocks": blocks}

        def get_textpage_ocr(self, language: str) -> object:
            self.ocr_languages.append(language)
            return self.textpage

    class FakeDocument:
        def __init__(self, pages: list["TestOCRFallback.FakePage"]) -> None:
            self.pages = pages

        def __len__(self) -> int:
            return len(self.pages)

        def __getitem__(self, index: int) -> "TestOCRFallback.FakePage":
            return self.pages[index]

    def test_uses_ocr_for_scanned_pdf(self, scanned_pdf_path: Path):
        """Scanned image-only PDFs should still produce extracted content."""
        extractor = PDFStructureExtractor()

        result = extractor.extract_text_with_structure(str(scanned_pdf_path))

        assert result["stats"]["num_paragraphs"] > 0
        assert len(result["sections"]) > 0

    def test_ocr_language_is_forwarded(self):
        """Configured Tesseract language expressions should pass through unchanged."""
        config = Config()
        config.OCR_LANGUAGE = "eng+fra"
        extractor = PDFStructureExtractor(config)
        page = self.FakePage(native_text=None)

        lines = list(extractor._iter_lines_ocr(self.FakeDocument([page])))

        assert lines[0]["text"] == "OCR text"
        assert page.ocr_languages == ["eng+fra"]

    def test_uses_ocr_only_for_pages_without_native_text(self):
        """Mixed documents should retain native text and OCR scanned pages."""
        extractor = PDFStructureExtractor()
        native_page = self.FakePage(native_text="Native text")
        scanned_page = self.FakePage(native_text=None, ocr_text="Scanned text")

        lines = list(extractor._iter_lines(self.FakeDocument([native_page, scanned_page])))

        assert [line["text"] for line in lines] == ["Native text", "Scanned text"]
        assert native_page.ocr_languages == []
        assert scanned_page.ocr_languages == ["eng"]

    def test_reports_ocr_language_failures(self):
        """Unavailable language packs should produce an actionable package error."""

        class FailingPage(self.FakePage):
            def get_textpage_ocr(self, language: str) -> object:
                raise RuntimeError("language data not found")

        config = Config()
        config.OCR_LANGUAGE = "fra"
        extractor = PDFStructureExtractor(config)
        native_page = self.FakePage(native_text="Native text")
        failing_page = FailingPage(native_text=None)

        with pytest.raises(PDFProcessingError, match="page 2.*fra"):
            list(extractor._iter_lines(self.FakeDocument([native_page, failing_page])))


class TestFontAnalysis:
    """Test font size analysis on real documents."""

    def test_analyze_font_sizes_on_real_pdf(self, real_pdf_path: Path):
        """Font analysis should return sensible histogram and heading levels."""
        extractor = PDFStructureExtractor()

        with fitz.open(str(real_pdf_path)) as doc:
            font_histogram, heading_levels = extractor.analyze_font_sizes(doc)

        # Should have found some fonts
        assert len(font_histogram) > 0

        # All font sizes should be positive
        for size, count in font_histogram.items():
            assert size > 0
            assert count > 0

        # If heading levels were detected, they should be valid
        for size, level in heading_levels.items():
            assert level.startswith("H")
            level_num = int(level[1:])
            assert 1 <= level_num <= 6


class TestParagraphGrouping:
    """Test paragraph grouping logic."""

    def test_groups_close_lines_together(self):
        """Lines close together should be grouped into one paragraph."""
        extractor = PDFStructureExtractor()
        lines = [
            {"text": "Line 1", "font_size": 12.0, "top": 100, "bottom": 112},
            {"text": "Line 2", "font_size": 12.0, "top": 114, "bottom": 126},
            {"text": "Line 3", "font_size": 12.0, "top": 128, "bottom": 140},
        ]

        paragraphs = extractor._group_paragraphs(lines)

        # All lines are close, should be one paragraph
        assert len(paragraphs) == 1
        assert len(paragraphs[0]) == 3

    def test_splits_on_large_gaps(self):
        """Lines with large vertical gaps should be split into separate paragraphs."""
        extractor = PDFStructureExtractor()
        lines = [
            {"text": "Para 1 Line 1", "font_size": 12.0, "top": 100, "bottom": 112},
            {"text": "Para 1 Line 2", "font_size": 12.0, "top": 114, "bottom": 126},
            # Big gap here
            {"text": "Para 2 Line 1", "font_size": 12.0, "top": 200, "bottom": 212},
            {"text": "Para 2 Line 2", "font_size": 12.0, "top": 214, "bottom": 226},
        ]

        paragraphs = extractor._group_paragraphs(lines)

        assert len(paragraphs) == 2
        assert len(paragraphs[0]) == 2
        assert len(paragraphs[1]) == 2

    def test_handles_empty_input(self):
        """Empty input should return empty output."""
        extractor = PDFStructureExtractor()
        paragraphs = extractor._group_paragraphs([])
        assert paragraphs == []

    def test_handles_single_line(self):
        """Single line should be its own paragraph."""
        extractor = PDFStructureExtractor()
        lines = [{"text": "Solo line", "font_size": 12.0, "top": 100, "bottom": 112}]

        paragraphs = extractor._group_paragraphs(lines)

        assert len(paragraphs) == 1
        assert len(paragraphs[0]) == 1

    def test_splits_at_page_boundaries(self):
        """Coordinate resets on a new page must not merge paragraphs."""
        extractor = PDFStructureExtractor()
        lines = [
            {"page": 0, "text": "Page one", "font_size": 12.0, "top": 700, "bottom": 712},
            {"page": 1, "text": "Page two", "font_size": 12.0, "top": 72, "bottom": 84},
        ]

        paragraphs = extractor._group_paragraphs(lines)

        assert len(paragraphs) == 2


class TestHeadingClassification:
    """Test heading level classification."""

    def test_classifies_known_sizes(self):
        """Known heading sizes should return correct levels."""
        extractor = PDFStructureExtractor()
        heading_levels = {18.0: "H1", 16.0: "H2", 14.0: "H3"}

        assert extractor._classify_level(18.0, heading_levels) == "H1"
        assert extractor._classify_level(16.0, heading_levels) == "H2"
        assert extractor._classify_level(14.0, heading_levels) == "H3"

    def test_returns_none_for_body_text(self):
        """Body text sizes should return None."""
        extractor = PDFStructureExtractor()
        heading_levels = {18.0: "H1", 16.0: "H2"}

        assert extractor._classify_level(12.0, heading_levels) is None
        assert extractor._classify_level(10.0, heading_levels) is None

    def test_handles_rounding(self):
        """Font sizes should be rounded for comparison."""
        extractor = PDFStructureExtractor()
        heading_levels = {16.0: "H1"}

        # 16.04 rounds to 16.0
        assert extractor._classify_level(16.04, heading_levels) == "H1"


class TestBoldHeadingSignal:
    """Test opt-in font-weight heading classification."""

    @staticmethod
    def _line(text: str = "Overview") -> dict:
        return {
            "text": text,
            "font_size": 12.0,
            "is_bold": True,
            "bold_ratio": 1.0,
            "page": 0,
            "flow_region": 0,
            "top": 100.0,
            "bottom": 112.0,
        }

    @staticmethod
    def _previous_line() -> dict:
        return {"page": 0, "flow_region": 0, "top": 70.0, "bottom": 82.0}

    def test_bold_body_text_promoted_when_enabled(self):
        """A short separated bold line should become the next heading level."""
        config = Config()
        config.USE_BOLD_AS_HEADING_SIGNAL = True
        extractor = PDFStructureExtractor(config)

        level = extractor._classify_line(self._line(), {18.0: "H1"}, self._previous_line())

        assert level == "H2"

    def test_bold_body_text_unchanged_when_disabled(self):
        """Bold body-sized text should remain content by default."""
        extractor = PDFStructureExtractor()

        level = extractor._classify_line(self._line(), {18.0: "H1"}, self._previous_line())

        assert level is None

    def test_long_bold_sentence_is_not_promoted(self):
        """Bold paragraphs should not be mistaken for headings."""
        config = Config()
        config.USE_BOLD_AS_HEADING_SIGNAL = True
        extractor = PDFStructureExtractor(config)
        text = "This is a long bold sentence that should remain ordinary paragraph content because it reads like prose."

        level = extractor._classify_line(self._line(text), {}, self._previous_line())

        assert level is None

    def test_column_transition_does_not_count_as_heading_spacing(self):
        """The first bold line in another column still needs a visual gap."""
        config = Config()
        config.USE_BOLD_AS_HEADING_SIGNAL = True
        extractor = PDFStructureExtractor(config)
        line = self._line()
        line.update({"flow_region": "0-1", "top": 100.0})
        previous = self._previous_line()
        previous.update({"flow_region": "0-0", "bottom": 112.0})

        level = extractor._classify_line(line, {}, previous)

        assert level is None

    def test_bold_flags_are_retained_on_normalized_lines(self):
        """PyMuPDF span flags should be reflected in normalized line style."""
        extractor = PDFStructureExtractor()
        blocks = [
            {
                "lines": [
                    {
                        "spans": [
                            {
                                "text": "Bold heading",
                                "size": 12.0,
                                "flags": fitz.TEXT_FONT_BOLD,
                                "bbox": (50.0, 100.0, 130.0, 112.0),
                            }
                        ]
                    }
                ]
            }
        ]

        line = list(extractor._iter_lines_from_blocks(0, blocks))[0]

        assert line["is_bold"] is True
        assert line["bold_ratio"] == 1.0


class TestTitleExtraction:
    """Test title extraction from documents."""

    def test_extracts_title_from_real_pdf(self, real_pdf_path: Path):
        """Should extract a non-empty title from a real PDF."""
        extractor = PDFStructureExtractor()

        with fitz.open(str(real_pdf_path)) as doc:
            title = extractor._extract_title(doc, {})

        assert title is not None
        assert len(title) > 0
        assert title != "Untitled Document"

    def test_prefers_pdf_metadata_title(self):
        """Valid PDF metadata should beat larger decorative page text."""
        extractor = PDFStructureExtractor()
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "DECORATION", fontsize=36)
        doc.set_metadata({"title": "My Real Title"})

        title = extractor._extract_title(doc, {})
        doc.close()

        assert title == "My Real Title"

    def test_ignores_margin_numeral_without_metadata(self):
        """A large decorative numeral should not replace a plausible title."""
        extractor = PDFStructureExtractor()
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((20, 40), "7", fontsize=36)
        page.insert_text((72, 120), "A Practical PDF Title", fontsize=24)

        title = extractor._extract_title(doc, {})
        doc.close()

        assert title == "A Practical PDF Title"

    def test_combines_all_spans_in_title_line(self):
        """Visual title selection should return the complete line text."""
        extractor = PDFStructureExtractor()

        class FakePage:
            rect = fitz.Rect(0, 0, 600, 800)

            def get_text(self, output: str) -> dict:
                assert output == "dict"
                return {
                    "blocks": [
                        {
                            "lines": [
                                {
                                    "spans": [
                                        {"text": "Structured ", "size": 24, "bbox": (72, 100, 180, 126)},
                                        {"text": "PDF Title", "size": 24, "bbox": (180, 100, 290, 126)},
                                    ]
                                }
                            ]
                        }
                    ]
                }

        class FakeDocument:
            metadata: dict[str, str] = {}

            def __len__(self) -> int:
                return 1

            def __getitem__(self, index: int) -> FakePage:
                assert index == 0
                return FakePage()

        title = extractor._extract_title(FakeDocument(), {})

        assert title == "Structured PDF Title"

    def test_font_prominence_outweighs_wide_body_text(self):
        """A wide body line should not outscore a modestly larger title."""

        class FakePage:
            rect = fitz.Rect(0, 0, 600, 800)

            def get_text(self, output: str) -> dict:
                assert output == "dict"
                return {
                    "blocks": [
                        {
                            "lines": [
                                {"spans": [{"text": "Short Title", "size": 14, "bbox": (72, 80, 150, 98)}]},
                                {
                                    "spans": [
                                        {
                                            "text": "A long body sentence extending across nearly the full available page width.",
                                            "size": 12,
                                            "bbox": (50, 130, 550, 145),
                                        }
                                    ]
                                },
                            ]
                        }
                    ]
                }

        class FakeDocument:
            metadata: dict[str, str] = {}

            def __len__(self) -> int:
                return 1

            def __getitem__(self, index: int) -> FakePage:
                assert index == 0
                return FakePage()

        title = PDFStructureExtractor()._extract_title(FakeDocument(), {})

        assert title == "Short Title"

    def test_one_point_font_difference_outweighs_body_width(self):
        """Even a modestly larger title font should remain the primary signal."""

        class FakePage:
            rect = fitz.Rect(0, 0, 600, 800)

            def get_text(self, output: str) -> dict:
                assert output == "dict"
                return {
                    "blocks": [
                        {
                            "lines": [
                                {"spans": [{"text": "Brief Title", "size": 13, "bbox": (72, 200, 110, 216)}]},
                                {
                                    "spans": [
                                        {
                                            "text": "A long body sentence extending across nearly the full available page width.",
                                            "size": 12,
                                            "bbox": (50, 240, 550, 255),
                                        }
                                    ]
                                },
                            ]
                        }
                    ]
                }

        class FakeDocument:
            metadata: dict[str, str] = {}

            def __len__(self) -> int:
                return 1

            def __getitem__(self, index: int) -> FakePage:
                assert index == 0
                return FakePage()

        assert PDFStructureExtractor()._extract_title(FakeDocument(), {}) == "Brief Title"

    def test_top_edge_text_can_be_a_real_title(self):
        """Non-decorative title text near the page top should remain eligible."""
        extractor = PDFStructureExtractor()
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 22), "Top Edge Title", fontsize=20)
        page.insert_text((72, 100), "Ordinary body content across the page", fontsize=12)

        title = extractor._extract_title(doc, {})
        doc.close()

        assert title == "Top Edge Title"


class TestConfig:
    """Test Config class."""

    def test_config_defaults(self):
        """Default config values should be sensible."""
        config = Config()

        assert config.MAX_PAGES_FOR_FONT_ANALYSIS == 10
        assert config.MIN_HEADING_FREQUENCY == 0.001
        assert config.MAX_HEADING_LEVELS == 6
        assert config.DETECT_COLUMNS is True
        assert config.USE_BOLD_AS_HEADING_SIGNAL is False
        assert config.OCR_LANGUAGE == "eng"

    def test_ocr_language_reads_environment(self, monkeypatch: pytest.MonkeyPatch):
        """OCR language should be read when a Config instance is created."""
        monkeypatch.setenv("PDF_TO_JSON_OCR_LANGUAGE", "deu+eng")

        config = Config()

        assert config.OCR_LANGUAGE == "deu+eng"

    def test_get_config_returns_dict(self):
        """get_config should return a dictionary representation."""
        config = Config()
        config_dict = config.get_config()

        assert isinstance(config_dict, dict)
        assert "max_pages_for_font_analysis" in config_dict
        assert config_dict["max_pages_for_font_analysis"] == 10

    def test_instances_are_independent(self):
        """Modifying one Config instance should not affect others."""
        config1 = Config()
        config2 = Config()

        # Modify config1
        config1.MAX_PAGES_FOR_FONT_ANALYSIS = 99

        # config2 should be unchanged
        assert config2.MAX_PAGES_FOR_FONT_ANALYSIS == 10
        assert config1.MAX_PAGES_FOR_FONT_ANALYSIS == 99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
