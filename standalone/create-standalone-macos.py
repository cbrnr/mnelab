#!/usr/bin/env python3
import sys
from importlib.metadata import PackageNotFoundError, version

import dmgbuild
import PyInstaller.__main__


def build_app():
    """Run PyInstaller to create the .app bundle."""
    print("Building MNELAB.app...")
    PyInstaller.__main__.run(["mnelab-macos.spec", "--clean", "--noconfirm"])


def build_dmg():
    """Build the DMG from the existing .app bundle."""
    print("Building DMG...")
    try:
        mnelab_version = version("mnelab")
    except PackageNotFoundError:
        raise RuntimeError(
            "MNELAB version not found. Please install MNELAB in your environment."
        )

    dmgbuild.build_dmg(
        filename=f"MNELAB-{mnelab_version}.dmg",
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


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["build-app", "build-dmg"]:
        print("Usage: python create-standalone-macos.py [build-app | build-dmg]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "build-app":
        build_app()
    elif action == "build-dmg":
        build_dmg()
