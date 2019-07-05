from os.path import getsize, join, split, splitext
from collections import Counter, defaultdict
from functools import wraps
from copy import deepcopy
from datetime import datetime
import numpy as np
from numpy.core.records import fromarrays
from scipy.io import savemat
import mne

from .utils import read_raw_xdf, have


SUPPORTED_FORMATS = "*.bdf *.edf *.gdf *.fif *.vhdr *.set"
if have["pyxdf"]:
    SUPPORTED_FORMATS += " *.xdf"
SUPPORTED_EXPORT_FORMATS = "*.fif *.set"
if have["pyedflib"]:
    SUPPORTED_EXPORT_FORMATS += " *.edf *.bdf"


class LabelsNotFoundError(Exception):
    pass


class InvalidAnnotationsError(Exception):
    pass


class AddReferenceError(Exception):
    pass


def data_changed(f):
    """Call self.view.data_changed method after function call."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        f(*args, **kwargs)
        args[0].view.data_changed()
    return wrapper


class Model:
    """Data model for MNELAB."""
    def __init__(self):
        self.view = None  # current view
        self.data = []  # list of data sets
        self.index = -1  # index of currently active data set
        self.history = []  # command history

    @data_changed
    def insert_data(self, dataset):
        """Insert data set after current index."""
        self.index += 1
        self.data.insert(self.index, dataset)

    @data_changed
    def update_data(self, dataset):
        """Update/overwrite data set at current index."""
        self.current = dataset

    @data_changed
    def remove_data(self):
        """Remove data set at current index."""
        try:
            self.data.pop(self.index)
        except IndexError:
            raise IndexError("Cannot remove data set from an empty list.")
        else:
            if self.index >= len(self.data):  # if last entry was removed
                self.index = len(self.data) - 1  # reset index to last entry

    @data_changed
    def duplicate_data(self):
        """Duplicate current data set."""
        self.insert_data(deepcopy(self.current))
        self.current["fname"] = None
        self.current["ftype"] = None

    @property
    def names(self):
        """Return list of all data set names."""
        return [item["name"] for item in self.data]

    @property
    def nbytes(self):
        """Return size (in bytes) of all data sets."""
        return sum([item["data"].get_data().nbytes for item in self.data])

    @property
    def current(self):
        """Return current data set."""
        if self.index > -1:
            return self.data[self.index]
        else:
            return None

    @current.setter
    def current(self, value):
        self.data[self.index] = value

    def __len__(self):
        """Return number of data sets."""
        return len(self.data)

    @data_changed
    def load(self, fname, *args, **kwargs):
        """Load data set from file."""
        name, ext = splitext(split(fname)[-1])
        ftype = ext[1:].upper()
        if ext.lower() not in SUPPORTED_FORMATS:
            raise ValueError(f"File format {ftype} is not supported.")

        if ext.lower() in [".edf", ".bdf", ".gdf"]:
            raw, type = self._load_edf(fname), "raw"
        elif ext in [".fif"]:
            raw, type = self._load_fif(fname)
        elif ext in [".vhdr"]:
            raw, type = self._load_brainvision(fname), "raw"
        elif ext in [".set"]:
            raw, type = self._load_eeglab(fname), "raw"
        elif ext in [".xdf"]:
            raw, type = self._load_xdf(fname, *args, **kwargs), "raw"

        self.insert_data(defaultdict(lambda: None, name=name, fname=fname,
                                     ftype=ftype, data=raw, type=type))

    def _load_edf(self, fname):
        raw = mne.io.read_raw_edf(fname, preload=True)
        self.history.append(f"raw = mne.io.read_raw_edf('{fname}', "
                            f"preload=True)")
        return raw

    def _load_fif(self, fname):
        try:
            raw = mne.io.read_raw_fif(fname, preload=True)
            self.history.append(f"raw = mne.io.read_raw_fif('{fname}', "
                                f"preload=True)")
            return raw, "raw"
        except ValueError:
            try:
                epochs = mne.read_epochs(fname, preload=True)
                self.history.append(f"raw = mne.read_epochs('{fname}',"
                                    f" preload=True)")
                return epochs, "epochs"
            except ValueError:
                evoked = mne.read_evokeds(fname)
                self.history.append(f"raw = mne.read_evokeds('{fname}',"
                                    f" preload=True)")
                return evoked, "evoked"

    def _load_brainvision(self, fname):
        raw = mne.io.read_raw_brainvision(fname, preload=True)
        self.history.append(f"raw = mne.io.read_raw_brainvision('{fname}',"
                            f" preload=True)")
        return raw

    def _load_eeglab(self, fname):
        raw = mne.io.read_raw_eeglab(fname, preload=True)
        self.history.append(f"raw = mne.io.read_raw_eeglab('{fname}', "
                            f"preload=True)")
        return raw

    def _load_xdf(self, fname, stream_id):
        raw = read_raw_xdf(fname, stream_id=stream_id)
        return raw

    @data_changed
    def find_events(self, stim_channel, consecutive=True, initial_event=True,
                    uint_cast=True, min_duration=0, shortest_event=0):
        """Find events in raw data."""
        events = mne.find_events(self.current["data"],
                                 stim_channel=stim_channel,
                                 consecutive=consecutive,
                                 initial_event=initial_event,
                                 uint_cast=uint_cast,
                                 min_duration=min_duration,
                                 shortest_event=shortest_event)
        if events.shape[0] > 0:  # if events were found
            self.current["events"] = events
            self.history.append("events = mne.find_events(raw)")

    @data_changed
    def events_from_annotations(self):
        """Convert annotations to events."""
        events, _ = mne.events_from_annotations(self.current["raw"])
        if events.shape[0] > 0:
            self.current["events"] = events
            self.history.append("events, _ = mne.events_from_annotations(raw)")

    def export_raw(self, fname):
        """Export raw to file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".fif"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        if ext == ".fif":
            self.current["data"].save(fname)
        elif ext == ".set":
            self._export_set(fname)
        elif ext in (".edf", ".bdf"):
            self._export_edf(fname)

    def _export_set(self, fname):
        """Export raw to EEGLAB file."""
        data = self.current["data"].get_data() * 1e6  # convert to microvolts
        fs = self.current["data"].info["sfreq"]
        times = self.current["data"].times
        ch_names = self.current["data"].info["ch_names"]
        chanlocs = fromarrays([ch_names], names=["labels"])
        events = fromarrays([self.current["data"].annotations.description,
                             self.current["data"].annotations.onset * fs + 1,
                             self.current["data"].annotations.duration * fs],
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

    def _export_edf(self, fname):
        """Export raw to EDF/BDF file (requires pyEDFlib)."""
        import pyedflib
        name, ext = splitext(split(fname)[-1])
        if ext == ".edf":
            filetype = pyedflib.FILETYPE_EDFPLUS
            dmin, dmax = -32768, 32767
        elif ext == ".bdf":
            filetype = pyedflib.FILETYPE_BDFPLUS
            dmin, dmax = -8388608, 8388607
        data = self.current["data"].get_data() * 1e6  # convert to microvolts
        fs = self.current["data"].info["sfreq"]
        nchan = self.current["data"].info["nchan"]
        ch_names = self.current["data"].info["ch_names"]
        if self.current["data"].info["meas_date"] is not None:
            meas_date = self.current['data'].info["meas_date"][0]
        else:
            meas_date = None
        prefilter = (f"{self.current['data'].info['highpass']}Hz - "
                     f"{self.current['data'].info['lowpass']}")
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
        if meas_date is not None:
            f.setStartdatetime(datetime.utcfromtimestamp(meas_date))
        # note that currently, only blocks of whole seconds can be written
        f.writeSamples(data_list)
        if self.current["data"].annotations is not None:
            for ann in self.current["data"].annotations:
                f.writeAnnotation(ann["onset"], ann["duration"],
                                  ann["description"])

    def export_bads(self, fname):
        """Export bad channels info to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        with open(fname, "w") as f:
            f.write(",".join(self.current["data"].info["bads"]))

    def export_events(self, fname):
        """Export events to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        np.savetxt(fname, self.current["events"][:, [0, 2]], fmt="%d",
                   delimiter=",", header="pos,type", comments="")

    def export_annotations(self, fname):
        """Export annotations to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        anns = self.current["data"].annotations
        with open(fname, "w") as f:
            f.write("type,onset,duration\n")
            for a in zip(anns.description, anns.onset, anns.duration):
                f.write(",".join([a[0], str(a[1]), str(a[2])]))
                f.write("\n")

    def export_ica(self, fname):
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".fif"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        self.current["ica"].save(fname)

    @data_changed
    def import_bads(self, fname):
        """Import bad channels info from a CSV file."""
        with open(fname) as f:
            bads = f.read().replace(" ", "").strip().split(",")
            unknown = set(bads) - set(self.current["data"].info["ch_names"])
            if unknown:
                msg = ("The following imported channel labels are not " +
                       "present in the data: " + ",".join(unknown))
                raise LabelsNotFoundError(msg)
            else:
                self.current["data"].info["bads"] = bads

    @data_changed
    def import_events(self, fname):
        """Import events from a CSV file."""
        pos, desc = [], []
        with open(fname) as f:
            f.readline()  # skip header
            for line in f:
                p, d = [int(l.strip()) for l in line.split(",")]
                pos.append(p)
                desc.append(d)
        events = np.column_stack((pos, desc))
        events = np.insert(events, 1, 0, axis=1)  # insert zero column
        if self.current["events"] is not None:
            events = np.row_stack((self.current["events"], events))
            events = np.unique(events, axis=0)
        self.current["events"] = events

    @data_changed
    def import_annotations(self, fname):
        """Import annotations from a CSV file."""
        descs, onsets, durations = [], [], []
        fs = self.current["data"].info["sfreq"]
        with open(fname) as f:
            f.readline()  # skip header
            for line in f:
                ann = line.split(",")
                if len(ann) == 3:  # type, onset, duration
                    onset = float(ann[1].strip())
                    duration = float(ann[2].strip())
                    if onset > self.current["data"].n_times / fs:
                        msg = ("One or more annotations are outside of the "
                               "data range.")
                        raise InvalidAnnotationsError(msg)
                    else:
                        descs.append(ann[0].strip())
                        onsets.append(onset)
                        durations.append(duration)
        annotations = mne.Annotations(onsets, durations, descs)
        self.current["data"].annotations = annotations

    @data_changed
    def import_ica(self, fname):
        self.current["ica"] = mne.preprocessing.read_ica(fname)

    def get_info(self):
        """Get basic information on current data set.

        Returns
        -------
        info : dict
            Dictionary with information on current data set.
        """
        data = self.current["data"]
        fname = self.current["fname"]
        ftype = self.current["ftype"]
        reference = self.current["reference"]
        events = self.current["events"]
        montage = self.current["montage"]
        ica = self.current["ica"]

        if data.info["bads"]:
            nbads = len(data.info["bads"])
            nchan = f"{data.info['nchan']} ({nbads} bad)"
        else:
            nchan = data.info["nchan"]
        chans = Counter([mne.io.pick.channel_type(data.info, i)
                         for i in range(data.info["nchan"])])
        # sort by channel type (always move "stim" to end of list)
        chans = sorted(dict(chans).items(),
                       key=lambda x: (x[0] == "stim", x[0]))

        if events is not None:
            nevents = events.shape[0]
            unique = [str(e) for e in sorted(set(events[:, 2]))]
            if len(unique) > 20:  # do not show all events
                first = ", ".join(unique[:10])
                last = ", ".join(unique[-10:])
                events = f"{nevents} ({first + ', ..., ' + last})"
            else:
                events = f"{nevents} ({', '.join(unique)})"
        else:
            events = "-"

        if isinstance(reference, list):
            reference = ",".join(reference)

        if ica is not None:
            method = ica.method.title()
            if method == "Fastica":
                method = "FastICA"
            ica = f"{method} ({ica.n_components_} components)"
        else:
            ica = "-"

        size_disk = f"{getsize(fname) / 1024 ** 2:.2f} MB" if fname else "-"

        if self.current["type"] == "raw":

            if data.annotations is not None:
                annots = len(data.annotations.description)
                if annots == 0:
                    annots = "-"
            else:
                annots = "-"
            return {"File name": fname if fname else "-",
                    "File type": ftype if ftype else "-",
                    "Data type": "Raw",
                    "Size on disk": size_disk,
                    "Size in memory": f"{data.get_data().nbytes / 1024**2:.2f} MB",
                    "Channels": f"{nchan} (" + ", ".join(
                        [" ".join([str(v), k.upper()]) for k, v in chans]) + ")",
                    "Samples": data.n_times,
                    "Sampling frequency": f"{data.info['sfreq']:.6g} Hz",
                    "Length": f"{data.n_times / data.info['sfreq']:.6g} s",
                    "Events": events,
                    "Annotations": annots,
                    "Reference": reference if reference else "-",
                    "Montage": montage if montage is not None else "-",
                    "ICA": ica}

        elif self.current["type"] == "epochs":

            return {"File name": fname if fname else "-",
                    "File type": ftype if ftype else "-",
                    "Data type": "Epochs",
                    "Size on disk": size_disk,
                    "Size in memory": f"{data.get_data().nbytes / 1024**2:.2f} MB",
                    "Channels": f"{nchan} (" + ", ".join(
                        [" ".join([str(v), k.upper()]) for k, v in chans]) + ")",
                    "Samples": len(data.times),
                    "Sampling frequency": f"{data.info['sfreq']:.6g} Hz",
                    "Length": f"{len(data.times) / data.info['sfreq']:.6g} s",
                    "Reference": reference if reference else "-",
                    "Montage": montage if montage is not None else "-",
                    "ICA": ica}

    @data_changed
    def drop_channels(self, drops):
        # conversion to list required for MNE < 0.19
        self.current["data"] = self.current["data"].drop_channels(list(drops))
        self.current["name"] += " (channels dropped)"

    @data_changed
    def set_channel_properties(self, bads=None, names=None, types=None):
        if bads:
            self.current["data"].info["bads"] = bads
        if names:
            mne.rename_channels(self.current["data"].info, names)
        if types:
            self.current["data"].set_channel_types(types)

    @data_changed
    def set_montage(self, montage):
        self.current["montage"] = montage
        self.current["data"].set_montage(montage)

    @data_changed
    def filter(self, low, high):
        self.current["data"].filter(low, high)
        self.current["name"] += " ({}-{} Hz)".format(low, high)
        self.history.append("raw.filter({}, {})".format(low, high))

    @data_changed
    def apply_ica(self):
        self.current["ica"].apply(self.current["raw"])
        self.history.append(f"ica.apply(inst=raw, "
                            f"exclude={self.current['ica'].exclude})")
        self.current["name"] += " (ICA)"

    @data_changed
    def set_reference(self, ref):
        self.current["reference"] = ref
        if ref == "average":
            self.current["name"] += " (average ref)"
            self.current["data"].set_eeg_reference(ref, projection=False)
        else:
            self.current["name"] += " (" + ",".join(ref) + ")"
            if set(ref) - set(self.current["data"].info["ch_names"]):
                # add new reference channel(s) to data
                try:
                    mne.add_reference_channels(self.current["data"], ref,
                                               copy=False)
                except RuntimeError:
                    raise AddReferenceError("Cannot add reference channels "
                                            "to average reference signals.")
            else:
                # re-reference to existing channel(s)
                self.current["data"].set_eeg_reference(ref, projection=False)

    @data_changed
    def set_events(self, events):
        self.current["events"] = events

    @data_changed
    def set_annotations(self, onset, duration, description):
        self.current["data"].set_annotations(mne.Annotations(onset, duration,
                                                            description))
