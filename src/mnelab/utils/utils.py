# © MNELAB developers
#
# License: BSD (3-clause)

import re
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


def natural_sort(lst):
    """Sort a list in natural order."""

    def key(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]

    return sorted(lst, key=key)
