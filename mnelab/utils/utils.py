# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from pathlib import Path

import numpy as np


def has_locations(info):
    locs = np.array([ch["loc"][:3] for ch in info["chs"]])
    return not (np.allclose(locs, 0) or (~np.isfinite(locs)).all())


def image_path(fname):
    """Return absolute path to image fname."""
    root = Path(__file__).parent.parent
    return str((root / "images" / Path(fname)).resolve())
