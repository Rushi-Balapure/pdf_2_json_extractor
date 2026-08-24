"""
Command-line interface for pdf_2_json_extractor library.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__, extract_pdf_to_dict
from .exceptions import PdfToJsonError


def _serialize(result: dict[str, Any], compact: bool) -> str:
    """Serialize extraction output using the requested formatting."""
    if compact:
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(result, ensure_ascii=False, indent=2)


def _resolve_pdf_paths(raw_paths: list[str]) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Resolve files and non-recursive directory contents deterministically."""
    resolved: list[Path] = []
    failures: list[tuple[Path, str]] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        if not path.exists():
            failures.append((path, "path not found"))
            continue
        if path.is_symlink() and path.is_dir():
            failures.append((path, "directory symlinks are not supported"))
            continue
        if path.is_dir():
            try:
                matches = [child for child in path.iterdir() if child.is_file() and child.suffix.lower() == ".pdf"]
            except OSError as exc:
                failures.append((path, f"cannot scan directory: {exc}"))
                continue
            if not matches:
                failures.append((path, "no PDF files found in directory"))
                continue
            resolved.extend(matches)
        else:
            resolved.append(path)
    return sorted(resolved, key=lambda path: str(path).casefold()), failures


def _write_json(path: Path, result: dict[str, Any], compact: bool) -> None:
    """Atomically write one new UTF-8 JSON result without overwriting files."""
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output '{path}'")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
            temporary.write(_serialize(result, compact))
            temporary_path = Path(temporary.name)
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise FileExistsError(f"refusing to overwrite existing output '{path}'") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _run_single(pdf_path: Path, output: str | None, compact: bool) -> None:
    """Run the backward-compatible single-file CLI flow."""
    result = extract_pdf_to_dict(str(pdf_path))
    json_str = _serialize(result, compact)
    if output:
        Path(output).write_text(json_str, encoding="utf-8")
        print(f"Successfully extracted PDF content to '{output}'")
        return
    sys.stdout.buffer.write(json_str.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _run_batch(
    pdf_paths: list[Path], output: str | None, compact: bool, resolution_failures: list[tuple[Path, str]]
) -> int:
    """Process a deterministic batch, continuing after per-file failures."""
    if output is None:
        raise ValueError("An output directory is required for multiple PDFs")
    stems = [path.stem.casefold() for path in pdf_paths]
    if len(stems) != len(set(stems)):
        raise ValueError("Duplicate output stems would overwrite the same JSON file")

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not output_dir.is_dir():
        raise ValueError(f"Batch output path is not a directory: '{output_dir}'")

    failed = bool(resolution_failures)
    for path, message in resolution_failures:
        print(f"FAILED {path}: {message}", file=sys.stderr)
    for pdf_path in pdf_paths:
        destination = output_dir / f"{pdf_path.stem}.json"
        try:
            _write_json(destination, extract_pdf_to_dict(str(pdf_path)), compact)
            print(f"OK {pdf_path} -> {destination}", file=sys.stderr)
        except Exception as exc:
            failed = True
            print(f"FAILED {pdf_path}: {exc}", file=sys.stderr)
    return 1 if failed else 0


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
  pdf_2_json_extractor pdfs/ -o output/               # Process a directory
  pdf_2_json_extractor one.pdf two.pdf -o output/     # Process multiple PDFs
        """
    )

    parser.add_argument(
        "pdf_paths",
        nargs="+",
        help="PDF file or directory paths to process"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file, or output directory for multiple PDFs"
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

    try:
        pdf_paths, resolution_failures = _resolve_pdf_paths(args.pdf_paths)
        if not pdf_paths:
            for path, message in resolution_failures:
                print(f"Error: {path}: {message}", file=sys.stderr)
            raise SystemExit(1)
        if len(pdf_paths) == 1 and not resolution_failures:
            _run_single(pdf_paths[0], args.output, args.compact)
            return
        raise SystemExit(_run_batch(pdf_paths, args.output, args.compact, resolution_failures))
    except (PdfToJsonError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
