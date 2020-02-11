# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from os.path import getsize, join, split, splitext
from collections import Counter, defaultdict
from functools import wraps
from copy import deepcopy
from datetime import datetime
import numpy as np
from numpy.core.records import fromarrays
from scipy.io import savemat
import mne

from .utils import IMPORT_FORMATS, EXPORT_FORMATS, read_raw_xdf, split_fname


class LabelsNotFoundError(Exception):
    pass


class InvalidAnnotationsError(Exception):
    pass


class AddReferenceError(Exception):
    pass


class UnknownFileTypeError(Exception):
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
        self.history = ["from copy import deepcopy",
                        "import mne",
                        "",
                        "datasets = []"]

    @data_changed
    def insert_data(self, dataset):
        """Insert data set after current index."""
        self.index += 1
        self.data.insert(self.index, dataset)
        self.history.append(f"datasets.insert({self.index}, data)")

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
        self.history[-1] = self.history[-1][:-5] + "deepcopy(data))"
        self.history.append(f"data = datasets[{self.index}]")
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
        name, ext, ftype = split_fname(fname, IMPORT_FORMATS)

        if ext == ".edf":
            data, dtype = self._load_edf(fname), "raw"
        elif ext == ".bdf":
            data, dtype = self._load_bdf(fname), "raw"
        elif ext == ".gdf":
            data, dtype = self._load_gdf(fname), "raw"
        elif ext in (".fif", ".fif.gz"):
            data, dtype = self._load_fif(fname)
        elif ext == ".vhdr":
            data, dtype = self._load_brainvision(fname), "raw"
        elif ext == ".set":
            data, dtype = self._load_eeglab(fname), "raw"
        elif ext == ".cnt":
            data, dtype = self._load_cnt(fname), "raw"
        elif ext == ".mff":
            # fname is really a directory, so remove any trailing slashes
            fname = fname.rstrip("/").rstrip("\\")
            data, dtype = self._load_egi(fname), "raw"
        elif ext == ".nxe":
            data, dtype = self._load_nxe(fname), "raw"
        elif ext in (".xdf", ".xdfz", ".xdf.gz"):
            data, dtype = self._load_xdf(fname, *args, **kwargs), "raw"
        else:
            raise UnknownFileTypeError(f"Unknown file type for {fname}.")

        if ext == ".vhdr":
            fsize = getsize(join(split(fname)[0], name + ".eeg")) / 1024 ** 2
        else:
            fsize = getsize(fname) / 1024 ** 2

        self.insert_data(defaultdict(lambda: None, name=name, fname=fname,
                                     ftype=ftype, fsize=fsize, data=data,
                                     dtype=dtype))

    def _load_edf(self, fname):
        data = mne.io.read_raw_edf(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_edf('{fname}', "
                            f"preload=True)")
        return data

    def _load_bdf(self, fname):
        data = mne.io.read_raw_bdf(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_bdf('{fname}', "
                            f"preload=True)")
        return data

    def _load_gdf(self, fname):
        data = mne.io.read_raw_gdf(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_gdf('{fname}', "
                            f"preload=True)")
        return data

    def _load_fif(self, fname):
        try:
            data = mne.io.read_raw_fif(fname, preload=True)
            self.history.append(f"data = mne.io.read_raw_fif('{fname}', "
                                f"preload=True)")
            return data, "raw"
        except ValueError:
            try:
                data = mne.read_epochs(fname, preload=True)
                self.history.append(f"data = mne.read_epochs('{fname}', "
                                    f"preload=True)")
                return data, "epochs"
            except ValueError:
                data = mne.read_evokeds(fname)
                self.history.append(f"data = mne.read_evokeds('{fname}', "
                                    f"preload=True)")
                return data, "evoked"

    def _load_brainvision(self, fname):
        data = mne.io.read_raw_brainvision(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_brainvision('{fname}', "
                            f"preload=True)")
        return data

    def _load_eeglab(self, fname):
        data = mne.io.read_raw_eeglab(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_eeglab('{fname}', "
                            f"preload=True)")
        return data

    def _load_cnt(self, fname):
        data = mne.io.read_raw_cnt(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_cnt('{fname}', "
                            f"preload=True)")
        return data

    def _load_egi(self, fname):
        data = mne.io.read_raw_egi(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_egi('{fname}', "
                            f"preload=True)")
        return data

    def _load_nxe(self, fname):
        data = mne.io.read_raw_eximia(fname, preload=True)
        self.history.append(f"data = mne.io.read_raw_eximia('{fname}', "
                            f"preload=True)")
        return data

    @staticmethod
    def _load_xdf(fname, stream_id):
        data = read_raw_xdf(fname, stream_id=stream_id)
        return data

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
            self.history.append("events = mne.find_events(data)")

    @data_changed
    def events_from_annotations(self):
        """Convert annotations to events."""
        events, _ = mne.events_from_annotations(self.current["data"])
        if events.shape[0] > 0:
            self.current["events"] = events
            self.history.append("events, _ = "
                                "mne.events_from_annotations(data)")

    def export_data(self, fname, ffilter):
        """Export raw to file."""
        name, ext, ftype = split_fname(fname, EXPORT_FORMATS)
        if ext != ffilter:
            ext = ffilter
            fname += ext

        if ext in (".fif", ".fif.gz"):
            self.current["data"].save(fname)
        elif ext == ".set":
            self._export_set(fname)
        elif ext in (".edf", ".bdf"):
            self._export_edf(fname)
        elif ext == ".eeg":
            self._export_bv(fname)

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

    def _export_bv(self, fname):
        """Export data to BrainVision EEG/VHDR/VMRK file (requires pybv)."""
        import pybv
        head, tail = split(fname)
        name, ext = splitext(tail)
        data = self.current["data"].get_data()
        fs = self.current["data"].info["sfreq"]
        ch_names = self.current["data"].info["ch_names"]
        events = None
        if not isinstance(self.current["events"], np.ndarray):
            if self.current["data"].annotations:
                events = mne.events_from_annotations(self.current["data"])[0]
                dur = self.current["data"].annotations.duration * fs
                events = np.column_stack([events[:, [0, 2]], dur.astype(int)])
        else:
            events = self.current["events"][:, [0, 2]]
        pybv.write_brainvision(data, fs, ch_names, name, head, events=events)

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
                p, d = [int(token.strip()) for token in line.split(",")]
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
        self.current["data"].set_annotations(annotations)

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
        fsize = self.current["fsize"]
        dtype = self.current["dtype"].capitalize()
        reference = self.current["reference"]
        events = self.current["events"]
        montage = self.current["montage"]
        ica = self.current["ica"]

        length = f"{len(data.times) / data.info['sfreq']:.6g} s"
        samples = f"{len(data.times)}"
        if self.current["dtype"] == "epochs":  # add epoch count
            length = f"{self.current['data'].events.shape[0]} x {length}"
            samples = f"{self.current['data'].events.shape[0]} x {samples}"

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

        size_disk = f"{fsize:.2f} MB" if fname else "-"

        if hasattr(data, "annotations") and data.annotations is not None:
            annots = len(data.annotations.description)
            if annots == 0:
                annots = "-"
        else:
            annots = "-"
        return {"File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Data type": dtype,
                "Size on disk": size_disk,
                "Size in memory": f"{data.get_data().nbytes / 1024**2:.2f} MB",
                "Channels": f"{nchan} (" + ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans]) + ")",
                "Samples": samples,
                "Sampling frequency": f"{data.info['sfreq']:.6g} Hz",
                "Length": length,
                "Events": events,
                "Annotations": annots,
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
        if bads != self.current["data"].info["bads"]:
            self.current["data"].info["bads"] = bads
            self.history.append(f"data.info['bads'] = {bads}")
        if names:
            mne.rename_channels(self.current["data"].info, names)
            self.history.append(f"mne.rename_channels(data.info, {names})")
        if types:
            self.current["data"].set_channel_types(types)
            self.history.append(f"data.set_channel_types({types})")

    @data_changed
    def set_montage(self, montage):
        self.current["montage"] = montage
        self.current["data"].set_montage(montage, raise_if_subset=False)
        self.history.append(f"data.set_montage('{montage}', "
                            f"raise_if_subset=False)")

    @data_changed
    def filter(self, low, high):
        self.current["data"].filter(low, high)
        self.current["name"] += f" ({low}-{high} Hz)"
        self.history.append(f"data.filter({low}, {high})")

    @data_changed
    def crop(self, start, stop):
        self.current["data"].crop(start, stop)
        self.current["name"] += " (cropped)"
        self.history.append(f"data.crop({start}, {stop})")

    def get_compatibles(self):
        """Return a list of data sets that are compatible with the current one.

        This function is useful for checking data sets before appending.

        Returns
        -------
        compatibles : list
            List with compatible data sets.
        """
        compatibles = []
        current = self.current["data"]
        for d in filter(lambda x:
                        (isinstance(x["data"], type(current))) and
                        (x["data"].info["nchan"] == current.info["nchan"]) and
                        (set(x["data"].info["ch_names"]) == set(current.info["ch_names"])) and
                        (x["data"].info["bads"] == current.info["bads"]) and
                        (all(x["data"]._cals == current._cals)) and
                        (np.isclose(x["data"].info["sfreq"], current.info["sfreq"])) and
                        (np.isclose(x["data"].info["highpass"], current.info["highpass"])) and
                        (np.isclose(x["data"].info["lowpass"], current.info["lowpass"])),
                        self.data):
            if d["name"] != self.current["name"]:
                compatibles.append(d)
        return compatibles

    @data_changed
    def append_data(self, names):
        """Append the given raw data sets."""
        for d in self.data:
            if d["name"] in names and d["data"] is not None:
                self.current["data"].append(d["data"], preload=True)
        self.current["name"] += " (appended)"
        self.history.append(f"data.append({names})")

    @data_changed
    def apply_ica(self):
        self.current["ica"].apply(self.current["data"])
        self.history.append(f"ica.apply(inst=data, "
                            f"exclude={self.current['ica'].exclude})")
        self.current["name"] += " (ICA)"

    @data_changed
    def interpolate_bads(self, reset_bads, mode, origin):
        self.current["data"].interpolate_bads(reset_bads, mode, origin)
        self.history.append(f'data.interpolate_bads(reset_bads={reset_bads}, '
                            f'mode={mode}, origin={origin})')
        self.current["name"] += " (interpolated)"

    @data_changed
    def epoch_data(self, events, tmin, tmax, baseline):
        epochs = mne.Epochs(self.current["data"], self.current["events"],
                            event_id=events, tmin=tmin, tmax=tmax,
                            baseline=baseline, preload=True)
        self.history.append(f'data = mne.Epochs(data, events, '
                            f'event_id={events}, tmin={tmin}, tmax={tmax}, '
                            f'baseline={baseline}, preload=True)')
        self.current["data"] = epochs
        self.current["dtype"] = "epochs"
        self.current["events"] = self.current["data"].events
        self.current["name"] += " (epoched)"

    @data_changed
    def set_reference(self, ref):
        self.current["reference"] = ref
        if ref == "average":
            self.current["name"] += " (average ref)"
            self.current["data"].set_eeg_reference(ref)
            self.history.append(f'data.set_eeg_reference("average")')
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
                    self.history.append(f'mne.add_reference_channels(data, '
                                        f'{ref}, copy=False)')
            else:
                # re-reference to existing channel(s)
                self.current["data"].set_eeg_reference(ref)
                self.history.append(f'data.set_eeg_reference({ref})')

    @data_changed
    def set_events(self, events):
        self.current["events"] = events

    @data_changed
    def set_annotations(self, onset, duration, description):
        self.current["data"].set_annotations(mne.Annotations(onset, duration,
                                                             description))
