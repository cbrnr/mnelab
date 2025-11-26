# © MNELAB developers
#
# License: BSD (3-clause)

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import mne
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


def annotations_between_events(
    events,
    sfreq,
    start_events,
    end_events,
    max_time=None,
    start_offset=0,
    end_offset=0,
    annotation="BAD_INTERTRIAL",
    extend_start=True,
    extend_end=True,
):
    """Create annotations between events."""
    onsets = []
    durations = []
    descriptions = []

    # 2. Logic to find events
    mask_start = np.isin(events[:, 2], start_events)
    mask_end = np.isin(events[:, 2], end_events)

    starts_raw = events[mask_start, 0] / sfreq
    ends_raw = events[mask_end, 0] / sfreq

    valid_onsets = []
    valid_durations = []

    # Find pairs
    last_valid_end_time = -1.0
    for t_start in starts_raw:
        if t_start < last_valid_end_time:
            continue

        future_ends = ends_raw[ends_raw > t_start]
        if len(future_ends) == 0:
            break

        t_end = future_ends[0]

        duration = (t_end + end_offset) - (t_start + start_offset)

        if duration > 0:
            valid_onsets.append(t_start + start_offset)
            valid_durations.append(duration)
            last_valid_end_time = t_end + end_offset

    if valid_onsets:
        onsets.extend(valid_onsets)
        durations.extend(valid_durations)
        descriptions.extend([annotation] * len(valid_onsets))

    if extend_start:
        boundaries = []
        if len(starts_raw) > 0:
            boundaries.append(starts_raw[0] + start_offset)
        if len(ends_raw) > 0:
            boundaries.append(ends_raw[0] + end_offset)
        if boundaries:
            first_boundary = min(boundaries)
            if first_boundary > 0:
                onsets.append(0.0)
                durations.append(first_boundary)
                descriptions.append(annotation)

    if extend_end:
        if max_time is None:
            pass
        else:
            boundaries = []
            if len(starts_raw) > 0:
                boundaries.append(starts_raw[-1] + start_offset)
            if len(ends_raw) > 0:
                boundaries.append(ends_raw[-1] + end_offset)
            if boundaries:
                last_boundary = max(boundaries)
                duration = max_time - last_boundary

                if duration > 0:
                    onsets.append(last_boundary)
                    durations.append(duration)
                    descriptions.append(annotation)

    return mne.Annotations(onset=onsets, duration=durations, description=descriptions)


@dataclass
class Montage:
    montage: DigMontage
    name: str
    path: Path = None
