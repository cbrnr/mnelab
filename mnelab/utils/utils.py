# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

import numpy as np


def count_locations(info):
    locs = np.array([ch["loc"][:3] for ch in info["chs"]])
    valid_locs = np.any(~np.isclose(locs, 0) & np.isfinite(locs), axis=1)
    return valid_locs.sum()


def image_path(fname):
    """Return absolute path to image fname."""
    root = Path(__file__).parent.parent
    return str((root / "images" / Path(fname)).resolve())


def interface_style():
    """Return current platform interface style (light or dark)."""
    try:  # currently only works on macOS
        from Foundation import NSUserDefaults as NSUD
    except ImportError:
        return None
    style = NSUD.standardUserDefaults().stringForKey_("AppleInterfaceStyle")
    if style == "Dark":
        return "dark"
    else:
        return "light"
