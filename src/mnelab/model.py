# © MNELAB developers
#
# License: BSD (3-clause)

from collections import Counter, defaultdict
from copy import deepcopy
from functools import wraps
from os.path import getsize, join, split, splitext
from pathlib import Path

import mne
import numpy as np

from mnelab.io import read_raw, write_raw
from mnelab.io.readers import split_name_ext
from mnelab.utils import count_locations


class LabelsNotFoundError(Exception):
    pass


class InvalidAnnotationsError(Exception):
    pass


class AddReferenceError(Exception):
    pass


def data_changed(f):
    """Call self.view.data_changed method after function call."""

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if self.view is not None:
            with self.view._wait_cursor():
                result = f(self, *args, **kwargs)
                self.view.data_changed()
        else:
            result = f(self, *args, **kwargs)
        return result

    return wrapper


class Model:
    """Data model for MNELAB."""

    def __init__(self):
        self.view = None  # current view
        self.data = []  # list of data sets
        self.index = -1  # index of currently active data set
        self.history = [
            "from copy import deepcopy",
            "import mne",
            "from mnelab.io import read_raw" "\n",
            "datasets = []",
        ]

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
        fname = str(Path(fname).resolve())
        data = read_raw(fname, *args, **kwargs, preload=True)
        argstr = ", " + f"{', '.join(f'{v}' for v in args)}" if args else ""
        if kwargs:
            kwargstr = (
                ", " + f"{', '.join(f'{k}={repr(v)}' for k, v in kwargs.items())}"
            )
        else:
            kwargstr = ""
        self.history.append(
            f'data = read_raw("{fname}"{argstr}{kwargstr}, preload=True)'.replace(
                "'", '"'
            )
        )
        fsize = getsize(data.filenames[0]) / 1024**2  # convert to MB
        name, ext = split_name_ext(fname)
        self.insert_data(
            defaultdict(
                lambda: None,
                name=name,
                fname=fname,
                ftype=ext.upper()[1:],
                fsize=fsize,
                data=data,
                dtype="raw",
                montage=None,
                events=np.empty((0, 3), dtype=int),
                event_mapping=defaultdict(str),
            )
        )

    @data_changed
    def find_events(
        self,
        stim_channel,
        consecutive=True,
        initial_event=True,
        uint_cast=True,
        min_duration=0,
        shortest_event=0,
    ):
        """Find events in raw data."""
        events = mne.find_events(
            self.current["data"],
            stim_channel=stim_channel,
            consecutive=consecutive,
            initial_event=initial_event,
            uint_cast=uint_cast,
            min_duration=min_duration,
            shortest_event=shortest_event,
        )
        if events.shape[0] > 0:  # if events were found
            self.current["events"] = events
            hist = "events = mne.find_events(data"
            hist += f", stim_channel={stim_channel!r}"
            if consecutive != "increasing":
                hist += f", consecutive={consecutive!r}"
            if initial_event:
                hist += f", initial_event={initial_event!r}"
            if uint_cast:
                hist += f", uint_cast={uint_cast!r}"
            if min_duration > 0:
                hist += f", min_duration={min_duration!r}"
            if shortest_event != 2:
                hist += f", shortest_event={shortest_event!r}"
            hist += ")"
            self.history.append(hist)

    @data_changed
    def events_from_annotations(self):
        """Convert annotations to events."""
        events, mapping = mne.events_from_annotations(self.current["data"])
        if events.shape[0] > 0:
            # swap mapping for annotations from {str: int} to {int: str}
            mapping = {v: k for k, v in mapping.items()}
            self.current["events"] = events
            self.current["event_mapping"] = mapping
            self.history.append("events, _ = mne.events_from_annotations(data)")

    @data_changed
    def annotations_from_events(self):
        """Convert events to annotations."""
        mapping = self.current.get("event_mapping")
        annots = mne.annotations_from_events(
            self.current["events"],
            self.current["data"].info["sfreq"],
            event_desc=mapping,
        )
        if len(annots) > 0:
            self.current["data"].set_annotations(annots)
            hist = 'annots = mne.annotations_from_events(events, data.info["sfreq"]'
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

    def export_events(self, fname):
        """Export events to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        np.savetxt(
            fname,
            self.current["events"][:, [0, 2]],
            fmt="%d",
            delimiter=",",
            header="pos,type",
            comments="",
        )

    def export_annotations(self, fname):
        """Export annotations to a CSV file."""
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        annots = self.current["data"].annotations
        with open(fname, "w") as f:
            f.write("type,onset,duration\n")
            for a in zip(annots.description, annots.onset, annots.duration):
                f.write(",".join([a[0], str(a[1]), str(a[2])]))
                f.write("\n")

    def export_ica(self, fname):
        """Export ICA solution to file."""
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
                raise LabelsNotFoundError(
                    "The following imported channel labels are not contained in the "
                    "data: " + ",".join(unknown)
                )
            else:
                self.current["data"].info["bads"] = bads

    @data_changed
    def import_events(self, fname):
        """Import events from a CSV or FIF file."""
        if fname.lower().endswith(".csv"):
            pos, desc = [], []
            with open(fname) as f:
                f.readline()  # skip header
                for line in f:
                    p, d = (int(token.strip()) for token in line.split(","))
                    pos.append(p)
                    desc.append(d)
            events = np.column_stack((pos, desc))
            events = np.insert(events, 1, 0, axis=1)  # insert zero column
            if self.current["events"] is not None:
                events = np.row_stack((self.current["events"], events))
                events = np.unique(events, axis=0)
            self.current["events"] = events
        elif fname.lower().endswith(".fif"):
            self.current["events"] = mne.read_events(fname)
        else:
            raise ValueError(f"Unsupported event file: {fname}")

    @data_changed
    def import_annotations(self, fname):
        """Import annotations from a CSV file."""
        descs, onsets, durations = [], [], []
        fs = self.current["data"].info["sfreq"]
        with open(fname) as f:
            f.readline()  # skip header
            for line in f:
                annot = line.split(",")
                if len(annot) == 3:  # type, onset, duration
                    onset = float(annot[1].strip())
                    duration = float(annot[2].strip())
                    if onset > self.current["data"].n_times / fs:
                        raise InvalidAnnotationsError(
                            "One or more annotations are outside the data range."
                        )
                    else:
                        descs.append(annot[0].strip())
                        onsets.append(onset)
                        durations.append(duration)
        annotations = mne.Annotations(onsets, durations, descs)
        self.current["data"].set_annotations(annotations)

    @data_changed
    def import_ica(self, fname):
        """Import ICA solution from file."""
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

        fs = data.info["sfreq"]
        n_samples = len(data.times)
        samples = f"{n_samples:,}".replace(",", "\u2009")

        seconds = n_samples / fs
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        hours, minutes = int(hours), int(minutes)
        if hours > 0:
            length = f"{hours}\u2009h {minutes}\u2009m {seconds:.3g}\u2009s"
        elif minutes > 0:
            length = f"{minutes}\u2009m {seconds:.3g}\u2009s"
        else:
            length = f"{seconds:.3g}\u2009s"

        if self.current["dtype"] == "epochs":  # add epoch count
            length = f"{self.current['data'].events.shape[0]} x {length}"
            samples = f"{self.current['data'].events.shape[0]} x {samples}"

        if data.info["bads"]:
            nbads = len(data.info["bads"])
            nchan = f"{data.info['nchan']} ({nbads} bad)"
        else:
            nchan = data.info["nchan"]
        chans = Counter(
            [mne.channel_type(data.info, i) for i in range(data.info["nchan"])]
        )
        # sort by channel type (always move "stim" to end of list)
        chans = sorted(dict(chans).items(), key=lambda x: (x[0] == "stim", x[0]))
        chans = ", ".join([" ".join([str(v), k.upper()]) for k, v in chans])

        if events is not None and events.shape[0] > 0:
            unique, counts = np.unique(events[:, 2], return_counts=True)
            events = f"{events.shape[0]} ("
            if len(unique) < 8:
                events += ", ".join([f"{u}: {c}" for u, c in zip(unique, counts)])
            elif 8 <= len(unique) <= 12:
                events += ", ".join([f"{u}" for u in unique])
            else:
                first = ", ".join([f"{u}" for u in unique[:6]])
                last = ", ".join([f"{u}" for u in unique[-6:]])
                events += f"{first}, ..., {last}"
            events += ")"
        else:
            events = "-"

        if isinstance(reference, list):
            reference = ",".join(reference)

        locations = count_locations(self.current["data"].info)

        if montage is None and not locations:
            montage_text = "none"
        elif montage is None and locations:
            montage_text = f"custom ({locations}/{data.info['nchan']} locations)"
        elif montage:
            montage_text = f"{montage} ({locations}/{data.info['nchan']} locations)"

        if ica is not None:
            method = ica.method.title()
            if method == "Fastica":
                method = "FastICA"
            ica = f"{method} ({ica.n_components_} components)"
        else:
            ica = "-"

        size_disk = f"{fsize:.2f}\u2009MB" if fname else "-"

        if hasattr(data, "annotations") and data.annotations is not None:
            annots = len(data.annotations.description)
            if annots == 0:
                annots = "-"
        else:
            annots = "-"
        return {
            "File name": fname if fname else "-",
            "File type": ftype if ftype else "-",
            "Data type": dtype,
            "Size on disk": size_disk,
            "Size in memory": f"{data.get_data().nbytes / 1024**2:.2f}\u2009MB",
            "Channels": f"{nchan} (" + chans + ")",
            "Samples": samples,
            "Sampling frequency": f"{fs:.6g}\u2009Hz",
            "Length": length,
            "Events": events,
            "Annotations": annots,
            "Reference": reference if reference else "-",
            "Montage": montage_text,
            "ICA": ica,
        }

    @data_changed
    def pick_channels(self, picks):
        self.current["data"] = self.current["data"].pick(picks)
        self.current["name"] += " (channels picked)"
        self.history.append(f"data.pick({picks})")

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
    def rename_channels(self, new_names):
        old_names = self.current["data"].info["ch_names"]
        mapping = {o: n for o, n in zip(old_names, new_names) if o != n}
        if not mapping:
            return
        mne.rename_channels(self.current["data"].info, mapping)
        self.history.append(f"mne.rename_channels(data.info, {mapping})")

    @data_changed
    def set_montage(
        self,
        montage,
        match_case=False,
        match_alias=False,
        on_missing="raise",
    ):
        self.current["data"].set_montage(
            montage=montage,
            match_case=match_case,
            match_alias=match_alias,
            on_missing=on_missing,
        )
        self.current["montage"] = montage
        if montage is None:
            self.history.append("data.set_montage(None)")
        else:
            self.history.append(
                f"data.set_montage({montage!r}, match_case={match_case}, "
                f"match_alias={match_alias}, on_missing={on_missing!r})"
            )

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
        """Return idx and names of those sets that are compatible with the current one.

        This function checks which data sets can be appended to the current data set.

        Returns
        -------
        compatibles: List[Tuple[index, name]]
            List of Tuples with compatible data sets.
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
            if not np.isclose(d["data"].info["highpass"], data.info["highpass"]):
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
            compatibles.append((idx, d["name"]))
        return compatibles

    @data_changed
    def append_data(self, selected_idx):
        """Append the given raw data sets."""
        self.current["name"] += " (appended)"
        files = [self.current["data"]]
        indices = []

        for idx in selected_idx:
            files.append(self.data[idx]["data"])
            indices.append(f"datasets[{idx}]")

        if self.current["dtype"] == "raw":
            self.current["data"] = mne.concatenate_raws(files)
            self.history.append(f"mne.concatenate_raws(data, {', '.join(indices)})")
        elif self.current["dtype"] == "epochs":
            self.current["data"] = mne.concatenate_epochs(files)
            self.history.append(f"mne.concatenate_epochs(data, {', '.join(indices)})")

    @data_changed
    def apply_ica(self):
        self.current["ica"].apply(self.current["data"])
        self.history.append(
            f"ica.apply(inst=data, exclude={self.current['ica'].exclude})"
        )
        self.current["name"] += " (ICA)"

    @data_changed
    def interpolate_bads(self, reset_bads, mode, origin):
        self.current["data"].interpolate_bads(reset_bads, mode, origin)
        self.history.append(
            f"data.interpolate_bads(reset_bads={reset_bads}, mode={mode}, "
            f"origin={origin})"
        )
        self.current["name"] += " (interpolated)"

    @data_changed
    def epoch_data(self, event_id, tmin, tmax, baseline):
        epochs = mne.Epochs(
            self.current["data"],
            self.current["events"],
            event_id=event_id,
            tmin=tmin,
            tmax=tmax,
            baseline=baseline,
            preload=True,
        )
        self.history.append(
            f"data = mne.Epochs(data, events, event_id={event_id}, "
            f"tmin={tmin}, tmax={tmax}, baseline={baseline}, preload=True)"
        )
        self.current["data"] = epochs
        self.current["dtype"] = "epochs"
        self.current["events"] = self.current["data"].events
        self.current["name"] += " (epoched)"

    @data_changed
    def drop_bad_epochs(self, reject, flat):
        self.current["data"].drop_bad(reject, flat)
        self.current["name"] += " (dropped bad epochs)"
        self.history.append(f"data.drop_bad({reject}, {flat})")

    @data_changed
    def convert_od(self):
        self.current["data"] = mne.preprocessing.nirs.optical_density(
            self.current["data"]
        )
        self.current["name"] += " (OD)"
        self.history.append("data = mne.preprocessing.nirs.optical_density(data)")

    @data_changed
    def convert_beer_lambert(self):
        self.current["data"] = mne.preprocessing.nirs.beer_lambert_law(
            self.current["data"]
        )
        self.current["name"] += " (BL)"
        self.history.append("data = mne.preprocessing.nirs.beer_lambert_law(data)")

    @data_changed
    def change_reference(self, add, ref):
        self.current["reference"] = ref
        if add:
            mne.add_reference_channels(self.current["data"], add, copy=False)
            self.history.append(f"mne.add_reference_channels(data, {add}, copy=False)")
        if ref is None:
            return

        self.current["reference"] = ref
        if ref == "average":
            self.current["name"] += " (average ref)"
        else:
            self.current["name"] += " (" + ",".join(ref) + ")"
        self.current["data"].set_eeg_reference(ref)
        self.history.append(f"data.set_eeg_reference({ref!r})")

    @data_changed
    def set_events(self, events):
        self.current["events"] = events

    @data_changed
    def set_annotations(self, onset, duration, description):
        self.current["data"].set_annotations(
            mne.Annotations(onset, duration, description)
        )

    @data_changed
    def move_data(self, source, target):
        """
        Change the position of a single data set in `self.data`.

        Parameters
        ----------
        source : int
            The data set's initial index.
        target : int
            The index the data set should be moved to.
        """
        # first the data set is copied to the target index
        self.data.insert(target, self.data[source])
        self.history.append(f"datasets.insert({target}, datasets[{source}])")
        # if moved to the front, the source index is increased by 1
        if source > target:
            source += 1
        # if moved to the back, the new index (after removing the original data set)
        # will be 1 less that the target index
        else:
            target -= 1
        self.index = target
        self.data.pop(source)
        self.history.append(f"datasets.pop({source})")
