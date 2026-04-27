# © MNELAB developers
#
# License: BSD (3-clause)

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from edfio import Edf, EdfSignal
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialogButtonBox, QToolButton

from mnelab.dialogs.history import HistoryDialog
from mnelab.dialogs.pipeline import ApplyPipelineDialog, load_pipeline
from mnelab.mainwindow import MainWindow
from mnelab.model import Model
from mnelab.widgets.infowidget import InfoWidget


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


def test_edit_pipeline_uses_apply_confirmation(view, tmp_path):
    """Edited pipelines go through the same apply confirmation dialog."""
    _load_sample_edf(view, tmp_path)
    original_pipeline = {
        "pipeline_format": 1,
        "steps": [{"operation": "crop", "params": {"tmin": 0.0, "tmax": 1.0}}],
    }
    edited_pipeline = {
        "pipeline_format": 1,
        "steps": [{"operation": "crop", "params": {"tmin": 0.0, "tmax": 2.0}}],
    }

    with (
        patch(
            "mnelab.mainwindow.QFileDialog.getOpenFileName",
            return_value=("pipeline.mnepipe", "MNELAB pipeline (*.mnepipe)"),
        ),
        patch("mnelab.dialogs.pipeline.load_pipeline", return_value=original_pipeline),
        patch("mnelab.dialogs.pipeline_builder.PipelineBuilderDialog") as MockBuilder,
        patch("mnelab.dialogs.pipeline.ApplyPipelineDialog") as MockApplyDialog,
        patch("mnelab.mainwindow.PipelineProgressDialog") as MockProgressDialog,
        patch.object(view.model, "apply_pipeline") as apply_pipeline,
        patch("mnelab.mainwindow.QApplication.processEvents"),
    ):
        MockBuilder.return_value.exec.return_value = True
        MockBuilder.return_value.get_pipeline.return_value = edited_pipeline
        MockApplyDialog.return_value.exec.return_value = True
        MockApplyDialog.return_value.selected_dataset_indices.return_value = [
            view.model.index
        ]
        MockProgressDialog.return_value.wasCanceled.return_value = False

        view.edit_pipeline()

    MockBuilder.assert_called_once_with(view, original_pipeline)
    apply_args = MockApplyDialog.call_args.args
    assert apply_args[:3] == (view, edited_pipeline, view.model.current)
    args, kwargs = apply_pipeline.call_args
    assert args == (edited_pipeline,)
    assert "progress_callback" in kwargs
    assert "is_cancelled" in kwargs
    assert "review_callback" in kwargs


def test_history_dialog_creates_pipeline_from_selected_steps(view, qtbot):
    """History can seed the Pipeline Builder from selected pipeline steps."""
    pipeline = {
        "pipeline_format": 1,
        "created": "2026-04-27T12:00:00+00:00",
        "hints": {"dtype": "raw"},
        "steps": [
            {"operation": "filter", "name": "Filter", "params": {"l_freq": 1.0}},
            {"operation": "crop", "name": "Crop", "params": {"tmin": 0.0, "tmax": 2.0}},
        ],
    }
    selected_pipeline = {
        "pipeline_format": 1,
        "created": "2026-04-27T12:00:00+00:00",
        "hints": {"dtype": "raw"},
        "steps": [pipeline["steps"][1]],
    }
    edited_pipeline = {
        "pipeline_format": 1,
        "created": "2026-04-27T12:00:00+00:00",
        "hints": {"dtype": "raw"},
        "steps": [
            {"operation": "crop", "name": "Crop", "params": {"tmin": 0.5, "tmax": 2.0}}
        ],
    }

    dialog = HistoryDialog(view, ["data.filter(...)"], [], pipeline, scope="branch")
    qtbot.addWidget(dialog)
    dialog.tabs.setCurrentIndex(2)
    dialog.pipeline_list.item(1).setSelected(True)

    with (
        patch("mnelab.dialogs.pipeline_builder.PipelineBuilderDialog") as MockBuilder,
        patch.object(view, "_confirm_and_apply_pipeline") as confirm,
    ):
        MockBuilder.return_value.exec.return_value = True
        MockBuilder.return_value.get_pipeline.return_value = edited_pipeline

        dialog._create_pipeline()

    assert dialog.windowTitle() == "Branch History"
    assert dialog.tabs.count() == 3
    assert dialog.tabs.tabText(2) == "Branch pipeline"
    assert dialog.pipelinebutton.text() == "Create pipeline from branch..."
    MockBuilder.assert_called_once_with(view, selected_pipeline)
    confirm.assert_called_once_with(edited_pipeline)


def test_history_dialog_pipeline_copy_and_save_are_valid_json(view, qtbot, tmp_path):
    """Pipeline JSON from HistoryDialog can be loaded as strict JSON."""
    pipeline = {
        "pipeline_format": 1,
        "created": "2026-04-27T12:00:00+00:00",
        "hints": {"dtype": "raw"},
        "steps": [
            {
                "operation": "crop",
                "name": "Crop",
                "params": {"start": 0.0, "stop": 1.0},
            }
        ],
    }
    dialog = HistoryDialog(view, ["data.crop(...)"], [], pipeline, scope="branch")
    qtbot.addWidget(dialog)
    dialog.tabs.setCurrentIndex(2)

    dialog._copy_to_clipboard()
    copied = QGuiApplication.clipboard().text()
    assert json.loads(copied)["steps"][0]["operation"] == "crop"

    save_path = tmp_path / "branch-pipeline"
    with patch(
        "mnelab.dialogs.history.QFileDialog.getSaveFileName",
        return_value=(str(save_path), "MNELAB pipeline (*.mnepipe)"),
    ):
        dialog._save_pipeline()

    saved = (tmp_path / "branch-pipeline.mnepipe").read_text(encoding="utf-8")
    assert json.loads(saved)["steps"][0]["params"] == {"start": 0.0, "stop": 1.0}


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

    assert not buttonbox.button(QDialogButtonBox.StandardButton.Ok).isEnabled()


def test_apply_pipeline_dialog_selects_multiple_datasets(view, qtbot):
    """The apply dialog exposes checked root datasets for batch application."""
    pipeline = {"pipeline_format": 1, "steps": []}
    dataset_options = [
        {"index": 0, "name": "sub-01", "dtype": "raw", "checked": True},
        {"index": 1, "name": "sub-02", "dtype": "raw", "checked": False},
    ]

    dialog = ApplyPipelineDialog(
        view,
        pipeline,
        view.model.current,
        dataset_options=dataset_options,
    )
    qtbot.addWidget(dialog)

    assert dialog.selected_dataset_indices() == [0]


def test_history_dialog_uses_dataset_wording_for_roots(view, qtbot):
    """Root history dialogs use dataset wording instead of branch wording."""
    dialog = HistoryDialog(
        view,
        ["data = read_raw(...)"],
        [],
        {"pipeline_format": 1, "steps": []},
        scope="dataset",
    )
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Dataset History"
    assert dialog.tabs.tabText(2) == "Dataset pipeline"
    assert dialog.pipelinebutton.text() == "Create pipeline from dataset..."


def test_info_widget_uses_dataset_or_branch_action_labels(qtbot):
    """The provenance action row uses dataset/branch wording consistently."""
    widget = InfoWidget()
    qtbot.addWidget(widget)

    widget.set_values(
        {
            "File name": "-",
            "_dataset_index": 0,
            "_history_scope": "dataset",
            "_has_replayable_steps": False,
        }
    )
    dataset_buttons = [
        button.text() for button in widget.findChildren(QToolButton) if button.text()
    ]
    assert dataset_buttons == [
        "Dataset history...",
        "Export dataset history...",
    ]

    widget.set_values(
        {
            "File name": "-",
            "_dataset_index": 1,
            "_history_scope": "branch",
            "_has_replayable_steps": True,
        }
    )
    branch_buttons = [
        button.text() for button in widget.findChildren(QToolButton) if button.text()
    ]
    assert branch_buttons == [
        "Branch history...",
        "Export branch history...",
        "Create pipeline from branch...",
        "Save pipeline for branch...",
    ]


def test_info_widget_branch_action_buttons_emit_signals(qtbot):
    """The provenance action row emits the correct dataset-scoped signals."""
    widget = InfoWidget(
        {
            "File name": "-",
            "_dataset_index": 5,
            "_history_scope": "branch",
            "_has_replayable_steps": True,
        }
    )
    qtbot.addWidget(widget)

    emitted = {
        "history": [],
        "export": [],
        "create": [],
        "save": [],
    }
    widget.showHistoryRequested.connect(lambda idx: emitted["history"].append(idx))
    widget.exportHistoryRequested.connect(lambda idx: emitted["export"].append(idx))
    widget.createPipelineRequested.connect(lambda idx: emitted["create"].append(idx))
    widget.savePipelineRequested.connect(lambda idx: emitted["save"].append(idx))

    buttons = {button.text(): button for button in widget.findChildren(QToolButton)}
    qtbot.mouseClick(buttons["Branch history..."], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(buttons["Export branch history..."], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(
        buttons["Create pipeline from branch..."], Qt.MouseButton.LeftButton
    )
    qtbot.mouseClick(buttons["Save pipeline for branch..."], Qt.MouseButton.LeftButton)

    assert emitted == {
        "history": [5],
        "export": [5],
        "create": [5],
        "save": [5],
    }


def test_show_history_for_dataset_uses_dataset_or_branch_scope(view, tmp_path):
    """MainWindow passes the correct history scope for root and derived datasets."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    root_index = view.model.index
    view.model.filter(lower=1.0)
    branch_index = view.model.index

    with patch("mnelab.mainwindow.HistoryDialog") as MockHistoryDialog:
        view.show_history_for_dataset(root_index)
        root_args = MockHistoryDialog.call_args.args
        assert root_args[4] == "dataset"

        view.show_history_for_dataset(branch_index)
        branch_args = MockHistoryDialog.call_args.args
        assert branch_args[4] == "branch"


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
        MockApplyDialog.return_value.selected_dataset_indices.return_value = [
            view.model.index
        ]
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


def test_confirm_and_apply_pipeline_runs_selected_root_datasets(view, tmp_path):
    """Pipeline apply can target more than one loaded root dataset."""
    fs = 256
    signal = np.zeros(30 * fs)
    first = tmp_path / "first.edf"
    second = tmp_path / "second.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(first)
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(second)
    view.model.load(first)
    first_index = view.model.index
    view.model.load(second)
    second_index = view.model.index

    pipeline = {
        "pipeline_format": 1,
        "steps": [{"operation": "set_events", "params": {"events": [[5, 0, 11]]}}],
    }

    with (
        patch("mnelab.dialogs.pipeline.ApplyPipelineDialog") as MockApplyDialog,
        patch("mnelab.mainwindow.PipelineProgressDialog") as MockProgressDialog,
        patch.object(view.model, "apply_pipeline") as apply_pipeline,
        patch("mnelab.mainwindow.QApplication.processEvents"),
    ):
        MockApplyDialog.return_value.exec.return_value = True
        MockApplyDialog.return_value.selected_dataset_indices.return_value = [
            first_index,
            second_index,
        ]
        MockProgressDialog.return_value.wasCanceled.return_value = False

        view._confirm_and_apply_pipeline(pipeline)

    assert apply_pipeline.call_count == 2
    MockProgressDialog.assert_called_once_with(view, 2)


def test_info_widget_can_jump_to_parent_dataset(view, qtbot, tmp_path):
    """The provenance section can navigate back to the parent dataset."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    parent_index = view.model.index
    view.model.filter(lower=1.0)

    info_widget = view.infowidget.widget(0)
    jump_button = next(
        button
        for button in info_widget.findChildren(QToolButton)
        if button.toolTip() == "Jump to parent dataset"
    )

    qtbot.mouseClick(jump_button, Qt.MouseButton.LeftButton)

    assert view.model.index == parent_index


def test_sidebar_history_signal_opens_branch_history(view, tmp_path):
    """Sidebar branch-history requests open the history for the targeted dataset."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    parent_index = view.model.index
    view.model.filter(lower=1.0)

    with patch("mnelab.mainwindow.HistoryDialog") as MockHistoryDialog:
        view.sidebar.showHistoryRequested.emit(parent_index)

    args = MockHistoryDialog.call_args.args
    assert args[0] is view
    assert args[1] == view.model.get_history(parent_index)
    assert args[2] == view.model.log
    assert args[3]["pipeline_format"] == 1
    assert args[3]["hints"] == view.model.get_pipeline(parent_index)["hints"]
    assert args[3]["steps"] == view.model.get_pipeline(parent_index)["steps"]
    MockHistoryDialog.return_value.exec.assert_called_once()


def test_sidebar_create_pipeline_signal_opens_branch_builder(view, tmp_path):
    """Sidebar branch-pipeline requests open the builder for the targeted dataset."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)

    view.model.load(path)
    view.model.filter(lower=1.0)
    branch_index = view.model.index
    edited_pipeline = {
        "pipeline_format": 1,
        "steps": [{"operation": "crop", "params": {"start": 0.0, "stop": 1.0}}],
    }

    with (
        patch("mnelab.dialogs.pipeline_builder.PipelineBuilderDialog") as MockBuilder,
        patch.object(view, "_confirm_and_apply_pipeline") as confirm,
    ):
        MockBuilder.return_value.exec.return_value = True
        MockBuilder.return_value.get_pipeline.return_value = edited_pipeline

        view.sidebar.createPipelineRequested.emit(branch_index)

    builder_args = MockBuilder.call_args.args
    assert builder_args[0] is view
    assert builder_args[1]["pipeline_format"] == 1
    assert builder_args[1]["hints"] == view.model.get_pipeline(branch_index)["hints"]
    assert builder_args[1]["steps"] == view.model.get_pipeline(branch_index)["steps"]
    confirm.assert_called_once_with(edited_pipeline)


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
    view.data_changed()

    assert not view.all_actions["save_pipeline"].isEnabled()
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
    """Roots without replayable steps omit branch pipeline actions entirely."""
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
        "Show dataset history...",
        "Export dataset history...",
    ]
    assert "Create pipeline from branch..." not in root_labels
    assert "Save pipeline for branch..." not in root_labels
    assert "create_pipeline" not in root_actions
    assert "save_pipeline" not in root_actions
    assert root_actions["export_history"].isEnabled()

    view.model.filter(lower=1.0)
    branch_index = view.model.index
    branch_menu, branch_actions = view.sidebar._create_context_menu(branch_index)

    branch_labels = [
        action.text() for action in branch_menu.actions() if not action.isSeparator()
    ]
    assert branch_labels == [
        "Show branch history...",
        "Export branch history...",
        "Create pipeline from branch...",
        "Save pipeline for branch...",
    ]
    assert any(action.isSeparator() for action in branch_menu.actions())
    assert branch_actions["create_pipeline"].isEnabled()
    assert branch_actions["save_pipeline"].isEnabled()
