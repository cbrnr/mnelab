# © MNELAB developers
#
# License: BSD (3-clause)

import os
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from functools import wraps
from os.path import getsize, join, split, splitext
from pathlib import Path

import mne
import numpy as np

from mnelab.io import UnsupportedFileTypeError, read_epochs, read_raw, write_raw
from mnelab.io.readers import split_name_ext
from mnelab.utils import count_locations, run_iclabel


class LabelsNotFoundError(Exception):
    pass


class InvalidAnnotationsError(Exception):
    pass


class AddReferenceError(Exception):
    pass


def data_changed(_func=None, *, invalidate_cache=True):
    """Decorator: call view.data_changed() after f(), optionally invalidating cache."""

    def decorator(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if invalidate_cache and self.current is not None:
                self._invalidate_cache()
            if self.view is not None:
                with self.view._wait_cursor():
                    result = f(self, *args, **kwargs)
                    self.view.data_changed()
            else:
                result = f(self, *args, **kwargs)
            return result

        return wrapper

    if _func is not None:
        return decorator(_func)
    return decorator


class Model:
    """Data model for MNELAB."""

    def __init__(self):
        self.view = None  # current view
        self.data = []  # list of data sets
        self.index = -1  # index of currently active data set
        self._next_id = 1  # monotonically increasing dataset ID counter
        self._temp_files = set()  # paths of temporary .fif cache files
        self.log = []  # captured MNE log messages
        self.history = [
            "from copy import deepcopy",
            "import mne",
            "from mnelab.io import read_raw",
            "from mnelab.utils import annotations_between_events, run_iclabel",
            "import numpy as np",
            "from mnelab.utils import ("
            "detect_extreme_values,"
            "detect_kurtosis,"
            "detect_peak_to_peak,"
            "detect_with_autoreject,"
            ")"
            "",
            "datasets = []",
        ]

    @data_changed(invalidate_cache=False)
    def insert_data(self, dataset, parent_id=None):
        """Insert data set after current index."""
        dataset["id"] = self._next_id
        dataset["parent_id"] = parent_id
        self._next_id += 1
        self.index += 1
        self.data.insert(self.index, dataset)
        self.history.append(f"datasets.insert({self.index}, data)")

    @data_changed(invalidate_cache=False)
    def update_data(self, dataset):
        """Update/overwrite data set at current index."""
        self.current = dataset

    @data_changed(invalidate_cache=False)
    def remove_data(self, index=-1):
        """Remove data set at current index."""
        if index == -1:
            index = self.index

        self._cleanup_dataset_cache(self.data[index])
        self.data.pop(index)
        self.history.append(f"datasets.pop({index})")

        if self.index >= len(self.data):  # if last entry was removed
            self.index = len(self.data) - 1  # reset index to last entry

    @data_changed(invalidate_cache=False)
    def duplicate_data(self):
        """Duplicate current data set."""
        parent_id = self.current["id"]
        self.insert_data(deepcopy(self.current), parent_id=parent_id)
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
        return sum(
            item["data"].get_data().nbytes
            for item in self.data
            if item["data"] is not None
        )

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

    def find_index_by_id(self, dataset_id):
        """Return the list index of the dataset with the given stable ID."""
        for i, dataset in enumerate(self.data):
            if dataset["id"] == dataset_id:
                return i
        return -1

    def find_descendants(self, dataset_id):
        """Return all datasets that are direct or indirect children of dataset_id."""
        descendants = []
        queue = [dataset_id]
        while queue:
            cur = queue.pop(0)
            for ds in self.data:
                if ds["parent_id"] == cur:
                    descendants.append(ds)
                    queue.append(ds["id"])
        return descendants

    @data_changed(invalidate_cache=False)
    def remove_data_cascade(self, dataset_id):
        """Remove a dataset and all its descendants."""
        ids_to_remove = set()
        queue = [dataset_id]
        while queue:
            cur = queue.pop(0)
            ids_to_remove.add(cur)
            queue.extend(ds["id"] for ds in self.data if ds["parent_id"] == cur)
        # remove from highest index to lowest to keep earlier indices valid
        indices = sorted(
            [i for i, ds in enumerate(self.data) if ds["id"] in ids_to_remove],
            reverse=True,
        )
        for i in indices:
            self._cleanup_dataset_cache(self.data[i])
            self.data.pop(i)
            self.history.append(f"datasets.pop({i})")
        if self.index >= len(self.data):
            self.index = len(self.data) - 1

    @data_changed(invalidate_cache=False)
    def load_data(self, data, fname, name=None):
        """Load a Raw or Epochs object as a new dataset.

        Parameters
        ----------
        data : mne.io.Raw | mne.Epochs
            The data object to load.
        fname : str
            The file path.
        name : str, optional
            Custom name for the dataset. If None, uses the filename.
        """
        fname = str(Path(fname).resolve().as_posix())
        fsize = getsize(fname) / 1024**2  # convert to MB
        if name is None:
            name, ext = split_name_ext(fname)
        else:
            _, ext = split_name_ext(fname)
        if isinstance(data, mne.BaseEpochs):
            dtype = "epochs"
            events = data.events
            # invert event_id from {label: id} to {id: label} for event_mapping
            event_mapping = defaultdict(str, {v: k for k, v in data.event_id.items()})
        else:
            dtype = "raw"
            events = np.empty((0, 3), dtype=int)
            event_mapping = defaultdict(str)
        self.insert_data(
            defaultdict(
                lambda: None,
                name=name,
                fname=fname,
                ftype=ext.upper()[1:],
                fsize=fsize,
                data=data,
                dtype=dtype,
                montage=None,
                events=events,
                event_mapping=event_mapping,
                _cache_path=None,
            )
        )

    @data_changed(invalidate_cache=False)
    def load(self, fname, *args, **kwargs):
        """Load data set from file."""
        fname = str(Path(fname).resolve().as_posix())
        try:
            data = read_raw(fname, *args, **kwargs, preload=True)
        except ValueError as e:
            try:
                data = read_epochs(fname, *args, **kwargs, preload=True)
            except UnsupportedFileTypeError:
                raise e
            self.history.append(
                f'data = read_epochs("{fname}", preload=True)'.replace("'", '"')
            )
        else:
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
        name, _ = split_name_ext(fname)
        self.load_data(data, fname, name=name)

    @data_changed
    def find_events(
        self,
        stim_channel,
        consecutive=True,
        initial_event=False,
        mask=None,
        min_duration=0,
        shortest_event=0,
    ):
        """Find events in raw data."""
        events = mne.find_events(
            self.current["data"],
            stim_channel=stim_channel,
            consecutive=consecutive,
            initial_event=initial_event,
            mask=mask,
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
            if mask is not None:
                hist += f", mask={mask!r}"
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
        # get unique event types
        unique_events = {
            int(v): str(v) for v in np.unique(self.current["events"][:, 2])
        }
        event_mapping = {
            k: v for k, v in self.current.get("event_mapping").items() if v
        }
        mapping = {**unique_events, **event_mapping}
        annots = mne.annotations_from_events(
            self.current["events"],
            self.current["data"].info["sfreq"],
            event_desc=mapping,
        )
        if len(annots) > 0:
            annots = mne.Annotations(
                onset=annots.onset,
                duration=annots.duration,
                description=annots.description,
                orig_time=self.current["data"].annotations.orig_time,
            )
            self.current["data"].set_annotations(
                self.current["data"].annotations + annots
            )
            hist = 'annots = mne.annotations_from_events(events, data.info["sfreq"]'
            if mapping is not None:
                hist += f", event_desc={mapping}"
            hist += ")\n"
            hist += "data.set_annotations(data.annotations + annots)"
            self.history.append(hist)

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

    def export_annotations(self, fname, types=None):
        """Export annotations to a CSV file.

        Parameters
        ----------
        fname : str
            Destination file path.
        types : list of str or None
            Annotation types (descriptions) to export.  If `None`, all types are
            exported.
        """
        name, ext = splitext(split(fname)[-1])
        ext = ext if ext else ".csv"  # automatically add extension
        fname = join(split(fname)[0], name + ext)
        annots = self.current["data"].annotations
        with open(fname, "w") as f:
            f.write("type,onset,duration\n")
            for desc, onset, duration in zip(
                annots.description, annots.onset, annots.duration
            ):
                if types is None or desc in types:
                    f.write(",".join([desc, str(onset), str(duration)]))
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
                events = np.vstack((self.current["events"], events))
                events = np.unique(events, axis=0)
            self.current["events"] = events
        elif fname.lower().endswith(".fif"):
            self.current["events"] = mne.read_events(fname)
        else:
            raise ValueError(f"Unsupported event file: {fname}")

    @data_changed
    def import_annotations(self, fname, types=None, description=None, unit="seconds"):
        """Import annotations from a CSV file.

        Parameters
        ----------
        fname : str
            Source file path.
        types : list of str or None
            Annotation types to import. `None` imports all types.
        description : str or None
            Label assigned to every annotation when the file has no type column. Ignored
            when the type column is present.
        unit : str
            `"seconds"` (default) or `"samples"`. When `"samples"`, onset and duration
            values are divided by `sfreq` to convert them to seconds.
        """
        descs, onsets, durations = [], [], []
        fs = self.current["data"].info["sfreq"]
        try:
            with open(fname) as f:
                header = f.readline().strip()
                has_type_col = header == "type,onset,duration"
                no_type_col = header == "onset,duration"
                if not has_type_col and not no_type_col:
                    raise InvalidAnnotationsError(
                        "Invalid annotations file (expected header: "
                        "'type,onset,duration' or 'onset,duration')."
                    )
                for line in f:
                    annot = line.split(",")
                    if has_type_col:
                        if len(annot) < 3:
                            continue
                        desc = annot[0].strip()
                        onset_str = annot[1].strip()
                        duration_str = annot[2].strip()
                    else:  # no type column
                        if len(annot) < 2:
                            continue
                        desc = description if description is not None else "annotation"
                        onset_str = annot[0].strip()
                        duration_str = annot[1].strip()
                    if types is not None and desc not in types:
                        continue
                    try:
                        onset = float(onset_str)
                        duration = float(duration_str)
                    except ValueError:
                        raise InvalidAnnotationsError(
                            "One or more annotations have invalid onset or duration"
                            " values."
                        )
                    if unit == "samples":
                        onset /= fs
                        duration /= fs
                    if onset > self.current["data"].n_times / fs:
                        raise InvalidAnnotationsError(
                            "One or more annotations are outside the data range."
                        )
                    descs.append(desc)
                    onsets.append(onset)
                    durations.append(duration)
        except InvalidAnnotationsError:
            raise
        except UnicodeDecodeError:
            raise InvalidAnnotationsError(
                "The file contains binary data and cannot be read as CSV."
            )
        existing = self.current["data"].annotations
        new = mne.Annotations(onsets, durations, descs, orig_time=existing.orig_time)
        self.current["data"].set_annotations(existing + new)

    @data_changed
    def import_ica(self, fname):
        """Import ICA solution from file."""
        self.current["ica"] = mne.preprocessing.read_ica(fname)
        self.current["iclabel"] = None
        self.history.append(f"ica = mne.preprocessing.read_ica({fname!r})")

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
            events = "–"

        if isinstance(reference, list):
            reference = ",".join(reference)

        locations = count_locations(self.current["data"].info)

        if montage is None and not locations:
            montage_text = "–"
        elif montage is None and locations:
            montage_text = f"custom ({locations}/{data.info['nchan']} locations)"
        else:
            montage_text = (
                f"{montage.name} ({locations}/{data.info['nchan']} locations)"
            )
        if ica is not None:
            method = ica.method.title()
            if method == "Fastica":
                method = "FastICA"
            n_active = ica.n_components_ - len(ica.exclude)
            ica = f"{method} ({n_active}/{ica.n_components_} components)"
        else:
            ica = "–"

        size_disk = f"{fsize:.2f}\u2009MB" if fname else "–"

        if hasattr(data, "annotations") and data.annotations is not None:
            annots = len(data.annotations.description)
            if annots == 0:
                annots = "–"
        else:
            annots = "–"
        return {
            "File Name": fname if fname else "–",
            "File Type": ftype if ftype else "–",
            "Data Type": dtype,
            "Size on Disk": size_disk,
            "Size in Memory": f"{data.get_data().nbytes / 1024**2:.2f}\u2009MB",
            "Channels": f"{nchan} (" + chans + ")",
            "Samples": samples,
            "Sampling Frequency": f"{fs:.6g}\u2009Hz",
            "Length": length,
            "Events": events,
            "Annotations": annots,
            "Reference": reference if reference else "–",
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
        self.current["montage"] = montage
        self.current["data"].set_montage(
            montage=montage.montage if montage is not None else None,
            match_case=match_case,
            match_alias=match_alias,
            on_missing=on_missing,
        )
        if montage is None:
            self.history.append("data.set_montage(None)")
        else:
            if montage.path is not None:
                self.history.append(
                    f"montage = mne.read_custom_montage('{montage.path}')"
                )
            else:
                self.history.append(
                    f"montage = mne.channels.make_standard_montage('{montage.name}')"
                )
            self.history.append(
                f"data.set_montage(montage, match_case={match_case}, "
                f"match_alias={match_alias}, on_missing={on_missing!r})"
            )
            self.current["iclabel"] = None

    @data_changed
    def filter(self, lower=None, upper=None, notch=None):
        """Apply filters to the current data based on provided parameters."""
        if lower is not None and upper is not None:  # bandpass filter
            self.current["data"].filter(lower, upper)
            self.current["name"] += f" ({lower}-{upper}\u2009Hz)"
            self.history.append(f"data.filter({lower}, {upper})")
        elif lower is not None:  # highpass filter
            self.current["data"].filter(lower, None)
            self.current["name"] += f" (>{lower}\u2009Hz)"
            self.history.append(f"data.filter({lower}, None)")
        elif upper is not None:  # lowpass filter
            self.current["data"].filter(None, upper)
            self.current["name"] += f" (<{upper}\u2009Hz)"
            self.history.append(f"data.filter(None, {upper})")
        elif notch is not None:  # notch filter
            self.current["data"].notch_filter(notch)
            self.current["name"] += f" (notch {notch}\u2009Hz)"
            self.history.append(f"data.notch_filter({notch})")

    @data_changed
    def crop(self, start, stop):
        self.current["data"].crop(start, stop)
        self.current["name"] += " (cropped)"
        self.history.append(f"data.crop({start}, {stop})")

    def get_compatibles(self):
        """Return indices and names of datasets compatible with the current one.

        Checks which datasets can be appended to the current dataset.

        Returns
        -------
        list of tuple of (int, str)
            Indices and names of compatible datasets.
        """
        compatibles = []
        data = self.current["data"]
        for idx, d in enumerate(self.data):
            if idx == self.index:  # skip current dataset
                continue
            if d["dtype"] not in ("raw", "epochs"):
                continue
            if d["dtype"] != self.current["dtype"]:
                continue
            d_info = d["data"].info if d["data"] is not None else d["_evict_info"]
            if d_info["nchan"] != data.info["nchan"]:
                continue
            if set(d_info["ch_names"]) != set(data.info["ch_names"]):
                continue
            if d_info["bads"] != data.info["bads"]:
                continue
            if not np.isclose(d_info["sfreq"], data.info["sfreq"]):
                continue
            if not np.isclose(d_info["highpass"], data.info["highpass"]):
                continue
            if not np.isclose(d_info["lowpass"], data.info["lowpass"]):
                continue
            if d["dtype"] == "raw":
                d_cals = d["data"]._cals if d["data"] is not None else d["_evict_cals"]
                if any(d_cals != data._cals):
                    continue
            if d["dtype"] == "epochs":
                if d["data"] is not None:
                    d_tmin = d["data"].tmin
                    d_tmax = d["data"].tmax
                    d_baseline = d["data"].baseline
                else:
                    d_tmin = d["_evict_tmin"]
                    d_tmax = d["_evict_tmax"]
                    d_baseline = d["_evict_baseline"]
                if d_tmin != data.tmin:
                    continue
                if d_tmax != data.tmax:
                    continue
                if d_baseline != data.baseline:
                    continue
            compatibles.append((idx, d["name"]))
        return compatibles

    @data_changed
    def append_data(self, selected_idx):
        """Append the given raw data sets."""
        for idx in selected_idx:  # ensure all source datasets are in memory
            self.reload_dataset(idx)
        self.current["name"] += " (appended)"
        datasets = [self.current["data"]]
        indices = []

        for idx in selected_idx:
            datasets.append(self.data[idx]["data"])
            indices.append(f"datasets[{idx}]")

        if self.current["dtype"] == "raw":
            self.current["data"] = mne.concatenate_raws(datasets)
            self.history.append(f"mne.concatenate_raws(data, {', '.join(indices)})")
        elif self.current["dtype"] == "epochs":
            self.current["data"] = mne.concatenate_epochs(datasets)
            self.history.append(f"mne.concatenate_epochs(data, {', '.join(indices)})")

    @data_changed
    def apply_ica(self):
        self.current["ica"].apply(self.current["data"])
        self.history.append(
            f"ica.apply(inst=data, exclude={self.current['ica'].exclude})"
        )
        self.current["name"] += " (ICA)"

    @data_changed(invalidate_cache=False)
    def get_iclabels(self):
        """Get ICLabel classifications for current ICA solution."""
        if self.current["iclabel"] is None:
            if self.current["data"].get_montage() is None:
                raise ValueError("Montage must be set before ICLabel classification.")
            if self.current["ica"] is None:
                raise ValueError("No ICA solution found in current data set.")
            probs = run_iclabel(self.current["data"], self.current["ica"])
            self.current["iclabel"] = probs
            self.history.append("probs = run_iclabel(data, ica)")
        return self.current["iclabel"]

    @data_changed
    def interpolate_bads(self):
        self.current["data"].interpolate_bads()
        self.history.append("data.interpolate_bads()")
        self.current["name"] += " (interpolated)"

    @data_changed
    def epoch_data(self, event_id, tmin, tmax, baseline):
        epochs = mne.Epochs(
            self.current["data"],
            self.current["events"][np.isin(self.current["events"][:, 2], event_id)],
            tmin=tmin,
            tmax=tmax,
            baseline=baseline,
            preload=True,
        )
        self.history.append(
            f"data = mne.Epochs(data, events[np.isin(events[:, 2], {event_id})], "
            f"tmin={tmin}, tmax={tmax}, baseline={baseline}, preload=True)"
        )
        self.current["data"] = epochs
        self.current["dtype"] = "epochs"
        self.current["events"] = self.current["data"].events

    @data_changed
    def drop_bad_epochs(self, reject, flat):
        self.current["data"].drop_bad(reject, flat)
        self.current["name"] += " (dropped bad epochs)"
        self.history.append(f"data.drop_bad({reject}, {flat})")

    @data_changed
    def drop_detected_artifacts(self, indices):
        self.current["data"].drop(indices, reason="ARTIFACT_DETECTION")
        self.current["name"] += " (dropped detected epochs)"

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

    @data_changed(invalidate_cache=False)
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

        # pop and save
        item = self.data.pop(source)
        self.history.append(f"item = datasets.pop({source})")

        # insert
        self.data.insert(target, item)
        self.history.append(f"datasets.insert({target}, item)")

        # select
        self.index = target
        self.history.append(f"data = datasets[{target}]")

    def _cleanup_dataset_cache(self, dataset):
        """Delete the temp cache file for a dataset, if one exists."""
        path = dataset["_cache_path"]
        if path:
            Path(path).unlink(missing_ok=True)
            self._temp_files.discard(path)
            dataset["_cache_path"] = None

    def _invalidate_cache(self):
        """Mark the current dataset's cache as stale.

        The cache path is cleared so the next eviction will write a fresh file.
        The old temp file (if any) is left on disk and collected by `cleanup()`.
        """
        self.current["_cache_path"] = None

    def evict_dataset(self, index):
        """Remove the in-memory data for the dataset at *index*.

        If no cache file exists yet the data is saved to a temporary FIF file
        first. If a valid cache already exists (e.g. from a previous eviction
        cycle) the write is skipped.
        """
        dataset = self.data[index]
        if dataset["data"] is None:
            return  # already evicted
        if dataset["_cache_path"] is None:
            suffix = "_raw.fif" if dataset["dtype"] == "raw" else "_epo.fif"
            fd, path = tempfile.mkstemp(suffix=suffix, prefix="mnelab_")
            os.close(fd)
            dataset["data"].save(path, overwrite=True)
            dataset["_cache_path"] = path
            self._temp_files.add(path)
        # snapshot fields needed to check compatibility while evicted
        dataset["_evict_info"] = dataset["data"].info
        if dataset["dtype"] == "raw":
            dataset["_evict_cals"] = dataset["data"]._cals.copy()
        else:
            dataset["_evict_tmin"] = dataset["data"].tmin
            dataset["_evict_tmax"] = dataset["data"].tmax
            dataset["_evict_baseline"] = dataset["data"].baseline
        dataset["data"] = None

    def reload_dataset(self, index):
        """Restore in-memory data for the dataset at *index* from its cache.

        Parameters
        ----------
        index : int
            Index into `self.data`.

        Raises
        ------
        RuntimeError
            If no cache file exists for the dataset.
        """
        dataset = self.data[index]
        if dataset["data"] is not None:
            return  # already in memory
        path = dataset["_cache_path"]
        if path is None:
            raise RuntimeError(
                f"Dataset at index {index} has no cache file to reload from."
            )
        if dataset["dtype"] == "raw":
            dataset["data"] = mne.io.read_raw_fif(path, preload=True)
        else:
            dataset["data"] = mne.read_epochs(path, preload=True)

    def cleanup(self):
        """Delete all temporary cache files created during this session."""
        for path in list(self._temp_files):
            Path(path).unlink(missing_ok=True)
        self._temp_files.clear()
