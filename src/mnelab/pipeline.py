# © MNELAB developers
#
# License: BSD (3-clause)

"""Small, JSON-serializable processing pipelines."""

import json
import math
from functools import wraps
from inspect import signature
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
}

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
}

RAW_ONLY = {
    "crop",
    "remove_line_noise",
    "find_events",
    "events_from_annotations",
    "annotations_from_events",
    "epoch_data",
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


def serialize_montage(arguments):
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
            if unsupported:
                self.mark_pipeline_unsupported(method.__name__)
                return result
            bound = method_signature.bind(self, *args, **kwargs)
            bound.apply_defaults()
            try:
                params = (
                    serialize(bound.arguments)
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
    label = OPERATIONS.get(op, op.replace("_", " ").title())
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
    details = ", ".join(f"{key}={value!r}" for key, value in params.items())
    return f"{label}: {details}" if details else label


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
