from os.path import getsize, join, split, splitext
from collections import Counter, defaultdict
from functools import wraps
from copy import deepcopy
import numpy as np
import mne


SUPPORTED_FORMATS = "*.bdf *.edf *.fif *.vhdr"


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
        return sum([item["raw"].get_data().nbytes for item in self.data])

    @property
    def current(self):
        """Return current data set."""
        return self.data[self.index]

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
        if ext.lower() not in SUPPORTED_FORMATS:
            raise ValueError(f"File format {ftype} is not supported.")

        if ext.lower() in [".edf", ".bdf"]:
            raw = mne.io.read_raw_edf(fname, preload=True)
            self.history.append(f"raw = mne.io.read_raw_edf('{fname}', "
                                f"preload=True)")
        elif ext in [".fif"]:
            raw = mne.io.read_raw_fif(fname, preload=True)
            self.history.append(f"raw = mne.io.read_raw_fif('{fname}', "
                                f"preload=True)")
        elif ext in [".vhdr"]:
            raw = mne.io.read_raw_brainvision(fname, preload=True)
            self.history.append(f"raw = mne.io.read_raw_brainvision('{fname}',"
                                f" preload=True)")

        self.insert_data(defaultdict(lambda: None, name=name, fname=fname,
                                     ftype=ftype, raw=raw))
        self.find_events()

    @data_changed
    def find_events(self, consecutive=True, initial_event=False,
                    uint_cast=False, min_duration=0, shortest_event=2):
        """Find events in raw data."""
        events = mne.find_events(self.current["raw"], consecutive=consecutive,
                                 initial_event=initial_event,
                                 uint_cast=uint_cast,
                                 min_duration=min_duration,
                                 shortest_event=shortest_event)
        if events.shape[0] > 0:  # if events were found
            self.current["events"] = events
            self.history.append("events = mne.find_events(raw)")

    def export_raw(self, fname):
        """Export raw to FIF file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".fif"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        self.current["raw"].save(fname)

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
        with open(fname) as f:
            bads = f.read().replace(" ", "").strip().split(",")
            unknown = set(bads) - set(self.current["raw"].info["ch_names"])
            if unknown:
                msg = ("The following imported channel labels are not " +
                       "present in the data: " + ",".join(unknown))
                raise LabelsNotFoundError(msg)
            else:
                self.current["raw"].info["bads"] = bads

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
        fs = self.current["raw"].info["sfreq"]
        with open(fname) as f:
            f.readline()  # skip header
            for line in f:
                ann = line.split(",")
                if len(ann) == 3:  # type, onset, duration
                    onset = float(ann[1].strip())
                    duration = float(ann[2].strip())
                    if onset > self.current["raw"].n_times / fs:
                        msg = ("One or more annotations are outside of the "
                               "data range.")
                        raise InvalidAnnotationsError(msg)
                    else:
                        descs.append(ann[0].strip())
                        onsets.append(onset)
                        durations.append(duration)
        annotations = mne.Annotations(onsets, durations, descs)
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
        fname = self.current["fname"]
        ftype = self.current["ftype"]
        reference = self.current["reference"]
        events = self.current["events"]
        montage = self.current["montage"]
        ica = self.current["ica"]

        if raw.info["bads"]:
            nbads = len(raw.info["bads"])
            nchan = f"{raw.info['nchan']} ({nbads} bad)"
        else:
            nchan = raw.info["nchan"]
        chans = Counter([mne.io.pick.channel_type(raw.info, i)
                         for i in range(raw.info["nchan"])])
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

        if raw.annotations is not None:
            annots = len(raw.annotations.description)
        else:
            annots = "-"

        if ica is not None:
            method = ica.method.replace("-", " ").title().replace("ica", "ICA")
            ica = f"{method} ({ica.n_components_} components)"
        else:
            ica = "-"

        size_disk = f"{getsize(fname) / 1024 ** 2:.2f} MB" if fname else "-"

        return {"File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Size on disk": size_disk,
                "Size in memory": f"{raw.get_data().nbytes / 1024**2:.2f} MB",
                "Channels": f"{nchan} (" + ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans]) + ")",
                "Samples": raw.n_times,
                "Sampling frequency": f"{raw.info['sfreq']:.2f} Hz",
                "Length": f"{raw.n_times / raw.info['sfreq']:.2f} s",
                "Events": events,
                "Annotations": annots,
                "Reference": reference if reference else "-",
                "Montage": montage if montage is not None else "-",
                "ICA": ica}

    @data_changed
    def drop_channels(self, drops):
        self.current["raw"] = self.current["raw"].drop_channels(drops)
        self.current["name"] += " (channels dropped)"

    @data_changed
    def set_channel_properties(self, bads=None, names=None, types=None):
        if bads:
            self.current["raw"].info["bads"] = bads
        if names:
            mne.rename_channels(self.current["raw"].info, names)
        if types:
            self.current["raw"].set_channel_types(types)

    @data_changed
    def set_montage(self, montage):
        self.current["montage"] = montage
        self.current["raw"].set_montage(montage)

    @data_changed
    def filter(self, low, high):
        self.current["raw"].filter(low, high)
        self.current["name"] += " ({}-{} Hz)".format(low, high)
        self.history.append("raw.filter({}, {})".format(low, high))

    @data_changed
    def set_reference(self, ref):
        self.current["reference"] = ref
        if ref == "average":
            self.current["name"] += " (average ref)"
            self.current["raw"].set_eeg_reference(ref, projection=False)
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
