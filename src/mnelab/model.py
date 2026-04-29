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
from mnelab.utils import (
    Montage,
    count_locations,
    read_annotations_from_file,
    run_iclabel,
)


class LabelsNotFoundError(Exception):
    pass


class InvalidAnnotationsError(Exception):
    pass


class AddReferenceError(Exception):
    pass


class PipelineCancelledError(Exception):
    pass


UNREPLAYABLE_PIPELINE_OPS = {"append_data"}
PARAMETERIZED_IMPORT_OPS = {"import_annotations", "import_bads", "import_ica"}
PIPELINE_EXECUTION_MODES = ("automatic", "prompt", "review", "skip")


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
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            # capture params via introspection
            sig = inspect.signature(f)
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            params = dict(bound.arguments)
            params.pop("self", None)

            # create child dataset
            parent_index = self.index
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
            new_dataset["created_at"] = datetime.now(UTC).isoformat()
            new_dataset["data_mode"] = "copied" if copy_data else "shared"
            new_dataset["fname"] = None
            new_dataset["ftype"] = None
            new_dataset["fsize"] = None
            self.index += 1
            # _insert_at keeps parent_index refs consistent across all datasets
            self._insert_at(self.index, new_dataset)

            # run the operation on the new (current) dataset
            if self.view is not None:
                with self.view._wait_cursor():
                    try:
                        result = f(self, *args, **kwargs)
                    except Exception:
                        # remove the child and undo the parent_index shifts
                        self.data.pop(self.index)
                        for ds in self.data:
                            pi = ds.get("parent_index")
                            if pi is not None and pi >= self.index:
                                ds["parent_index"] = pi - 1
                        self.index = parent_index
                        raise
                    self.view.data_changed()
            else:
                try:
                    result = f(self, *args, **kwargs)
                except Exception:
                    self.data.pop(self.index)
                    for ds in self.data:
                        pi = ds.get("parent_index")
                        if pi is not None and pi >= self.index:
                            ds["parent_index"] = pi - 1
                    self.index = parent_index
                    raise
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
        self.pipeline_run_report = []  # last pipeline apply status report

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

        # collect the target and all its descendants
        to_remove = sorted({index} | set(self._get_descendants(index)), reverse=True)

        for idx in to_remove:
            self.data.pop(idx)

        # update stored parent_index values in remaining datasets
        for ds in self.data:
            pi = ds.get("parent_index")
            if pi is not None:
                ds["parent_index"] = pi - sum(1 for r in to_remove if r < pi)

        if not self.data:
            self.index = -1
        else:
            new_pos = index - sum(1 for r in to_remove if r <= index)
            self.index = max(0, min(new_pos, len(self.data) - 1))

    @data_changed
    def duplicate_data(self):
        """Duplicate current data set as a child node in the pipeline tree."""
        parent_index = self.index
        new_dataset = deepcopy(self.current)
        new_dataset["parent_index"] = parent_index
        new_dataset["operation"] = "duplicate"
        new_dataset["operation_params"] = {}
        new_dataset["created_at"] = datetime.now(UTC).isoformat()
        new_dataset["data_mode"] = "copied"
        new_dataset["fname"] = None
        new_dataset["ftype"] = None
        new_dataset["fsize"] = None
        self.index += 1
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
                created_at=datetime.now(UTC).isoformat(),
                data_mode="root",
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

    @pipeline_step("import_bads")
    def import_bads(self, fname):
        """Import bad channels info from a CSV file."""
        fname = str(fname)
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

    @pipeline_step("import_events")
    def import_events(self, fname):
        """Import events from a CSV or FIF file."""
        fname = str(fname)
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

    @pipeline_step("import_annotations")
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
        existing = self.current["data"].annotations
        fs = self.current["data"].info["sfreq"]
        try:
            new = read_annotations_from_file(
                str(fname),
                fs,
                types=types,
                description=description,
                unit=unit,
                orig_time=existing.orig_time,
                max_time=self.current["data"].n_times / fs,
            )
        except ValueError as exc:
            raise InvalidAnnotationsError(str(exc)) from None
        self.current["data"].set_annotations(existing + new)

    @pipeline_step("import_ica", copy_data=False)
    def import_ica(self, fname):
        """Import ICA solution from file."""
        fname = str(fname)
        self.current["ica"] = mne.preprocessing.read_ica(fname)
        self.current["iclabel"] = None

    @pipeline_step("run_ica", copy_data=False)
    def run_ica(
        self,
        method,
        n_components=None,
        reject_by_annotation=True,
        fit_params=None,
        random_state=97,
        _fitted_ica=None,
    ):
        """Fit an ICA solution for the current dataset."""
        if _fitted_ica is None:
            ica = mne.preprocessing.ICA(
                method=method,
                n_components=n_components,
                fit_params=fit_params,
                random_state=random_state,
            )
            ica.fit(self.current["data"], reject_by_annotation=reject_by_annotation)
        else:
            ica = _fitted_ica
        self.current["ica"] = ica
        self.current["iclabel"] = None
        self.current["operation_params"].pop("_fitted_ica", None)

    @pipeline_step("set_ica_exclude", copy_data=False)
    def set_ica_exclude(self, exclude):
        """Set excluded ICA components."""
        self.current["ica"].exclude = sorted(int(component) for component in exclude)

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

        parent_index = self.current.get("parent_index")
        history_scope = "dataset" if parent_index is None else "branch"

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
            "_dataset_index": self.index,
            "_history_scope": history_scope,
            "_has_replayable_steps": self.has_replayable_pipeline(),
        }

    def get_dataset_details(self, idx=None):
        """Get provenance details for a dataset.

        Parameters
        ----------
        idx : int | None
            Dataset index. Defaults to `self.index`.

        Returns
        -------
        details : dict
            Dictionary with provenance information for a dataset.
        """
        if idx is None:
            idx = self.index
        dataset = self.data[idx]
        parent_index = dataset.get("parent_index")
        operation = dataset.get("operation")
        operation_params = dataset.get("operation_params") or {}

        lineage_depth = len(self.get_pipeline_steps(idx)) - 1
        created_text = self._format_created_at(dataset.get("created_at"))

        if parent_index is None:
            parent_name = "-"
            operation_label = "Root dataset"
            params_text = "-"
            generated_code = "-"
            data_mode_text = "Loaded from file"
        else:
            parent_name = self.data[parent_index]["name"]
            operation_label = (operation or "Unknown step").replace("_", " ").title()
            operation_label = operation_label.replace("Ica", "ICA")
            params_text = self._summarize_operation_params(operation_params)
            generated_code = self._step_to_history(operation, operation_params) or "-"
            if dataset.get("data_mode") == "shared":
                data_mode_text = "Shared with parent"
            else:
                data_mode_text = "Copied from parent"

        return {
            "Lineage depth": lineage_depth,
            "Created": created_text,
            "Data mode": data_mode_text,
            "Parent dataset": parent_name,
            "Derivation": operation_label,
            "Derivation parameters": params_text,
            "Generated code": generated_code,
            "_parent_dataset_index": parent_index,
            "_dataset_index": idx,
        }

    def _format_created_at(self, timestamp):
        """Format a dataset creation timestamp for display."""
        if not timestamp:
            return "-"
        try:
            dt = datetime.fromisoformat(timestamp)
        except ValueError:
            return str(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def _summarize_operation_params(self, params):
        """Summarize operation parameters for the info widget."""
        if not params:
            return "-"

        def summarize_value(value):
            if isinstance(value, np.ndarray):
                text = f"array{value.shape}"
            elif isinstance(value, (list, tuple)):
                if len(value) <= 4 and all(
                    not isinstance(item, (list, tuple, dict, np.ndarray))
                    for item in value
                ):
                    text = repr(list(value))
                else:
                    text = f"[{len(value)} items]"
            elif isinstance(value, dict):
                keys = list(value)
                preview = ", ".join(str(key) for key in keys[:4])
                if len(keys) > 4:
                    preview += ", ..."
                text = "{" + preview + "}"
            elif isinstance(value, str) and ("/" in value or "\\" in value):
                text = Path(value).name
            else:
                text = repr(value)
            if len(text) > 48:
                return text[:45] + "..."
            return text

        parts = [
            f"{key}={summarize_value(value)}"
            for key, value in params.items()
            if not key.startswith("_") and value is not None
        ]
        return ", ".join(parts) if parts else "-"

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

    @pipeline_step("set_montage", copy_data=False)
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
        parent_idx = self.current["parent_index"]
        adjusted_idx = [idx + 1 if idx > parent_idx else idx for idx in selected_idx]
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

    @pipeline_step("set_events")
    def set_events(self, events):
        self.current["events"] = np.asarray(events, dtype=int)
        if self.current["dtype"] == "epochs":
            self.current["data"].events = self.current["events"]

    @pipeline_step("set_annotations")
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
        if not 0 <= source < len(self.data):
            raise IndexError(f"source index out of range: {source}")
        if not self.data:
            return

        target = max(0, min(target, len(self.data) - 1))
        order = list(range(len(self.data)))
        moved_old_index = order.pop(source)
        order.insert(target, moved_old_index)
        new_index_for_old = {old: new for new, old in enumerate(order)}

        self.data = [self.data[old] for old in order]
        for dataset in self.data:
            parent_index = dataset.get("parent_index")
            if parent_index is not None:
                dataset["parent_index"] = new_index_for_old[parent_index]

        self.index = new_index_for_old[moved_old_index]

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

    def get_unreplayable_pipeline_steps(self, idx=None):
        """Return branch steps that cannot be replayed automatically."""
        return [
            step
            for step in self.get_pipeline_steps(idx)[1:]
            if step["operation"] in self._UNREPLAYABLE_OPS
        ]

    def has_replayable_pipeline(self, idx=None):
        """Return whether dataset[idx] has a non-empty replayable branch."""
        steps = self.get_pipeline_steps(idx)[1:]
        return bool(steps) and not self.get_unreplayable_pipeline_steps(idx)

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
            "from mnelab.io import read_raw",
            "from mnelab.utils import (",
            "    annotations_between_events,",
            "    read_annotations_from_file,",
            "    run_iclabel,",
            ")",
            "import numpy as np",
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
        elif operation == "import_ica":
            fname = p.get("fname")
            if fname is not None:
                fname = str(fname)
            return f"ica = mne.preprocessing.read_ica({fname!r})"
        elif operation == "run_ica":
            kwargs = [f"method={p.get('method')!r}"]
            if p.get("n_components") is not None:
                kwargs.append(f"n_components={p.get('n_components')!r}")
            if p.get("fit_params"):
                kwargs.append(f"fit_params={p.get('fit_params')!r}")
            if p.get("random_state") is not None:
                kwargs.append(f"random_state={p.get('random_state')!r}")
            lines = [f"ica = mne.preprocessing.ICA({', '.join(kwargs)})"]
            if p.get("reject_by_annotation", True):
                lines.append("ica.fit(data, reject_by_annotation=True)")
            else:
                lines.append("ica.fit(data, reject_by_annotation=False)")
            return "\n".join(lines)
        elif operation == "set_ica_exclude":
            return f"ica.exclude = {p.get('exclude', [])!r}"
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
        elif operation == "import_bads":
            fname = p.get("fname")
            if fname is not None:
                fname = str(fname)
            return (
                f"with open({fname!r}) as f:\n"
                "    data.info['bads'] = f.read().replace(' ', '').strip().split(',')"
            )
        elif operation == "import_events":
            fname = p.get("fname")
            if fname is not None:
                fname = str(fname)
            if isinstance(fname, str) and fname.lower().endswith(".csv"):
                return (
                    "new_events = np.loadtxt("
                    f"{fname!r}, delimiter=',', skiprows=1, dtype=int"
                    ")\n"
                    "new_events = np.atleast_2d(new_events)\n"
                    "new_events = np.column_stack((\n"
                    "    new_events[:, 0],\n"
                    "    np.zeros(len(new_events), dtype=int),\n"
                    "    new_events[:, 1],\n"
                    "))\n"
                    "if 'events' in locals() and len(events) > 0:\n"
                    "    events = np.unique(np.vstack((events, new_events)), axis=0)\n"
                    "else:\n"
                    "    events = new_events"
                )
            return f"events = mne.read_events({fname!r})"
        elif operation == "import_annotations":
            fname = p.get("fname")
            if fname is not None:
                fname = str(fname)
            return "\n".join(
                [
                    "new_annots = read_annotations_from_file(",
                    f"    {fname!r},",
                    "    data.info['sfreq'],",
                    f"    types={p.get('types')!r},",
                    f"    description={p.get('description')!r},",
                    f"    unit={p.get('unit', 'seconds')!r},",
                    "    orig_time=data.annotations.orig_time,",
                    "    max_time=data.n_times / data.info['sfreq'],",
                    ")",
                    "data.set_annotations(data.annotations + new_annots)",
                ]
            )
        elif operation == "events_from_annotations":
            return "events, _ = mne.events_from_annotations(data)"
        elif operation == "annotations_from_events":
            return (
                "annots = mne.annotations_from_events(events, data.info['sfreq'])\n"
                "data.set_annotations(data.annotations + annots)"
            )
        elif operation == "set_events":
            return f"events = np.asarray({p.get('events')!r}, dtype=int)"
        elif operation == "set_annotations":
            return (
                "data.set_annotations(mne.Annotations("
                f"{p.get('onset')!r}, {p.get('duration')!r}, {p.get('description')!r}"
                "))"
            )
        elif operation == "append_data":
            return "# append_data: source datasets depend on session context"
        elif operation == "duplicate":
            return "data = deepcopy(data)"
        return None

    def _dataset_stem(self, dataset):
        """Return the file-derived dataset stem for placeholder expansion."""
        fname = dataset.get("fname") if dataset else None
        if fname:
            stem, _ = split_name_ext(fname)
            return stem
        return dataset.get("name") if dataset else ""

    def _root_dataset(self, idx=None):
        """Return the root ancestor dataset for `idx`."""
        if idx is None:
            idx = self.index
        if idx < 0 or idx >= len(self.data):
            return None
        while self.data[idx].get("parent_index") is not None:
            idx = self.data[idx]["parent_index"]
        return self.data[idx]

    def _dataset_prefix(self, dataset_stem):
        """Return a shorter prefix for dataset sidecar files."""
        if not dataset_stem:
            return ""
        return dataset_stem.split("_", 1)[0].split(" ", 1)[0]

    def _serialize_import_fname(self, fname, root_dataset):
        """Return a dataset-relative template for import sidecar files."""
        if root_dataset is None or fname is None:
            return str(fname) if fname is not None else None

        path = Path(fname)
        filename = path.name
        root_stem = self._dataset_stem(root_dataset)
        root_prefix = self._dataset_prefix(root_stem)

        if root_stem and filename.startswith(root_stem):
            filename = "{dataset}" + filename[len(root_stem) :]
        elif (
            root_prefix
            and root_prefix != root_stem
            and filename.startswith(root_prefix)
        ):
            filename = "{dataset_prefix}" + filename[len(root_prefix) :]
        else:
            return str(fname)

        parent = path.parent
        root_fname = root_dataset.get("fname")
        if root_fname and parent == Path(root_fname).parent:
            parent_text = "{dataset_dir}"
        elif str(parent) in ("", "."):
            parent_text = ""
        else:
            parent_text = parent.as_posix()

        if parent_text:
            return f"{parent_text}/{filename}"
        return filename

    def _resolve_import_fname(self, fname):
        """Resolve a dataset-relative import filename template."""
        if not isinstance(fname, str):
            return fname
        if not any(
            token in fname
            for token in ("{dataset}", "{dataset_prefix}", "{dataset_dir}")
        ):
            return fname

        root_dataset = self._root_dataset()
        dataset_stem = self._dataset_stem(root_dataset)
        dataset_dir = "."
        if root_dataset is not None and root_dataset.get("fname"):
            dataset_dir = Path(root_dataset["fname"]).parent.as_posix()
        return (
            fname.replace("{dataset_dir}", dataset_dir)
            .replace("{dataset_prefix}", self._dataset_prefix(dataset_stem))
            .replace("{dataset}", dataset_stem)
        )

    def _serialize_params(self, operation, params, root_dataset=None):
        """Convert operation params to a JSON-serializable dict."""
        result = {}
        for k, v in (params or {}).items():
            if k.startswith("_"):
                continue  # skip internal keys (e.g. _mapping)
            if v is None:
                result[k] = None
            elif operation in PARAMETERIZED_IMPORT_OPS and k == "fname":
                result[k] = self._serialize_import_fname(v, root_dataset)
            elif isinstance(v, Montage):
                result[k] = {
                    "__type__": "Montage",
                    "name": v.name,
                    "path": str(v.path) if v.path else None,
                }
            elif isinstance(v, Path):
                result[k] = str(v)
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
            if operation in PARAMETERIZED_IMPORT_OPS and k == "fname":
                result[k] = self._resolve_import_fname(v)
            elif isinstance(v, dict) and v.get("__type__") == "Montage":
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
        pipeline = self.get_pipeline(idx)
        if pipeline is None or not pipeline.get("steps"):
            return

        unreplayable = self.get_unreplayable_pipeline_steps(idx)
        if unreplayable:
            operations = ", ".join(repr(step["operation"]) for step in unreplayable)
            raise ValueError(
                "Pipeline contains operations that cannot be replayed "
                f"automatically: {operations}."
            )

        with open(path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, indent=2)

    def get_pipeline(self, idx=None):
        """Return the pipeline from the root ancestor to dataset[idx].

        Parameters
        ----------
        idx : int or None
            Dataset index. Defaults to `self.index`.

        Returns
        -------
        pipeline : dict | None
            Pipeline dictionary in .mnepipe format.
        """
        if idx is None:
            idx = self.index

        steps = self.get_pipeline_steps(idx)
        if not steps:
            return None

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
                    "params": self._serialize_params(
                        operation,
                        step["params"],
                        root_ds,
                    ),
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
        return pipeline

    # operations that cannot be applied generically to a new dataset
    _UNREPLAYABLE_OPS = UNREPLAYABLE_PIPELINE_OPS

    def apply_pipeline(
        self,
        pipeline_dict,
        progress_callback=None,
        is_cancelled=None,
        review_callback=None,
    ):
        """Apply a saved pipeline to the current dataset.

        Parameters
        ----------
        pipeline_dict : dict
            The loaded pipeline dictionary from a .mnepipe file.
        progress_callback : callable | None
            Optional callback called after each completed step with
            `(step_index, step_dict)`.
        is_cancelled : callable | None
            Optional callback returning `True` if the apply process should stop.
        review_callback : callable | None
            Optional callback called for `prompt` and `review` execution modes with
            `(step_index, step_dict, execution_mode)`. Return `True` to continue.

        Raises
        ------
        ValueError
            If any step uses a non-replayable operation.
        PipelineCancelledError
            If the apply process is cancelled before the next step starts.
        """
        steps = pipeline_dict.get("steps", [])
        self.pipeline_run_report = []
        for step_index, step in enumerate(steps, start=1):
            if is_cancelled is not None and is_cancelled():
                raise PipelineCancelledError()
            operation = step["operation"]
            execution_mode = step.get("execution_mode", "automatic")
            report_entry = {
                "step": step_index,
                "operation": operation,
                "execution_mode": execution_mode,
                "status": "running",
            }
            if operation in self._UNREPLAYABLE_OPS:
                report_entry["status"] = "failed"
                report_entry["message"] = "Operation cannot be replayed automatically."
                self.pipeline_run_report.append(report_entry)
                raise ValueError(
                    f"Operation {operation!r} cannot be replayed automatically "
                    "because it requires referencing other session datasets."
                )
            if execution_mode not in PIPELINE_EXECUTION_MODES:
                report_entry["status"] = "failed"
                report_entry["message"] = "Unknown execution mode."
                self.pipeline_run_report.append(report_entry)
                raise ValueError(f"Unknown pipeline execution mode: {execution_mode!r}")
            if execution_mode == "skip":
                report_entry["status"] = "skipped"
                self.pipeline_run_report.append(report_entry)
                if progress_callback is not None:
                    progress_callback(step_index, step)
                continue
            if execution_mode in {"prompt", "review"}:
                if review_callback is None:
                    report_entry["status"] = "needs_review"
                    report_entry["message"] = "Review callback required."
                    self.pipeline_run_report.append(report_entry)
                    raise ValueError(
                        f"Pipeline step {step_index} requires a "
                        f"{execution_mode!r} checkpoint."
                    )
                if not review_callback(step_index, step, execution_mode):
                    report_entry["status"] = "cancelled"
                    self.pipeline_run_report.append(report_entry)
                    raise PipelineCancelledError()
            params = self._deserialize_params(operation, step.get("params", {}))
            method = getattr(self, operation, None)
            if method is None:
                report_entry["status"] = "failed"
                report_entry["message"] = "Unknown operation."
                self.pipeline_run_report.append(report_entry)
                raise ValueError(f"Unknown pipeline operation: {operation!r}")
            try:
                method(**params)
            except Exception as exc:
                report_entry["status"] = "failed"
                report_entry["message"] = str(exc)
                self.pipeline_run_report.append(report_entry)
                raise
            report_entry["status"] = "complete"
            self.pipeline_run_report.append(report_entry)
            if progress_callback is not None:
                progress_callback(step_index, step)
