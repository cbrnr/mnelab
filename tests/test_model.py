# © MNELAB developers
#
# License: BSD (3-clause)

import json
import math
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import mne
import numpy as np
import pytest
from edfio import Edf, EdfSignal
from mne import Annotations

from mnelab.model import InvalidAnnotationsError, Model, PipelineCancelledError
from mnelab.utils import Montage


class DummyICA:
    def __init__(
        self,
        method="infomax",
        n_components=None,
        fit_params=None,
        random_state=None,
    ):
        self.method = method
        self.requested_n_components = n_components
        self.n_components_ = n_components or 1
        self.fit_params = fit_params or {}
        self.random_state = random_state
        self.exclude = []
        self.reject_by_annotation = None

    def fit(self, inst, reject_by_annotation=True):
        self.reject_by_annotation = reject_by_annotation
        self.n_components_ = self.requested_n_components or 1
        return self

    def apply(self, inst):
        inst._data[:] = inst.get_data() + 1.0
        return inst


@pytest.fixture(scope="module")
def edf_files(tmp_path_factory):
    """Generate .edf files for testing purposes."""
    fs = 256
    signals = [
        np.linspace(-1, 1, 30 * fs),
        np.linspace(-10, -15, 30 * fs),
        np.linspace(10, 15, 30 * fs),
    ]
    paths = []
    for i, signal_data in enumerate(signals):
        path = tmp_path_factory.mktemp("data") / f"sample_{i}.edf"
        Edf([EdfSignal(signal_data, sampling_frequency=fs, label="EEG")]).write(path)
        paths.append(path)
    return paths


@pytest.mark.parametrize("duplicate_data", [True, False])
def test_append_data(edf_files, duplicate_data):
    """Test append_data method."""

    model = Model()
    for file in edf_files:
        model.load(file)

    data = [d["data"].get_data()[0] for d in model.data]

    assert len(model.data) == len(edf_files), (
        "Number of data sets in model is not equal to number of files after loading"
    )

    idx_list = [1, 2]  # data sets to append
    model.index = 0  # set current data set
    if duplicate_data:  # adjust for index change if duplicated
        model.duplicate_data()
        idx_list = [idx + 1 if idx >= model.index else idx for idx in idx_list]

    model.append_data(idx_list)

    assert (
        len(model.data) == len(edf_files) + 2 if duplicate_data else len(edf_files) + 1
    ), "Number of data sets in model is not equal to number of files after appending"

    assert model.current["name"].endswith("(appended)"), (
        "Name of appended data set does not match expected name"
    )

    assert len(model.current["data"].times) == sum(len(d) for d in data), (
        "Length of appended data set does not match expected length"
    )

    appended_data = model.current["data"].get_data()[0]

    assert math.isclose(appended_data[0], data[0][0], rel_tol=1e-12), (
        "Value at index 0 is incorrect"
    )

    assert math.isclose(
        appended_data[(idx := len(data[0]) - 1)], data[0][-1], rel_tol=1e-12
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(
        appended_data[(idx := len(data[0]))], data[1][0], rel_tol=1e-12
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(
        appended_data[(idx := len(data[0]) + len(data[1]) - 1)],
        data[1][-1],
        rel_tol=1e-12,
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(
        appended_data[(idx := len(data[0]) + len(data[1]))], data[2][0], rel_tol=1e-12
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(appended_data[-1], data[2][-1], rel_tol=1e-12), (
        "Value at last index is incorrect"
    )


@pytest.fixture
def model_with_data(tmp_path):
    """Model with a single 30-second EDF file loaded."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)
    model = Model()
    model.load(path)
    return model


def _write_annotations_csv(path, rows, header=True):
    """Write a CSV annotation file."""
    with open(path, "w") as f:
        if header:
            f.write("type,onset,duration\n")
        for row in rows:
            f.write(",".join(str(v) for v in row) + "\n")


def test_import_annotations_basic(model_with_data, tmp_path):
    """Imported annotations are added to the data."""
    csv = tmp_path / "annots.csv"
    _write_annotations_csv(csv, [("BAD", 1.0, 0.5), ("BAD", 5.0, 1.0)])
    model_with_data.import_annotations(csv)
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 2
    assert list(annots.description) == ["BAD", "BAD"]
    np.testing.assert_allclose(annots.onset, [1.0, 5.0])
    np.testing.assert_allclose(annots.duration, [0.5, 1.0])


def test_import_annotations_merges_with_existing(model_with_data, tmp_path):
    """Imported annotations are appended to already-existing annotations."""
    model_with_data.current["data"].set_annotations(
        Annotations([2.0], [0.25], ["EXISTING"])
    )
    csv = tmp_path / "annots.csv"
    _write_annotations_csv(csv, [("NEW", 10.0, 1.0)])
    model_with_data.import_annotations(csv)
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 2
    assert "EXISTING" in annots.description
    assert "NEW" in annots.description


def test_import_annotations_filter_by_type(model_with_data, tmp_path):
    """Only annotation types listed in `types` are imported."""
    csv = tmp_path / "annots.csv"
    _write_annotations_csv(csv, [("BAD", 1.0, 0.5), ("GOOD", 5.0, 1.0)])
    model_with_data.import_annotations(csv, types=["BAD"])
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    assert annots.description[0] == "BAD"


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param([("BAD", "abc", "xyz")], id="non_numeric_values"),
        pytest.param([("BAD", 9999.0, 1.0)], id="outside_range"),
    ],
)
def test_import_annotations_invalid_input(model_with_data, tmp_path, rows):
    """Invalid CSV content raises InvalidAnnotationsError."""
    csv = tmp_path / "bad.csv"
    _write_annotations_csv(csv, rows)
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(csv)


def test_import_annotations_binary_file(model_with_data, tmp_path):
    """A binary file raises InvalidAnnotationsError."""
    binary = tmp_path / "binary.csv"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\xfe")
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(binary)


def test_import_annotations_invalid_header(model_with_data, tmp_path):
    """A file without the expected CSV header raises InvalidAnnotationsError."""
    csv = tmp_path / "bad_header.csv"
    csv.write_text("afsklasdjfkasdikfkasdjklfs\n")
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(csv)


def test_import_annotations_outside_range_does_not_change_existing(
    model_with_data, tmp_path
):
    """When an invalid file is rejected, pre-existing annotations are unchanged."""
    model_with_data.current["data"].set_annotations(
        Annotations([2.0], [0.25], ["EXISTING"])
    )
    csv = tmp_path / "out_of_range.csv"
    _write_annotations_csv(csv, [("BAD", 9999.0, 1.0)])
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(csv)
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    assert annots.description[0] == "EXISTING"


def test_import_annotations_no_type_column(model_with_data, tmp_path):
    """A two-column file (onset,duration) uses the supplied description."""
    csv = tmp_path / "no_type.csv"
    with open(csv, "w") as f:
        f.write("onset,duration\n")
        f.write("1.0,0.5\n")
        f.write("5.0,1.0\n")
    model_with_data.import_annotations(csv, description="BAD")
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 2
    assert list(annots.description) == ["BAD", "BAD"]
    np.testing.assert_allclose(annots.onset, [1.0, 5.0])
    np.testing.assert_allclose(annots.duration, [0.5, 1.0])


def test_import_annotations_no_type_column_default_description(
    model_with_data, tmp_path
):
    """A two-column file without a supplied description defaults to 'annotation'."""
    csv = tmp_path / "no_type.csv"
    with open(csv, "w") as f:
        f.write("onset,duration\n")
        f.write("1.0,0.5\n")
    model_with_data.import_annotations(csv, description=None)
    annots = model_with_data.current["data"].annotations
    assert annots.description[0] == "annotation"


def test_import_annotations_in_samples(model_with_data, tmp_path):
    """When unit='samples', onset and duration are divided by sfreq."""
    fs = model_with_data.current["data"].info["sfreq"]  # 256 Hz
    csv = tmp_path / "samples.csv"
    _write_annotations_csv(csv, [("BAD", int(1.0 * fs), int(0.5 * fs))])
    model_with_data.import_annotations(csv, unit="samples")
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    np.testing.assert_allclose(annots.onset, [1.0], rtol=1e-6)
    np.testing.assert_allclose(annots.duration, [0.5], rtol=1e-6)


def test_import_annotations_in_samples_no_type_column(model_with_data, tmp_path):
    """unit='samples' works with two-column files as well."""
    fs = model_with_data.current["data"].info["sfreq"]
    csv = tmp_path / "samples_no_type.csv"
    with open(csv, "w") as f:
        f.write("onset,duration\n")
        f.write(f"{int(2.0 * fs)},{int(1.0 * fs)}\n")
    model_with_data.import_annotations(csv, description="STIM", unit="samples")
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    assert annots.description[0] == "STIM"
    np.testing.assert_allclose(annots.onset, [2.0], rtol=1e-6)
    np.testing.assert_allclose(annots.duration, [1.0], rtol=1e-6)


def test_import_bads_creates_replayable_pipeline_step(model_with_data, tmp_path):
    """Importing bad channels creates a replayable pipeline step."""
    csv = tmp_path / "bads.csv"
    csv.write_text("EEG")

    model_with_data.import_bads(csv)

    assert len(model_with_data.data) == 2
    assert model_with_data.current["operation"] == "import_bads"
    assert model_with_data.current["parent_index"] == 0
    assert model_with_data.current["data"].info["bads"] == ["EEG"]
    assert "data.info['bads']" in "\n".join(model_with_data.get_history())

    pipeline_path = tmp_path / "import_bads.mnepipe"
    model_with_data.save_pipeline(path=pipeline_path)
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    assert pipeline["steps"][-1]["operation"] == "import_bads"
    assert pipeline["steps"][-1]["params"]["fname"] == str(csv)

    replay_model = Model()
    replay_model.load(model_with_data.data[0]["fname"])
    replay_model.apply_pipeline(pipeline)
    assert replay_model.current["data"].info["bads"] == ["EEG"]


def test_import_events_creates_replayable_pipeline_step(model_with_data, tmp_path):
    """Importing events is preserved in history and pipeline replay."""
    csv = tmp_path / "events.csv"
    csv.write_text("pos,type\n10,1\n20,2\n")

    model_with_data.import_events(csv)

    np.testing.assert_array_equal(
        model_with_data.current["events"],
        np.array([[10, 0, 1], [20, 0, 2]]),
    )
    assert model_with_data.current["operation"] == "import_events"
    history = "\n".join(model_with_data.get_history())
    assert "np.loadtxt" in history

    pipeline_path = tmp_path / "import_events.mnepipe"
    model_with_data.save_pipeline(path=pipeline_path)
    replay_model = Model()
    replay_model.load(model_with_data.data[0]["fname"])
    replay_model.apply_pipeline(json.loads(pipeline_path.read_text(encoding="utf-8")))
    np.testing.assert_array_equal(
        replay_model.current["events"],
        np.array([[10, 0, 1], [20, 0, 2]]),
    )


def test_import_annotations_creates_replayable_pipeline_step(model_with_data, tmp_path):
    """Importing annotations is preserved in history and pipeline replay."""
    csv = tmp_path / "annots.csv"
    _write_annotations_csv(csv, [("BAD", 1.0, 0.5), ("GOOD", 2.0, 0.25)])

    model_with_data.import_annotations(csv, types=["BAD"])

    annots = model_with_data.current["data"].annotations
    assert model_with_data.current["operation"] == "import_annotations"
    assert list(annots.description) == ["BAD"]
    history = "\n".join(model_with_data.get_history())
    assert "new_annots = read_annotations_from_file(" in history

    pipeline_path = tmp_path / "import_annotations.mnepipe"
    model_with_data.save_pipeline(path=pipeline_path)
    replay_model = Model()
    replay_model.load(model_with_data.data[0]["fname"])
    replay_model.apply_pipeline(json.loads(pipeline_path.read_text(encoding="utf-8")))
    replay_annots = replay_model.current["data"].annotations
    assert list(replay_annots.description) == ["BAD"]
    np.testing.assert_allclose(replay_annots.onset, [1.0])
    np.testing.assert_allclose(replay_annots.duration, [0.5])


def test_set_events_and_annotations_are_saved_and_replayed(model_with_data, tmp_path):
    """Manual event and annotation edits become replayable pipeline steps."""
    events = np.array([[5, 0, 11], [15, 0, 22]])

    model_with_data.set_events(events)
    model_with_data.set_annotations([1.0], [0.5], ["MANUAL"])

    steps = model_with_data.get_pipeline_steps()
    assert [step["operation"] for step in steps[1:]] == [
        "set_events",
        "set_annotations",
    ]
    history = "\n".join(model_with_data.get_history())
    assert "events = np.asarray(" in history
    assert "data.set_annotations(mne.Annotations(" in history

    pipeline_path = tmp_path / "manual_metadata.mnepipe"
    model_with_data.save_pipeline(path=pipeline_path)
    replay_model = Model()
    replay_model.load(model_with_data.data[0]["fname"])
    replay_model.apply_pipeline(json.loads(pipeline_path.read_text(encoding="utf-8")))

    np.testing.assert_array_equal(replay_model.current["events"], events)
    replay_annots = replay_model.current["data"].annotations
    assert list(replay_annots.description) == ["MANUAL"]
    np.testing.assert_allclose(replay_annots.onset, [1.0])
    np.testing.assert_allclose(replay_annots.duration, [0.5])


def test_ica_pipeline_steps_are_saved_and_replayed(
    model_with_data, tmp_path, monkeypatch
):
    """Run/set exclude/apply ICA is saved and replayed as a pipeline."""
    monkeypatch.setattr(mne.preprocessing, "ICA", DummyICA)

    model_with_data.run_ica(
        method="infomax",
        n_components=1,
        reject_by_annotation=True,
        fit_params={"extended": True},
        random_state=97,
    )
    model_with_data.set_ica_exclude([0])
    model_with_data.apply_ica()

    assert [step["operation"] for step in model_with_data.get_pipeline_steps()[1:]] == [
        "run_ica",
        "set_ica_exclude",
        "apply_ica",
    ]
    history = "\n".join(model_with_data.get_history())
    assert "mne.preprocessing.ICA(" in history
    assert "ica.exclude = [0]" in history
    assert "ica.apply(inst=data)" in history
    assert model_with_data.current["ica"].exclude == [0]
    np.testing.assert_allclose(
        model_with_data.current["data"].get_data(),
        np.ones_like(model_with_data.current["data"].get_data()),
    )

    pipeline_path = tmp_path / "ica_pipeline.mnepipe"
    model_with_data.save_pipeline(path=pipeline_path)
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    assert [step["operation"] for step in pipeline["steps"]] == [
        "run_ica",
        "set_ica_exclude",
        "apply_ica",
    ]

    replay_model = Model()
    replay_model.load(model_with_data.data[0]["fname"])
    monkeypatch.setattr(mne.preprocessing, "ICA", DummyICA)
    replay_model.apply_pipeline(pipeline)
    assert replay_model.current["ica"].exclude == [0]
    np.testing.assert_allclose(
        replay_model.current["data"].get_data(),
        np.ones_like(replay_model.current["data"].get_data()),
    )


def test_import_ica_creates_replayable_pipeline_step(
    model_with_data, tmp_path, monkeypatch
):
    """Importing an ICA solution is preserved in history and pipeline replay."""

    def fake_read_ica(_fname):
        imported = DummyICA(method="fastica", n_components=1)
        imported.exclude = [0]
        return imported

    monkeypatch.setattr(mne.preprocessing, "read_ica", fake_read_ica)

    ica_path = tmp_path / "solution-ica.fif"
    ica_path.write_text("dummy")

    model_with_data.import_ica(ica_path)

    assert model_with_data.current["operation"] == "import_ica"
    assert model_with_data.current["ica"].exclude == [0]
    history = "\n".join(model_with_data.get_history())
    assert "mne.preprocessing.read_ica" in history

    pipeline_path = tmp_path / "import_ica.mnepipe"
    model_with_data.save_pipeline(path=pipeline_path)
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    assert pipeline["steps"][-1]["operation"] == "import_ica"
    assert pipeline["steps"][-1]["params"]["fname"] == str(ica_path)

    replay_model = Model()
    replay_model.load(model_with_data.data[0]["fname"])
    monkeypatch.setattr(mne.preprocessing, "read_ica", fake_read_ica)
    replay_model.apply_pipeline(pipeline)
    assert replay_model.current["ica"].exclude == [0]


def test_import_file_steps_are_parameterized_by_dataset_prefix(tmp_path, monkeypatch):
    """Import sidecar files resolve against the replay target dataset prefix."""

    def write_edf(path):
        fs = 256
        signal = np.zeros(30 * fs)
        Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    read_ica_paths = []

    def fake_read_ica(fname):
        read_ica_paths.append(Path(fname).name)
        imported = DummyICA(method="fastica", n_components=1)
        imported.exclude = [0]
        return imported

    monkeypatch.setattr(mne.preprocessing, "read_ica", fake_read_ica)

    source_raw = tmp_path / "s01_raw.edf"
    target_raw = tmp_path / "s02_raw.edf"
    write_edf(source_raw)
    write_edf(target_raw)

    source_bads = tmp_path / "s01-bad_channels.csv"
    target_bads = tmp_path / "s02-bad_channels.csv"
    source_bads.write_text("EEG")
    target_bads.write_text("EEG")

    source_annotations = tmp_path / "s01-annotations.csv"
    target_annotations = tmp_path / "s02-annotations.csv"
    _write_annotations_csv(source_annotations, [("SOURCE", 1.0, 0.5)])
    _write_annotations_csv(target_annotations, [("TARGET", 2.0, 0.25)])

    source_ica = tmp_path / "s01-ica.fif.gz"
    target_ica = tmp_path / "s02-ica.fif.gz"
    source_ica.write_text("source")
    target_ica.write_text("target")

    model = Model()
    model.load(source_raw)
    model.import_bads(source_bads)
    model.import_annotations(source_annotations)
    model.import_ica(source_ica)

    pipeline_path = tmp_path / "imports.mnepipe"
    model.save_pipeline(path=pipeline_path)
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))

    assert pipeline["steps"][0]["params"]["fname"] == (
        "{dataset_dir}/{dataset_prefix}-bad_channels.csv"
    )
    assert pipeline["steps"][1]["params"]["fname"] == (
        "{dataset_dir}/{dataset_prefix}-annotations.csv"
    )
    assert pipeline["steps"][2]["params"]["fname"] == (
        "{dataset_dir}/{dataset_prefix}-ica.fif.gz"
    )

    replay_model = Model()
    replay_model.load(target_raw)
    replay_model.apply_pipeline(pipeline)

    assert replay_model.current["data"].info["bads"] == ["EEG"]
    replay_annotations = replay_model.current["data"].annotations
    assert list(replay_annotations.description) == ["TARGET"]
    np.testing.assert_allclose(replay_annotations.onset, [2.0])
    np.testing.assert_allclose(replay_annotations.duration, [0.25])
    assert read_ica_paths[-1] == "s02-ica.fif.gz"


def test_apply_pipeline_reports_progress_and_can_cancel(model_with_data):
    """Pipeline replay reports completed steps and stops cleanly on cancel."""
    pipeline = {
        "pipeline_format": 1,
        "steps": [
            {"operation": "set_events", "params": {"events": [[5, 0, 11]]}},
            {
                "operation": "set_annotations",
                "params": {
                    "onset": [1.0],
                    "duration": [0.5],
                    "description": ["MANUAL"],
                },
            },
        ],
    }
    progress = []

    def progress_callback(step_index, step):
        progress.append((step_index, step["operation"]))

    def is_cancelled():
        return len(progress) >= 1

    with pytest.raises(PipelineCancelledError):
        model_with_data.apply_pipeline(
            pipeline,
            progress_callback=progress_callback,
            is_cancelled=is_cancelled,
        )

    assert progress == [(1, "set_events")]
    np.testing.assert_array_equal(
        model_with_data.current["events"],
        np.array([[5, 0, 11]]),
    )
    assert len(model_with_data.current["data"].annotations) == 0


def test_apply_pipeline_supports_execution_modes_and_report(model_with_data):
    """Skip and review modes are represented in the run report."""
    pipeline = {
        "pipeline_format": 1,
        "steps": [
            {
                "operation": "set_events",
                "execution_mode": "skip",
                "params": {"events": [[1, 0, 1]]},
            },
            {
                "operation": "set_events",
                "execution_mode": "review",
                "params": {"events": [[2, 0, 2]]},
            },
        ],
    }
    review_calls = []

    def review_callback(step_index, step, execution_mode):
        review_calls.append((step_index, step["operation"], execution_mode))
        return True

    model_with_data.apply_pipeline(pipeline, review_callback=review_callback)

    assert review_calls == [(2, "set_events", "review")]
    np.testing.assert_array_equal(
        model_with_data.current["events"],
        np.array([[2, 0, 2]]),
    )
    assert [entry["status"] for entry in model_with_data.pipeline_run_report] == [
        "skipped",
        "complete",
    ]


def test_apply_pipeline_requires_review_callback(model_with_data):
    """Review checkpoints are explicit and cannot run silently."""
    pipeline = {
        "pipeline_format": 1,
        "steps": [
            {
                "operation": "set_events",
                "execution_mode": "review",
                "params": {"events": [[2, 0, 2]]},
            }
        ],
    }

    with pytest.raises(ValueError, match="review"):
        model_with_data.apply_pipeline(pipeline)

    assert model_with_data.pipeline_run_report[0]["status"] == "needs_review"


def test_dataset_details_include_provenance_for_derived_dataset(model_with_data):
    """Derived datasets expose provenance details outside the main info block."""
    parent_name = model_with_data.current["name"]

    model_with_data.filter(lower=1.0)

    info = model_with_data.get_info()
    details = model_with_data.get_dataset_details()

    assert "Lineage depth" not in info
    assert "Created" not in info
    assert "Data mode" not in info
    assert "Parent dataset" not in info
    assert "Derivation" not in info
    assert "Derivation parameters" not in info
    assert "Generated code" not in info
    assert details["Lineage depth"] == 1
    assert details["Created"].endswith("UTC")
    assert details["Data mode"] == "Copied from parent"
    assert details["Parent dataset"] == parent_name
    assert details["Derivation"] == "Filter"
    assert details["Derivation parameters"] == "lower=1.0"
    assert details["Generated code"] == "data.filter(1.0, None)"
    assert model_with_data.current["data_mode"] == "copied"
    datetime.fromisoformat(model_with_data.current["created_at"])


def test_dataset_details_mark_shared_pipeline_steps(model_with_data, monkeypatch):
    """Shared-data pipeline steps are marked in dataset details."""
    monkeypatch.setattr(mne.preprocessing, "ICA", DummyICA)

    model_with_data.run_ica(method="infomax", random_state=97)

    details = model_with_data.get_dataset_details()

    assert details["Data mode"] == "Shared with parent"
    assert model_with_data.current["data_mode"] == "shared"


def test_set_montage_is_shared_pipeline_step(model_with_data, tmp_path):
    """Setting a montage records a shared-data pipeline step."""
    montage = Montage(
        mne.channels.make_standard_montage("standard_1020"),
        "standard_1020",
    )

    parent_data = model_with_data.current["data"]
    model_with_data.set_montage(montage, on_missing="ignore")

    details = model_with_data.get_dataset_details()

    assert model_with_data.current["operation"] == "set_montage"
    assert model_with_data.current["data"] is parent_data
    assert model_with_data.current["data_mode"] == "shared"
    assert details["Data mode"] == "Shared with parent"
    assert details["Derivation"] == "Set Montage"
    assert "data.set_montage" in details["Generated code"]

    pipeline_path = tmp_path / "montage.mnepipe"
    model_with_data.save_pipeline(path=pipeline_path)
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    assert pipeline["steps"][-1]["operation"] == "set_montage"


def test_get_info_marks_unreplayable_branches(edf_files):
    """Unreplayable branches are flagged so UI actions stay consistent."""
    model = Model()
    for file in edf_files[:2]:
        model.load(file)

    model.index = 0
    model.append_data([1])

    info = model.get_info()

    assert info["_history_scope"] == "branch"
    assert not info["_has_replayable_steps"]
    assert not model.has_replayable_pipeline()
    with pytest.raises(ValueError, match="append_data"):
        model.save_pipeline(path="unreplayable.mnepipe")


def test_get_history_does_not_import_missing_artifact_helpers(model_with_data):
    """Generated history avoids stale imports and remains syntactically valid."""
    model_with_data.filter(lower=1.0)

    history = "\n".join(model_with_data.get_history())

    assert "detect_extreme_values" not in history
    assert "detect_kurtosis" not in history
    assert "detect_peak_to_peak" not in history
    assert "detect_with_autoreject" not in history
    compile(history, "<mnelab-history>", "exec")


def test_move_data_remaps_parent_indices():
    """Moving rows keeps lineage references pointing at the same datasets."""
    root_a = {
        "name": "root-a",
        "parent_index": None,
        "operation": None,
        "operation_params": None,
        "dtype": "raw",
    }
    child_a = {
        "name": "child-a",
        "parent_index": 0,
        "operation": "filter",
        "operation_params": {"lower": 1.0},
        "dtype": "raw",
    }
    root_b = {
        "name": "root-b",
        "parent_index": None,
        "operation": None,
        "operation_params": None,
        "dtype": "raw",
    }
    model = Model()
    model.data = [root_a, child_a, root_b]
    original_child = deepcopy(child_a)

    model.move_data(2, 0)

    assert [dataset["name"] for dataset in model.data] == [
        "root-b",
        "root-a",
        "child-a",
    ]
    assert model.index == 0
    assert model.data[2]["parent_index"] == 1
    assert model.data[2]["operation_params"] == original_child["operation_params"]
    assert [step["name"] for step in model.get_pipeline_steps(2)] == [
        "root-a",
        "child-a",
    ]
