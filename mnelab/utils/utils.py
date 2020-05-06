import numpy as np


def has_locations(info):
    locs = np.array([ch["loc"][:3] for ch in info["chs"]])
    return not (np.allclose(locs, 0) or (~np.isfinite(locs)).all())
