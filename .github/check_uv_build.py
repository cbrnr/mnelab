#!/usr/bin/env python

"""Check that uv_build in pyproject.toml is compatible with the latest uv version."""

import os
import re
import sys

from packaging.specifiers import SpecifierSet
from packaging.version import Version

with open("pyproject.toml") as f:
    content = f.read()

match = re.search(r'"(uv_build\s*[^"]+)"', content)
if not match:
    print("ERROR: Could not find uv_build requirement in pyproject.toml")
    sys.exit(1)

requirement = match.group(1)
print(f"Found requirement: {requirement}")

spec_str = requirement.replace("uv_build", "").strip()
specifiers = SpecifierSet(spec_str)

latest = Version(os.environ["UV_LATEST_VERSION"])
print(f"Latest uv version: {latest}")

if latest in specifiers:
    print(f"OK: '{requirement}' is compatible with uv {latest}.")
else:
    print(f"ERROR: '{requirement}' is NOT compatible with uv {latest}.")
    print("Please update the uv_build requirement in pyproject.toml.")
    sys.exit(1)
