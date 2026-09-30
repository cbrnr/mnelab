# © MNELAB developers
#
# License: BSD (3-clause)

"""Small, JSON-serializable processing pipelines."""

import json
import math
from functools import wraps
from inspect import signature
from os.path import commonprefix
from pathlib import Path

import mne
import numpy as np

OPERATIONS = {
    "filter": "Filter Data",
    "remove_line_noise": "Remove Line Noise",
    "resample": "Resample Data",
    "crop": "Crop Data",
    "pick_channels": "Pick Channels",
    "set_channel_properties": "Channel Properties",
    "change_reference": "Change Reference",
    "interpolate_bads": "Interpolate Bad Channels",
    "find_events": "Find Events",
    "events_from_annotations": "Events From Annotations",
    "annotations_from_events": "Annotations From Events",
    "epoch_data": "Create Epochs",
    "drop_bad_epochs": "Drop Bad Epochs",
    "set_montage": "Set Montage",
    "import_bads": "Import Bad Channels",
    "import_events": "Import Events",
    "import_annotations": "Import Annotations",
    "import_ica": "Import ICA",
    "apply_ica": "Apply ICA",
}

FILE_IMPORTS = frozenset(
    {"import_bads", "import_events", "import_annotations", "import_ica"}
)

PARAMETERS = {
    "filter": {"lower", "upper", "notch"},
    "remove_line_noise": {"line_freq", "include_harmonics"},
    "resample": {"sfreq"},
    "crop": {"start", "stop"},
    "pick_channels": {"picks"},
    "set_channel_properties": {"bads", "names", "types"},
    "change_reference": {"add", "ref"},
    "interpolate_bads": set(),
    "find_events": {
        "stim_channel",
        "consecutive",
        "initial_event",
        "mask",
        "min_duration",
        "shortest_event",
    },
    "events_from_annotations": set(),
    "annotations_from_events": set(),
    "epoch_data": {"event_id", "tmin", "tmax", "baseline"},
    "drop_bad_epochs": {"reject", "flat"},
    "set_montage": {
        "montage_name",
        "montage_positions",
        "match_case",
        "match_alias",
        "on_missing",
    },
    "import_bads": {"file"},
    "import_events": {"file"},
    "import_annotations": {"file", "types", "description", "unit"},
    "import_ica": {"file"},
    "apply_ica": set(),
}

RAW_ONLY = {
    "crop",
    "remove_line_noise",
    "find_events",
    "events_from_annotations",
    "annotations_from_events",
    "epoch_data",
    "import_events",
    "import_annotations",
}
EPOCHS_ONLY = {"drop_bad_epochs"}


def _json_safe(value):
    """Convert ordinary model arguments into JSON-compatible values."""
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _json_safe(item) for key, item in value.items()}
    raise TypeError(f"Cannot record pipeline parameter {value!r}.")


def make_file_spec(fname, source_fname=None):
    """Suggest a matching file rule when names share a dataset identifier."""
    path = Path(fname).expanduser().resolve()
    if source_fname is not None:
        source = Path(source_fname).expanduser().resolve()
        if path.parent == source.parent:
            identifier = commonprefix((source.name, path.name)).rstrip("-_.")
            source_rest = source.name[len(identifier) :]
            file_rest = path.name[len(identifier) :]
            boundaries = ("", "-", "_", ".")
            if (
                identifier
                and source_rest[:1] in boundaries
                and file_rest[:1] in boundaries
            ):
                return {
                    "mode": "matching",
                    "data_pattern": f"{{id}}{source_rest}",
                    "file_pattern": f"{{id}}{file_rest}",
                }
    return {"mode": "fixed", "path": str(path)}


def serialize_import(arguments, result):
    """Record a matching rule or the contents of a fixed input file."""
    model = arguments["self"]
    source_fname = model.current.get("source_fname") or model.current.get("fname")
    file_spec = make_file_spec(arguments["fname"], source_fname)
    if file_spec["mode"] == "fixed" and result is not None:
        file_spec = {"mode": "embedded", "data": _json_safe(result)}
    params = {"file": file_spec}
    params.update(
        (key, _json_safe(value))
        for key, value in arguments.items()
        if key not in {"self", "fname"}
    )
    return params


def validate_file_spec(spec):
    """Validate an embedded input or an external file rule."""
    if not isinstance(spec, dict):
        raise TypeError("File rule must be an object.")
    if spec.get("mode") == "fixed":
        if set(spec) != {"mode", "path"} or not isinstance(spec["path"], str):
            raise ValueError("Invalid fixed file rule.")
        if not Path(spec["path"]).is_absolute():
            raise ValueError("Fixed file paths must be absolute.")
    elif spec.get("mode") == "embedded":
        if set(spec) != {"mode", "data"}:
            raise ValueError("Invalid embedded file contents.")
        _json_safe(spec["data"])
    elif spec.get("mode") == "matching":
        if set(spec) != {"mode", "data_pattern", "file_pattern"}:
            raise ValueError("Invalid matching file rule.")
        for key in ("data_pattern", "file_pattern"):
            pattern = spec[key]
            if not isinstance(pattern, str) or pattern.count("{id}") != 1:
                raise ValueError(f"{key} must contain one {{id}} placeholder.")
            if "{" in pattern.replace("{id}", "") or "}" in pattern.replace("{id}", ""):
                raise ValueError(f"Unknown placeholder in {key}.")
        if Path(spec["data_pattern"]).name != spec["data_pattern"]:
            raise ValueError("Dataset pattern must be a filename.")
        if Path(spec["file_pattern"]).is_absolute():
            raise ValueError("Matching file pattern must be relative.")
    else:
        raise ValueError("Unknown file rule mode.")


def resolve_file_spec(spec, source_fname, *, check_exists=True):
    """Resolve a file rule against the original file of the target dataset."""
    validate_file_spec(spec)
    if spec["mode"] == "embedded":
        raise ValueError("Embedded contents do not have a file path.")
    if spec["mode"] == "fixed":
        path = Path(spec["path"])
    else:
        if source_fname is None:
            raise ValueError("Target dataset has no source filename for file matching.")
        source = Path(source_fname)
        prefix, suffix = spec["data_pattern"].split("{id}")
        name = source.name
        if not name.startswith(prefix) or not name.endswith(suffix):
            raise ValueError(f"Target filename {name!r} does not match the file rule.")
        identifier = name[len(prefix) : len(name) - len(suffix) if suffix else None]
        if not identifier:
            raise ValueError("Target filename has no dataset identifier.")
        relative = spec["file_pattern"].replace("{id}", identifier)
        path = source.parent / relative
    path = path.expanduser().resolve()
    if check_exists and not path.is_file():
        raise ValueError(f"Matching file not found: {path}")
    return path


def serialize_montage(arguments, _result=None):
    """Record a built-in name, custom positions, or a target montage reference."""
    montage = arguments["montage"]
    if montage is None:
        positions = None
    elif montage.embedded:
        positions = "embedded"
    elif montage.path is None and montage.name in mne.channels.get_builtin_montages():
        positions = None
    else:
        positions = _json_safe(montage.montage.get_positions())
    return {
        "montage_name": montage.name if montage is not None else None,
        "montage_positions": positions,
        "match_case": arguments["match_case"],
        "match_alias": arguments["match_alias"],
        "on_missing": arguments["on_missing"],
    }


def pipeline_step(_method=None, *, unsupported=False, serialize=None):
    """Record a successful model operation on the current dataset."""

    def decorate(method):
        method_signature = signature(method)

        @wraps(method)
        def wrapper(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            if self._replaying_pipeline:
                return result
            if unsupported:
                self.mark_pipeline_unsupported(method.__name__)
                return result
            bound = method_signature.bind(self, *args, **kwargs)
            bound.apply_defaults()
            try:
                params = (
                    serialize(bound.arguments, result)
                    if serialize is not None
                    else {
                        key: _json_safe(value)
                        for key, value in bound.arguments.items()
                        if key != "self"
                    }
                )
                if params is None:
                    self.mark_pipeline_unsupported(method.__name__)
                    return result
                step = {"op": method.__name__, "params": params}
                validate_step(step)
            except (TypeError, ValueError):
                self.mark_pipeline_unsupported(method.__name__)
            else:
                self.current.setdefault("pipeline_steps", []).append(step)
            return result

        return wrapper

    return decorate(_method) if _method is not None else decorate


def has_unsupported(steps):
    """Return whether a pipeline contains an operation that cannot be replayed."""
    return any(step.get("unsupported") for step in steps)


def step_label(step):
    """Return a readable one-line description of a pipeline step."""
    op = step["op"]
    label = OPERATIONS.get(op, op.replace("_", " ").title().replace("Ica", "ICA"))
    if step.get("unsupported"):
        return f"{label} (cannot replay)"
    params = step["params"]
    if op == "filter":
        if params["notch"] is not None:
            return f"Notch filter: {params['notch']:g} Hz"
        if params["lower"] is not None and params["upper"] is not None:
            return f"Bandpass filter: {params['lower']:g}–{params['upper']:g} Hz"
        if params["lower"] is not None:
            return f"Highpass filter: {params['lower']:g} Hz"
        return f"Lowpass filter: {params['upper']:g} Hz"
    if op == "remove_line_noise":
        label = f"Remove line noise: {params['line_freq']:g} Hz"
        return label + (" and harmonics" if params["include_harmonics"] else "")
    if op == "resample":
        return f"Resample to {params['sfreq']:g} Hz"
    if op == "crop":
        start = "beginning" if params["start"] is None else f"{params['start']:g} s"
        stop = "end" if params["stop"] is None else f"{params['stop']:g} s"
        return f"Crop: {start} to {stop}"
    if op == "set_montage":
        if params["montage_name"] is None:
            return "Clear Montage"
        if (
            isinstance(params["montage_positions"], dict)
            and "file" in params["montage_positions"]
        ):
            file_spec = params["montage_positions"]["file"]
            return f"Set Montage from {file_spec_label(file_spec)}"
        label = (
            "Use Target's Embedded Montage"
            if params["montage_positions"] == "embedded"
            else f"Set Montage: {params['montage_name']}"
        )
        options = []
        if params["match_case"]:
            options.append("case-sensitive")
        if params["match_alias"]:
            options.append("match aliases")
        if params["on_missing"] != "raise":
            options.append(f"{params['on_missing']} missing")
        return label + (f" ({', '.join(options)})" if options else "")
    if op in FILE_IMPORTS:
        label = f"{label} from {file_spec_label(params['file'])}"
        if op == "import_annotations":
            options = []
            if params["types"] is not None:
                options.append(f"types={params['types']!r}")
            if params["description"] is not None:
                options.append(f"description={params['description']!r}")
            if params["unit"] == "samples":
                options.append("samples")
            if options:
                label += f" ({', '.join(options)})"
        return label
    details = ", ".join(f"{key}={value!r}" for key, value in params.items())
    return f"{label}: {details}" if details else label


def file_spec_label(spec):
    """Return a short description of a file rule."""
    if spec["mode"] == "embedded":
        return "embedded contents"
    return spec["file_pattern"] if spec["mode"] == "matching" else spec["path"]


def validate_step(step):
    """Validate one step and return its operation name."""
    if not isinstance(step, dict):
        raise TypeError("Each pipeline step needs an operation and parameters.")
    if step.get("unsupported") is True and set(step) == {"op", "unsupported"}:
        if not isinstance(step["op"], str) or not step["op"]:
            raise ValueError("Invalid pipeline operation name.")
        return step["op"]
    if set(step) != {"op", "params"}:
        raise ValueError("Each pipeline step needs an operation and parameters.")
    op = step["op"]
    if not isinstance(op, str) or op not in OPERATIONS:
        raise ValueError(f"Unknown pipeline operation: {op!r}.")
    params = step["params"]
    if not isinstance(params, dict) or set(params) != PARAMETERS[op]:
        raise ValueError(f"Invalid parameters for {OPERATIONS[op]}.")
    _json_safe(params)
    if "file" in params:
        validate_file_spec(params["file"])
        mode = params["file"]["mode"]
        if op == "import_ica" and mode == "embedded":
            raise ValueError("ICA solutions must be loaded from a file.")
        if op != "import_ica" and mode == "fixed":
            raise ValueError("Fixed imports must embed their contents.")
        if mode == "embedded":
            data = params["file"]["data"]
            if op == "import_bads" and (
                not isinstance(data, list)
                or not data
                or not all(isinstance(name, str) for name in data)
            ):
                raise ValueError("Invalid embedded bad channels.")
            if op == "import_events" and (
                not isinstance(data, dict)
                or set(data) != {"events", "merge"}
                or not isinstance(data["merge"], bool)
                or not isinstance(data["events"], list)
                or not all(
                    isinstance(row, list)
                    and len(row) == 3
                    and all(type(value) is int for value in row)
                    for row in data["events"]
                )
            ):
                raise ValueError("Invalid embedded events.")
            if op == "import_annotations" and (
                not isinstance(data, list)
                or not all(
                    isinstance(row, list)
                    and len(row) == 3
                    and isinstance(row[0], str)
                    and all(
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                        for value in row[1:]
                    )
                    for row in data
                )
            ):
                raise ValueError("Invalid embedded annotations.")
    if op == "import_annotations":
        if params["types"] is not None and (
            not isinstance(params["types"], list)
            or not all(isinstance(item, str) for item in params["types"])
        ):
            raise ValueError("Annotation types must be a list of names or null.")
        if params["description"] is not None and not isinstance(
            params["description"], str
        ):
            raise ValueError("Annotation description must be text or null.")
        if params["unit"] not in {"seconds", "samples"}:
            raise ValueError("Annotation unit must be seconds or samples.")
    for key, value in params.items():
        if key == "include_harmonics":
            if not isinstance(value, bool):
                raise ValueError("Include harmonics must be true or false.")
        elif (
            op in {"filter", "remove_line_noise", "resample", "crop"}
            and value is not None
            and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            )
        ):
            raise ValueError(f"{key} must be a finite number or null.")

    if op == "filter":
        lower, upper, notch = (
            params["lower"],
            params["upper"],
            params["notch"],
        )
        if notch is not None:
            valid = notch > 0 and lower is None and upper is None
        else:
            valid = (
                (lower is not None or upper is not None)
                and (lower is None or lower > 0)
                and (upper is None or upper > 0)
                and (lower is None or upper is None or lower < upper)
            )
        if not valid:
            raise ValueError("Invalid filter frequencies.")
    elif op == "remove_line_noise" and (
        params["line_freq"] is None or params["line_freq"] <= 0
    ):
        raise ValueError("Line frequency must be positive.")
    elif op == "resample" and (params["sfreq"] is None or params["sfreq"] <= 0):
        raise ValueError("Sampling frequency must be positive.")
    elif op == "crop":
        start, stop = params["start"], params["stop"]
        if (start is None and stop is None) or any(
            value is not None and value < 0 for value in (start, stop)
        ):
            raise ValueError("Crop needs a non-negative start or stop time.")
        if start is not None and stop is not None and start >= stop:
            raise ValueError("Crop stop time must be after start time.")
    elif op == "set_montage":
        name, positions = params["montage_name"], params["montage_positions"]
        if name is None:
            if positions is not None:
                raise ValueError("Montage positions need a name.")
        elif not isinstance(name, str) or not name:
            raise ValueError("Montage name must be a non-empty string.")
        elif positions is None and name not in mne.channels.get_builtin_montages():
            raise ValueError(f"Unknown built-in montage: {name!r}.")
        if (
            positions is not None
            and positions != "embedded"
            and not isinstance(positions, dict)
        ):
            raise ValueError("Invalid montage positions or source.")
        if isinstance(positions, dict) and "file" in positions:
            if set(positions) != {"file"}:
                raise ValueError("Invalid montage file rule.")
            validate_file_spec(positions["file"])
            if positions["file"]["mode"] != "matching":
                raise ValueError("Montage file rules must match the target dataset.")
        if not isinstance(params["match_case"], bool) or not isinstance(
            params["match_alias"], bool
        ):
            raise ValueError("Montage matching options must be true or false.")
        if not isinstance(params["on_missing"], str) or params["on_missing"] not in {
            "raise",
            "warn",
            "ignore",
        }:
            raise ValueError("Invalid missing-channel option for montage.")
    return op


def validate_for_data(step, data, dtype):
    """Check a step against the data it will actually process."""
    op = validate_step(step)
    if step.get("unsupported"):
        raise ValueError(f"{step_label(step)} cannot be replayed.")
    params = step["params"]
    if op in RAW_ONLY and dtype != "raw":
        raise ValueError(f"{OPERATIONS[op]} requires raw data.")
    if op in EPOCHS_ONLY and dtype != "epochs":
        raise ValueError(f"{OPERATIONS[op]} requires epochs data.")
    if dtype not in {"raw", "epochs"}:
        raise ValueError("Pipelines require raw or epochs data.")
    nyquist = data.info["sfreq"] / 2
    if op == "filter":
        frequencies = [params[key] for key in ("lower", "upper", "notch")]
        if any(freq is not None and freq >= nyquist for freq in frequencies):
            raise ValueError("Filter frequency must be below the Nyquist frequency.")
    elif op == "remove_line_noise" and params["line_freq"] >= nyquist:
        raise ValueError("Line frequency must be below the Nyquist frequency.")
    elif op == "crop":
        duration = data.times[-1]
        if params["start"] is not None and params["start"] >= duration:
            raise ValueError("Crop start time exceeds the data duration.")
        if params["stop"] is not None and params["stop"] > duration:
            raise ValueError("Crop stop time exceeds the data duration.")
    return op


def load_pipeline(path):
    """Load and validate pipeline steps from a JSON file."""
    with open(path, encoding="utf-8") as file:
        document = json.load(file)
    if not isinstance(document, dict) or set(document) != {"version", "steps"}:
        raise ValueError("Invalid pipeline file.")
    if type(document["version"]) is not int or document["version"] != 1:
        raise ValueError("Unsupported pipeline file version.")
    steps = document["steps"]
    if not isinstance(steps, list):
        raise TypeError("Pipeline steps must be a list.")
    for step in steps:
        validate_step(step)
    return steps


def save_pipeline(path, steps):
    """Save pipeline steps to a JSON file."""
    for step in steps:
        validate_step(step)
    if has_unsupported(steps):
        raise ValueError("Remove operations that cannot be replayed before saving.")
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump({"version": 1, "steps": steps}, file, indent=2)
        file.write("\n")
