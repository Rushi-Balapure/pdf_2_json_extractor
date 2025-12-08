# pdf_2_json_extractor Library Usage Examples

## Installation

```bash
# Install from PyPI
pip install pdf_2_json_extractor

# Or install from source
git clone https://github.com/your-username/pdf_2_json_extractor.git
cd pdf_2_json_extractor
pip install -e .
```

## Basic Usage

### Python API

```python
import pdf_2_json_extractor

# Extract PDF to dictionary
result = pdf_2_json_extractor.extract_pdf_to_dict("document.pdf")
print(f"Title: {result['title']}")
print(f"Pages: {result['stats']['page_count']}")
print(f"Sections: {result['stats']['num_sections']}")

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

# Compact output
pdf_2_json_extractor document.pdf --compact

# Pretty print (default)
pdf_2_json_extractor document.pdf --pretty
```

## Docker Usage

```bash
# Build the container
docker build -t pdf_2_json_extractor:latest .

# Extract from a single PDF
docker run --rm -v $(pwd)/pdfs:/pdfs pdf_2_json_extractor:latest /pdfs/document.pdf

# Process multiple PDFs with output redirection
docker run --rm -v $(pwd)/pdfs:/pdfs pdf_2_json_extractor:latest /pdfs/document.pdf > output.json
```

## Batch Processing

```bash
# Process all PDFs in a directory
for pdf in pdfs/*.pdf; do
    echo "Processing: $pdf"
    pdf_2_json_extractor "$pdf" -o "output/$(basename "$pdf" .pdf).json"
done
```

## Advanced Usage

### Custom Configuration

```python
from pdf_2_json_extractor import PDFStructureExtractor, Config

# Create custom configuration
config = Config()
config.MAX_PAGES_FOR_FONT_ANALYSIS = 5
config.MIN_HEADING_FREQUENCY = 0.002

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

## Performance Testing

```bash
# Run benchmark script
chmod +x benchmark.sh
./benchmark.sh

# Test with a specific PDF
time pdf_2_json_extractor document.pdf
```

## Expected Output Format

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
