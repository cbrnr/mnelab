# © MNELAB developers
#
# License: BSD (3-clause)

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from mne import channel_type
from mne.channels import DigMontage
from mne.defaults import _handle_default


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
        return [
            int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))
        ]

    return sorted(lst, key=key)


def calculate_channel_stats(raw):
    # extract channel info
    nchan = raw.info["nchan"]
    data = raw.get_data()
    cols = defaultdict(list)
    cols["name"] = raw.ch_names
    cols["type"] = [channel_type(raw.info, i) for i in range(nchan)]

    # vectorized calculations
    cols["min"], cols["Q1"], cols["median"], cols["Q3"], cols["max"] = np.percentile(
        data, [0, 25, 50, 75, 100], axis=1
    )
    cols["mean"] = np.mean(data, axis=1)

    # scaling and units
    scalings = _handle_default("scalings")
    units = _handle_default("units")
    cols["unit"] = []
    for i in range(nchan):
        unit = units.get(cols["type"][i])
        scaling = scalings.get(cols["type"][i], 1)
        cols["unit"].append(unit if scaling != 1 else "")
        if scaling != 1:
            for col in ["min", "Q1", "mean", "median", "Q3", "max"]:
                cols[col][i] *= scaling

    return cols, nchan


@dataclass
class Montage:
    montage: DigMontage
    name: str
    path: Path = None
