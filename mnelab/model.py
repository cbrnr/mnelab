import csv
from os.path import getsize, join, split, splitext
from collections import Counter, defaultdict
from functools import wraps
from copy import deepcopy
from datetime import datetime
import numpy as np
from numpy.core.records import fromarrays
from scipy.io import savemat
import mne
import matplotlib.pyplot as plt
from .utils.montage import eeg_to_montage


SUPPORTED_FORMATS = "*.bdf *.edf *.fif *.vhdr *.set *.sef"
SUPPORTED_EXPORT_FORMATS = "*.fif *.set"

try:
    import philistine
except ImportError:
    have_philistine = False
else:
    have_philistine = True
    SUPPORTED_EXPORT_FORMATS += "*.vhdr"


try:
    import pyedflib
except ImportError:
    have_pyedflib = False
else:
    have_pyedflib = True
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
        self.view = None   # current view
        self.data = []     # list of data sets
        self.index = -1    # index of currently active data set
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
        sum = 0
        for item in self.data:
            if item["raw"]:
                sum += item["raw"].get_data().nbytes
            elif item["epochs"]:
                sum += item["epochs"].get_data().nbytes
            elif item["evoked"]:
                sum += item["evoked"].data.nbytes
        return sum

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
    def load(self, fname):
        """Load data set from file."""
        name, ext = splitext(split(fname)[-1])
        ftype = ext[1:].upper()
        montage = None
        epochs = None
        if ext.lower() not in SUPPORTED_FORMATS:
            raise ValueError("File format {} is not supported.".format(ftype))

        if ext.lower() in [".edf", ".bdf"]:
            raw = mne.io.read_raw_edf(fname, preload=True)
            self.history.append(
                "raw = mne.io.read_raw_edf('{}')".format(fname),
                "preload=True)")
        elif ext in [".fif"]:
            try:
                raw = mne.io.read_raw_fif(fname, preload=True)
                montage = eeg_to_montage(raw)
                self.history.append(
                    "raw = mne.io.read_raw_fif('{}', ".format(fname)
                    + "preload=True)")
            except ValueError:
                raw = None
                try:
                    epochs = mne.read_epochs(fname, preload=True)
                    evoked = None
                    montage = eeg_to_montage(epochs)
                    self.history.append(
                        "epochs = mne.read_epochs('{}', ".format(fname)
                        + "preload=True)")
                except ValueError:
                    evoked = mne.read_evokeds(fname)
                    epochs = None
                    montage = eeg_to_montage(evoked)
                    self.history.append(
                        "evoked = mne.read_evokeds('{}')".format(fname))

        elif ext in [".vhdr"]:
            raw = mne.io.read_raw_brainvision(fname, preload=True)
            self.history.append(
                "raw = mne.io.read_raw_brainvision('{}',".format(fname),
                " preload=True)")
        elif ext in [".set"]:
            raw = mne.io.read_raw_eeglab(fname, preload=True)
            self.history.append(
                "raw = mne.io.read_raw_eeglab('{}', ".format(fname),
                "preload=True)")

        elif ext in [".sef"]:
            from .utils.read import read_sef
            raw = read_sef(fname)
            raw.load_data()
            self.history.append(
                "raw = read_sef'{}', ".format(fname),
                "preload=True")

        self.insert_data(defaultdict(lambda: None, name=name, fname=fname,
                                     ftype=ftype, raw=raw, epochs=epochs,
                                     isApplied=False, montage=montage))

    @data_changed
    def find_events(self, stim_channel, consecutive=True, initial_event=True,
                    uint_cast=True, min_duration=0, shortest_event=0):
        """Find events in raw data."""
        events = mne.find_events(self.current["raw"],
                                 stim_channel=stim_channel,
                                 consecutive=consecutive,
                                 initial_event=initial_event,
                                 uint_cast=uint_cast,
                                 min_duration=min_duration,
                                 shortest_event=shortest_event)
        if events.shape[0] > 0:  # if events were found
            self.current["events"] = events
            self.history.append("events = mne.find_events(raw)")

    def export_data(self, fname):
        """Export raw to file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".fif"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        if self.current["raw"]:
            if ext == ".fif":
                self.current["raw"].save(fname)
            elif ext == ".set":
                self._export_set(fname)
            elif ext in (".edf", ".bdf"):
                self._export_edf(fname)
            elif ext == ".vhdr":
                philistine.mne.write_raw_brainvision(
                    self.current["raw"], fname)

        elif self.current["epochs"]:
            if ext == ".fif":
                self.current["epochs"].save(fname)

        elif self.current["evoked"]:
            if ext == ".fif":
                self.current["evoked"].save(fname)

    def _export_set(self, fname):
        """Export raw to EEGLAB file."""
        data = self.current["raw"].get_data() * 1e6  # convert to microvolts
        fs = self.current["raw"].info["sfreq"]
        times = self.current["raw"].times
        ch_names = self.current["raw"].info["ch_names"]
        chanlocs = fromarrays([ch_names], names=["labels"])
        events = fromarrays([self.current["raw"].annotations.description,
                             self.current["raw"].annotations.onset * fs + 1,
                             self.current["raw"].annotations.duration * fs],
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
        name, ext = splitext(split(fname)[-1])
        if ext == ".edf":
            filetype = pyedflib.FILETYPE_EDFPLUS
            dmin, dmax = -32768, 32767
        elif ext == ".bdf":
            filetype = pyedflib.FILETYPE_BDFPLUS
            dmin, dmax = -8388608, 8388607
        data = self.current["raw"].get_data() * 1e6  # convert to microvolts
        fs = self.current["raw"].info["sfreq"]
        nchan = self.current["raw"].info["nchan"]
        ch_names = self.current["raw"].info["ch_names"]
        meas_date = self.current["raw"].info["meas_date"][0]
        prefilter = (
            "{}}Hz - ".format(self.current['raw'].info['highpass']),
            "{}".format(self.curset_montagerent['raw'].info['lowpass']))
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
        f.setStartdatetime(datetime.utcfromtimestamp(meas_date))
        # note that currently, only blocks of whole seconds can be written
        f.writeSamples(data_list)
        if self.current["raw"].annotations is not None:
            for ann in self.current["raw"].annotations:
                f.writeAnnotation(ann["onset"], ann["duration"],
                                  ann["description"])

    def export_bads(self, fname):
        """Export bad channels info to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        with open(fname, "w") as f:
            f.write(",".join(self.current["raw"].info["bads"]))

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
        anns = self.current["raw"].annotations
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
        bads = []
        print(fname)
        if fname[-4:] == ".csv":
            with open(fname) as csv_file:
                bads = csv_file.readline().rstrip('\n').split(",")
        elif fname[-4:] == ".txt":
            with open(fname) as txtfile:
                bads = txtfile.readline().rstrip('\n').split(" ")
        unknown = set(bads) - set(self.current["raw"].info["ch_names"])
        known = set(bads) - set(unknown)
        if unknown:
            msg = ("The following imported channel labels are not " +
                   "present in the data: " + ",".join(unknown))
            self.current["raw"].info["bads"] += known
            self.view.data_changed()
            raise LabelsNotFoundError(msg)
        else:
            self.current["raw"].info["bads"] += bads

    @data_changed
    def import_events(self, fname):
        """Import events from a CSV file."""

        if fname.endswith('.csv'):
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

        if fname.endswith('.mrk'):
            beg, end, desc = [], [], []
            desc_str = []
            with open(fname) as f:
                f.readline()
                for line in f:
                    line = line.replace(' ', '')
                    line = line.replace('"', '')
                    line = line.replace('\n', '')
                    b, e, d = tuple(line.split("\t"))
                    beg.append(int(b))
                    end.append(int(e))
                    if d not in desc_str:
                        desc_str.append(d)
                    desc.append(desc_str.index(d))
            events = np.column_stack((beg, desc))
            events = np.insert(events, 1, 0, axis=1)
            if self.current["events"] is not None:
                events = np.row_stack((self.current["events"], events))
                events = np.unique(events, axis=0)
            self.current["events"] = events

    @data_changed
    def import_annotations(self, fname):
        """Import annotations from a CSV file."""
        if fname.endswith('.csv'):
            descs, onsets, durations = [], [], []
            fs = self.current["raw"].info["sfreq"]
            with open(fname) as f:
                f.readline()  # skip header
                for line in f:
                    ann = line.split(",")
                    if len(ann) == 3:  # type, onset, duration
                        onset = float(ann[1].strip())
                        duration = float(ann[2].strip())
                        if onset > self.current["raw"].n_times / fs:
                            msg = ("One or more annotations are outside "
                                   "of the data range.")
                            raise InvalidAnnotationsError(msg)
                        else:
                            descs.append(ann[0].strip())
                            onsets.append(onset)
                            durations.append(duration)
            annotations = mne.Annotations(onsets, durations, descs)
            self.current["raw"].annotations = annotations

        if fname.endswith('.mrk'):
            beg, end, desc = [], [], []
            fs = self.current["raw"].info["sfreq"]
            with open(fname) as f:
                f.readline()
                for line in f:
                    line = line.replace(' ', '')
                    line = line.replace('"', '')
                    line = line.replace('\n', '')
                    b, e, d = tuple(line.split("\t"))
                    beg.append(int(b))
                    end.append(int(e))
                    desc.append(d)
            beg, end = np.array(beg), np.array(end)
            onsets = beg / fs
            durations = (end - beg) / fs
            annotations = mne.Annotations(onsets, durations, desc)
            self.current["raw"].annotations = annotations

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
        raw = self.current["raw"]
        epochs = self.current["epochs"]
        evoked = self.current["evoked"]
        fname = self.current["fname"]
        ftype = self.current["ftype"]
        reference = self.current["reference"]
        events = self.current["events"]
        montage = self.current["montage"]
        ica = self.current["ica"]

        if raw is not None:
            data = raw
        elif epochs is not None:
            data = epochs
        elif evoked is not None:
            data = evoked
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

        if isinstance(reference, list):
            reference = ",".join(reference)

        size_disk = f"{getsize(fname) / 1024 ** 2:.2f} MB" if fname else "-"

        if ica is not None:
            method = ica.method.title()
            if method == "Fastica":
                method = "FastICA"
            ica = f"{method} ({ica.n_components_} components)"
        else:
            ica = "-"

        if raw is not None:  # Raw informations
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
            if raw.annotations is not None:
                annots = len(raw.annotations.description)
                if annots == 0:
                    annots = "-"
            else:
                annots = "-"

            return {
                "File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Size on disk": size_disk,
                "Size in memory": "{:.2f} MB".format(
                    raw.get_data().nbytes / 1024**2),
                "Data type": "MNE Raw",
                "Channels": "{} (".format(nchan) + ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans]) + ")",
                "Samples": raw.n_times,
                "Sampling frequency": "{:.2f} Hz".format(raw.info['sfreq']),
                "Length": "{:.2f} s".format(raw.n_times / raw.info['sfreq']),
                "Events": events,
                "Annotations": annots,
                "Reference": reference if reference else "-",
                "Montage": montage if montage is not None else "-",
                "ICA": ica + " applied = " + str(self.current["isApplied"])
            }

        elif epochs:  # Epochs informations
            return {
                "File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Size on disk": size_disk,
                "Size in memory": "{:.2f} MB".format(
                    epochs.get_data().nbytes / 1024**2),
                "Data type": "MNE Epochs",
                "Channels": "{} (".format(nchan) + ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans]) + ")",
                "Samples": len(epochs.times),
                "Sampling frequency": "{:.2f} Hz".format(epochs.info['sfreq']),
                "Number of Epochs": str(epochs.get_data().shape[0]),
                "Length": "{:.2f} s".format(
                    epochs.times[-1] - epochs.times[0]),
                "Reference": reference if reference else "-",
                "Montage": montage if montage is not None else "-",
                "ICA": ica + " applied = " + str(self.current["isApplied"])
            }

        elif evoked:
            return {
                "File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Size on disk": size_disk,
                "Size in memory": "{:.2f} MB".format(
                    evoked.data.nbytes / 1024**2),
                "Data type": "MNE Evoked",
                "Channels": "{} (".format(nchan) + ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans]) + ")",
                "Samples": len(evoked.times),
                "Sampling frequency": "{:.2f} Hz".format(evoked.info['sfreq']),
                "Length": "{:.2f} s".format(
                    evoked.times[-1] - evoked.times[0]),
                "Reference": reference if reference else "-",
                "Montage": montage if montage is not None else "-",
            }

    @data_changed
    def drop_channels(self, drops):
        if self.current["raw"]:
            self.current["raw"] = (self.current["raw"]
                                   .drop_channels(list(drops)))
        elif self.current["epochs"]:
            self.current["epochs"] = (self.current["epochs"]
                                      .drop_channels(list(drops)))
        else:
            self.current["evoked"] = (self.current["evoked"]
                                      .drop_channels(list(drops)))
        self.current["name"] += " (channels dropped)"

    @data_changed
    def set_channel_properties(self, bads=None, names=None, types=None):
        if self.current["raw"]:
            if bads:
                self.current["raw"].info["bads"] = bads
            if names:
                mne.rename_channels(self.current["raw"].info, names)
            if types:
                self.current["raw"].set_channel_types(types)
        else:
            if bads:
                self.current["epochs"].info["bads"] = bads
            if names:
                mne.rename_channels(self.current["epochs"].info, names)
            if types:
                self.current["epochs"].set_channel_types(types)

    @data_changed
    def set_montage(self, montage):
        self.current["montage"] = montage
        if self.current["raw"]:
            self.current["raw"].set_montage(montage)
            self.history.append("raw.set_montage()")
        elif self.current["epochs"]:
            self.current["epochs"].set_montage(montage)
            self.history.append("epochs.set_montage()")
        elif self.current["evoked"]:
            self.current["evoked"].set_montage(montage)
            self.history.append("evoked.set_montage()")

    @data_changed
    def filter(self, low, high, notch_freqs):
        if self.current["raw"]:
            data = self.current["raw"]
            str = 'raw'
        elif self.current["epochs"]:
            data = self.current["epochs"]
            str = 'epochs'
        elif self.current["evoked"]:
            data = self.current["evoked"]
            str = 'evoked'

        data.filter(low, high)
        self.history.append(str + ".filter({}, {})".format(low, high))
        self.current["name"] += " (Filter {}-{})".format(low, high)
        if notch_freqs is not None:
            try:
                data.notch_filter(notch_freqs)
                self.history.append(
                    str + ".notch_filter({})".format(notch_freqs))
                self.current["name"] += " (Notch {})".format(notch_freqs)
            except Exception as e:
                print(e)

    @data_changed
    def apply_ica(self):
        if self.current["raw"]:
            self.current["ica"].apply(self.current["raw"])
        if self.current["epochs"]:
            self.current["ica"].apply(self.current["epochs"])
        if self.current["evoked"]:
            self.current["ica"].apply(self.current["evoked"])
        self.current["isApplied"] = True
        self.current["name"] += " applied_ica"

    @data_changed
    def interpolate_bads(self):
        if self.current["raw"]:
            if eeg_to_montage(self.current["raw"]) is not None:
                self.current["raw"].interpolate_bads(reset_bads=True)
                self.current["name"] += " (Interpolated)"
        else:
            if eeg_to_montage(self.current["epochs"]) is not None:
                self.current["epochs"].interpolate_bads(reset_bads=True)
                self.current["name"] += " (Interpolated)"

    @data_changed
    def add_events(self):
        from mne import Annotations
        events = self.current['events']
        onsets = events[:, 0] / self.current['raw'].info['sfreq']
        durations = np.zeros(events.shape[0])
        desc = np.array([str(e) for e in events[:, 1]])
        annot = Annotations(onsets, durations, desc)
        self.current['raw'].set_annotations(annot)
        self.current["name"] += " (events added)"

    @data_changed
    def epoch_data(self, selected, tmin, tmax):
        epochs = mne.Epochs(self.current["raw"], self.current["events"],
                            event_id=selected, tmin=tmin, tmax=tmax,
                            preload=True)
        self.current["raw"] = None
        self.current["epochs"] = epochs
        self.current["name"] += " (epoched)"

    @data_changed
    def evoke_data(self):
        evoked = self.current["epochs"].average()
        self.current["raw"] = None
        self.current["epochs"] = None
        self.current["evoked"] = evoked
        self.current["name"] += " (evoked)"

    @data_changed
    def set_reference(self, ref):
        self.current["reference"] = ref
        if ref == "average":
            self.current["name"] += " (average ref)"
            if self.current["raw"]:
                self.current["raw"].set_eeg_reference(ref, projection=False)
            else:
                self.current["epochs"].set_eeg_reference(ref, projection=False)
        else:
            self.current["name"] += " (" + ",".join(ref) + ")"
            if set(ref) - set(self.current["raw"].info["ch_names"]):
                # add new reference channel(s) to data
                try:
                    mne.add_reference_channels(self.current["raw"], ref,
                                               copy=False)
                except RuntimeError:
                    raise AddReferenceError("Cannot add reference channels "
                                            "to average reference signals.")
            else:
                # re-reference to existing channel(s)
                self.current["raw"].set_eeg_reference(ref, projection=False)
