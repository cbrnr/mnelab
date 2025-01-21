# © MNELAB developers
#
# License: BSD (3-clause)

from collections import defaultdict

import numpy as np
from mne import channel_type
from mne.defaults import _handle_default


def calculate_channel_stats(raw):
    nchan = raw.info["nchan"]
    cols = defaultdict(list)
    cols["name"] = raw.ch_names

    for i in range(nchan):
        ch = raw.info["chs"][i]
        data = raw[i][0]
        cols["type"].append(channel_type(raw.info, i))
        cols["unit"].append(ch.get("unit", ""))
        cols["min"].append(np.min(data))
        cols["Q1"].append(np.percentile(data, 25))
        cols["mean"].append(np.mean(data))
        cols["median"].append(np.median(data))
        cols["Q3"].append(np.percentile(data, 75))
        cols["max"].append(np.max(data))

    scalings = _handle_default("scalings")
    units = _handle_default("units")
    for i in range(nchan):
        unit = units.get(cols["type"][i])
        scaling = scalings.get(cols["type"][i], 1)
        if scaling != 1:
            cols["unit"][i] = unit
            for col in ["min", "Q1", "mean", "median", "Q3", "max"]:
                cols[col][i] *= scaling

    return cols, nchan
