# © MNELAB developers
#
# License: BSD (3-clause)

import pytest
from PySide6.QtCore import QItemSelectionModel

from mnelab.dialogs.xdf_streams import XDFStreamsDialog


@pytest.fixture
def rows():
    """Rows mirroring a typical XDF file with data, marker, and string streams."""
    return [
        [1, "Keyboard", "Markers", 1, "string", 0.0],  # classic marker
        [2, "BrainAmpSeries-1", "EEG", 67, "float32", 256.0],  # data stream
        [3, "BrainAmpSeries-1-Sampled-Markers", "sampledMarkers", 1, "string", 5000.0],
        [4, "AudioCaptureWin", "Audio", 2, "float32", 44100.0],  # data stream
    ]


def test_all_rows_shown(qtbot, rows):
    """Test that marker streams are included in the table, not filtered out."""
    dialog = XDFStreamsDialog(None, rows, fname="x")
    qtbot.addWidget(dialog)

    assert dialog.view.rowCount() == len(rows)


def test_all_streams_selected_by_default(qtbot, rows):
    """Test that all streams (data and marker) are selected by default."""
    dialog = XDFStreamsDialog(None, rows, fname="x")
    qtbot.addWidget(dialog)

    selected = set(dialog.selected_streams) | set(dialog.selected_markers)
    assert selected == {row[0] for row in rows}
    assert set(dialog.selected_streams) == {2, 4}
    assert set(dialog.selected_markers) == {1, 3}


def test_ok_disabled_with_only_markers_selected(qtbot, rows):
    """Test that OK is disabled unless at least one non-marker stream is selected."""
    dialog = XDFStreamsDialog(None, rows, fname="x")
    qtbot.addWidget(dialog)

    ok_button = dialog.buttonbox.button(dialog.buttonbox.StandardButton.Ok)

    dialog.view.clearSelection()
    selection_model = dialog.view.selectionModel()
    for row in range(dialog.view.rowCount()):
        if dialog._is_marker_row(row):
            selection_model.select(
                dialog.view.model().index(row, 0),
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
    assert not dialog.selected_streams
    assert dialog.selected_markers
    assert not ok_button.isEnabled()


def test_ok_enabled_with_data_stream_selected(qtbot, rows):
    """Test that OK is enabled once a non-marker stream is selected."""
    dialog = XDFStreamsDialog(None, rows, fname="x")
    qtbot.addWidget(dialog)

    ok_button = dialog.buttonbox.button(dialog.buttonbox.StandardButton.Ok)
    assert ok_button.isEnabled()


def test_suggested_fs_ignores_marker_rows(qtbot, rows):
    """Test that the suggested sampling rate is based on data streams only."""
    dialog = XDFStreamsDialog(None, rows, fname="x")
    qtbot.addWidget(dialog)

    # data streams have sampling rates 256 (67 channels) and 44100 (2 channels); the
    # marker stream at 5000 Hz (1 channel) must not skew the suggestion
    assert dialog.fs_new.value() == 256.0
