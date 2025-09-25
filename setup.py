#!/usr/bin/env python3
"""
Setup script for rob - Robinhood Position Manager CLI Tool
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="rob-robinhood",
    version="1.0.0",
    author="Adam",
    author_email="",
    description="Robinhood Position Manager - Manage your portfolio positions in bulk",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/rob",
    packages=find_packages(),
    py_modules=['rob'],
    include_package_data=True,
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'rob=rob:main',
        ],
    },
    keywords="robinhood trading portfolio finance cli",
    project_urls={
        "Bug Reports": "https://github.com/slugiscool99/rob/issues",
        "Source": "https://github.com/slugiscool99/rob",
    },
)
