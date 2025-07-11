#!/usr/bin/env python3
from importlib.metadata import PackageNotFoundError, version

import dmgbuild
import PyInstaller.__main__

try:
    mnelab_version = version("mnelab")
except PackageNotFoundError:
    raise RuntimeError(
        "MNELAB version not found. Please install MNELAB in your environment."
    )

PyInstaller.__main__.run(["mnelab-macos.spec", "--clean", "--noconfirm"])

dmgbuild.build_dmg(
    filename=f"dist/MNELAB-{mnelab_version}.dmg",
    volume_name="MNELAB",
    settings={
        "format": "UDBZ",
        "files": ["dist/MNELAB.app"],
        "symlinks": {"Applications": "/Applications"},
        "icon_locations": {
            "MNELAB.app": (100, 100),
            "Applications": (400, 100),
        },
        "icon_size": 128,
        "window_rect": ((100, 100), (640, 320)),
    },
)
