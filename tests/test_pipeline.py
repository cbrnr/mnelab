# © MNELAB developers
#
# License: BSD (3-clause)

import json

import mne
import numpy as np
import pytest
from edfio import Edf, EdfSignal

from mnelab.model import Model, PipelineStepError
from mnelab.pipeline import (
    REGISTRY,
    check_pipeline,
    has_unsupported,
    make_context,
    pipeline_from_dict,
    pipeline_mutates_data,
    pipeline_to_dict,
)


@pytest.fixture(scope="module")
def edf_file(tmp_path_factory):
    """Generate a multi-channel .edf file for testing."""
    fs = 256
    labels = ["Fz", "Cz", "Pz"]
    signals = [
        EdfSignal(np.linspace(-1, 1, 30 * fs), sampling_frequency=fs, label=label)
        for label in labels
    ]
    path = tmp_path_factory.mktemp("data") / "sample.edf"
    Edf(signals).write(path)
    return path


@pytest.fixture(scope="module")
def fif_file_with_stim(tmp_path_factory):
    """Generate a .fif file with a stim channel containing a single event marker."""
    fs = 256
    n_samples = 5 * fs
    eeg_data = np.random.default_rng(0).standard_normal((2, n_samples)) * 1e-6
    stim_data = np.zeros((1, n_samples))
    stim_data[0, fs] = 5  # single event with code 5 at t=1s
    data = np.vstack([eeg_data, stim_data])
    info = mne.create_info(["Fz", "Cz", "Stim"], fs, ch_types=["eeg", "eeg", "stim"])
    raw = mne.io.RawArray(data, info)
    path = tmp_path_factory.mktemp("data") / "sample_stim_raw.fif"
    raw.save(path)
    return path


def test_records_supported_steps(edf_file):
    """Supported operations attach structured steps to the dataset."""
    model = Model()
    model.load(edf_file)
    model.filter(1, 40)
    model.resample(128)
    assert model.current["pipeline_steps"] == [
        {"op": "filter", "params": {"lower": 1, "upper": 40, "notch": None}},
        {"op": "resample", "params": {"sfreq": 128}},
    ]


def test_records_unsupported_sentinel(edf_file):
    """Non-reproducible operations are recorded as a sentinel step."""
    model = Model()
    model.load(edf_file)
    model.set_montage(None)  # setting a montage is not reproducible
    assert model.current["pipeline_steps"] == [
        {"op": "set_montage", "unsupported": True}
    ]
    assert has_unsupported(model.current["pipeline_steps"])


def test_duplicate_inherits_independent_steps(edf_file):
    """A duplicated dataset inherits an independent copy of the pipeline steps."""
    model = Model()
    model.load(edf_file)
    model.filter(1, 40)
    parent_steps = model.current["pipeline_steps"]
    model.duplicate_data()
    child_steps = model.current["pipeline_steps"]
    assert child_steps == parent_steps
    assert child_steps is not parent_steps  # deep-copied, not shared
    model.resample(128)  # only extends the child's chain
    assert len(model.current["pipeline_steps"]) == 2
    assert len(parent_steps) == 1


def test_json_roundtrip_retuples_baseline():
    """Saving and loading preserves steps; the baseline tuple is restored."""
    steps = [
        {"op": "filter", "params": {"lower": 1.0, "upper": 40.0, "notch": None}},
        {
            "op": "epoch_data",
            "params": {
                "event_id": [1],
                "tmin": -0.2,
                "tmax": 0.5,
                "baseline": [-0.2, 0],
            },
        },
    ]
    document = pipeline_to_dict(steps, source_name="test")
    loaded = pipeline_from_dict(json.loads(json.dumps(document)))
    assert loaded == steps
    kwargs = REGISTRY["epoch_data"].deserialize(loaded[1]["params"])
    assert kwargs["baseline"] == (-0.2, 0)


def test_pipeline_from_dict_rejects_invalid():
    """Loading rejects documents that are not valid pipelines."""
    with pytest.raises(ValueError):
        pipeline_from_dict({"not": "a pipeline"})


def test_apply_pipeline_to_other_dataset(edf_file):
    """A pipeline captured from one dataset can be applied to another."""
    model = Model()
    model.load(edf_file)
    model.filter(1, 40)
    model.resample(128)
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    model.load(edf_file)  # second, unprocessed dataset becomes current
    assert model.current["data"].info["sfreq"] == 256
    model.apply_pipeline(steps)
    assert model.current["data"].info["sfreq"] == 128
    assert model.current["pipeline_steps"] == steps


def test_apply_pipeline_raises_on_failing_step(edf_file):
    """A failing step raises PipelineStepError identifying the step."""
    model = Model()
    model.load(edf_file)
    steps = [
        {"op": "resample", "params": {"sfreq": 128}},
        {"op": "pick_channels", "params": {"picks": ["NOPE"]}},
    ]
    with pytest.raises(PipelineStepError) as excinfo:
        model.apply_pipeline(steps)
    assert excinfo.value.index == 1
    assert excinfo.value.op == "Pick Channels"


def test_apply_pipeline_raises_on_unsupported_step(edf_file):
    """An unsupported sentinel step cannot be applied."""
    model = Model()
    model.load(edf_file)
    steps = [{"op": "set_montage", "unsupported": True}]
    with pytest.raises(PipelineStepError):
        model.apply_pipeline(steps)


def test_check_pipeline_valid(edf_file):
    """A compatible pipeline reports no problems."""
    model = Model()
    model.load(edf_file)
    steps = [
        {"op": "filter", "params": {"lower": 1.0, "upper": 40.0, "notch": None}},
        {"op": "pick_channels", "params": {"picks": ["Fz", "Cz"]}},
    ]
    assert check_pipeline(steps, make_context(model.current)) == []


def test_check_pipeline_detects_incompatibilities(edf_file):
    """Incompatible and unsupported steps are reported."""
    model = Model()
    model.load(edf_file)
    steps = [
        {"op": "pick_channels", "params": {"picks": ["MISSING"]}},
        {"op": "set_montage", "unsupported": True},
    ]
    problems = check_pipeline(steps, make_context(model.current))
    indices = [index for index, _, _ in problems]
    assert indices == [0, 1]


def test_check_pipeline_requires_raw_for_epoching(edf_file):
    """Epoching requires raw data with events."""
    model = Model()
    model.load(edf_file)
    steps = [
        {
            "op": "epoch_data",
            "params": {"event_id": [1], "tmin": 0, "tmax": 1, "baseline": None},
        }
    ]
    problems = check_pipeline(steps, make_context(model.current))
    assert len(problems) == 1  # no events available


def test_records_find_events(fif_file_with_stim):
    """find_events records a structured step with the resolved parameters."""
    model = Model()
    model.load(fif_file_with_stim)
    model.find_events(stim_channel="Stim")
    assert model.current["pipeline_steps"] == [
        {
            "op": "find_events",
            "params": {
                "stim_channel": "Stim",
                "consecutive": True,
                "initial_event": False,
                "mask": None,
                "min_duration": 0,
                "shortest_event": 0,
            },
        }
    ]


def test_check_pipeline_find_events_valid(fif_file_with_stim):
    """A find_events step targeting an existing stim channel is compatible."""
    model = Model()
    model.load(fif_file_with_stim)
    steps = [{"op": "find_events", "params": {"stim_channel": "Stim"}}]
    ctx = make_context(model.current)
    assert ctx["has_events"] is False
    assert check_pipeline(steps, ctx) == []
    assert ctx["has_events"] is True  # find_events makes events available downstream


def test_check_pipeline_find_events_missing_channel(fif_file_with_stim):
    """A find_events step referencing a non-existent stim channel is flagged."""
    model = Model()
    model.load(fif_file_with_stim)
    steps = [{"op": "find_events", "params": {"stim_channel": "NOPE"}}]
    problems = check_pipeline(steps, make_context(model.current))
    assert len(problems) == 1


def test_apply_pipeline_find_events_then_epoch(fif_file_with_stim):
    """A captured find_events + epoch_data chain replays on another dataset."""
    model = Model()
    model.load(fif_file_with_stim)
    model.find_events(stim_channel="Stim")
    model.epoch_data(event_id=[5], tmin=-0.1, tmax=0.1, baseline=None)
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    model.load(fif_file_with_stim)  # fresh, unprocessed raw dataset
    assert model.current["dtype"] == "raw"
    model.apply_pipeline(steps)
    assert model.current["dtype"] == "epochs"
    assert len(model.current["data"]) == 1


def test_pipeline_mutates_data_for_signal_processing_steps():
    """Steps that change the signal data (e.g. filter) require duplication."""
    steps = [{"op": "filter", "params": {"lower": 1.0, "upper": 40.0, "notch": None}}]
    assert pipeline_mutates_data(steps) is True


def test_pipeline_does_not_mutate_data_for_metadata_only_steps():
    """Metadata-only steps (e.g. find_events) do not require duplication.

    This matches the interactive behavior: running Find Events, Channel Properties, or
    Rename Channels from the menu never creates a new dataset (see the corresponding
    handlers in mainwindow.py, none of which call auto_duplicate()).
    """
    steps = [
        {"op": "find_events", "params": {"stim_channel": "Stim"}},
        {
            "op": "set_channel_properties",
            "params": {"bads": ["Fz"], "names": {}, "types": {}},
        },
        {"op": "rename_channels", "params": {"new_names": ["A", "B"]}},
    ]
    assert pipeline_mutates_data(steps) is False


def test_pipeline_mutates_data_for_mixed_steps():
    """A pipeline mutates data if at least one step does, even if others don't."""
    steps = [
        {"op": "find_events", "params": {"stim_channel": "Stim"}},
        {"op": "resample", "params": {"sfreq": 128}},
    ]
    assert pipeline_mutates_data(steps) is True


def test_apply_pipeline_find_events_does_not_create_new_dataset(fif_file_with_stim):
    """Applying a metadata-only pipeline modifies the current dataset in place."""
    model = Model()
    model.load(fif_file_with_stim)
    n_datasets_before = len(model.data)
    # apply_pipeline() itself never duplicates; that decision belongs to the caller
    # (MainWindow.apply_pipeline), which consults pipeline_mutates_data() first
    steps = [{"op": "find_events", "params": {"stim_channel": "Stim"}}]
    assert pipeline_mutates_data(steps) is False
    model.apply_pipeline(steps)
    assert len(model.data) == n_datasets_before  # no new dataset was created
    assert len(model.current["events"]) == 1
