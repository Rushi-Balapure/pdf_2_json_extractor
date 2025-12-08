"""
Advanced usage examples for pdf_2_json_extractor library.
"""

import json

import pdf_2_json_extractor
from pdf_2_json_extractor import Config, PDFStructureExtractor
from pdf_2_json_extractor.exceptions import PdfToJsonError


def example_batch_processing():
    """Example of processing multiple PDFs."""
    print("=== Batch Processing ===")

    pdf_files = ["document1.pdf", "document2.pdf", "document3.pdf"]
    results = []

    for pdf_file in pdf_files:
        try:
            result = pdf_2_json_extractor.extract_pdf_to_dict(pdf_file)
            results.append({
                "file": pdf_file,
                "title": result["title"],
                "sections": len(result["sections"]),
                "pages": result["stats"]["page_count"]
            })
            print(f"[OK] Processed {pdf_file}: {result['title']}")
        except PdfToJsonError as e:
            print(f"[FAIL] Failed to process {pdf_file}: {e}")

    # Save batch results
    with open("batch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nBatch results saved to batch_results.json")

def example_heading_analysis():
    """Example of analyzing document structure."""
    print("\n=== Heading Analysis ===")

    try:
        result = pdf_2_json_extractor.extract_pdf_to_dict("sample.pdf")

        # Analyze heading structure
        heading_counts = {}
        for section in result["sections"]:
            level = section.get("level", "content")
            if level.startswith("H"):
                heading_counts[level] = heading_counts.get(level, 0) + 1

        print("Heading structure:")
        for level in sorted(heading_counts.keys()):
            print(f"  {level}: {heading_counts[level]} headings")

        # Find sections with specific headings
        introduction_sections = [
            s for s in result["sections"]
            if s.get("title", "").lower().find("introduction") != -1
        ]

        print(f"\nFound {len(introduction_sections)} sections with 'introduction' in title")

    except PdfToJsonError as e:
        print(f"Error: {e}")

def example_content_filtering():
    """Example of filtering and processing content."""
    print("\n=== Content Filtering ===")

    try:
        result = pdf_2_json_extractor.extract_pdf_to_dict("sample.pdf")

        # Extract only headings
        headings = [
            {"level": s["level"], "title": s["title"]}
            for s in result["sections"]
            if s.get("level", "").startswith("H")
        ]

        print("Document outline:")
        for heading in headings:
            indent = "  " * (int(heading["level"][1]) - 1) if heading["level"].startswith("H") else ""
            print(f"{indent}{heading['title']}")

        # Extract all paragraphs
        all_paragraphs = []
        for section in result["sections"]:
            all_paragraphs.extend(section.get("paragraphs", []))

        print(f"\nTotal paragraphs: {len(all_paragraphs)}")
        print(f"Average paragraph length: {sum(len(p) for p in all_paragraphs) / len(all_paragraphs):.1f} characters")

    except PdfToJsonError as e:
        print(f"Error: {e}")

def example_custom_extraction():
    """Example of custom extraction with specific requirements."""
    print("\n=== Custom Extraction ===")

    # Create custom configuration for academic papers
    config = Config()
    config.MAX_PAGES_FOR_FONT_ANALYSIS = 3  # Analyze fewer pages for faster processing
    config.MIN_HEADING_FREQUENCY = 0.005     # More strict heading detection
    config.DEBUG_MODE = True                 # Enable debug logging

    extractor = PDFStructureExtractor(config)

    try:
        result = extractor.extract_text_with_structure("academic_paper.pdf")

        # Extract specific sections (common in academic papers)
        sections_by_type = {
            "abstract": [],
            "introduction": [],
            "methodology": [],
            "results": [],
            "conclusion": []
        }

        for section in result["sections"]:
            title = section.get("title", "").lower()
            for section_type in sections_by_type:
                if section_type in title:
                    sections_by_type[section_type].append(section)

        print("Academic paper structure:")
        for section_type, sections in sections_by_type.items():
            print(f"  {section_type.title()}: {len(sections)} sections")

    except PdfToJsonError as e:
        print(f"Error: {e}")

def example_export_formats():
    """Example of exporting to different formats."""
    print("\n=== Export Formats ===")

    try:
        result = pdf_2_json_extractor.extract_pdf_to_dict("sample.pdf")

        # Export to Markdown
        markdown_content = []
        for section in result["sections"]:
            level = section.get("level", "content")
            title = section.get("title", "")
            paragraphs = section.get("paragraphs", [])

            if level.startswith("H"):
                # Add heading
                heading_level = int(level[1]) if len(level) > 1 else 1
                markdown_content.append(f"{'#' * heading_level} {title}")
            else:
                # Add content
                if title:
                    markdown_content.append(f"**{title}**")

            # Add paragraphs
            for paragraph in paragraphs:
                markdown_content.append(paragraph)
                markdown_content.append("")  # Empty line

        with open("output.md", "w", encoding="utf-8") as f:
            f.write("\n".join(markdown_content))
        print("[OK] Exported to Markdown: output.md")

        # Export to plain text
        text_content = []
        for section in result["sections"]:
            title = section.get("title", "")
            paragraphs = section.get("paragraphs", [])

            if title:
                text_content.append(title)
                text_content.append("=" * len(title))

            for paragraph in paragraphs:
                text_content.append(paragraph)
                text_content.append("")

        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(text_content))
        print("[OK] Exported to plain text: output.txt")

    except PdfToJsonError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("pdf_2_json_extractor Advanced Examples")
    print("======================================")

    # Run advanced examples
    example_batch_processing()
    example_heading_analysis()
    example_content_filtering()
    example_custom_extraction()
    example_export_formats()

    print("\nAdvanced examples completed!")
