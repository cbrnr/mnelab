# © MNELAB developers
#
# License: BSD (3-clause)

import mne
import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

import mnelab.mainwindow as mainwindow_module
from mnelab.dialogs.calc import CalcDialog
from mnelab.dialogs.channel_properties import ChannelPropertiesDialog
from mnelab.dialogs.crop import CropDialog
from mnelab.dialogs.find_events import FindEventsDialog
from mnelab.mainwindow import MainWindow
from mnelab.model import Model
from mnelab.settings import read_settings


def test_initial_actions(qtbot):
    """Test if initial actions are correctly enabled/disabled."""
    model = Model()
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)

    for name, action in view.all_actions.items():
        if name in view.always_enabled:
            assert action.isEnabled()
        else:
            assert not action.isEnabled()


@pytest.fixture
def loaded_view(tmp_path, qtbot):
    """Create a file-backed data set with a stim channel."""
    path = tmp_path / "sample.fif"
    path.touch()
    info = mne.create_info(["STI 014"], 100, ch_types="stim")
    signal = np.zeros((1, 100))
    signal[0, 10:20] = 1
    model = Model()
    model.load_data(mne.io.RawArray(signal, info), path)
    view = MainWindow(model)
    model.view = view
    qtbot.addWidget(view)
    return model, view


def test_channel_properties_preserve_file_backed_data(loaded_view, monkeypatch):
    """Channel edits create a child and leave the loaded data unchanged."""
    model, view = loaded_view
    root = model.current

    def rename_and_accept(dialog):
        dialog.model.item(0, 1).setText("Trigger")
        return True

    monkeypatch.setattr(ChannelPropertiesDialog, "exec", rename_and_accept)
    view.channel_properties()

    assert len(model) == 2
    assert model.current["parent_id"] == root["id"]
    model.reload_dataset(0)
    assert root["data"].ch_names == ["STI 014"]
    assert model.current["data"].ch_names == ["Trigger"]


def test_unchanged_channel_properties_do_not_duplicate(loaded_view, monkeypatch):
    """Accepting the unchanged dialog leaves the data set list alone."""
    model, view = loaded_view
    monkeypatch.setattr(ChannelPropertiesDialog, "exec", lambda dialog: True)

    view.channel_properties()

    assert len(model) == 1


def test_find_events_preserves_file_backed_data(loaded_view, monkeypatch):
    """Detected events belong only to the derived data set."""
    model, view = loaded_view
    root = model.current
    monkeypatch.setattr(FindEventsDialog, "exec", lambda dialog: True)

    view.find_events()

    assert len(model) == 2
    assert model.current["parent_id"] == root["id"]
    assert root["events"].size == 0
    model.reload_dataset(0)
    assert root["data"].events.size == 0
    np.testing.assert_array_equal(model.current["events"], [[10, 0, 1]])


def test_failed_import_discards_child(loaded_view, monkeypatch, tmp_path):
    """An invalid metadata import does not leave an empty derived data set."""
    model, view = loaded_view
    path = tmp_path / "bads.csv"
    path.write_text("UNKNOWN")
    history = model.history.copy()
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(path), "*.csv")
    )
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)

    view.import_file(model.import_bads, "Import bad channels", "*.csv")

    assert len(model) == 1
    assert model.current["data"].info["bads"] == []
    assert model.history == history


def _fail_bads_import(view, monkeypatch, tmp_path):
    """Import an invalid bad channels file through the main window."""
    path = tmp_path / "bads.csv"
    path.write_text("UNKNOWN")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *args: (str(path), "*.csv")
    )
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
    view.import_file(view.model.import_bads, "Import bad channels", "*.csv")


def test_failed_import_selects_parent(loaded_view, monkeypatch, tmp_path):
    """A discarded child does not leave the following data set selected."""
    model, view = loaded_view
    other = tmp_path / "other.fif"
    other.touch()
    info = mne.create_info(["EEG 001"], 100, ch_types="eeg")
    model.load_data(mne.io.RawArray(np.zeros((1, 100)), info), other)
    model.index = 0
    root = model.current

    _fail_bads_import(view, monkeypatch, tmp_path)

    assert len(model) == 2
    assert model.current is root


def test_failed_import_reloads_evicted_parent(loaded_view, monkeypatch, tmp_path):
    """With memory saving, the reselected parent is loaded again."""
    model, view = loaded_view
    monkeypatch.setattr(
        mainwindow_module,
        "read_settings",
        lambda key: True if key == "memory_saving" else read_settings(key),
    )

    _fail_bads_import(view, monkeypatch, tmp_path)

    assert len(model) == 1
    assert model.current["data"] is not None
    model.cleanup()


def test_crop_from_start_records_open_end(loaded_view, monkeypatch):
    """Keeping the default stop time crops until the end of any data set."""
    model, view = loaded_view

    def crop_start(dialog):
        dialog._start.setValue(0.5)
        return True

    monkeypatch.setattr(CropDialog, "exec", crop_start)
    view.crop()

    assert len(model) == 2
    assert model.current["pipeline_steps"][-1] == {
        "op": "crop",
        "params": {"start": 0.5, "stop": None},
    }


def test_failed_ica_does_not_create_data_set(loaded_view, monkeypatch):
    """An ICA fitting error is reported without adding a data set."""
    model, view = loaded_view
    errors = []

    class FailedJob:
        def get(self):
            raise ValueError("ICA failed")

    class Message:
        def __init__(self, parent, title, text, details):
            errors.append(text)

        def show(self):
            pass

    monkeypatch.setattr(mainwindow_module.RunICADialog, "exec", lambda dialog: True)
    monkeypatch.setattr(CalcDialog, "exec", lambda dialog: True)
    monkeypatch.setattr(model, "start_ica", lambda *args: FailedJob())
    monkeypatch.setattr(mainwindow_module, "ErrorMessageBox", Message)

    view.run_ica()

    assert len(model) == 1
    assert errors == ["ICA failed"]
