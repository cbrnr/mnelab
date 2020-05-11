# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from pathlib import Path

import numpy as np
from numpy.core.records import fromarrays
from scipy.io import savemat
import mne

from ..utils import have


def write_fif(fname, raw):
    raw.save(fname)


def write_set(fname, raw):
    """Export raw to EEGLAB .set file."""
    data = raw.get_data() * 1e6  # convert to microvolts
    fs = raw.info["sfreq"]
    times = raw.times
    ch_names = raw.info["ch_names"]
    chanlocs = fromarrays([ch_names], names=["labels"])
    events = fromarrays([raw.annotations.description,
                         raw.annotations.onset * fs + 1,
                         raw.annotations.duration * fs],
                        names=["type", "latency", "duration"])
    savemat(fname, dict(EEG=dict(data=data,
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
                                 icaweights=[])),
            appendmat=False)


def write_edf(fname, raw):
    """Export raw to EDF/BDF file (requires pyEDFlib)."""
    import pyedflib

    ext = "".join(Path(fname).suffixes)
    if ext == ".edf":
        filetype = pyedflib.FILETYPE_EDFPLUS
        dmin, dmax = -32768, 32767
    elif ext == ".bdf":
        filetype = pyedflib.FILETYPE_BDFPLUS
        dmin, dmax = -8388608, 8388607
    data = raw.get_data() * 1e6  # convert to microvolts
    fs = raw.info["sfreq"]
    nchan = raw.info["nchan"]
    ch_names = raw.info["ch_names"]
    if raw.info["meas_date"] is not None:
        meas_date = raw.info["meas_date"]
    else:
        meas_date = None
    prefilter = (f"{raw.info['highpass']}Hz - "
                 f"{raw.info['lowpass']}")
    pmin, pmax = data.min(axis=1), data.max(axis=1)
    f = pyedflib.EdfWriter(fname, nchan, filetype)
    channel_info = []
    data_list = []
    for i in range(nchan):
        channel_info.append(dict(label=ch_names[i],
                                 dimension="uV",
                                 sample_rate=fs,
                                 physical_min=pmin[i],
                                 physical_max=pmax[i],
                                 digital_min=dmin,
                                 digital_max=dmax,
                                 transducer="",
                                 prefilter=prefilter))
        data_list.append(data[i])
    f.setTechnician("Exported by MNELAB")
    f.setSignalHeaders(channel_info)
    if raw.info["meas_date"] is not None:
        f.setStartdatetime(meas_date)
    # note that currently, only blocks of whole seconds can be written
    f.writeSamples(data_list)
    for ann in raw.annotations:
        f.writeAnnotation(ann["onset"], ann["duration"], ann["description"])


def write_bv(fname, raw, events=None):
    """Export data to BrainVision EEG/VHDR/VMRK file (requires pybv)."""
    import pybv

    name, ext = Path(fname).stem, "".join(Path(fname).suffixes)
    parent = Path(fname).parent
    data = raw.get_data()
    fs = raw.info["sfreq"]
    ch_names = raw.info["ch_names"]
    events = None
    if events is None:
        if raw.annotations:
            events = mne.events_from_annotations(raw)[0]
            dur = raw.annotations.duration * fs
            events = np.column_stack([events[:, [0, 2]], dur.astype(int)])
    else:
        events = events[:, [0, 2]]
    pybv.write_brainvision(data, fs, ch_names, name, parent, events=events)


# supported write file formats
writers = {".fif": write_fif,
           ".fif.gz": write_fif,
           ".set": write_set}
if have["pybv"]:
    writers.update({".eeg": write_bv})
if have["pyedflib"]:
    writers.update({".edf": write_edf,
                    ".bdf": write_edf})

WRITE_FORMATS = {"Elekta Neuromag": ".fif",
                 "Elekta Neuromag (compressed)": ".fif.gz",
                 "EEGLAB": ".set"}
if have["pyedflib"]:
    WRITE_FORMATS["European Data Format"] = ".edf"
    WRITE_FORMATS["BioSemi Data Format"] = ".bdf"
if have["pybv"]:
    WRITE_FORMATS["BrainVision"] = ".eeg"

def write_raw(fname, raw):
    ext = "".join(Path(fname).suffixes)
    if ext in writers:
        writers[ext](fname, raw)
    else:
        raise ValueError(f"Unknown file type {ext}.")
