# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

import mne
import numpy as np
from numpy.core.records import fromarrays
from scipy.io import savemat

from mnelab.utils import have


def write_fif(fname, raw):
    raw.save(fname, overwrite=True)


def write_set(fname, raw):
    """Export raw to EEGLAB .set file."""
    data = raw.get_data() * 1e6  # convert to microvolts
    fs = raw.info["sfreq"]
    times = raw.times
    ch_names = raw.info["ch_names"]
    chanlocs = fromarrays([ch_names], names=["labels"])
    events = fromarrays(
        [
            raw.annotations.description,
            raw.annotations.onset * fs + 1,
            raw.annotations.duration * fs,
        ],
        names=["type", "latency", "duration"],
    )
    savemat(
        fname,
        dict(
            EEG=dict(
                data=data,
                setname=fname,
                nbchan=data.shape[0],
                pnts=data.shape[1],
                trials=1,
                srate=fs,
                xmin=times[0],
                xmax=times[-1],
                chanlocs=chanlocs,
                event=events,
                icawinv=[],
                icasphere=[],
                icaweights=[],
            )
        ),
        appendmat=False,
    )


def write_edf(fname, raw):
    """Export raw to EDF file."""
    raw.export(fname)


def write_bv(fname, raw, events=None):
    """Export data to BrainVision EEG/VHDR/VMRK file (requires pybv)."""
    import pybv

    name, _ = Path(fname).stem, "".join(Path(fname).suffixes)
    parent = Path(fname).parent
    data = raw.get_data()
    fs = raw.info["sfreq"]
    ch_names = raw.info["ch_names"]
    if events is None:
        if raw.annotations:
            events = mne.events_from_annotations(raw, regexp=None)[0]
            dur = raw.annotations.duration * fs
            events = np.column_stack([events[:, [0, 2]], dur.astype(int)])
    else:
        events = events[:, [0, 2]]
    units = [ch["unit"] for ch in raw.info["chs"]]
    units = ["µV" if unit == 107 else "AU" for unit in units]
    pybv.write_brainvision(
        data=data,
        sfreq=fs,
        ch_names=ch_names,
        fname_base=name,
        folder_out=parent,
        events=events,
        unit=units,
    )


# this dict contains each supported file extension as a key; the corresponding value is a
# list with three elements: (1) the writer function, (2) the full file format name, and (3)
# a (comma-separated) string indicating the supported objects
writers = {
    ".edf": [write_edf, "European Data Format", "raw"],
    ".fif": [write_fif, "Elekta Neuromag", "raw,epoch"],
    ".fif.gz": [write_fif, "Elekta Neuromag", "raw,epoch"],
    ".set": [write_set, "EEGLAB", "raw"],
    ".eeg": [write_bv, "BrainVision", "raw"],
}


def write_raw(fname, raw):
    maxsuffixes = max([ext.count(".") for ext in writers.keys()])
    suffixes = Path(fname).suffixes
    for i in range(-maxsuffixes, 0):
        ext = "".join(suffixes[i:])
        if ext in writers.keys():
            return writers[ext][0](fname, raw)
    else:
        raise ValueError(f"Unknown file type '{suffixes}'.")
