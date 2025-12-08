# Multi-stage build for pdf_2_json_extractor library
FROM python:3.11-slim as builder

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip build

# Copy source code
COPY . /app
WORKDIR /app

# Build the library
RUN python -m build

# Production stage
FROM python:3.11-slim

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Copy built package from builder stage
COPY --from=builder --chown=app:app /app/dist/*.whl /tmp/

# Install the library
RUN pip install --no-cache-dir /tmp/*.whl

# Set Python optimizations for CPU performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONOPTIMIZE=2

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import pdf_2_json_extractor; print('pdf_2_json_extractor library ready')" || exit 1

# Create a simple CLI script
RUN echo '#!/usr/bin/env python3\n\
import sys\n\
import pdf_2_json_extractor\n\
import json\n\
\n\
if len(sys.argv) != 2:\n\
    print("Usage: pdf_2_json_extractor <pdf_file>")\n\
    sys.exit(1)\n\
\n\
try:\n\
    result = pdf_2_json_extractor.extract_pdf_to_dict(sys.argv[1])\n\
    print(json.dumps(result, indent=2))\n\
except Exception as e:\n\
    print(f\"Error: {e}\", file=sys.stderr)\n\
    sys.exit(1)' > /home/app/pdf_2_json_extractor_cli.py && \
    chmod +x /home/app/pdf_2_json_extractor_cli.py

# Entry point
ENTRYPOINT ["python", "/home/app/pdf_2_json_extractor_cli.py"]
