from os.path import getsize, join, split, splitext
from collections import Counter, defaultdict
from functools import wraps
from copy import deepcopy
from numpy import savetxt
import mne


SUPPORTED_FORMATS = "*.bdf *.edf *.fif *.vhdr"


class LabelsNotFoundError(Exception):
    pass


class InvalidAnnotationsError(Exception):
    pass


def new_or_edit(f):
    @wraps(f)
    def wrapper(*args):
        self = args[0]
        # if data is stored in a file, create a new data set
        if self.current["fname"] is not None:
            self.insert_data(deepcopy(self.current))
            self.current["fname"] = None
        # apply function
        return f(*args)
    return wrapper


def data_changed(f):
    @wraps(f)
    def wrapper(*args):
        f(*args)
        args[0].view.data_changed()
    return wrapper


class Model:
    """Data model for MNELAB."""
    def __init__(self):
        self.view = None  # current view
        self.data = []  # list of data sets
        self.index = -1  # index of currently active data set

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

    @property
    def names(self):
        """Return list of all data set names."""
        return [item["name"] for item in self.data]

    @property
    def nbytes(self):
        """Return size (in bytes) of all data sets."""
        return sum([item["raw"]._data.nbytes for item in self.data])

    @property
    def current(self):
        """Return current data set."""
        return self.data[self.index]

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
            # history.append("raw = mne.io.read_raw_edf('{}', "
            #                "stim_channel=-1, preload=True)".format(fname))
        elif ext in [".fif"]:
            raw = mne.io.read_raw_fif(fname, preload=True)
            # history.append("raw = mne.io.read_raw_fif('{}', "
            #                "preload=True)".format(fname))
        elif ext in [".vhdr"]:
            raw = mne.io.read_raw_brainvision(fname, preload=True)
            # history.append("raw = mne.io.read_raw_brainvision('{}', "
            #                "preload=True)".format(fname))

        self.insert_data(defaultdict(lambda: None, name=name, fname=fname,
                                     ftype=ftype, raw=raw))
        self.find_events()

    @data_changed
    def find_events(self):
        """Find events in raw data."""
        events = mne.find_events(self.current["raw"], consecutive=False)
        if events.shape[0] > 0:  # if events were found
            self.current["events"] = events

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
        savetxt(fname, self.current["events"][:, [0, 2]], fmt="%d",
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
            method = ica.method.replace("-", " ").title()
            ica = f"{method} ({ica.n_components_} components)"
        else:
            ica = "-"

        size_disk = f"{getsize(fname) / 1024 ** 2:.2f} MB" if fname else "-"

        return {"File name": fname if fname else "-",
                "File type": ftype if ftype else "-",
                "Number of channels": nchan,
                "Channels": ", ".join(
                    [" ".join([str(v), k.upper()]) for k, v in chans]),
                "Samples": raw.n_times,
                "Sampling frequency": f"{raw.info['sfreq']:.2f} Hz",
                "Length": f"{raw.n_times / raw.info['sfreq']:.2f} s",
                "Events": events,
                "Annotations": annots,
                "Reference": reference if reference else "-",
                "Montage": montage if montage is not None else "-",
                "ICA": ica,
                "Size in memory": f"{raw._data.nbytes / 1024 ** 2:.2f} MB",
                "Size on disk": size_disk}

    @data_changed
    @new_or_edit
    def drop_channels(self, drops):
        self.current["raw"] = self.current["raw"].drop_channels(drops)
        self.current["name"] = self.current["name"] + " (channels dropped)"
        self.view.data_changed()
