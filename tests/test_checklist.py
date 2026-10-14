# © MNELAB developers
#
# License: BSD (3-clause)

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from mnelab.dialogs.annotations import AnnotationTypesDialog
from mnelab.dialogs.annotations_from_events import AnnotationsIntervalDialog
from mnelab.dialogs.epoch import EpochDialog
from mnelab.dialogs.pick_channels import PickChannelsDialog
from mnelab.dialogs.reference import ReferenceDialog
from mnelab.widgets import COL_CHECK, CheckListWidget

ITEMS = ["1", "2", "3", "4", "5"]


def set_checked(widget, row, checked):
    state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
    widget.item(row, COL_CHECK).setCheckState(state)


def click_header(qtbot, widget, column):
    header = widget.horizontalHeader()
    pos = QPoint(header.sectionViewportPosition(column) + 10, 5)
    qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=pos)


def ok_enabled(dialog):
    return dialog.buttonbox.button(QDialogButtonBox.StandardButton.Ok).isEnabled()


@pytest.mark.parametrize("checked", [True, False])
def test_initial_state(qtbot, checked):
    """Test that all items are initially checked or unchecked."""
    widget = CheckListWidget(ITEMS, "Event", "events", checked=checked)
    qtbot.addWidget(widget)
    assert widget.checked_texts() == (ITEMS if checked else [])
    expected = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
    assert widget.horizontalHeader()._check_state == expected


def test_checked_texts(qtbot):
    """Test that checked texts are returned in display order."""
    widget = CheckListWidget(ITEMS, "Event", "events", checked=False)
    qtbot.addWidget(widget)
    set_checked(widget, 3, True)
    set_checked(widget, 1, True)
    assert widget.checked_texts() == ["2", "4"]
    assert widget.horizontalHeader()._check_state == Qt.CheckState.PartiallyChecked


def test_checks_changed(qtbot):
    """Test that `checks_changed` is emitted when a checkbox changes."""
    widget = CheckListWidget(ITEMS, "Event", "events", checked=False)
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.checks_changed):
        set_checked(widget, 0, True)


def test_shift_click_range(qtbot, monkeypatch):
    """Test that Shift-clicking a checkbox sets the check state of a range of rows."""
    widget = CheckListWidget(ITEMS, "Event", "events", checked=False)
    qtbot.addWidget(widget)
    set_checked(widget, 1, True)
    monkeypatch.setattr(
        QApplication, "keyboardModifiers", lambda: Qt.KeyboardModifier.ShiftModifier
    )
    with qtbot.waitSignal(widget.checks_changed):
        set_checked(widget, 3, True)
    assert widget.checked_texts() == ["2", "3", "4"]
    set_checked(widget, 1, False)  # range upwards from the last clicked row
    assert widget.checked_texts() == []


def test_check_all(qtbot):
    """Test that the header checkbox checks or unchecks all items."""
    widget = CheckListWidget(ITEMS, "Event", "events")
    qtbot.addWidget(widget)
    widget.show()
    header = widget.horizontalHeader()
    click_header(qtbot, widget, COL_CHECK)  # all checked: uncheck all
    assert widget.checked_texts() == []
    assert header._check_state == Qt.CheckState.Unchecked
    set_checked(widget, 2, True)
    click_header(qtbot, widget, COL_CHECK)  # some checked: check all
    assert widget.checked_texts() == ITEMS
    assert header._check_state == Qt.CheckState.Checked
    click_header(qtbot, widget, 1)  # text column neither sorts nor checks
    assert widget.checked_texts() == ITEMS
    assert header.sortIndicatorSection() != 1


def test_rows_are_not_selectable(qtbot):
    """Test that rows cannot be selected (checkboxes are the only way to select)."""
    widget = CheckListWidget(ITEMS, "Event", "events")
    qtbot.addWidget(widget)
    widget.selectAll()
    assert not widget.selectedItems()


def test_epoch_dialog(qtbot):
    """Test that OK requires at least one checked event type."""
    dialog = EpochDialog(None, ITEMS)
    qtbot.addWidget(dialog)
    assert not ok_enabled(dialog)
    set_checked(dialog.events, 1, True)
    set_checked(dialog.events, 3, True)
    assert ok_enabled(dialog)
    assert dialog.selected_events == [2, 4]
    dialog.events.set_all_checked(False)
    assert not ok_enabled(dialog)


def test_pick_channels_dialog(qtbot):
    """Test that OK depends on the checked items of the active list."""
    dialog = PickChannelsDialog(None, ["Fz", "Cz", "Pz"], ["eeg", "eog"])
    qtbot.addWidget(dialog)
    assert dialog.names.checked_texts() == ["Fz", "Cz", "Pz"]
    assert ok_enabled(dialog)
    dialog.names.set_all_checked(False)
    assert not ok_enabled(dialog)
    dialog.by_type.setChecked(True)
    assert dialog.types.checked_texts() == ["eeg", "eog"]
    assert ok_enabled(dialog)


def test_reference_dialog(qtbot):
    """Test that re-referencing to channels requires at least one checked channel."""
    dialog = ReferenceDialog(None, ["Fz", "Cz", "Pz"])
    qtbot.addWidget(dialog)
    dialog.reref_channels.setChecked(True)
    assert not ok_enabled(dialog)
    set_checked(dialog.reref_channellist, 2, True)
    assert ok_enabled(dialog)
    assert dialog.reref_channellist.checked_texts() == ["Pz"]


def test_annotation_types_dialog(qtbot):
    """Test that all annotation types are initially checked."""
    dialog = AnnotationTypesDialog(None, ["T0", "T1", "T2"])
    qtbot.addWidget(dialog)
    assert dialog.selected_types == ["T0", "T1", "T2"]
    set_checked(dialog.list_widget, 1, False)
    assert dialog.selected_types == ["T0", "T2"]
    dialog.list_widget.set_all_checked(False)
    assert not ok_enabled(dialog)


def test_annotations_interval_dialog(qtbot):
    """Test that intervals require checked start and end events."""
    dialog = AnnotationsIntervalDialog(None, {1: 10, 2: 10, 3: 5}, ["a"])
    qtbot.addWidget(dialog)
    dialog.event_event_button.setChecked(True)
    dialog.annotation_combo.setCurrentText("interval")
    assert not ok_enabled(dialog)
    set_checked(dialog.start_event_list, 0, True)
    set_checked(dialog.end_event_list, 1, True)
    assert ok_enabled(dialog)
    data = dialog.event_to_event_data()
    assert data["start_events"] == [1]
    assert data["end_events"] == [2]
    set_checked(dialog.end_event_list, 0, True)  # same event as start event
    assert not ok_enabled(dialog)
