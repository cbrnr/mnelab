# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from os.path import getsize, join, split, splitext
from pathlib import Path
from collections import Counter, defaultdict
from functools import wraps
from copy import deepcopy

import numpy as np
import mne

from .utils import has_locations
from .io import read_raw, write_raw


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
        self.history = ["from copy import deepcopy",
                        "import mne",
                        "from mnelab.io import read_raw"
                        "\n",
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
        self.data.pop(self.index)
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
        data = read_raw(fname, *args, preload=True, **kwargs)
        self.history.append(f'data = read_raw("{fname}", preload=True)')
        fsize = getsize(data.filenames[0]) / 1024**2  # convert to MB
        name, ext = Path(fname).stem, "".join(Path(fname).suffixes)
        self.insert_data(defaultdict(lambda: None, name=name, fname=fname,
                                     ftype=ext.upper()[1:], fsize=fsize,
                                     data=data, dtype="raw"))

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
        events, mapping = mne.events_from_annotations(self.current["data"])
        if events.shape[0] > 0:
            # swap mapping for annots from {str: int} to {int: str}
            mapping = {v: k for k, v in mapping.items()}
            self.current["events"] = events
            self.current["event_mapping"] = mapping
            self.history.append("events, _ = "
                                "mne.events_from_annotations(data)")

    @data_changed
    def annotations_from_events(self):
        """Convert events to annotations."""
        mapping = self.current.get("event_mapping")
        annots = mne.annotations_from_events(
            self.current["events"],
            self.current["data"].info["sfreq"],
            event_desc=mapping
        )
        if len(annots) > 0:
            self.current["data"].set_annotations(annots)
            hist = ("annots = mne.annotations_from_events(events, "
                    'data.info["sfreq"]')
            if mapping is not None:
                hist += f", event_desc={mapping}"
            hist += ")"
            self.history.append(hist)
            self.history.append("data = data.set_annotations(annots)")

    def export_data(self, fname):
        """Export raw to file."""
        write_raw(fname, self.current["data"])

    def export_bads(self, fname):
        """Export bad channels info to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        with open(fname, "w") as f:
            f.write(",".join(self.current["data"].info["bads"]))
        print("Bad channels exported: ", fname)

    def export_events(self, fname):
        """Export events to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        np.savetxt(fname, self.current["events"][:, [0, 2]], fmt="%d",
                   delimiter=",", header="pos,type", comments="")
        print("Events exported: ", fname)

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
        print("Annotations exported: ", fname)

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
        locations = has_locations(self.current["data"].info)
        ica = self.current["ica"]

        length = f"{data.times[-1] - data.times[0]:.6g} s"
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
                "Locations": "Yes" if locations else "-",
                "ICA": ica}

    @data_changed
    def drop_channels(self, drops):
        self.current["data"] = self.current["data"].drop_channels(drops)
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
        self.current["data"].set_montage(montage)
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

        This function is useful for checking which data sets can be appended to
        the current data set.

        Returns
        -------
        compatibles : list
            List with compatible data sets.
        """
        compatibles = []
        data = self.current["data"]
        for idx, d in enumerate(self.data):
            if idx == self.index:  # skip current data set
                continue
            if d["dtype"] not in ("raw", "epochs"):
                continue
            if d["dtype"] != self.current["dtype"]:
                continue
            if d["data"].info["nchan"] != data.info["nchan"]:
                continue
            if set(d["data"].info["ch_names"]) != set(data.info["ch_names"]):
                continue
            if d["data"].info["bads"] != data.info["bads"]:
                continue
            if not np.isclose(d["data"].info["sfreq"], data.info["sfreq"]):
                continue
            if not np.isclose(d["data"].info["highpass"],
                              data.info["highpass"]):
                continue
            if not np.isclose(d["data"].info["lowpass"], data.info["lowpass"]):
                continue
            if d["dtype"] == "raw" and any(d["data"]._cals != data._cals):
                continue
            if d["dtype"] == "epochs":
                if d["data"].tmin != data.tmin:
                    continue
                if d["data"].tmax != data.tmax:
                    continue
                if d["data"].baseline != data.baseline:
                    continue

            compatibles.append(d)
        return compatibles

    @data_changed
    def append_data(self, names):
        """Append the given raw data sets."""
        files = [self.current["data"]]
        for d in self.data:
            if d["name"] in names:
                files.append(d["data"])

        names.insert(0, self.current["name"])
        if self.current["dtype"] == "raw":
            self.current["data"] = mne.concatenate_raws(files)
            self.history.append(f"mne.concatenate_raws({names})")
        elif self.current["dtype"] == "epochs":
            self.current["data"] = mne.concatenate_epochs(files)
            self.history.append(f"mne.concatenate_epochs({names})")
        self.current["name"] += " (appended)"

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
    def convert_od(self):
        self.current["data"] = mne.preprocessing.nirs.optical_density(
            self.current["data"])
        self.current["name"] += " (OD)"
        self.history.append(
            "data = mne.preprocessing.nirs.optical_density(data)")

    @data_changed
    def convert_beer_lambert(self):
        self.current["data"] = mne.preprocessing.nirs.beer_lambert_law(
            self.current["data"])
        self.current["name"] += " (BL)"
        self.history.append(
            "data = mne.preprocessing.nirs.beer_lambert_law(data)")

    @data_changed
    def set_reference(self, ref, bichan=None):
        self.current["reference"] = ref
        if ref == "average":
            self.current["name"] += " (average ref)"
            self.current["data"].set_eeg_reference(ref)
            self.history.append('data.set_eeg_reference("average")')
        if ref == "bipolar":
            self.current["name"] += " (original + bipolar ref)"

            anodes = [i[1:-1].split(', ').pop(0)
                      .rstrip("'\"").lstrip("\"'").strip() for i in bichan]
            cathodes = [i[1:-1].split(', ').pop(1)
                        .rstrip("'\"").lstrip("\"'").strip() for i in bichan]
            anodes_ch_names = []
            cathodes_ch_names = []

            for anode in anodes:
                for ch_name in self.current["data"].info["ch_names"]:
                    if anode in ch_name:
                        anodes_ch_names.append(ch_name)
            for cathode in cathodes:
                for ch_name in self.current["data"].info["ch_names"]:
                    if cathode in ch_name:
                        cathodes_ch_names.append(ch_name)

            self.current["data"] = mne.set_bipolar_reference(
                self.current["data"],
                anode=anodes_ch_names,
                cathode=cathodes_ch_names,
                drop_refs=False)
            d = {x: x.strip() for x in
                 self.current["data"].info["ch_names"] if "EEG" in x}
            mne.rename_channels(self.current["data"].info, d)
            self.history.append(f'data.set_bipolar_reference({ref})')

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
