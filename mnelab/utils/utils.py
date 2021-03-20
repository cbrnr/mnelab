# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

import sys
from pathlib import Path

import numpy as np


def has_locations(info):
    locs = np.array([ch["loc"][:3] for ch in info["chs"]])
    return not (np.allclose(locs, 0) or (~np.isfinite(locs)).all())


def image_path(fname):
    """Return absolute path to image fname."""
    root = Path(__file__).parent.parent
    return str((root / "images" / Path(fname)).resolve())


def interface_style():
    """Return current platform interface style (light or dark)."""
    if sys.platform.startswith("darwin"):
        try:
            from Foundation import NSUserDefaults
        except ImportError:
            return None
        defaults = NSUserDefaults.standardUserDefaults()
        style = defaults.stringForKey_("AppleInterfaceStyle")
        if style == "Dark":
            return "dark"
        else:
            return "light"
    elif sys.platform.startswith("win"):
        from winreg import OpenKey, QueryValueEx, HKEY_CURRENT_USER
        s = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with OpenKey(HKEY_CURRENT_USER, s) as key:
            value = QueryValueEx(key, "AppsUseLightTheme")[0]
        if value == 0:
            return "dark"
        else:
            return "light"
