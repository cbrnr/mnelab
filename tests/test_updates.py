# © MNELAB developers
#
# License: BSD (3-clause)

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from edfio import Edf, EdfSignal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox, QListWidget, QPushButton

from mnelab.dialogs.dataset_details import DatasetDetailsDialog
from mnelab.dialogs.history import LogDialog
from mnelab.dialogs.pipeline import ApplyPipelineDialog, load_pipeline
from mnelab.mainwindow import MainWindow
from mnelab.model import Model


@pytest.fixture
def view(qtbot):
    model = Model()
    win = MainWindow(model)
    model.view = win
    qtbot.addWidget(win)
    return win


def _urlopen_mock(tag_name):
    """Return a mock for urlopen that yields a response with the given tag_name."""
    data = json.dumps({"tag_name": tag_name}).encode()
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = data
    cm.__exit__.return_value = False
    return MagicMock(return_value=cm)


def _load_sample_edf(view, tmp_path, name="sample.edf"):
    """Load a small EDF file into the view model."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / name
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)
    view.model.load(path)
    return path


def test_check_updates_network_error(view):
    """When the network request fails, a warning dialog is shown."""
    with (
        patch("mnelab.mainwindow.urlopen", side_effect=OSError("no network")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "Could not retrieve" in text
    instance.exec.assert_called_once()


def test_check_updates_update_available(view):
    """When a newer version exists, the dialog mentions both versions."""
    with (
        patch("mnelab.mainwindow.urlopen", _urlopen_mock("v99.0.0")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
        patch("mnelab.mainwindow.__version__", "1.0.0"),
        patch("mnelab.mainwindow.IS_DEV_VERSION", False),
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "99.0.0" in text
    assert "1.0.0" in text
    instance.exec.assert_called_once()


def test_check_updates_up_to_date(view):
    """When already on the latest version, the dialog says so."""
    with (
        patch("mnelab.mainwindow.urlopen", _urlopen_mock("v1.0.0")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
        patch("mnelab.mainwindow.__version__", "1.0.0"),
        patch("mnelab.mainwindow.IS_DEV_VERSION", False),
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "latest version" in text
    instance.exec.assert_called_once()


def test_check_updates_dev_version(view):
    """When running a dev version, the dialog mentions that and the latest release."""
    with (
        patch("mnelab.mainwindow.urlopen", _urlopen_mock("v1.0.0")),
        patch("mnelab.mainwindow.QMessageBox") as MockBox,
        patch("mnelab.mainwindow.__version__", "1.1.0.dev0"),
        patch("mnelab.mainwindow.IS_DEV_VERSION", True),
    ):
        view.show_check_for_updates()

    instance = MockBox.return_value
    text = instance.setText.call_args[0][0]
    assert "development version" in text
    informative = instance.setInformativeText.call_args[0][0]
    assert "1.0.0" in informative
    instance.exec.assert_called_once()


def test_open_pipeline_editor_opens_builder(view, tmp_path):
    """The Pipeline Editor opens pre-populated with the current dataset's pipeline."""
    _load_sample_edf(view, tmp_path)

    fixed_pipeline = view.model.get_pipeline(view.model.index)
    fixed_history = view.model.get_history(view.model.index)

    with (
        patch.object(view.model, "get_pipeline", return_value=fixed_pipeline),
        patch.object(view.model, "get_history", return_value=fixed_history),
        patch("mnelab.dialogs.pipeline_builder.PipelineBuilderDialog") as MockBuilder,
    ):
        MockBuilder.return_value.exec.return_value = False

        view.open_pipeline_editor()

    MockBuilder.assert_called_once_with(view, fixed_pipeline, fixed_history)


def test_load_pipeline_validates_step_shape(tmp_path):
    """Malformed pipeline files fail before the apply flow starts."""
    path = tmp_path / "broken.mnepipe"
    path.write_text(json.dumps({"pipeline_format": 1, "steps": [{"params": {}}]}))

    with pytest.raises(ValueError, match="operation"):
        load_pipeline(path)


def test_apply_pipeline_dialog_disables_unreplayable_operations(view, qtbot):
    """The apply confirmation blocks session-dependent pipeline steps."""
    pipeline = {
        "pipeline_format": 1,
        "steps": [{"operation": "append_data", "params": {"selected_idx": [1]}}],
    }

    dialog = ApplyPipelineDialog(view, pipeline, view.model.current)
    qtbot.addWidget(dialog)
    buttonbox = dialog.findChild(QDialogButtonBox)
    step_list = dialog.findChild(QListWidget)

    assert not buttonbox.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    assert step_list.item(0).text() == "Append data"


def test_log_dialog_shows_mne_log(view, qtbot):
    """LogDialog shows the MNE log content."""
    dialog = LogDialog(view, ["INFO: Opening raw..."])
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Log"
    assert dialog.log == "INFO: Opening raw..."


def test_show_history_for_dataset_opens_pipeline_dialog(view, tmp_path):
    """show_history_for_dataset opens the Pipeline dialog with history tab."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    view.model.filter(lower=1.0)
    branch_index = view.model.index

    fixed_pipeline = view.model.get_pipeline(branch_index)
    fixed_history = view.model.get_history(branch_index)

    with (
        patch.object(view.model, "get_pipeline", return_value=fixed_pipeline),
        patch.object(view.model, "get_history", return_value=fixed_history),
        patch("mnelab.dialogs.pipeline_builder.PipelineBuilderDialog") as MockBuilder,
    ):
        MockBuilder.return_value.exec.return_value = False
        view.show_history_for_dataset(branch_index)

    MockBuilder.assert_called_once_with(view, fixed_pipeline, fixed_history)


def test_apply_pipeline_uses_progress_dialog(view, tmp_path):
    """Applying a pipeline shows and updates the progress dialog."""
    _load_sample_edf(view, tmp_path)
    pipeline = {
        "pipeline_format": 1,
        "steps": [
            {"operation": "crop", "params": {"tmin": 0.0, "tmax": 1.0}},
            {"operation": "crop", "params": {"tmin": 0.0, "tmax": 2.0}},
        ],
    }

    def apply_pipeline_side_effect(
        pipeline_dict,
        progress_callback=None,
        is_cancelled=None,
        review_callback=None,
    ):
        assert is_cancelled is not None
        assert review_callback is not None
        for index, step in enumerate(pipeline_dict["steps"], start=1):
            progress_callback(index, step)

    with (
        patch("mnelab.dialogs.pipeline.ApplyPipelineDialog") as MockApplyDialog,
        patch("mnelab.mainwindow.PipelineProgressDialog") as MockProgressDialog,
        patch.object(
            view.model,
            "apply_pipeline",
            side_effect=apply_pipeline_side_effect,
        ),
        patch("mnelab.mainwindow.QApplication.processEvents"),
    ):
        MockApplyDialog.return_value.exec.return_value = True
        MockProgressDialog.return_value.wasCanceled.return_value = False

        view._confirm_and_apply_pipeline(pipeline)

    apply_args = MockApplyDialog.call_args.args
    assert apply_args[:3] == (view, pipeline, view.model.current)
    MockProgressDialog.assert_called_once_with(view, 2)
    MockProgressDialog.return_value.show.assert_called_once()
    MockProgressDialog.return_value.update_progress.assert_any_call(
        1, pipeline["steps"][0]
    )
    MockProgressDialog.return_value.update_progress.assert_any_call(
        2, pipeline["steps"][1]
    )
    MockProgressDialog.return_value.close.assert_called_once()


def test_dataset_details_dialog_can_jump_to_parent_dataset(view, qtbot, tmp_path):
    """The details dialog can navigate back to the parent dataset."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    parent_index = view.model.index
    view.model.filter(lower=1.0)

    dialog = DatasetDetailsDialog(view, view.model.get_dataset_details())
    dialog.datasetSelected.connect(view._update_data)
    qtbot.addWidget(dialog)
    jump_button = next(
        button
        for button in dialog.findChildren(QPushButton)
        if button.toolTip() == "Jump to parent dataset"
    )

    qtbot.mouseClick(jump_button, Qt.MouseButton.LeftButton)

    assert view.model.index == parent_index


def test_show_dataset_details_signal_opens_dialog(view, tmp_path):
    """Sidebar detail requests open the dataset details dialog."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    dataset_index = view.model.index

    with patch("mnelab.mainwindow.DatasetDetailsDialog") as MockDialog:
        view.sidebar.showDetailsRequested.emit(dataset_index)

    args = MockDialog.call_args.args
    assert args[0] is view
    assert args[1] == view.model.get_dataset_details(dataset_index)
    MockDialog.return_value.datasetSelected.connect.assert_called_once_with(
        view._update_data
    )
    MockDialog.return_value.exec.assert_called_once()


def test_sidebar_history_signal_opens_pipeline_dialog(view, tmp_path):
    """Sidebar branch-history requests open the Pipeline dialog with history."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    view.model.filter(lower=1.0)
    branch_index = view.model.index

    fixed_pipeline = view.model.get_pipeline(branch_index)
    fixed_history = view.model.get_history(branch_index)

    with (
        patch.object(view.model, "get_pipeline", return_value=fixed_pipeline),
        patch.object(view.model, "get_history", return_value=fixed_history),
        patch("mnelab.dialogs.pipeline_builder.PipelineBuilderDialog") as MockBuilder,
    ):
        MockBuilder.return_value.exec.return_value = False
        view.sidebar.showHistoryRequested.emit(branch_index)

    MockBuilder.assert_called_once_with(view, fixed_pipeline, fixed_history)
    MockBuilder.return_value.exec.assert_called_once()


def test_sidebar_save_pipeline_signal_saves_branch_pipeline(view, tmp_path):
    """Sidebar branch-pipeline save requests save the targeted dataset pipeline."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    view.model.filter(lower=1.0)
    branch_index = view.model.index

    with (
        patch(
            "mnelab.mainwindow.QFileDialog.getSaveFileName",
            return_value=("branch-pipeline", "MNELAB pipeline (*.mnepipe)"),
        ),
        patch.object(view.model, "save_pipeline") as save_pipeline,
    ):
        view.sidebar.savePipelineRequested.emit(branch_index)

    save_pipeline.assert_called_once_with(
        idx=branch_index, path="branch-pipeline.mnepipe"
    )


def test_save_pipeline_is_disabled_for_unreplayable_branches(view, tmp_path):
    """Global and branch save paths reject branches that cannot replay."""
    fs = 256
    signal = np.zeros(30 * fs)
    first = tmp_path / "first.edf"
    second = tmp_path / "second.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(first)
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(second)

    view.model.load(first)
    view.model.load(second)
    view.model.index = 0
    view.model.append_data([1])
    branch_index = view.model.index
    assert not view.model.has_replayable_pipeline(branch_index)
    view.data_changed()
    with (
        patch("mnelab.mainwindow.QMessageBox.information") as information,
        patch("mnelab.mainwindow.QFileDialog.getSaveFileName") as get_save_name,
    ):
        view.save_pipeline_for_dataset(branch_index)

    information.assert_called_once()
    get_save_name.assert_not_called()


def test_sidebar_export_history_signal_exports_branch_history(view, tmp_path):
    """Sidebar branch-history export requests write the targeted dataset history."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    view.model.filter(lower=1.0)
    branch_index = view.model.index
    export_path = tmp_path / "branch-history"

    with patch(
        "mnelab.mainwindow.QFileDialog.getSaveFileName",
        return_value=(str(export_path), "Python Files (*.py)"),
    ):
        view.sidebar.exportHistoryRequested.emit(branch_index)

    saved = (tmp_path / "branch-history.py").read_text(encoding="utf-8")
    assert "data.filter(1.0, None)" in saved


def test_sidebar_context_menu_hides_pipeline_actions_for_root(view, tmp_path):
    """Roots without replayable steps show Apply but not Save pipeline."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    root_index = view.model.index
    root_menu, root_actions = view.sidebar._create_context_menu(root_index)

    root_labels = [
        action.text() for action in root_menu.actions() if not action.isSeparator()
    ]
    assert root_labels == [
        "Dataset details...",
        "Show dataset history...",
        "Export dataset history...",
        "Apply pipeline...",
    ]
    assert "Save pipeline..." not in root_labels
    assert "save_pipeline" not in root_actions
    assert "apply_pipeline" in root_actions
    assert root_actions["show_details"].isEnabled()
    assert root_actions["export_history"].isEnabled()

    view.model.filter(lower=1.0)
    branch_index = view.model.index
    assert not view.sidebar.topLevelItem(0).child(0).text(0).startswith("1.")
    branch_menu, branch_actions = view.sidebar._create_context_menu(branch_index)

    branch_labels = [
        action.text() for action in branch_menu.actions() if not action.isSeparator()
    ]
    assert branch_labels == [
        "Dataset details...",
        "Show branch history...",
        "Export branch history...",
        "Apply pipeline...",
        "Save pipeline...",
    ]
    assert any(action.isSeparator() for action in branch_menu.actions())
    assert branch_actions["save_pipeline"].isEnabled()
