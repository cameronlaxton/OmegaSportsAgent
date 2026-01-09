#!/usr/bin/env python
"""
Setup script for OmegaSports Validation Lab.
"""

from setuptools import setup, find_packages
from pathlib import Path

project_root = Path(__file__).parent
long_description = (project_root / "README.md").read_text()

setup(
    name="omega-sports-validation-lab",
    version="1.0.0",
    description="Experimental framework for validating and optimizing the OmegaSports betting edge detection engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cameron Laxton",
    author_email="cameron@laxcorp.com",
    url="https://github.com/cameronlaxton/OmegaSports-Validation-Lab",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "requests>=2.30.0",
        "python-dotenv>=1.0.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "pytest>=7.4.0",
        "jupyter>=1.0.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
)
