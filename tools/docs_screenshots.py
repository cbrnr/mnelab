"""Render marked documentation screenshots at half their PNG width."""

import re
from pathlib import Path
from struct import unpack

SCREENSHOT = re.compile(
    r"(?P<image>!\[[^]]*\]\((?P<path>[^)]+\.png)\))[ \t]*\{[ \t]*\.screenshot[ \t]*\}"
)


def half_width(path):
    """Return half the width from a PNG header as a CSS pixel value."""
    with path.open("rb") as stream:
        header = stream.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Invalid screenshot PNG: {path}")
    width = unpack(">I", header[16:20])[0]
    return f"{width // 2}{'.5' if width % 2 else ''}"


def on_page_markdown(markdown, page, **kwargs):
    """Replace the screenshot marker with a responsive, half-size width."""
    source_dir = Path(page.file.abs_src_path).parent

    def replace(match):
        width = half_width(source_dir / match["path"])
        return f'{match["image"]}{{ style="width: {width}px; max-width: 100%" }}'

    return SCREENSHOT.sub(replace, markdown)
