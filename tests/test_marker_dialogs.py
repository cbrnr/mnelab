# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt

from mnelab.dialogs.annotations import AnnotationsDialog
from mnelab.dialogs.events import EventsDialog


def test_events_dialog_tracks_rows_across_sorting(qtbot):
    """Event edits retain their stable row identity after sorting."""
    dialog = EventsDialog(None, [100, 200], [1, 2], {})
    qtbot.addWidget(dialog)

    dialog.event_table.item(0, 0).setData(Qt.ItemDataRole.EditRole, 300)
    dialog.event_table.selectRow(0)
    dialog.add_event()

    assert sorted(dialog.row_ids) == [0, 1, 2]
    assert dialog.row_ids[-1] == 0


def test_annotations_dialog_tracks_rows_across_sorting(qtbot):
    """Annotation edits retain their stable row identity after sorting."""
    dialog = AnnotationsDialog(None, [100, 200], [0, 0], ["A", "B"])
    qtbot.addWidget(dialog)

    dialog.table.item(0, 0).setData(Qt.ItemDataRole.EditRole, 300)
    dialog.table.selectRow(0)
    dialog.add_event()

    assert sorted(dialog.row_ids) == [0, 1, 2]
    assert dialog.row_ids[-1] == 0
