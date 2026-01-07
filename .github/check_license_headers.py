#!/usr/bin/env python

"""Check that all Python source files have the required license header."""

import sys
from itertools import islice
from pathlib import Path

REQUIRED_HEADER = """# © MNELAB developers
#
# License: BSD (3-clause)

"""


def check_file(file_path):
    """Check if a file has the required header."""
    with open(file_path, encoding="utf-8") as f:
        header = "".join(islice(f, 4))
    return header == REQUIRED_HEADER


def main():
    """Check all Python files in src/ and tests/ directories."""
    root = Path(__file__).parent.parent

    files = list(root.glob("src/**/*.py")) + list(root.glob("tests/**/*.py"))

    missing_header = [
        file_path.relative_to(root)
        for file_path in files
        if not check_file(file_path)
    ]

    if missing_header:
        print("The following files are missing the required license header:")
        for file_path in sorted(missing_header):
            print(f"  - {file_path}")
        print("\nRequired license header:")
        print(REQUIRED_HEADER, end="")
        sys.exit(1)
    else:
        print(f"✓ All {len(files)} source files have the required license header!")
        sys.exit(0)


if __name__ == "__main__":
    main()
