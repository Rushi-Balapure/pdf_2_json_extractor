# pdf_2_json_extractor

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![PyPI Version](https://img.shields.io/pypi/v/pdf_2_json_extractor.svg)](https://pypi.org/project/pdf_2_json_extractor/)
[![Coverage Status](https://coveralls.io/repos/github/Rushi-Balapure/pdf_2_json_extractor/badge.svg?branch=main)](https://coveralls.io/github/Rushi-Balapure/pdf_2_json_extractor?branch=main)

A high-performance Python library for extracting structured content from PDF documents with layout-aware text extraction. pdf_2_json_extractor preserves document structure including headings (H1-H6) and body text, outputting clean JSON format.

## Features

- **Layout-aware extraction**: Detects document structure including headings of different levels using font size and style analysis
- **Multilingual support**: Preserves Unicode text layers and supports configurable Tesseract languages for scanned pages
- **High performance**: Processes 50-page PDFs in ≤10 seconds on modern CPUs
- **Small footprint**: Minimal dependencies, no heavy ML models used
- **Offline operation**: No internet connectivity required to run
- **Cross-platform**: AMD64 compatible, runs purely on CPU
- **Easy to use**: Simple API with both programmatic and CLI interfaces

## Installation

```bash
pip install pdf_2_json_extractor
```

## Quick Start

### Python API

```python
import pdf_2_json_extractor

# Extract PDF to dictionary
result = pdf_2_json_extractor.extract_pdf_to_dict("document.pdf")
print(f"Title: {result['title']}")
print(f"Number of sections: {result['stats']['num_sections']}")

# Extract PDF to JSON string
json_output = pdf_2_json_extractor.extract_pdf_to_json("document.pdf")
print(json_output)

# Save to file
pdf_2_json_extractor.extract_pdf_to_json("document.pdf", "output.json")
```

### Command Line Interface

```bash
# Extract to stdout
pdf_2_json_extractor document.pdf

# Save to file
pdf_2_json_extractor document.pdf -o output.json

# Compact output; pretty-printed JSON is the default
pdf_2_json_extractor document.pdf --compact

# Process multiple files into an output directory
pdf_2_json_extractor first.pdf second.pdf -o output/

# Process all PDFs directly inside a directory
pdf_2_json_extractor pdfs/ -o output/
```

Directory scans are non-recursive, match `.pdf` case-insensitively, and do not
follow directory symlinks. Batch inputs are sorted before processing. Each
file's status is written to stderr, processing continues after individual
failures, and the command exits with status 1 if any file fails. Duplicate
input stems are rejected to prevent output overwrites.

## JSON Output Format

```json
{
  "title": "Document Title",
  "sections": [
    {
      "level": "H1",
      "title": "Chapter 1: Introduction",
      "paragraphs": ["This is the introduction text..."]
    },
    {
      "level": "H2", 
      "title": "1.1 Overview",
      "paragraphs": ["Overview content..."]
    },
    {
      "level": "content",
      "title": null,
      "paragraphs": ["Body text content..."]
    }
  ],
  "font_histogram": {
    "12.0": 1500,
    "14.0": 200,
    "16.0": 50
  },
  "heading_levels": {
    "16.0": "H1",
    "14.0": "H2"
  },
  "stats": {
    "page_count": 25,
    "processing_time": 2.34,
    "num_sections": 15,
    "num_headings": 8,
    "num_paragraphs": 45
  }
}
```

## Advanced Usage

### Custom Configuration

```python
from pdf_2_json_extractor import PDFStructureExtractor, Config

# Create custom configuration
config = Config()
config.MAX_PAGES_FOR_FONT_ANALYSIS = 5
config.MIN_HEADING_FREQUENCY = 0.002
config.INCLUDE_PAGE_NUMBERS = True

# Use with custom config
extractor = PDFStructureExtractor(config)
result = extractor.extract_text_with_structure("document.pdf")
```

### Error Handling

```python
from pdf_2_json_extractor import extract_pdf_to_dict
from pdf_2_json_extractor.exceptions import PdfToJsonError, InvalidPDFError, PDFFileNotFoundError

try:
    result = extract_pdf_to_dict("document.pdf")
except PDFFileNotFoundError:
    print("PDF file not found")
except InvalidPDFError:
    print("Invalid or corrupted PDF file")
except PdfToJsonError as e:
    print(f"Processing error: {e}")
```

## Configuration Options

Configuration environment variables are read when each `Config` instance is
created:

| Variable | Default | Purpose |
|---|---:|---|
| `PDF_TO_JSON_MAX_PAGES_FOR_FONT_ANALYSIS` | `10` | Maximum pages sampled for heading font analysis |
| `PDF_TO_JSON_MIN_HEADING_FREQUENCY` | `0.001` | Minimum character-frequency ratio for heading sizes |
| `PDF_TO_JSON_MAX_HEADING_LEVELS` | `6` | Deepest generated heading level |
| `PDF_TO_JSON_DETECT_COLUMNS` | `true` | Enable visual multi-column reading order |
| `PDF_TO_JSON_USE_BOLD_AS_HEADING_SIGNAL` | `false` | Promote short, separated bold lines when size is inconclusive |
| `PDF_TO_JSON_OCR_LANGUAGE` | `eng` | Tesseract language expression for image-only pages |
| `PDF_TO_JSON_INCLUDE_PAGE_NUMBERS` | `false` | Emit one-based source pages for headings and paragraphs |

Boolean settings accept `1`, `true`, `yes`, or `on` as true values.

OCR languages use Tesseract codes and may be combined with `+`, for example
`eng+fra`. The matching Tesseract language packs must be installed locally;
the extractor reports an error instead of silently switching languages when a
requested pack is unavailable.

Page traceability is opt-in to preserve the default output schema. When enabled,
paragraph strings become objects such as `{"text": "Paragraph text", "page": 2}`
and heading sections receive a `page` field. Internal page indexes are zero-based;
all page numbers in public output are one-based.

## Development

### Installation from Source

```bash
pip install pdf_2_json_extractor
```
or

```bash
git clone https://github.com/Rushi-Balapure/pdf_2_json_extractor.git
cd pdf_2_json_extractor
pip install -e .
```

### Building the Library

```bash
# Build the package
./build.sh

# Or manually
python -m build
```

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Docker Development

```bash
# Build Docker image
docker build -t pdf_2_json_extractor:latest .

# Run with Docker
docker run --rm -v $(pwd)/test:/test pdf_2_json_extractor:latest /test/document.pdf
```

## Performance

pdf_2_json_extractor is optimized for high performance:

- **CPU-only processing**: No GPU requirements
- **Streaming assembly**: Processes extracted lines page by page while retaining only the current paragraph's line state
- **Fast extraction**: Typical processing times:
  - 10-page document: ~1-2 seconds
  - 50-page document: ~5-10 seconds
  - 100-page document: ~15-25 seconds

The dictionary-returning API still retains the final extracted structure in
memory, so total memory use scales with the amount of content returned. Line
streaming bounds intermediate extraction overhead; it does not make the final
JSON result constant-memory.

## Supported Languages

pdf_2_json_extractor supports text extraction from PDFs containing:

- Latin scripts (English, Spanish, French, German, etc.)
- Cyrillic scripts (Russian, Bulgarian, Serbian, etc.)
- Asian scripts (Chinese, Japanese, Korean)
- Arabic and Hebrew scripts
- Other Unicode scripts

## License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

This package depends on [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright),
which is separately dual-licensed under the GNU AGPL 3.0 or an Artifex
commercial license. Users are responsible for ensuring that their use and
distribution comply with the applicable PyMuPDF license. This notice is for
transparency and is not legal advice.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## References

This library is inspired by the research paper:

**"Layout-Aware Text Extraction from Full-text PDF of Scientific Articles"**  
_Cartic Ramakrishnan, Abhishek Patnia, Eduard Hovy, Gully APC Burns_  
Published in Source Code for Biology and Medicine (2012)  
[Full Paper](http://www.scfbm.org/content/7/1/7)

## Support

For questions, issues, or contributions:

- 📧 Email: rishibalapure12@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/Rushi-Balapure/pdf_2_json_extractor/issues)
- 📖 Documentation: [GitHub Wiki](https://github.com/Rushi-Balapure/pdf_2_json_extractor/wiki)
