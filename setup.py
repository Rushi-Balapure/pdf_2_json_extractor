"""
Setup script for pdf_2_json_extractor library.
"""

import os

from setuptools import find_packages, setup


# Read the README file
def read_readme():
    '''
    This function reads the REAME.md file.
    '''
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "pdf_2_json_extractor - A high-performance PDF to JSON extraction library"

# Read requirements
def read_requirements():
    '''
    This function reads the requirements.txt file.
    '''
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return ["pymupdf>=1.24.0"]

setup(
    name="pdf_2_json_extractor",
    version="1.0.0",
    author="Rushi Balapure",
    author_email="rishibalapure12@gmail.com",
    description='''
    A high-performance PDF to JSON extraction library with layout-aware text extraction.
    That is optimised for CPU.''',
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/pdf_2_json_extractor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Text Processing",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
    },
    entry_points={
        "console_scripts": [
            "pdf_2_json_extractor=pdf_2_json_extractor.cli:main",
        ],
    },
    keywords="pdf json extraction text processing layout analysis",
    project_urls={
        "Bug Reports": "https://github.com/your-username/pdf_2_json_extractor/issues",
        "Source": "https://github.com/your-username/pdf_2_json_extractor",
        "Documentation": "https://github.com/your-username/pdf_2_json_extractor#readme",
    },
)
