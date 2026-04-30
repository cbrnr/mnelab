# © MNELAB developers
#
# License: BSD (3-clause)

import inspect
import json
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from functools import wraps
from importlib.metadata import version as _pkg_version
from os.path import getsize, join, split, splitext
from pathlib import Path

import mne
import numpy as np

from mnelab.io import read_raw, write_raw
from mnelab.io.readers import split_name_ext
from mnelab.utils import Montage, count_locations, run_iclabel


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


def pipeline_step(op_name, copy_data=True):
    """Create a child dataset, then run a mutating operation on it.

    Every decorated method automatically duplicates the current dataset and records the
    operation name and parameters before executing the body. This makes every mutation
    visible as a node in the pipeline tree.

    Parameters
    ----------
    op_name : str
        Name stored in the child dataset's `operation` field.
    copy_data : bool
        If True (default), the current dataset is deep-copied in full, including the
        heavy MNE data object. Set to False for operations that only *read* the data
        without modifying it (e.g. `find_events`) to avoid an unnecessary copy of the
        raw signal array.
    """

    def decorator(f):
        sig = inspect.signature(f)

        @wraps(f)
        def wrapper(self, *args, **kwargs):
            # capture params via introspection
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            params = dict(bound.arguments)
            params.pop("self", None)

            # create child dataset
            parent_index = self.index
            insert_index = self._child_insert_index(parent_index)
            if copy_data:
                new_dataset = deepcopy(self.current)
            else:
                # share the MNE data object; deep-copy only the lightweight metadata so
                # that the events array etc. are independent
                new_dataset = defaultdict(lambda: None)
                for k, v in self.current.items():
                    new_dataset[k] = deepcopy(v) if k != "data" else v
            new_dataset["parent_index"] = parent_index
            new_dataset["operation"] = op_name
            new_dataset["operation_params"] = params
            new_dataset["fname"] = None
            new_dataset["ftype"] = None
            new_dataset["fsize"] = None
            self.index = insert_index
            # _insert_at keeps parent_index refs consistent across all datasets
            self._insert_at(self.index, new_dataset)

            def _run_operation():
                try:
                    return f(self, *args, **kwargs)
                except Exception:
                    self._pop_at(insert_index)
                    self.index = parent_index
                    raise

            # run the operation on the new (current) dataset
            if self.view is not None:
                with self.view._wait_cursor():
                    result = _run_operation()
                    self.view.data_changed()
            else:
                result = _run_operation()
            return result

        return wrapper

    return decorator


class Model:
    """Data model for MNELAB."""

    def __init__(self):
        self.view = None  # current view
        self.data = []  # list of data sets
        self.index = -1  # index of currently active data set
        self.log = []  # captured MNE log messages

    @data_changed
    def insert_data(self, dataset):
        """Insert data set after current index."""
        self.index += 1
        self._insert_at(self.index, dataset)

    @data_changed
    def update_data(self, dataset):
        """Update/overwrite data set at current index."""
        self.current = dataset

    @data_changed
    def remove_data(self, index=-1):
        """Remove data set and all its descendants."""
        if index == -1:
            index = self.index
        old_index = self.index

        # collect the target and all its descendants
        to_remove_set = {index} | set(self._get_descendants(index))
        to_remove = sorted(to_remove_set, reverse=True)
        parent_index = self.data[index].get("parent_index")

        def adjusted(old):
            return old - sum(1 for removed in to_remove if removed < old)

        for idx in to_remove:
            self.data.pop(idx)

        # update stored parent_index values in remaining datasets
        for ds in self.data:
            pi = ds.get("parent_index")
            if pi is not None:
                ds["parent_index"] = adjusted(pi)

        if not self.data:
            self.index = -1
        elif old_index in to_remove_set:
            if parent_index is not None and parent_index not in to_remove_set:
                self.index = adjusted(parent_index)
            else:
                self.index = max(0, min(adjusted(index), len(self.data) - 1))
        else:
            self.index = adjusted(old_index)

    @data_changed
    def duplicate_data(self):
        """Duplicate current data set as a child node in the pipeline tree."""
        parent_index = self.index
        new_dataset = deepcopy(self.current)
        new_dataset["parent_index"] = parent_index
        new_dataset["operation"] = "duplicate"
        new_dataset["operation_params"] = {}
        new_dataset["fname"] = None
        new_dataset["ftype"] = None
        new_dataset["fsize"] = None
        self.index = self._child_insert_index(parent_index)
        self._insert_at(self.index, new_dataset)

    @property
    def names(self):
        """Return list of all data set names."""
        return [item["name"] for item in self.data]

    @property
    def nbytes(self):
        """Return size (in bytes) of all data sets.

        Datasets that share the same underlying MNE data object (e.g. after a
        `find_events` step where `copy_data=False`) are counted only once so that the
        reported total reflects actual memory consumption.
        """
        seen = set()
        total = 0
        for item in self.data:
            obj = item["data"]
            obj_id = id(obj)
            if obj_id not in seen:
                seen.add(obj_id)
                total += obj.get_data().nbytes
        return total

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
    def load_raw(self, raw, fname, name=None):
        """Load a Raw object as a new dataset.

        Parameters
        ----------
        raw : mne.io.Raw
            The raw data object to load.
        fname : str
            The file path.
        name : str, optional
            Custom name for the dataset. If None, uses the filename.
        """
        fname = str(Path(fname).resolve().as_posix())
        fsize = getsize(raw.filenames[0]) / 1024**2  # convert to MB
        if name is None:
            name, ext = split_name_ext(fname)
        else:
            _, ext = split_name_ext(fname)
        self.insert_data(
            defaultdict(
                lambda: None,
                name=name,
                fname=fname,
                ftype=ext.upper()[1:],
                fsize=fsize,
                data=raw,
                dtype="raw",
                montage=None,
                events=np.empty((0, 3), dtype=int),
                event_mapping=defaultdict(str),
            )
        )

    @data_changed
    def load(self, fname, *args, **kwargs):
        """Load data set from file."""
        fname = str(Path(fname).resolve().as_posix())
        data = read_raw(fname, *args, **kwargs, preload=True)
        name, _ = split_name_ext(fname)
        self.load_raw(data, fname, name=name)

    @pipeline_step("find_events", copy_data=False)
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

    @pipeline_step("events_from_annotations", copy_data=False)
    def events_from_annotations(self):
        """Convert annotations to events."""
        events, mapping = mne.events_from_annotations(self.current["data"])
        if events.shape[0] > 0:
            # swap mapping for annotations from {str: int} to {int: str}
            mapping = {v: k for k, v in mapping.items()}
            self.current["events"] = events
            self.current["event_mapping"] = mapping

    @pipeline_step("annotations_from_events")
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
            montage_text = "-"
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

    @pipeline_step("pick_channels")
    def pick_channels(self, picks):
        self.current["data"] = self.current["data"].pick(picks)
        self.current["name"] += " (channels picked)"

    @pipeline_step("set_channel_properties")
    def set_channel_properties(self, bads=None, names=None, types=None):
        if bads != self.current["data"].info["bads"]:
            self.current["data"].info["bads"] = bads
        if names:
            mne.rename_channels(self.current["data"].info, names)
        if types:
            self.current["data"].set_channel_types(types)

    @pipeline_step("rename_channels")
    def rename_channels(self, new_names):
        old_names = self.current["data"].info["ch_names"]
        mapping = {o: n for o, n in zip(old_names, new_names) if o != n}
        if not mapping:
            return
        mne.rename_channels(self.current["data"].info, mapping)
        # store computed mapping for history generation
        self.current["operation_params"]["_mapping"] = mapping

    @pipeline_step("set_montage")
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
        self.current["iclabel"] = None

    @pipeline_step("filter")
    def filter(self, lower=None, upper=None, notch=None):
        """Apply filters to the current data based on provided parameters."""
        if lower is not None and upper is not None:  # bandpass filter
            self.current["data"].filter(lower, upper)
            self.current["name"] += f" ({lower}-{upper}\u2009Hz)"
        elif lower is not None:  # highpass filter
            self.current["data"].filter(lower, None)
            self.current["name"] += f" (>{lower}\u2009Hz)"
        elif upper is not None:  # lowpass filter
            self.current["data"].filter(None, upper)
            self.current["name"] += f" (<{upper}\u2009Hz)"
        elif notch is not None:  # notch filter
            self.current["data"].notch_filter(notch)
            self.current["name"] += f" (notch {notch}\u2009Hz)"

    @pipeline_step("crop")
    def crop(self, start, stop):
        self.current["data"].crop(start, stop)
        self.current["name"] += " (cropped)"

    def get_compatibles(self):
        """Return indices and names of data sets compatible with the current one.

        This function checks which data sets can be appended to the current data set.

        Returns
        -------
        compatibles: List[Tuple[int, str]]
            List of tuples (index, name) with compatible data sets.
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

    @pipeline_step("append_data")
    def append_data(self, selected_idx):
        """Append the given raw data sets."""
        self.current["name"] += " (appended)"
        # adjust indices for the insertion made by @pipeline_step
        adjusted_idx = [idx + 1 if idx >= self.index else idx for idx in selected_idx]
        datasets = [self.current["data"]]
        datasets.extend(self.data[idx]["data"] for idx in adjusted_idx)
        if self.current["dtype"] == "raw":
            self.current["data"] = mne.concatenate_raws(datasets)
        elif self.current["dtype"] == "epochs":
            self.current["data"] = mne.concatenate_epochs(datasets)

    @pipeline_step("apply_ica")
    def apply_ica(self):
        self.current["ica"].apply(self.current["data"])
        self.current["name"] += " (ICA)"

    @data_changed
    def get_iclabels(self):
        """Get ICLabel classifications for current ICA solution."""
        if self.current["iclabel"] is None:
            if self.current["data"].get_montage() is None:
                raise ValueError("Montage must be set before ICLabel classification.")
            if self.current["ica"] is None:
                raise ValueError("No ICA solution found in current data set.")
            probs = run_iclabel(self.current["data"], self.current["ica"])
            self.current["iclabel"] = probs
        return self.current["iclabel"]

    @pipeline_step("interpolate_bads")
    def interpolate_bads(self):
        self.current["data"].interpolate_bads()
        self.current["name"] += " (interpolated)"

    @pipeline_step("epoch_data")
    def epoch_data(self, event_id, tmin, tmax, baseline):
        epochs = mne.Epochs(
            self.current["data"],
            self.current["events"][np.isin(self.current["events"][:, 2], event_id)],
            tmin=tmin,
            tmax=tmax,
            baseline=baseline,
            preload=True,
        )
        self.current["data"] = epochs
        self.current["dtype"] = "epochs"
        self.current["events"] = self.current["data"].events

    @pipeline_step("drop_bad_epochs")
    def drop_bad_epochs(self, reject, flat):
        self.current["data"].drop_bad(reject, flat)
        self.current["name"] += " (dropped bad epochs)"

    @pipeline_step("drop_detected_artifacts")
    def drop_detected_artifacts(self, indices):
        self.current["data"].drop(indices, reason="ARTIFACT_DETECTION")
        self.current["name"] += " (dropped detected epochs)"

    @pipeline_step("convert_od")
    def convert_od(self):
        self.current["data"] = mne.preprocessing.nirs.optical_density(
            self.current["data"]
        )
        self.current["name"] += " (OD)"

    @pipeline_step("convert_beer_lambert")
    def convert_beer_lambert(self):
        self.current["data"] = mne.preprocessing.nirs.beer_lambert_law(
            self.current["data"]
        )
        self.current["name"] += " (BL)"

    @pipeline_step("change_reference")
    def change_reference(self, add, ref):
        self.current["reference"] = ref
        if add:
            mne.add_reference_channels(self.current["data"], add, copy=False)
        if ref is None:
            return
        self.current["reference"] = ref
        if ref == "average":
            self.current["name"] += " (average ref)"
        else:
            self.current["name"] += " (" + ",".join(ref) + ")"
        self.current["data"].set_eeg_reference(ref)

    @data_changed
    def set_events(self, events):
        self.current["events"] = events

    @data_changed
    def set_annotations(self, onset, duration, description):
        self.current["data"].set_annotations(
            mne.Annotations(onset, duration, description)
        )

    def _insert_at(self, at_index, dataset):
        """Insert *dataset* at *at_index* and fix all `parent_index` refs.

        After a plain `list.insert` every dataset that was already at position `>=
        at_index` is silently shifted one slot forward, but their stored `parent_index`
        values are left stale.  This helper performs the insertion *and* increments
        every `parent_index` that points to a position that was displaced by the
        insertion.
        """
        self.data.insert(at_index, dataset)
        for ds in self.data:
            if ds is dataset:
                continue
            pi = ds.get("parent_index")
            if pi is not None and pi >= at_index:
                ds["parent_index"] = pi + 1

    def _pop_at(self, index):
        """Remove one dataset and undo the `parent_index` shifts."""
        self.data.pop(index)
        for ds in self.data:
            pi = ds.get("parent_index")
            if pi is not None and pi > index:
                ds["parent_index"] = pi - 1

    def _child_insert_index(self, index):
        """Return where a new child of dataset *index* should be inserted."""
        return max([index, *self._get_descendants(index)]) + 1

    def _get_descendants(self, index):
        """Return all descendant dataset indices for the dataset at index."""
        descendants = []
        to_visit = [index]
        while to_visit:
            current = to_visit.pop()
            for i, ds in enumerate(self.data):
                if ds.get("parent_index") == current:
                    descendants.append(i)
                    to_visit.append(i)
        return descendants

    def get_pipeline_steps(self, idx=None):
        """Return ordered list of datasets from root ancestor to dataset[idx].

        Parameters
        ----------
        idx : int or None
            Dataset index. Defaults to `self.index`.

        Returns
        -------
        steps : list of dict
            Each dict has keys `index`, `name`, `operation`, `params`, `dtype`.
        """
        if idx is None:
            idx = self.index
        chain = []
        current = idx
        while current is not None:
            chain.append(current)
            current = self.data[current].get("parent_index")
        chain.reverse()
        return [
            {
                "index": i,
                "name": self.data[i]["name"],
                "operation": self.data[i].get("operation"),
                "params": self.data[i].get("operation_params"),
                "dtype": self.data[i].get("dtype"),
            }
            for i in chain
        ]

    def get_pipeline_tree(self):
        """Return the pipeline tree for all root datasets and their descendants.

        Returns
        -------
        tree : list of dict
            One entry per root dataset, each with a `children` list that recursively
            contains child nodes.
        """
        children = defaultdict(list)
        roots = []
        for i, ds in enumerate(self.data):
            pi = ds.get("parent_index")
            if pi is None:
                roots.append(i)
            else:
                children[pi].append(i)

        def build_node(idx):
            ds = self.data[idx]
            return {
                "index": idx,
                "name": ds["name"],
                "dtype": ds.get("dtype"),
                "operation": ds.get("operation"),
                "operation_params": ds.get("operation_params"),
                "children": [build_node(c) for c in children[idx]],
            }

        return [build_node(r) for r in roots]

    def get_history(self, idx=None):
        """Generate Python history code for the pipeline leading to dataset[idx].

        Parameters
        ----------
        idx : int or None
            Dataset index. Defaults to `self.index`.

        Returns
        -------
        lines : list of str
        """
        if idx is None:
            idx = self.index

        steps = self.get_pipeline_steps(idx)
        if not steps:
            return []

        lines = [
            "from copy import deepcopy",
            "import mne",
            "import numpy as np",
            "from mnelab.io import read_raw",
            "",
            "",
        ]

        root = self.data[steps[0]["index"]]
        fname = root.get("fname")
        if fname:
            lines.append(f'data = read_raw("{fname}", preload=True)')
        else:
            lines.append("data = None  # source dataset has no associated file")
        lines.append("")

        for step in steps[1:]:
            code = self._step_to_history(step["operation"], step["params"] or {})
            if code:
                lines.append(code)

        return lines

    def _step_to_history(self, operation, params):
        """Return Python code string for one pipeline step."""
        p = params or {}
        if operation == "filter":
            lower, upper, notch = p.get("lower"), p.get("upper"), p.get("notch")
            if lower is not None and upper is not None:
                return f"data.filter({lower}, {upper})"
            elif lower is not None:
                return f"data.filter({lower}, None)"
            elif upper is not None:
                return f"data.filter(None, {upper})"
            elif notch is not None:
                return f"data.notch_filter({notch})"
        elif operation == "crop":
            return f"data.crop({p.get('start')}, {p.get('stop')})"
        elif operation == "pick_channels":
            return f"data.pick({p.get('picks')!r})"
        elif operation == "rename_channels":
            mapping = p.get("_mapping") or {}
            if mapping:
                return f"mne.rename_channels(data.info, {mapping!r})"
        elif operation == "set_channel_properties":
            lines = []
            if p.get("bads") is not None:
                lines.append(f"data.info['bads'] = {p['bads']!r}")
            if p.get("names"):
                lines.append(f"mne.rename_channels(data.info, {p['names']!r})")
            if p.get("types"):
                lines.append(f"data.set_channel_types({p['types']!r})")
            return "\n".join(lines) if lines else None
        elif operation == "set_montage":
            montage = p.get("montage")
            if montage is None:
                return "data.set_montage(None)"
            # montage stored as Montage dataclass at runtime
            name = getattr(montage, "name", None) or (
                montage.get("name") if isinstance(montage, dict) else None
            )
            path = getattr(montage, "path", None) or (
                montage.get("path") if isinstance(montage, dict) else None
            )
            mc = p.get("match_case", False)
            ma = p.get("match_alias", False)
            om = p.get("on_missing", "raise")
            if path:
                first = f"montage = mne.read_custom_montage({str(path)!r})"
            else:
                first = f"montage = mne.channels.make_standard_montage({name!r})"
            second = (
                f"data.set_montage(montage, match_case={mc}, "
                f"match_alias={ma}, on_missing={om!r})"
            )
            return f"{first}\n{second}"
        elif operation == "change_reference":
            lines = []
            add = p.get("add")
            ref = p.get("ref")
            if add:
                lines.append(f"mne.add_reference_channels(data, {add!r}, copy=False)")
            if ref is not None:
                lines.append(f"data.set_eeg_reference({ref!r})")
            return "\n".join(lines) if lines else None
        elif operation == "interpolate_bads":
            return "data.interpolate_bads()"
        elif operation == "epoch_data":
            return (
                f"data = mne.Epochs(data, "
                f"events[np.isin(events[:, 2], {p.get('event_id')!r})], "
                f"tmin={p.get('tmin')}, tmax={p.get('tmax')}, "
                f"baseline={p.get('baseline')}, preload=True)"
            )
        elif operation == "drop_bad_epochs":
            return f"data.drop_bad({p.get('reject')!r}, {p.get('flat')!r})"
        elif operation == "drop_detected_artifacts":
            return f"data.drop({p.get('indices')!r}, reason='ARTIFACT_DETECTION')"
        elif operation == "apply_ica":
            return "ica.apply(inst=data)"
        elif operation == "convert_od":
            return "data = mne.preprocessing.nirs.optical_density(data)"
        elif operation == "convert_beer_lambert":
            return "data = mne.preprocessing.nirs.beer_lambert_law(data)"
        elif operation == "find_events":
            parts = ["events = mne.find_events(data"]
            if p.get("stim_channel"):
                parts.append(f", stim_channel={p['stim_channel']!r}")
            if p.get("consecutive") not in (None, "increasing"):
                parts.append(f", consecutive={p['consecutive']!r}")
            if p.get("initial_event"):
                parts.append(f", initial_event={p['initial_event']!r}")
            if p.get("mask") is not None:
                parts.append(f", mask={p['mask']!r}")
            if p.get("min_duration", 0) > 0:
                parts.append(f", min_duration={p['min_duration']!r}")
            if p.get("shortest_event", 2) != 2:
                parts.append(f", shortest_event={p['shortest_event']!r}")
            parts.append(")")
            return "".join(parts)
        elif operation == "events_from_annotations":
            return "events, _ = mne.events_from_annotations(data)"
        elif operation == "annotations_from_events":
            return (
                "annots = mne.annotations_from_events(events, data.info['sfreq'])\n"
                "data.set_annotations(data.annotations + annots)"
            )
        elif operation == "append_data":
            return "# append_data: source datasets depend on session context"
        elif operation == "duplicate":
            return "data = deepcopy(data)"
        return None

    def _serialize_params(self, operation, params):
        """Convert operation params to a JSON-serializable dict."""
        result = {}
        for k, v in (params or {}).items():
            if k.startswith("_"):
                continue  # skip internal keys (e.g. _mapping)
            if v is None:
                result[k] = None
            elif isinstance(v, Montage):
                result[k] = {
                    "__type__": "Montage",
                    "name": v.name,
                    "path": str(v.path) if v.path else None,
                }
            elif isinstance(v, np.ndarray):
                result[k] = v.tolist()
            elif isinstance(v, tuple):
                result[k] = list(v)
            elif isinstance(v, (int, float, str, bool, list, dict)):
                result[k] = v
            else:
                try:
                    json.dumps(v)
                    result[k] = v
                except (TypeError, ValueError):
                    pass  # skip non-serializable params
        return result

    def _deserialize_params(self, operation, params):
        """Reconstruct operation params from their serialized form."""
        from mne.channels import make_standard_montage, read_custom_montage

        result = {}
        for k, v in (params or {}).items():
            if isinstance(v, dict) and v.get("__type__") == "Montage":
                if v.get("path"):
                    mne_montage = read_custom_montage(v["path"])
                    result[k] = Montage(
                        montage=mne_montage,
                        name=v["name"],
                        path=Path(v["path"]),
                    )
                else:
                    mne_montage = make_standard_montage(v["name"])
                    result[k] = Montage(montage=mne_montage, name=v["name"], path=None)
            elif k == "baseline" and isinstance(v, list):
                result[k] = tuple(v) if v is not None else None
            else:
                result[k] = v
        return result

    def save_pipeline(self, idx=None, path=None):
        """Save the pipeline from root ancestor to dataset[idx] as .mnepipe JSON.

        Parameters
        ----------
        idx : int or None
            Dataset index. Defaults to `self.index`.
        path : str or Path
            Destination file path.
        """
        if idx is None:
            idx = self.index

        steps = self.get_pipeline_steps(idx)
        if not steps:
            return

        root_ds = self.data[steps[0]["index"]]
        root_data = root_ds.get("data")
        hints = {}
        if root_ds.get("dtype"):
            hints["dtype"] = root_ds["dtype"]
        if root_data is not None:
            hints["sfreq"] = root_data.info["sfreq"]
            hints["nchan"] = root_data.info["nchan"]

        pipeline_steps = []
        for step in steps[1:]:  # skip root (source dataset)
            operation = step["operation"]
            pipeline_steps.append(
                {
                    "operation": operation,
                    "name": step["name"],
                    "params": self._serialize_params(operation, step["params"]),
                }
            )

        try:
            mnelab_version = _pkg_version("mnelab")
        except Exception:
            mnelab_version = "unknown"

        pipeline = {
            "mnelab_version": mnelab_version,
            "pipeline_format": 1,
            "created": datetime.now(UTC).isoformat(),
            "hints": hints,
            "steps": pipeline_steps,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, indent=2)

    # operations that cannot be applied generically to a new dataset
    _UNREPLAYABLE_OPS = {"append_data", "apply_ica"}

    def apply_pipeline(self, pipeline_dict):
        """Apply a saved pipeline to the current dataset.

        Parameters
        ----------
        pipeline_dict : dict
            The loaded pipeline dictionary from a .mnepipe file.

        Raises
        ------
        ValueError
            If any step uses a non-replayable operation.
        """
        steps = pipeline_dict.get("steps", [])
        for step in steps:
            operation = step["operation"]
            if operation in self._UNREPLAYABLE_OPS:
                raise ValueError(
                    f"Operation {operation!r} cannot be replayed automatically "
                    "because it requires referencing other session datasets."
                )
            params = self._deserialize_params(operation, step.get("params", {}))
            method = getattr(self, operation, None)
            if method is None:
                raise ValueError(f"Unknown pipeline operation: {operation!r}")
            method(**params)
