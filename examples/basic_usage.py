"""
Basic usage examples for pdf_2_json_extractor library.
"""

import pdf_2_json_extractor
from pdf_2_json_extractor.exceptions import PdfToJsonError


def example_basic_extraction():
    """Example of basic PDF extraction."""
    print("=== Basic PDF Extraction ===")

    try:
        # Extract PDF to dictionary
        result = pdf_2_json_extractor.extract_pdf_to_dict("sample.pdf")

        print(f"Document Title: {result['title']}")
        print(f"Number of Pages: {result['stats']['page_count']}")
        print(f"Processing Time: {result['stats']['processing_time']:.2f} seconds")
        print(f"Number of Sections: {result['stats']['num_sections']}")
        print(f"Number of Headings: {result['stats']['num_headings']}")
        print(f"Number of Paragraphs: {result['stats']['num_paragraphs']}")

        # Print first few sections
        print("\nFirst 3 sections:")
        for i, section in enumerate(result['sections'][:3]):
            level = section.get('level', 'content')
            title = section.get('title', 'No title')
            paragraphs = section.get('paragraphs', [])
            print(f"  {i+1}. [{level}] {title}")
            if paragraphs:
                print(f"     First paragraph: {paragraphs[0][:100]}...")

    except PdfToJsonError as e:
        print(f"Error: {e}")

def example_json_output():
    """Example of JSON output."""
    print("\n=== JSON Output ===")

    try:
        # Extract to JSON string
        json_output = pdf_2_json_extractor.extract_pdf_to_json("sample.pdf")
        print("JSON output (first 500 characters):")
        print(json_output[:500] + "...")

        # Save to file
        output_file = pdf_2_json_extractor.extract_pdf_to_json("sample.pdf", "output.json")
        print(f"\nSaved to file: {output_file}")

    except PdfToJsonError as e:
        print(f"Error: {e}")

def example_custom_config():
    """Example with custom configuration."""
    print("\n=== Custom Configuration ===")

    from pdf_2_json_extractor import Config, PDFStructureExtractor

    # Create custom configuration
    config = Config()
    config.MAX_PAGES_FOR_FONT_ANALYSIS = 5
    config.MIN_HEADING_FREQUENCY = 0.002
    config.DEBUG_MODE = True

    # Use with custom config
    extractor = PDFStructureExtractor(config)

    try:
        result = extractor.extract_text_with_structure("sample.pdf")
        print("Processed with custom config:")
        print(f"  Font histogram: {result['font_histogram']}")
        print(f"  Heading levels: {result['heading_levels']}")

    except PdfToJsonError as e:
        print(f"Error: {e}")

def example_error_handling():
    """Example of proper error handling."""
    print("\n=== Error Handling ===")

    from pdf_2_json_extractor.exceptions import InvalidPDFError, PDFFileNotFoundError

    try:
        _result = pdf_2_json_extractor.extract_pdf_to_dict("nonexistent.pdf")
    except PDFFileNotFoundError:
        print("[OK] Correctly caught: File not found")
    except InvalidPDFError:
        print("[OK] Correctly caught: Invalid PDF")
    except PdfToJsonError as e:
        print(f"[OK] Correctly caught: pdf_2_json_extractor error - {e}")
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")

if __name__ == "__main__":
    print("pdf_2_json_extractor Examples")
    print("=============================")

    # Run examples
    example_basic_extraction()
    example_json_output()
    example_custom_config()
    example_error_handling()

    print("\nExamples completed!")
