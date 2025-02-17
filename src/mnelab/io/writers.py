# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

from numpy.rec import fromarrays
from scipy.io import savemat


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


def write_bv(fname, raw):
    """Export data to BrainVision EEG/VHDR/VMRK file (requires pybv)."""
    raw.export(fname=Path(fname).with_suffix(".vhdr"))


# this dict contains each supported file extension as a key; the corresponding value is
# a list with three elements: (1) the writer function, (2) the full file format name,
# and (3) a (comma-separated) string indicating the supported objects
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
