"""
Command-line interface for pdf_2_json_extractor library.
"""

import argparse
import json
import os
import sys

from . import __version__, extract_pdf_to_dict
from .exceptions import PdfToJsonError


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract structured content from PDF files and output as JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdf_2_json_extractor document.pdf                    # Extract to stdout (pretty)
  pdf_2_json_extractor document.pdf -o output.json    # Save to file
  pdf_2_json_extractor document.pdf --compact         # Compact JSON output
        """
    )

    parser.add_argument(
        "pdf_path",
        help="Path to the PDF file to process"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)"
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact JSON output (no indentation)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"pdf_2_json_extractor {__version__}"
    )

    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file '{args.pdf_path}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        result = extract_pdf_to_dict(args.pdf_path)

        if args.compact:
            json_str = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        else:
            json_str = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"Successfully extracted PDF content to '{args.output}'")
        else:
            # Write directly to stdout buffer with explicit UTF-8 encoding
            # This avoids encoding issues on Windows where console might not be UTF-8
            sys.stdout.buffer.write(json_str.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()

    except PdfToJsonError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
