# © MNELAB developers
#
# License: BSD (3-clause)

"""Structured, replayable processing pipelines.

A pipeline is a list of steps. A step is either a supported operation

    {"op": "filter", "params": {"lower": 1.0, "upper": 40.0, "notch": None}}

or a sentinel marking a non-reproducible operation (ICA, append, montage, ...)

    {"op": "apply_ica", "unsupported": True}

Steps are recorded onto datasets as they are processed (see `Model.records_step`) and
can be applied to another dataset via `Model.apply_pipeline`. Because steps are plain
JSON-serializable dicts, pipelines can be saved to and loaded from disk.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from mnelab.utils import count_locations

PIPELINE_SCHEMA = 1


@dataclass(frozen=True)
class Op:
    """A supported pipeline operation."""

    key: str
    label: str  # human-readable label shown in the UI
    method: str  # name of the `Model` method to call on replay
    check: Callable  # (ctx, params) -> error message or None; mutates ctx in place
    params: tuple = ()  # parameter names (for display), in call order
    deserialize: Callable = field(default=lambda p: p)  # JSON params -> method kwargs
    mutates: bool = True  # whether this operation changes the underlying signal data


def make_context(dataset):
    """Build a lightweight state used to validate a pipeline against a dataset.

    The context simulates how each operation changes the data (channels, dtype, ...)
    so that chained operations can be validated without touching the real data.
    """
    info = dataset["data"].info
    return {
        "dtype": dataset["dtype"],
        "ch_names": set(info["ch_names"]),
        "ch_types": set(dataset["data"].get_channel_types()),
        "nchan": info["nchan"],
        "has_events": len(dataset["events"]) > 0,
        "has_locations": bool(count_locations(info)),
        "has_bads": bool(info["bads"]),
    }


def _missing(names, available):
    return sorted(set(names) - set(available))


# --- compatibility checks (each returns an error message or None, mutating ctx) ------


def _check_raw_or_epochs(ctx, params):
    if ctx["dtype"] not in ("raw", "epochs"):
        return f"requires raw or epochs data (current: {ctx['dtype']})"


def _check_raw(ctx, params):
    if ctx["dtype"] != "raw":
        return f"requires raw data (current: {ctx['dtype']})"


def _check_epochs(ctx, params):
    if ctx["dtype"] != "epochs":
        return f"requires epochs data (current: {ctx['dtype']})"


def _check_pick(ctx, params):
    picks = params["picks"]
    if set(picks) <= ctx["ch_types"]:  # picking by channel type
        return  # cannot statically know remaining channels, leave ch_names unchanged
    missing = _missing(picks, ctx["ch_names"])
    if missing:
        return f"unknown channels or types: {', '.join(missing)}"
    ctx["ch_names"] = set(picks)


def _check_channel_properties(ctx, params):
    bads, names, types = params["bads"], params["names"], params["types"]
    if bads:
        missing = _missing(bads, ctx["ch_names"])
        if missing:
            return f"unknown bad channels: {', '.join(missing)}"
        ctx["has_bads"] = True
    else:
        ctx["has_bads"] = False
    if names:
        missing = _missing(names.keys(), ctx["ch_names"])
        if missing:
            return f"cannot rename unknown channels: {', '.join(missing)}"
        ctx["ch_names"] = (ctx["ch_names"] - set(names.keys())) | set(names.values())
    if types:
        missing = _missing(types.keys(), ctx["ch_names"])
        if missing:
            return f"cannot set type of unknown channels: {', '.join(missing)}"
        ctx["ch_types"] |= set(types.values())


def _check_rename(ctx, params):
    new_names = params["new_names"]
    if len(new_names) != ctx["nchan"]:
        return f"expects {ctx['nchan']} channel names but pipeline has {len(new_names)}"
    ctx["ch_names"] = set(new_names)


def _check_reference(ctx, params):
    add, ref = params["add"], params["ref"]
    if add:
        clash = sorted(set(add) & ctx["ch_names"])
        if clash:
            return f"reference channels already exist: {', '.join(clash)}"
        ctx["ch_names"] |= set(add)
        ctx["nchan"] += len(add)
    if isinstance(ref, list):
        missing = _missing(ref, ctx["ch_names"])
        if missing:
            return f"unknown reference channels: {', '.join(missing)}"


def _check_interpolate(ctx, params):
    if not ctx["has_bads"]:
        return "no bad channels to interpolate"
    if not ctx["has_locations"]:
        return "channel locations required (set a montage first)"


def _check_epoch(ctx, params):
    if ctx["dtype"] != "raw":
        return f"requires raw data (current: {ctx['dtype']})"
    if not ctx["has_events"]:
        return "no events available to create epochs"
    ctx["dtype"] = "epochs"


def _check_find_events(ctx, params):
    if ctx["dtype"] != "raw":
        return f"requires raw data (current: {ctx['dtype']})"
    stim_channel = params["stim_channel"]
    if stim_channel not in ctx["ch_names"]:
        return f"unknown stim channel: {stim_channel}"
    ctx["has_events"] = True


def _deserialize_epoch(params):
    baseline = params["baseline"]
    return {**params, "baseline": tuple(baseline) if baseline is not None else None}


REGISTRY = {op.key: op for op in [
    Op("filter", "Filter", "filter", _check_raw_or_epochs,
       ("lower", "upper", "notch")),
    Op("resample", "Resample", "resample", _check_raw_or_epochs, ("sfreq",)),
    Op("crop", "Crop", "crop", _check_raw, ("start", "stop")),
    Op("pick_channels", "Pick Channels", "pick_channels", _check_pick, ("picks",)),
    Op("set_channel_properties", "Channel Properties", "set_channel_properties",
       _check_channel_properties, ("bads", "names", "types"), mutates=False),
    Op("rename_channels", "Rename Channels", "rename_channels", _check_rename,
       ("new_names",), mutates=False),
    Op("change_reference", "Change Reference", "change_reference", _check_reference,
       ("add", "ref")),
    Op("interpolate_bads", "Interpolate Bad Channels", "interpolate_bads",
       _check_interpolate),
    Op("find_events", "Find Events", "find_events", _check_find_events,
       ("stim_channel", "consecutive", "initial_event", "mask", "min_duration",
        "shortest_event"), mutates=False),
    Op("epoch_data", "Create Epochs", "epoch_data", _check_epoch,
       ("event_id", "tmin", "tmax", "baseline"), deserialize=_deserialize_epoch),
    Op("drop_bad_epochs", "Drop Bad Epochs", "drop_bad_epochs", _check_epochs,
       ("reject", "flat")),
]}  # fmt: skip


def is_supported(step):
    """Return True if a step is a reproducible (supported) operation."""
    return not step.get("unsupported", False)


def pipeline_mutates_data(steps):
    """Return True if applying the pipeline would change the underlying signal data.

    Steps that only touch metadata (e.g. channel properties, event detection) do not
    require duplicating the target data set first, matching how these operations behave
    when run interactively (see the corresponding `MainWindow` handlers).
    """
    return any(
        REGISTRY[step["op"]].mutates
        for step in steps
        if is_supported(step) and step["op"] in REGISTRY
    )


def step_label(step):
    """Return a human-readable label for a step."""
    op = REGISTRY.get(step["op"])
    return op.label if op is not None else step["op"]


def step_summary(step):
    """Return a short one-line summary of a step's parameters for display."""
    if not is_supported(step):
        return "unsupported (not reproducible)"
    op = REGISTRY[step["op"]]
    params = step["params"]
    parts = [f"{name}={params[name]!r}" for name in op.params if name in params]
    return ", ".join(parts)


def check_pipeline(steps, ctx):
    """Validate a pipeline against a context built from the target dataset.

    Returns a list of `(index, label, message)` tuples for every step that is
    incompatible or unsupported. An empty list means the pipeline can be applied.
    """
    problems = []
    for i, step in enumerate(steps):
        if not is_supported(step):
            problems.append((i, step_label(step), "unsupported operation"))
            continue
        if step["op"] not in REGISTRY:
            problems.append((i, step["op"], "unknown operation"))
            continue
        op = REGISTRY[step["op"]]
        message = op.check(ctx, step["params"])
        if message:
            problems.append((i, op.label, message))
    return problems


def has_unsupported(steps):
    """Return True if any step is an unsupported (non-reproducible) operation."""
    return any(not is_supported(step) for step in steps)


def pipeline_to_dict(steps, source_name=None):
    """Wrap steps in a serializable pipeline document."""
    return {
        "mnelab_pipeline": PIPELINE_SCHEMA,
        "created": datetime.now().isoformat(timespec="seconds"),
        "source": source_name,
        "steps": steps,
    }


def pipeline_from_dict(document):
    """Extract and validate steps from a loaded pipeline document."""
    if not isinstance(document, dict) or "mnelab_pipeline" not in document:
        raise ValueError("Not a valid MNELAB pipeline file.")
    if document["mnelab_pipeline"] != PIPELINE_SCHEMA:
        raise ValueError(
            f"Unsupported pipeline version {document['mnelab_pipeline']} "
            f"(expected {PIPELINE_SCHEMA})."
        )
    steps = document.get("steps")
    if not isinstance(steps, list):
        raise ValueError("Pipeline file does not contain any steps.")
    return steps
