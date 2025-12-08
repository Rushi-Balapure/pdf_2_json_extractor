#!/bin/bash
# Build script for pdf_2_json_extractor library

echo "Building pdf_2_json_extractor library..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

# Build the library package
echo "Building Python package..."
python3 -m build

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Build completed successfully!"
    echo ""
    echo "Generated packages:"
    ls -la dist/
    echo ""
    echo "To install the library:"
    echo "pip install dist/pdf_2_json_extractor-1.0.0-py3-none-any.whl"
    echo ""
    echo "To upload to PyPI:"
    echo "twine upload dist/*"
    echo ""
    echo "To test the library:"
    echo "pip install dist/pdf_2_json_extractor-1.0.0-py3-none-any.whl"
    echo "python -c \"import pdf_2_json_extractor; print('Library installed successfully!')\""
else
    echo "Build failed!"
    exit 1
fi