# © MNELAB developers
#
# License: BSD (3-clause)

import json
import shutil
from unittest.mock import patch

import mne
import numpy as np
import pytest
from edfio import Edf, EdfSignal

from mnelab.mainwindow import MainWindow
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
from mnelab.utils import Montage


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
def ica_solution():
    """Fit a small, reusable ICA solution matching `edf_file`'s channels (Fz/Cz/Pz)."""
    fs = 256
    n_samples = 30 * fs
    rng = np.random.default_rng(0)
    data = rng.standard_normal((3, n_samples)) * 1e-6
    info = mne.create_info(["Fz", "Cz", "Pz"], fs, ch_types="eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    raw.filter(1, None, verbose=False)
    ica = mne.preprocessing.ICA(
        n_components=2, method="fastica", max_iter=200, random_state=0
    )
    ica.fit(raw, verbose=False)
    ica.exclude = [0]
    return ica


@pytest.fixture
def write_ica(ica_solution):
    """Return a function that saves the shared ICA solution to a given path."""

    def _write(path):
        ica_solution.save(path, overwrite=True)
        return path

    return _write


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
    model.load(edf_file)
    model.append_data([0])  # appending datasets is not reproducible
    assert model.current["pipeline_steps"][-1] == {
        "op": "append_data",
        "unsupported": True,
    }
    assert has_unsupported(model.current["pipeline_steps"])


def test_records_set_montage_builtin(edf_file):
    """Setting a built-in montage records a reproducible step."""
    model = Model()
    model.load(edf_file)
    model.set_montage("standard_1020")
    assert model.current["pipeline_steps"] == [
        {
            "op": "set_montage",
            "params": {
                "montage_name": "standard_1020",
                "match_case": False,
                "match_alias": False,
                "on_missing": "raise",
            },
        }
    ]


def test_records_set_montage_clear(edf_file):
    """Clearing the montage records a reproducible step."""
    model = Model()
    model.load(edf_file)
    model.set_montage(None)
    assert model.current["pipeline_steps"] == [
        {
            "op": "set_montage",
            "params": {
                "montage_name": None,
                "match_case": False,
                "match_alias": False,
                "on_missing": "raise",
            },
        }
    ]


def test_records_set_custom_montage_unsupported(edf_file, tmp_path):
    """A montage loaded from a file is not reproducible."""
    model = Model()
    model.load(edf_file)
    dig = mne.channels.make_standard_montage("standard_1020")
    montage = Montage(dig, "custom.sfp", path=tmp_path / "custom.sfp")
    model.set_custom_montage(montage)
    assert model.current["pipeline_steps"] == [
        {"op": "set_custom_montage", "unsupported": True}
    ]


def test_records_set_custom_montage_embedded_unsupported(edf_file):
    """A montage extracted from the dataset itself is not reproducible."""
    model = Model()
    model.load(edf_file)
    dig = mne.channels.make_standard_montage("standard_1020")
    montage = Montage(dig, "Custom", embedded=True)
    model.set_custom_montage(montage)
    assert model.current["pipeline_steps"] == [
        {"op": "set_custom_montage", "unsupported": True}
    ]


def test_apply_pipeline_set_montage_builtin(edf_file):
    """A built-in montage step can be replayed on another dataset."""
    model = Model()
    model.load(edf_file)
    model.set_montage("standard_1020")
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    model.load(edf_file)  # second, unprocessed dataset becomes current
    assert model.current["data"].get_montage() is None
    model.apply_pipeline(steps)
    assert model.current["data"].get_montage() is not None


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


def test_records_import_bads_matching_convention(edf_file):
    """A sidecar file named after the dataset records a reproducible suffix."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_channels.csv"
    sidecar.write_text("Fz")
    model.import_bads(str(sidecar))
    assert model.current["pipeline_steps"][-1] == {
        "op": "import_bads",
        "params": {"suffix": "-bad_channels.csv"},
    }
    assert model.current["data"].info["bads"] == ["Fz"]


def test_records_import_bads_non_matching_convention_unsupported(edf_file, tmp_path):
    """A sidecar file that doesn't follow the naming convention is unsupported."""
    model = Model()
    model.load(edf_file)
    sidecar = tmp_path / "custom_bads.csv"  # different directory, unrelated name
    sidecar.write_text("Fz")
    model.import_bads(str(sidecar))
    assert model.current["pipeline_steps"][-1] == {
        "op": "import_bads",
        "unsupported": True,
    }


def test_apply_pipeline_import_bads_resolves_new_dataset_path(
    edf_file, tmp_path_factory
):
    """Replaying an import_bads step resolves the sidecar next to the new dataset."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_channels.csv"
    sidecar.write_text("Fz")
    model.import_bads(str(sidecar))
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    (other_dir / "other-bad_channels.csv").write_text("Cz")

    model.load(other_edf)
    assert model.current["data"].info["bads"] == []
    model.apply_pipeline(steps)
    assert model.current["data"].info["bads"] == ["Cz"]  # from other.edf's own sidecar


def test_records_import_bads_after_duplicate_still_matches_convention(edf_file):
    """A prior duplication (e.g. before filtering) must not break sidecar matching.

    `duplicate_data()` clears `fname` to `None` (mirroring `MainWindow.auto_duplicate`,
    called by essentially every interactive mutating operation such as Filter). The
    naming convention must still resolve via the frozen `source_fname`/`source_name`,
    not the (now `None`) `fname`.
    """
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_channels.csv"
    sidecar.write_text("Fz")

    model.duplicate_data()  # simulates auto_duplicate() before e.g. filtering
    assert model.current["fname"] is None
    model.filter(1, 40)
    model.import_bads(str(sidecar))

    steps = model.current["pipeline_steps"]
    assert steps[-1] == {"op": "import_bads", "params": {"suffix": "-bad_channels.csv"}}


def test_apply_pipeline_import_bads_onto_duplicated_target(edf_file, tmp_path_factory):
    """Replay resolves the sidecar even if the target dataset was itself duplicated."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_channels.csv"
    sidecar.write_text("Fz")
    model.import_bads(str(sidecar))
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    (other_dir / "other-bad_channels.csv").write_text("Cz")

    model.load(other_edf)
    model.duplicate_data()  # target dataset was itself processed before replay
    assert model.current["fname"] is None
    model.apply_pipeline(steps)
    assert model.current["data"].info["bads"] == ["Cz"]


def test_apply_pipeline_import_bads_missing_sidecar_raises(edf_file, tmp_path_factory):
    """Replaying an import_bads step with no matching sidecar fails clearly."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_channels.csv"
    sidecar.write_text("Fz")
    model.import_bads(str(sidecar))
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)  # no matching sidecar written here

    model.load(other_edf)
    with pytest.raises(PipelineStepError):
        model.apply_pipeline(steps)


def test_records_import_annotations_matching_convention(edf_file):
    """A sidecar annotations file named after the dataset records a suffix."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_segments.csv"
    sidecar.write_text("type,onset,duration\nBAD_movement,1.0,0.5\n")
    model.import_annotations(str(sidecar), types=["BAD_movement"])
    assert model.current["pipeline_steps"][-1] == {
        "op": "import_annotations",
        "params": {
            "suffix": "-bad_segments.csv",
            "types": ["BAD_movement"],
            "description": None,
            "unit": "auto",
        },
    }


def test_records_import_annotations_non_matching_convention_unsupported(
    edf_file, tmp_path
):
    """A non-conforming annotations sidecar is recorded as unsupported."""
    model = Model()
    model.load(edf_file)
    sidecar = tmp_path / "custom_annotations.csv"
    sidecar.write_text("type,onset,duration\nBAD_movement,1.0,0.5\n")
    model.import_annotations(str(sidecar))
    assert model.current["pipeline_steps"][-1] == {
        "op": "import_annotations",
        "unsupported": True,
    }


def test_apply_pipeline_import_annotations_resolves_new_dataset_path(
    edf_file, tmp_path_factory
):
    """Replaying an import_annotations step resolves the new dataset's own sidecar."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_segments.csv"
    sidecar.write_text("type,onset,duration\nBAD_movement,1.0,0.5\n")
    model.import_annotations(str(sidecar))
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    (other_dir / "other-bad_segments.csv").write_text(
        "type,onset,duration\nBAD_muscle,2.0,1.0\n"
    )

    model.load(other_edf)
    assert len(model.current["data"].annotations) == 0
    model.apply_pipeline(steps)
    annots = model.current["data"].annotations
    assert list(annots.description) == ["BAD_muscle"]


def test_apply_pipeline_import_annotations_unit_auto_uses_seconds_for_non_integers(
    edf_file, tmp_path_factory
):
    """Replaying import_annotations must not pin the samples-vs-seconds convention.

    Whether onset/duration values are in samples or seconds is a property of each
    sidecar file, not the pipeline step. Recording always stores `unit="auto"`
    (regardless of what was actually passed for the original file). On replay, values
    that already fit the data range and aren't whole numbers are used as seconds as-is.
    """
    model = Model()
    model.load(edf_file)  # 30s recording at 256 Hz
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_segments.csv"
    # 5120 samples at 256 Hz == 20.0s; recorded with the (now-irrelevant) unit="samples"
    sidecar.write_text("type,onset,duration\nBAD_movement,5120,256\n")
    model.import_annotations(str(sidecar), unit="samples")
    assert model.current["pipeline_steps"][-1]["params"]["unit"] == "auto"
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    # this dataset's own sidecar genuinely uses (non-integer) seconds
    (other_dir / "other-bad_segments.csv").write_text(
        "type,onset,duration\nBAD_muscle,20.5,1.0\n"
    )

    model.load(other_edf)
    model.apply_pipeline(steps)
    annots = model.current["data"].annotations
    assert annots.onset[0] == pytest.approx(20.5)  # used as-is, not divided by fs


def test_apply_pipeline_import_annotations_unit_auto_prefers_samples_for_integers(
    edf_file, tmp_path_factory
):
    """Whole-number onset/duration values are treated as samples, not seconds.

    Integers are a strong hint that they're sample indices, even when they'd also
    happen to fit the data range if taken literally as seconds (genuine second-
    precision onsets are rarely exact whole numbers).
    """
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_segments.csv"
    sidecar.write_text("type,onset,duration\nBAD_movement,1.0,0.5\n")
    model.import_annotations(str(sidecar))
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    # 20 and 1 would also be valid onset/duration in seconds for this 30s recording,
    # but being whole numbers, they're treated as samples (256 Hz) instead
    (other_dir / "other-bad_segments.csv").write_text(
        "type,onset,duration\nBAD_muscle,20,1\n"
    )

    model.load(other_edf)
    model.apply_pipeline(steps)
    annots = model.current["data"].annotations
    assert annots.onset[0] == pytest.approx(20 / 256)


def test_apply_pipeline_import_annotations_unit_auto_falls_back_out_of_range(
    edf_file, tmp_path_factory
):
    """A non-integer value that doesn't fit as seconds is retried as samples."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_segments.csv"
    sidecar.write_text("type,onset,duration\nBAD_movement,1.0,0.5\n")
    model.import_annotations(str(sidecar))  # default unit="seconds", forced to "auto"
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    # not whole numbers, so the format alone doesn't suggest samples; but 5120.5 is
    # far too large to be a literal seconds value for this 30s recording, so the data
    # range alone must trigger the samples fallback
    (other_dir / "other-bad_segments.csv").write_text(
        "type,onset,duration\nBAD_muscle,5120.5,256.5\n"
    )

    model.load(other_edf)
    model.apply_pipeline(steps)
    annots = model.current["data"].annotations
    assert annots.onset[0] == pytest.approx(5120.5 / 256)


def test_import_annotations_survives_json_roundtrip(edf_file):
    """Recorded import_annotations params survive a JSON save/load round trip."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_segments.csv"
    sidecar.write_text("onset,duration\n1.0,0.5\n")
    model.import_annotations(str(sidecar), description="BAD_movement", unit="samples")
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    document = pipeline_to_dict(steps, source_name=name)
    loaded = pipeline_from_dict(json.loads(json.dumps(document)))
    assert loaded == steps


def test_mainwindow_import_annotations_replays_across_differing_type_labels(
    edf_file, tmp_path_factory, qtbot
):
    """An unfiltered annotation import must not be pinned to one file's type labels.

    `MainWindow.import_annotations` records `types=None` (rather than the literal list
    of types discovered in the source file) whenever the user did not deliberately
    narrow the selection, so replaying the step on another dataset isn't silently
    restricted to labels that happen to appear in the very first file.
    """
    model = Model()
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)
    model.load(edf_file)

    name = model.current["name"]
    sidecar = edf_file.parent / f"{name}-bad_segments.csv"
    sidecar.write_text("type,onset,duration\nBAD_movement,1.0,0.5\n")
    with patch(
        "mnelab.mainwindow.QFileDialog.getOpenFileName",
        return_value=(str(sidecar), ""),
    ):
        view.import_annotations()
    steps = [dict(step) for step in model.current["pipeline_steps"]]
    assert steps[-1]["params"]["types"] is None
    view.pipeline = steps

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    # a different type label than the one found in the original sidecar file
    (other_dir / "other-bad_segments.csv").write_text(
        "type,onset,duration\nBAD_muscle,2.0,1.0\n"
    )

    model.load(other_edf)
    view.apply_pipeline()
    annots = model.current["data"].annotations
    assert list(annots.description) == ["BAD_muscle"]


def test_records_import_ica_matching_convention(edf_file, write_ica):
    """A sidecar ICA file named after the dataset records a reproducible suffix."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    ica_path = write_ica(edf_file.parent / f"{name}-ica.fif.gz")
    model.import_ica(str(ica_path))
    assert model.current["pipeline_steps"][-1] == {
        "op": "import_ica",
        "params": {"suffix": "-ica.fif.gz"},
    }
    assert model.current["ica"] is not None


def test_records_import_ica_non_matching_convention_unsupported(
    edf_file, tmp_path, write_ica
):
    """A non-conforming ICA sidecar path is recorded as unsupported."""
    model = Model()
    model.load(edf_file)
    ica_path = write_ica(tmp_path / "custom-ica.fif.gz")  # different directory
    model.import_ica(str(ica_path))
    assert model.current["pipeline_steps"][-1] == {
        "op": "import_ica",
        "unsupported": True,
    }


def test_records_apply_ica_now_supported(edf_file, write_ica):
    """Applying ICA now records a normal, reproducible step (no longer a sentinel)."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    ica_path = write_ica(edf_file.parent / f"{name}-ica.fif.gz")
    model.import_ica(str(ica_path))
    model.apply_ica()
    assert model.current["pipeline_steps"][-1] == {"op": "apply_ica", "params": {}}


def test_check_pipeline_apply_ica_requires_prior_import_ica(edf_file):
    """apply_ica is incompatible unless an ICA solution was loaded first."""
    model = Model()
    model.load(edf_file)
    problems = check_pipeline(
        [{"op": "apply_ica", "params": {}}], make_context(model.current)
    )
    assert len(problems) == 1

    problems = check_pipeline(
        [
            {"op": "import_ica", "params": {"suffix": "-ica.fif.gz"}},
            {"op": "apply_ica", "params": {}},
        ],
        make_context(model.current),
    )
    assert problems == []


def test_apply_pipeline_import_ica_then_apply_ica_end_to_end(
    edf_file, write_ica, tmp_path_factory
):
    """import_ica + apply_ica replay resolves the new dataset's own ICA solution."""
    model = Model()
    model.load(edf_file)
    name = model.current["name"]
    write_ica(edf_file.parent / f"{name}-ica.fif.gz")
    model.import_ica(str(edf_file.parent / f"{name}-ica.fif.gz"))
    model.apply_ica()
    steps = [dict(step) for step in model.current["pipeline_steps"]]

    other_dir = tmp_path_factory.mktemp("data")
    other_edf = other_dir / "other.edf"
    shutil.copy(edf_file, other_edf)
    write_ica(other_dir / "other-ica.fif.gz")

    model.load(other_edf)
    before = model.current["data"].get_data().copy()
    model.apply_pipeline(steps)
    after = model.current["data"].get_data()
    assert not np.allclose(before, after)
    assert model.current["ica"] is not None
