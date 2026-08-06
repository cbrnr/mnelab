import tomllib
from pathlib import Path

with open(Path(__file__).resolve().parent.parent / "pyproject.toml", "rb") as f:
    data = tomllib.load(f)

print(data["project"]["version"])
