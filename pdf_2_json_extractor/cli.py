"""
Command-line interface for pdf_2_json_extractor library.
"""

import argparse
import json
import os
import sys

from . import extract_pdf_to_dict, extract_pdf_to_json
from .exceptions import PdfToJsonError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract structured content from PDF files and output as JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdf_2_json_extractor document.pdf                    # Extract to stdout
  pdf_2_json_extractor document.pdf -o output.json    # Save to file
  pdf_2_json_extractor document.pdf --pretty          # Pretty print JSON
  pdf_2_json_extractor document.pdf --compact         # Compact JSON output
        """
    )

    parser.add_argument(
        "pdf_path",
        help = "Path to the PDF file to process"
    )

    parser.add_argument(
        "-o", "--output",
        help = "Output file path (default: stdout)"
    )

    parser.add_argument(
        "--pretty",
        action = "store_true",
        help = "Pretty print JSON output (default: True)"
    )

    parser.add_argument(
        "--compact",
        action = "store_true",
        help = "Compact JSON output (no indentation)"
    )

    parser.add_argument(
        "--version",
        action = "version",
        version = "pdf_2_json_extractor 1.0.0"
    )

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file '{args.pdf_path}' not found", file = sys.stderr)
        sys.exit(1)

    try:
        # Extract PDF content
        if args.output:
            # Save to file
            result = extract_pdf_to_dict(args.pdf_path)

            # Format JSON
            if args.compact:
                json_str = json.dumps(result, ensure_ascii = False, separators = (',', ':'))
            else:
                json_str = json.dumps(result, ensure_ascii = False, indent = 2)

            with open(args.output, 'w', encoding = 'utf-8') as f:
                f.write(json_str)

            print(f"Successfully extracted PDF content to '{args.output}'")
        else:
            # Output to stdout
            if args.compact:
                json_str = extract_pdf_to_json(args.pdf_path)
                # Remove indentation for compact output
                result = extract_pdf_to_dict(args.pdf_path)
                json_str = json.dumps(result, ensure_ascii = False, separators = (',', ':'))
            else:
                json_str = extract_pdf_to_json(args.pdf_path)

            print(json_str)

    except PdfToJsonError as e:
        print(f"Error: {e}", file = sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file = sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
