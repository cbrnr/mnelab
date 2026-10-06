# © MNELAB developers
#
# License: BSD (3-clause)

"""Tests for building and applying processing pipelines."""

import json
from collections import defaultdict
from copy import deepcopy

import mne
import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QWidget

import mnelab.widgets.sidebar as sidebar_module
from mnelab.dialogs.pipeline import FileRuleDialog, PipelineDialog
from mnelab.mainwindow import MainWindow
from mnelab.model import Model
from mnelab.pipeline import load_pipeline, make_file_spec, save_pipeline, step_label
from mnelab.settings import _DEFAULTS
from mnelab.utils import Montage, count_locations


@pytest.fixture
def model_with_raw():
    info = mne.create_info(["EEG 001"], sfreq=200, ch_types="eeg")
    signal = np.sin(np.arange(1200) / 10)[np.newaxis, :]
    raw = mne.io.RawArray(signal, info)
    model = Model()
    model.insert_data(
        defaultdict(
            lambda: None,
            name="Example",
            fname=None,
            ftype=None,
            data=raw,
            dtype="raw",
            events=np.empty((0, 3), dtype=int),
            _cache_path=None,
        )
    )
    return model


def test_apply_pipeline_creates_child_after_all_steps(model_with_raw):
    model = model_with_raw
    source = model.current
    source_data = source["data"].get_data().copy()
    steps = [
        {"op": "resample", "params": {"sfreq": 100}},
        {"op": "crop", "params": {"start": None, "stop": 2}},
    ]

    model.apply_pipeline(steps)

    assert len(model) == 2
    assert model.current["parent_id"] == source["id"]
    assert model.current["data"].info["sfreq"] == 100
    assert model.current["data"].n_times == 201
    assert source["data"].info["sfreq"] == 200
    np.testing.assert_array_equal(source["data"].get_data(), source_data)
    assert model.history[-4:] == [
        "datasets.insert(1, deepcopy(data))",
        "data = datasets[1]",
        "data.resample(100)",
        "data.crop(0, 2)",
    ]


def test_apply_pipeline_failure_leaves_source_untouched(model_with_raw):
    model = model_with_raw
    history = model.history.copy()
    source_data = model.current["data"].get_data().copy()
    steps = [
        {"op": "resample", "params": {"sfreq": 100}},
        {"op": "crop", "params": {"start": 8, "stop": None}},
    ]

    with pytest.raises(ValueError, match="Step 2 failed"):
        model.apply_pipeline(steps)

    assert len(model) == 1
    assert model.history == history
    assert model.current["data"].info["sfreq"] == 200
    np.testing.assert_array_equal(model.current["data"].get_data(), source_data)


def test_pipeline_filters_and_removes_line_noise(model_with_raw):
    model = model_with_raw
    source_data = model.current["data"].get_data().copy()
    model.apply_pipeline(
        [
            {
                "op": "filter",
                "params": {"lower": None, "upper": 40, "notch": None},
            },
            {
                "op": "remove_line_noise",
                "params": {"line_freq": 50, "include_harmonics": False},
            },
        ]
    )
    assert model.current["data"].get_data().shape == source_data.shape
    assert not np.array_equal(model.current["data"].get_data(), source_data)
    np.testing.assert_array_equal(model.data[0]["data"].get_data(), source_data)


def test_pipeline_file_round_trip_and_validation(tmp_path):
    path = tmp_path / "pipeline.json"
    steps = [
        {"op": "filter", "params": {"lower": 1, "upper": 30, "notch": None}},
        {"op": "resample", "params": {"sfreq": 100}},
    ]
    save_pipeline(path, steps)
    assert json.loads(path.read_text())["version"] == 1
    assert load_pipeline(path) == steps
    path.write_text(json.dumps({"version": 1, "steps": [{"op": "unknown"}]}))
    with pytest.raises(ValueError, match="pipeline step"):
        load_pipeline(path)

    path.write_text(json.dumps({"version": 2, "steps": steps}))
    with pytest.raises(ValueError, match="Unsupported pipeline file version"):
        load_pipeline(path)


def test_pipeline_dialog_edits_order(qtbot):
    steps = [
        {"op": "resample", "params": {"sfreq": 100}},
        {"op": "crop", "params": {"start": 0, "stop": 2}},
    ]
    dialog = PipelineDialog(None, steps)
    qtbot.addWidget(dialog)
    dialog.list.setCurrentRow(1)
    qtbot.mouseClick(dialog.up_button, Qt.LeftButton)
    assert dialog.steps[0]["op"] == "crop"
    assert steps[0]["op"] == "resample"
    qtbot.mouseClick(dialog.remove_button, Qt.LeftButton)
    assert len(dialog.steps) == 1

    assert dialog.save_button.isEnabled()


def test_file_imports_use_target_files_and_preserve_rules(tmp_path):
    info = mne.create_info(["EEG001", "EEG002"], 200, "eeg")
    raw = mne.io.RawArray(np.zeros((2, 1200)), info)
    model = Model()
    model.insert_data(
        defaultdict(
            lambda: None,
            name="s01",
            fname=None,
            source_fname=str(tmp_path / "s01.fif"),
            data=raw,
            dtype="raw",
            events=np.empty((0, 3), dtype=int),
            pipeline_steps=[],
            _cache_path=None,
        )
    )
    target = deepcopy(model.current)
    target["name"] = "s02"
    target["source_fname"] = str(tmp_path / "s02.fif")
    (tmp_path / "s01-bad_channels.csv").write_text("EEG001")
    (tmp_path / "s02-bad_channels.csv").write_text("EEG002")
    (tmp_path / "s01-events.csv").write_text("pos,type\n200,1\n")
    (tmp_path / "s02-events.csv").write_text("pos,type\n300,2\n")
    (tmp_path / "s01-annotations.csv").write_text(
        "type,onset,duration\nkeep,200,20\ndrop,400,20\n"
    )
    (tmp_path / "s02-annotations.csv").write_text(
        "type,onset,duration\nkeep,300,40\ndrop,500,20\n"
    )

    model.import_bads(str(tmp_path / "s01-bad_channels.csv"))
    model.import_events(str(tmp_path / "s01-events.csv"))
    model.import_annotations(
        str(tmp_path / "s01-annotations.csv"), types=["keep"], unit="samples"
    )
    steps = deepcopy(model.current["pipeline_steps"])
    assert [step["params"]["file"]["mode"] for step in steps] == ["matching"] * 3
    path = tmp_path / "imports.json"
    save_pipeline(path, steps)
    model.insert_data(target)
    model.duplicate_data()
    assert model.current["fname"] is None
    assert model.current["source_fname"] == str(tmp_path / "s02.fif")
    model.apply_pipeline(load_pipeline(path))

    assert model.current["data"].info["bads"] == ["EEG002"]
    assert model.current["events"][0, 2] == 2
    assert model.current["data"].annotations.description.tolist() == ["keep"]
    assert model.current["data"].annotations.onset[0] == 1.5
    assert model.current["pipeline_steps"] == steps

    model.index -= 1
    (tmp_path / "s02-events.csv").unlink()
    before = len(model)
    with pytest.raises(ValueError, match="Step 2 failed: Matching file not found"):
        model.apply_pipeline(steps)
    assert len(model) == before


def test_fixed_imports_embed_contents_and_replay_without_files(tmp_path):
    info = mne.create_info(["EEG001", "EEG002"], 200, "eeg")
    raw = mne.io.RawArray(np.zeros((2, 1200)), info)
    model = Model()
    model.insert_data(
        defaultdict(
            lambda: None,
            name="s01",
            source_fname=str(tmp_path / "s01.fif"),
            data=raw,
            dtype="raw",
            events=np.empty((0, 3), dtype=int),
            pipeline_steps=[],
        )
    )
    target = deepcopy(model.current)
    target["name"] = "s02"
    target["source_fname"] = str(tmp_path / "s02.fif")
    target["data"].resample(100)
    target["events"] = np.array([[100, 0, 9]])
    files = [
        tmp_path / "shared-bads.csv",
        tmp_path / "shared-events.csv",
        tmp_path / "shared-annotations.csv",
    ]
    files[0].write_text("EEG002")
    files[1].write_text("pos,type\n200,1\n")
    files[2].write_text("type,onset,duration\nkeep,200,20\ndrop,400,20\n")

    model.import_bads(str(files[0]))
    model.import_events(str(files[1]))
    model.import_annotations(str(files[2]), types=["keep"], unit="samples")
    steps = deepcopy(model.current["pipeline_steps"])
    assert [step["params"]["file"]["mode"] for step in steps] == ["embedded"] * 3
    assert steps[0]["params"]["file"]["data"] == ["EEG002"]
    assert steps[1]["params"]["file"]["data"] == {
        "events": [[200, 0, 1]],
        "merge": True,
    }
    assert steps[2]["params"]["file"]["data"] == [["keep", 200.0, 20.0]]
    path = tmp_path / "fixed-imports.json"
    save_pipeline(path, steps)
    for file in files:
        file.unlink()

    model.insert_data(target)
    model.apply_pipeline(load_pipeline(path))

    assert model.current["data"].info["bads"] == ["EEG002"]
    np.testing.assert_array_equal(
        model.current["events"], np.array([[100, 0, 9], [200, 0, 1]])
    )
    assert model.current["data"].annotations.description.tolist() == ["keep"]
    assert model.current["data"].annotations.onset[0] == 2
    assert model.current["data"].annotations.duration[0] == pytest.approx(0.2)
    assert model.current["pipeline_steps"] == steps


def test_file_rule_dialog_previews_target_path(tmp_path, qtbot):
    spec = make_file_spec(tmp_path / "s01-bad_channels.csv", tmp_path / "s01.fif")
    dialog = FileRuleDialog(None, spec, str(tmp_path / "s02.fif"))
    qtbot.addWidget(dialog)
    assert "s02-bad_channels.csv" in dialog.preview.text()
    assert dialog.ok_button.isEnabled()


def test_file_rule_dialog_embeds_selected_file(
    model_with_raw, tmp_path, qtbot, monkeypatch
):
    model = model_with_raw
    mne.rename_channels(model.current["data"].info, {"EEG 001": "EEG001"})
    model.current["source_fname"] = str(tmp_path / "s01.fif")
    source = tmp_path / "s01-bads.csv"
    source.write_text("EEG 001")
    fixed = tmp_path / "shared-bads.csv"
    fixed.write_text("EEG 001")
    model.import_bads(str(source))
    parent = QWidget()
    parent.model = model
    dialog = PipelineDialog(parent, model.current["pipeline_steps"])
    qtbot.addWidget(parent)
    qtbot.addWidget(dialog)
    dialog.list.setCurrentRow(0)

    def select_fixed(file_dialog):
        file_dialog.fixed_radio.setChecked(True)
        file_dialog.fixed_path.setText(str(fixed))
        assert file_dialog.ok_button.isEnabled()
        return 1

    monkeypatch.setattr(FileRuleDialog, "exec", select_fixed)
    dialog._edit_file_rule()

    assert dialog.steps[0]["params"]["file"] == {
        "mode": "embedded",
        "data": ["EEG001"],
    }


def test_unsupported_operation_is_visible_but_cannot_be_applied(model_with_raw, qtbot):
    model_with_raw.set_annotations([0.5], [0.2], ["bad"])
    steps = model_with_raw.current["pipeline_steps"]
    assert steps == [{"op": "set_annotations", "unsupported": True}]
    dialog = PipelineDialog(None, steps)
    qtbot.addWidget(dialog)
    assert not dialog.save_button.isEnabled()
    with pytest.raises(ValueError, match="cannot be replayed"):
        model_with_raw.apply_pipeline(steps)
    assert len(model_with_raw) == 1


def test_recorded_steps_follow_dataset_branch(model_with_raw):
    model = model_with_raw
    model.resample(100)
    root = model.current
    assert root["pipeline_steps"] == [{"op": "resample", "params": {"sfreq": 100}}]
    model.duplicate_data()
    model.crop(0, 2)
    assert [step["op"] for step in model.current["pipeline_steps"]] == [
        "resample",
        "crop",
    ]
    assert len(root["pipeline_steps"]) == 1


def test_additional_actions_are_recorded_and_replayed(model_with_raw):
    model = model_with_raw
    model.pick_channels(["EEG 001"])
    model.set_channel_properties(["EEG 001"], None, None)
    steps = model.current["pipeline_steps"]
    assert [step["op"] for step in steps] == [
        "pick_channels",
        "set_channel_properties",
    ]
    model.apply_pipeline(steps)
    assert model.current["data"].ch_names == ["EEG 001"]
    assert model.current["data"].info["bads"] == ["EEG 001"]


def test_event_and_epoch_steps_replay(model_with_raw, tmp_path):
    model = model_with_raw
    raw = model.current["data"]
    raw.add_channels(
        [
            mne.io.RawArray(
                np.zeros((1, raw.n_times)),
                mne.create_info(["STI 014"], 200, "stim"),
            )
        ]
    )
    raw._data[1, [200, 400]] = 1
    model.duplicate_data()
    model.find_events("STI 014")
    model.epoch_data([1], -0.1, 0.2, (None, 0))
    model.drop_bad_epochs({"eeg": 1e6}, None)
    steps = deepcopy(model.current["pipeline_steps"])
    assert [step["op"] for step in steps] == [
        "find_events",
        "epoch_data",
        "drop_bad_epochs",
    ]
    assert steps[1]["params"]["baseline"] == [None, 0]
    path = tmp_path / "events-and-epochs.json"
    save_pipeline(path, steps)

    model.index = 0
    model.apply_pipeline(load_pipeline(path))
    assert model.current["dtype"] == "epochs"
    assert len(model.current["data"]) == 2


def test_builtin_montage_is_recorded_saved_and_replayed(model_with_raw, tmp_path):
    model = model_with_raw
    mne.rename_channels(model.current["data"].info, {"EEG 001": "Cz"})
    model.duplicate_data()
    montage = Montage(
        mne.channels.make_standard_montage("colin27_1020"), "colin27_1020"
    )
    model.set_montage(montage, on_missing="ignore")
    steps = deepcopy(model.current["pipeline_steps"])
    assert steps[0]["op"] == "set_montage"
    assert steps[0]["params"]["montage_name"] == "colin27_1020"
    assert steps[0]["params"]["montage_positions"] is None
    path = tmp_path / "montage.json"
    save_pipeline(path, steps)

    model.index = 0
    model.apply_pipeline(load_pipeline(path))
    assert model.current["montage"].name == "colin27_1020"
    assert not model.current["montage"].embedded
    assert count_locations(model.current["data"].info) > 0


def test_custom_file_montage_and_clearing_replay(model_with_raw, tmp_path):
    model = model_with_raw
    mne.rename_channels(model.current["data"].info, {"EEG 001": "Cz"})
    path = tmp_path / "custom.sfp"
    path.write_text(
        "Cz 0.0 0.0 0.1\nPz 0.0 -0.1 0.0\n"
        "FidNz 0.0 0.1 0.0\nFidT9 -0.1 0.0 0.0\nFidT10 0.1 0.0 0.0\n"
    )
    montage = Montage(mne.channels.read_custom_montage(path), path.name, path)
    model.duplicate_data()
    model.set_montage(montage)
    model.set_montage(None)
    steps = deepcopy(model.current["pipeline_steps"])
    assert "Cz" in steps[0]["params"]["montage_positions"]["ch_pos"]
    assert steps[1]["params"]["montage_name"] is None
    saved = tmp_path / "custom-pipeline.json"
    save_pipeline(saved, steps)
    path.unlink()

    model.index = 0
    model.apply_pipeline(load_pipeline(saved)[:1])
    assert not model.current["montage"].embedded
    assert "make_dig_montage" in model.history[-2]

    model.index = 0
    model.apply_pipeline(load_pipeline(saved))
    assert model.current["montage"] is None
    assert model.current["data"].get_montage() is None


def test_matching_custom_montage_uses_target_file(
    model_with_raw, tmp_path, qtbot, monkeypatch
):
    model = model_with_raw
    mne.rename_channels(model.current["data"].info, {"EEG 001": "Cz"})
    source_fname = tmp_path / "s01-raw.fif"
    model.current["source_fname"] = str(source_fname)
    target = deepcopy(model.current)
    target["source_fname"] = str(tmp_path / "s02-raw.fif")
    for subject, height in (("s01", 0.1), ("s02", 0.2)):
        (tmp_path / f"{subject}-montage.sfp").write_text(
            f"Cz 0.0 0.0 {height}\nPz 0.0 -0.1 0.0\n"
            "FidNz 0.0 0.1 0.0\nFidT9 -0.1 0.0 0.0\nFidT10 0.1 0.0 0.0\n"
        )
    path = tmp_path / "s01-montage.sfp"
    model.set_montage(Montage(mne.channels.read_custom_montage(path), path.name, path))
    parent = QWidget()
    parent.model = model
    dialog = PipelineDialog(parent, model.current["pipeline_steps"])
    qtbot.addWidget(parent)
    qtbot.addWidget(dialog)
    dialog.list.setCurrentRow(0)
    assert dialog.file_rule_button.isEnabled()

    def select_matching(dialog):
        dialog.matching_radio.setChecked(True)
        return 1

    monkeypatch.setattr(FileRuleDialog, "exec", select_matching)
    dialog._edit_file_rule()
    steps = deepcopy(dialog.steps)
    assert steps[0]["params"]["montage_positions"]["file"]["mode"] == "matching"
    saved = tmp_path / "matching-montage.json"
    save_pipeline(saved, steps)
    model.insert_data(target)
    model.apply_pipeline(load_pipeline(saved))

    assert model.current["montage"].path.name == "s02-montage.sfp"
    assert not np.allclose(
        model.current["data"].info["chs"][0]["loc"][:3],
        model.data[0]["data"].info["chs"][0]["loc"][:3],
    )
    assert model.current["pipeline_steps"] == steps


def test_matching_ica_import_can_be_applied(model_with_raw, tmp_path, monkeypatch):
    model = model_with_raw
    model.current["source_fname"] = str(tmp_path / "s01.fif")
    target = deepcopy(model.current)
    target["source_fname"] = str(tmp_path / "s02.fif")
    for subject in ("s01", "s02"):
        (tmp_path / f"{subject}-ica.fif").touch()
    loaded = []

    class FakeICA:
        def __init__(self):
            self.exclude = [0]

        def apply(self, data):
            data._data += 1

    def read_ica(path):
        loaded.append(str(path))
        return FakeICA()

    monkeypatch.setattr(mne.preprocessing, "read_ica", read_ica)
    model.import_ica(str(tmp_path / "s01-ica.fif"))
    model.apply_ica()
    steps = deepcopy(model.current["pipeline_steps"])
    assert [step["op"] for step in steps] == ["import_ica", "apply_ica"]
    model.insert_data(target)
    model.apply_pipeline(steps)

    assert loaded[-1] == str(tmp_path / "s02-ica.fif")
    np.testing.assert_allclose(
        model.current["data"].get_data(), target["data"].get_data() + 1
    )
    assert model.current["pipeline_steps"] == steps


def test_ica_worker_is_owned_by_model(model_with_raw, monkeypatch):
    notifications = []
    pools = []

    class FakeICA:
        def __init__(self, n_components, method, fit_params):
            self.settings = (n_components, method, fit_params)
            self.exclude = []

        def fit(self, data, reject_by_annotation):
            self.data = data
            self.reject_by_annotation = reject_by_annotation
            return self

    class FakeResult:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    class FakePool:
        def __init__(self, processes):
            assert processes == 1
            self.closed = False
            self.terminated = False
            self.joined = False
            pools.append(self)

        def apply_async(self, func, args, callback, error_callback):
            value = func(*args)
            callback(value)
            return FakeResult(value)

        def close(self):
            self.closed = True

        def terminate(self):
            self.terminated = True

        def join(self):
            self.joined = True

    monkeypatch.setattr(mne.preprocessing, "ICA", FakeICA)
    monkeypatch.setattr("mnelab.model.mp.Pool", FakePool)
    model = model_with_raw
    job = model.start_ica(2, "infomax", {"extended": True}, True, notifications.append)
    assert model.current["ica"] is None
    assert len(notifications) == 1
    assert pools[0].closed

    model.finish_ica(job)
    assert model.current["ica"].settings == (2, "infomax", {"extended": True})
    assert model.current["ica"].data is model.current["data"]
    assert model.current["ica"].reject_by_annotation
    assert model.current["pipeline_steps"] == [{"op": "run_ica", "unsupported": True}]
    assert step_label(model.current["pipeline_steps"][0]) == "Run ICA (cannot replay)"
    assert pools[0].joined

    job = model.start_ica(2, "infomax", {}, True, notifications.append)
    job.cancel()
    assert pools[1].terminated and pools[1].joined
    assert len(model.current["pipeline_steps"]) == 1


def test_embedded_montage_uses_target_dataset(model_with_raw, tmp_path):
    model = model_with_raw
    mne.rename_channels(model.current["data"].info, {"EEG 001": "Cz"})
    model.duplicate_data()
    source_montage = Montage(
        mne.channels.make_standard_montage("colin27_1020"),
        "Source",
        embedded=True,
    )
    model.set_montage(source_montage)
    source_location = model.current["data"].info["chs"][0]["loc"][:3].copy()
    steps = deepcopy(model.current["pipeline_steps"])
    assert steps[0]["params"]["montage_positions"] == "embedded"
    path = tmp_path / "embedded-pipeline.json"
    save_pipeline(path, steps)

    model.index = 0
    with pytest.raises(ValueError, match="Target dataset has no embedded montage"):
        model.apply_pipeline(load_pipeline(path))
    assert len(model) == 2

    target_montage = Montage(
        mne.channels.make_standard_montage("biosemi64"),
        "Target",
        embedded=True,
    )
    model.current["data"].set_montage(target_montage.montage)
    model.current["montage"] = target_montage
    target_location = model.current["data"].info["chs"][0]["loc"][:3].copy()
    assert not np.allclose(source_location, target_location)

    model.apply_pipeline(load_pipeline(path))
    assert model.current["montage"].name == "Target"
    np.testing.assert_allclose(
        model.current["data"].info["chs"][0]["loc"][:3], target_location
    )
    assert any("make_dig_montage" in entry for entry in model.history)


def test_incompatible_montage_does_not_change_target(model_with_raw):
    model = model_with_raw
    model.duplicate_data()
    mne.rename_channels(model.current["data"].info, {"EEG 001": "Cz"})
    montage = Montage(
        mne.channels.make_standard_montage("colin27_1020"), "colin27_1020"
    )
    model.set_montage(montage, on_missing="ignore")
    steps = deepcopy(model.current["pipeline_steps"])
    model.index = 0
    before = len(model)

    with pytest.raises(ValueError, match="No channel locations match"):
        model.apply_pipeline(steps)

    assert len(model) == before
    assert model.current["data"].get_montage() is None


def test_mainwindow_can_apply_current_pipeline(model_with_raw, qtbot):
    model = model_with_raw
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)
    view.data_changed()
    view._apply_toolbar(_DEFAULTS["toolbar_actions"])
    assert view.all_actions["pipeline"] in view.toolbar.actions()
    assert not view.all_actions["pipeline"].icon().isNull()
    assert not view.all_actions["apply_pipeline"].isEnabled()
    assert not view.all_actions["create_pipeline"].isEnabled()

    model.resample(100)
    assert view.all_actions["create_pipeline"].isEnabled()

    view.pipeline = [{"op": "resample", "params": {"sfreq": 50}}]
    view.data_changed()
    view.all_actions["apply_pipeline"].trigger()

    assert len(model) == 2
    assert model.current["data"].info["sfreq"] == 50


def test_sidebar_dataset_can_fill_pipeline(model_with_raw, qtbot, monkeypatch):
    model = model_with_raw
    model.resample(100)
    root = model.current
    model.duplicate_data()
    model.crop(0, 2)
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)
    view.data_changed()
    monkeypatch.setattr(PipelineDialog, "exec", lambda self: self.accept() or 1)

    view.create_pipeline_for(root["id"])

    assert view.pipeline == root["pipeline_steps"]
    assert len(view.pipeline) == 1
    assert len(model) == 2

    class Menu:
        def __init__(self, parent):
            self.callback = None

        def addAction(self, label, callback):
            self.callback = callback
            return self

        def setEnabled(self, enabled):
            assert enabled

        def exec(self, pos):
            self.callback()

    view.pipeline = []
    monkeypatch.setattr(sidebar_module, "QMenu", Menu)
    monkeypatch.setattr(
        view.sidebar, "itemAt", lambda pos: view.sidebar.topLevelItem(0)
    )
    view.sidebar._show_context_menu(QPoint())
    assert view.pipeline == root["pipeline_steps"]


def test_file_rule_identifier_stops_at_separator(tmp_path):
    """A shared character after the identifier does not prevent matching."""
    spec = make_file_spec(tmp_path / "sub-01_events.csv", tmp_path / "sub-01_eeg.fif")

    assert spec == {
        "mode": "matching",
        "data_pattern": "{id}_eeg.fif",
        "file_pattern": "{id}_events.csv",
    }


def test_crop_to_end_replays_on_shorter_data(model_with_raw):
    model = model_with_raw
    model.current["data"].crop(0, 3)

    model.apply_pipeline([{"op": "crop", "params": {"start": 1, "stop": None}}])

    np.testing.assert_allclose(model.current["data"].times[-1], 2)


def test_iclabels_do_not_add_pipeline_steps(model_with_raw):
    model = model_with_raw
    model.current["pipeline_steps"] = []
    model.current["iclabel"] = np.zeros((1, 7))

    model.get_iclabels()

    assert model.current["pipeline_steps"] == []


def test_replayed_embedded_imports_record_history(model_with_raw):
    model = model_with_raw
    expected = deepcopy(model.current["data"])
    model.apply_pipeline(
        [
            {
                "op": "import_bads",
                "params": {"file": {"mode": "embedded", "data": ["EEG 001"]}},
            },
            {
                "op": "import_annotations",
                "params": {
                    "file": {"mode": "embedded", "data": [["A", 1.0, 0.5]]},
                    "types": None,
                    "description": None,
                    "unit": "seconds",
                },
            },
        ]
    )

    exec("\n".join(model.history[-2:]), {"data": expected, "mne": mne})  # noqa: S102

    assert expected.info["bads"] == ["EEG 001"]
    assert expected.annotations.description.tolist() == ["A"]
    np.testing.assert_allclose(expected.annotations.onset, [1.0])
