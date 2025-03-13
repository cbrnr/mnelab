#!/usr/bin/env python3
import dmgbuild
import PyInstaller.__main__

PyInstaller.__main__.run(["mnelab-macos.spec"])

dmgbuild.build_dmg(
    filename="dist/MNELAB.dmg",
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
