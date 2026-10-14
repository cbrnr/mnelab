# © MNELAB developers
#
# License: BSD (3-clause)

import warnings

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

import mnelab.mainwindow as mainwindow_module
from mnelab.dialogs.xdf_streams import (
    COL_CHECK,
    COL_ID,
    COL_IMPORT_AS,
    XDFStreamsDialog,
)
from mnelab.mainwindow import MainWindow
from mnelab.model import Model


def stream(stream_id, name, type_, channel_count, channel_format, nominal_srate):
    """Return stream information like `resolve_streams()`."""
    return {
        "stream_id": stream_id,
        "name": name,
        "type": type_,
        "channel_count": channel_count,
        "channel_format": channel_format,
        "nominal_srate": nominal_srate,
    }


@pytest.fixture
def streams():
    """Streams mirroring a typical XDF file with signal, marker, and trigger streams."""
    return [
        stream(1, "Keyboard", "Markers", 1, "string", 0.0),
        stream(2, "BrainAmpSeries-1", "EEG", 67, "float32", 256.0),
        stream(3, "BrainAmp-Sampled-Markers", "sampledMarkers", 1, "string", 5000.0),
        stream(4, "AudioCaptureWin", "Audio", 2, "float32", 44100.0),
        stream(5, "Triggers", "Trigger", 1, "int32", 1000.0),
        stream(6, "HeartRate", "Markers", 1, "float32", 0.0),
    ]


DEFAULT_MODES = {
    1: "annotations",
    2: "continuous",
    3: "annotations",
    4: "continuous",
    5: "discrete",
    6: "annotations",
}


@pytest.fixture
def make_dialog(qtbot):
    def _make_dialog(streams):
        dialog = XDFStreamsDialog(None, streams, fname="x")
        qtbot.addWidget(dialog)
        return dialog

    return _make_dialog


def find_row(dialog, stream_id):
    for row in range(dialog.view.rowCount()):
        if dialog.view.item(row, COL_ID).value() == stream_id:
            return row
    raise ValueError(f"Stream {stream_id} not found.")


def set_checked(dialog, stream_id, checked):
    state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
    dialog.view.item(find_row(dialog, stream_id), COL_CHECK).setCheckState(state)


def only_check(dialog, *stream_ids):
    for row in range(dialog.view.rowCount()):
        stream_id = dialog.view.item(row, COL_ID).value()
        set_checked(dialog, stream_id, stream_id in stream_ids)


def set_import_as(dialog, stream_id, text):
    dialog.view.cellWidget(find_row(dialog, stream_id), COL_IMPORT_AS).setCurrentText(
        text
    )


def ok_enabled(dialog):
    return dialog.buttonbox.button(dialog.buttonbox.StandardButton.Ok).isEnabled()


def test_defaults(make_dialog, streams):
    """Test that all streams are checked and imported as in MNEXTEND by default."""
    dialog = make_dialog(streams)

    assert dialog.view.rowCount() == len(streams)
    expected = {
        1: None,  # fixed choice, plain text
        2: ["Continuous", "Discrete"],
        3: None,
        4: ["Continuous", "Discrete"],
        5: ["Discrete", "Continuous"],
        6: ["Annotations", "Discrete"],
    }
    for stream_id, choices in expected.items():
        row = find_row(dialog, stream_id)
        assert dialog._is_checked(row)
        combo = dialog.view.cellWidget(row, COL_IMPORT_AS)
        if choices is None:
            assert combo is None
            assert dialog.view.item(row, COL_IMPORT_AS).text() == "Annotations"
        else:
            assert [combo.itemText(i) for i in range(combo.count())] == choices

    assert dialog.streams == DEFAULT_MODES
    assert ok_enabled(dialog)
    assert dialog.resample.isChecked()
    assert not dialog.resample.isEnabled()
    assert dialog.prefix_markers is False
    assert dialog._prefix_markers.isEnabled()
    # the 5000 Hz marker stream and the trigger stream must not drive the rate
    assert dialog.fs_new.value() == 256.0


def test_mapping(make_dialog, streams):
    """Test mapping of the import choices to `read_raw()` arguments."""
    dialog = make_dialog(streams)

    set_import_as(dialog, 2, "Discrete")
    set_import_as(dialog, 5, "Continuous")
    set_import_as(dialog, 6, "Discrete")
    assert dialog.streams == DEFAULT_MODES | {
        2: "discrete",
        5: "continuous",
        6: "discrete",
    }
    assert list(dialog.streams) == [1, 2, 3, 4, 5, 6]  # sorted by stream ID


def test_unchecked_streams_excluded(make_dialog, streams):
    """Test that unchecked streams are excluded everywhere."""
    dialog = make_dialog(streams)

    for stream_id in (1, 4, 5):
        set_checked(dialog, stream_id, False)
    set_import_as(dialog, 6, "Discrete")
    set_checked(dialog, 6, False)
    assert dialog.streams == {2: "continuous", 3: "annotations"}
    assert not dialog._prefix_markers.isEnabled()
    combo = dialog.view.cellWidget(find_row(dialog, 6), COL_IMPORT_AS)
    assert not combo.isEnabled()


def test_sorting_keeps_rows_intact(make_dialog, streams):
    """Test that sorting the table keeps the import choices with their streams."""
    dialog = make_dialog(streams)

    set_import_as(dialog, 6, "Discrete")
    dialog.view.sortByColumn(2, Qt.SortOrder.AscendingOrder)  # sort by name
    assert dialog._mode(find_row(dialog, 6)) == "discrete"
    assert dialog._mode(find_row(dialog, 5)) == "discrete"
    assert dialog._mode(find_row(dialog, 2)) == "continuous"
    assert dialog.streams == DEFAULT_MODES | {6: "discrete"}


def checked_ids(dialog):
    return sorted(
        dialog.view.item(row, COL_ID).value()
        for row in range(dialog.view.rowCount())
        if dialog._is_checked(row)
    )


def test_shift_click_range(make_dialog, streams, monkeypatch):
    """Test that Shift-clicking a checkbox sets the check state of a range of rows."""
    dialog = make_dialog(streams)

    set_checked(dialog, 2, False)
    monkeypatch.setattr(
        QApplication, "keyboardModifiers", lambda: Qt.KeyboardModifier.ShiftModifier
    )
    set_checked(dialog, 5, False)
    assert checked_ids(dialog) == [1, 6]
    set_checked(dialog, 3, True)  # range starts at the last clicked row
    assert checked_ids(dialog) == [1, 3, 4, 5, 6]

    # ranges follow the displayed order
    dialog.view.sortByColumn(2, Qt.SortOrder.AscendingOrder)  # sort by name
    names = [dialog.view.item(row, 2).text() for row in range(dialog.view.rowCount())]
    assert names[0] == "AudioCaptureWin" and names[1] == "BrainAmp-Sampled-Markers"
    monkeypatch.setattr(
        QApplication, "keyboardModifiers", lambda: Qt.KeyboardModifier.NoModifier
    )
    set_checked(dialog, 4, False)  # AudioCaptureWin
    monkeypatch.setattr(
        QApplication, "keyboardModifiers", lambda: Qt.KeyboardModifier.ShiftModifier
    )
    set_checked(dialog, 3, False)  # BrainAmp-Sampled-Markers
    assert checked_ids(dialog) == [1, 5, 6]


def click_header(qtbot, dialog, column):
    header = dialog.view.horizontalHeader()
    pos = QPoint(header.sectionViewportPosition(column) + 10, 5)
    qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=pos)


def test_sorting_by_header_click(qtbot, make_dialog, streams):
    """Test that clicking a column header sorts, except for unsortable columns."""
    dialog = make_dialog(streams)
    dialog.show()
    qtbot.waitExposed(dialog)
    header = dialog.view.horizontalHeader()

    def ids():
        return [dialog.view.item(row, COL_ID).value() for row in range(6)]

    click_header(qtbot, dialog, 2)  # sort by name
    assert header.sortIndicatorSection() == 2
    assert ids() == [4, 3, 2, 6, 1, 5]
    for column in (COL_CHECK, COL_IMPORT_AS):
        click_header(qtbot, dialog, column)
        assert header.sortIndicatorSection() == 2
        assert ids() == [4, 3, 2, 6, 1, 5]


def test_check_all(qtbot, make_dialog, streams):
    """Test that the header checkbox checks or unchecks all streams."""
    dialog = make_dialog(streams)
    dialog.show()
    qtbot.waitExposed(dialog)
    header = dialog.view.horizontalHeader()

    assert header._check_state == Qt.CheckState.Checked
    click_header(qtbot, dialog, COL_CHECK)  # all checked: uncheck all
    assert checked_ids(dialog) == []
    assert header._check_state == Qt.CheckState.Unchecked
    assert not ok_enabled(dialog)

    set_checked(dialog, 2, True)
    assert header._check_state == Qt.CheckState.PartiallyChecked
    click_header(qtbot, dialog, COL_CHECK)  # some checked: check all
    assert checked_ids(dialog) == [1, 2, 3, 4, 5, 6]
    assert header._check_state == Qt.CheckState.Checked
    assert dialog.streams == DEFAULT_MODES
    assert ok_enabled(dialog)


def test_ok_disabled_without_channels(make_dialog, streams):
    """Test that OK is disabled unless at least one stream is imported as channels."""
    dialog = make_dialog(streams)

    only_check(dialog, 1, 3, 6)
    assert set(dialog.streams.values()) == {"annotations"}
    assert not ok_enabled(dialog)
    assert not dialog.resample.isEnabled()
    assert not dialog.fs_new.isEnabled()

    set_import_as(dialog, 6, "Discrete")
    assert ok_enabled(dialog)


def test_resampling(make_dialog, streams):
    """Test when resampling is forced, optional, or unavailable."""
    dialog = make_dialog(streams)

    # a single regular-rate stream: optional and off by default
    only_check(dialog, 1, 2)
    assert dialog.resample.isEnabled()
    assert not dialog.resample.isChecked()
    assert not dialog.fs_new.isEnabled()
    assert not dialog.gap_threshold_checkbox.isEnabled()

    # the user's choice is kept when the selection changes
    dialog.resample.click()
    assert dialog.resample.isChecked()
    assert dialog.fs_new.isEnabled()
    assert dialog.gap_threshold_checkbox.isEnabled()
    set_checked(dialog, 1, False)
    assert dialog.resample.isEnabled()
    assert dialog.resample.isChecked()

    # several streams: forced
    set_checked(dialog, 4, True)
    assert not dialog.resample.isEnabled()
    assert dialog.resample.isChecked()
    assert dialog.fs_new.isEnabled()

    # a 0 Hz stream as channels: forced
    only_check(dialog, 6)
    set_import_as(dialog, 6, "Discrete")
    assert not dialog.resample.isEnabled()
    assert dialog.resample.isChecked()


def test_suggested_rate(make_dialog, streams):
    """Test the suggested sampling rate."""
    dialog = make_dialog(streams)

    # rule 1: continuous stream with the most channels
    only_check(dialog, 4, 5)
    assert dialog.fs_new.value() == 44100.0
    set_import_as(dialog, 4, "Discrete")  # rule 2: highest discrete rate
    assert dialog.fs_new.value() == 44100.0
    set_checked(dialog, 4, False)
    assert dialog.fs_new.value() == 1000.0
    set_checked(dialog, 5, False)  # rule 3: only 0 Hz streams as channels
    set_checked(dialog, 6, True)
    set_import_as(dialog, 6, "Discrete")
    assert dialog.fs_new.value() == 100.0
    set_checked(dialog, 5, True)
    assert dialog.fs_new.value() == 1000.0


def test_suggested_rate_ties(make_dialog):
    """Test that the higher rate wins if streams have the same number of channels."""
    dialog = make_dialog(
        [
            stream(1, "A", "EEG", 8, "float32", 250.0),
            stream(2, "B", "EEG", 8, "float32", 500.0),
            stream(3, "C", "EEG", 8, "float32", 128.0),
        ]
    )
    assert dialog.fs_new.value() == 500.0


def test_suggested_rate_muse(make_dialog):
    """Test that several small streams do not outvote the main stream."""
    dialog = make_dialog(
        [
            stream(1, "Muse", "EEG", 5, "float32", 256.0),
            stream(2, "Accelerometer", "ACC", 3, "float32", 52.0),
            stream(3, "Gyroscope", "GYRO", 3, "float32", 52.0),
            stream(4, "PPG", "PPG", 3, "float32", 64.0),
        ]
    )
    assert dialog.fs_new.value() == 256.0


def test_suggested_rate_manual_edit(make_dialog, streams):
    """Test that a manually edited rate is kept."""
    dialog = make_dialog(streams)

    dialog.fs_new.setValue(128.0)
    only_check(dialog, 4, 5)
    assert dialog.fs_new.value() == 128.0


def test_rate_range(make_dialog):
    """Test the rate range with only low or 0 Hz numeric streams."""
    dialog = make_dialog(
        [
            stream(1, "Markers", "Markers", 1, "string", 5000.0),
            stream(2, "Counter", "Markers", 1, "int32", 0.0),
            stream(3, "Slow", "Misc", 1, "float32", 10.0),
        ]
    )
    assert dialog.fs_new.minimum() == 1
    assert dialog.fs_new.maximum() == 100
    assert dialog.fs_new.value() == 10.0


def test_import_shows_warnings(qtbot, tmp_path, monkeypatch, streams):
    """Test that the dialog choices are passed on and relevant warnings are shown."""
    fname = tmp_path / "test.xdf"
    fname.touch()
    calls, shown = [], []

    def load(self, fname, **kwargs):
        calls.append(kwargs)
        warnings.warn("Lost value changes.", RuntimeWarning)
        warnings.warn("Lost value changes.", RuntimeWarning)
        warnings.warn("Unrecognized unit(s) 'kiloohm'.", RuntimeWarning)

    monkeypatch.setattr(mainwindow_module, "resolve_streams", lambda fname: streams)
    monkeypatch.setattr(XDFStreamsDialog, "exec", lambda self: True)
    monkeypatch.setattr(Model, "load", load)
    monkeypatch.setattr(
        mainwindow_module.QMessageBox, "warning", lambda *args: shown.append(args)
    )
    view = MainWindow(Model())
    qtbot.addWidget(view)
    view.open_data(str(fname))

    assert calls == [
        {
            "streams": DEFAULT_MODES,
            "prefix_markers": False,
            "fs_new": 256.0,
            "gap_threshold": 0.0,
        }
    ]
    assert len(shown) == 1
    # duplicates are removed, unit warnings are not shown
    assert shown[0][2] == "Lost value changes."
