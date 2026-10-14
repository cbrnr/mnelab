# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt

from mnelab.dialogs.append import AppendDialog


def test_append_dialog_moves_datasets(qtbot):
    """Test that moved data sets keep their model index without showing it."""
    dialog = AppendDialog(None, [(1, "a"), (4, "b"), (7, "c")])
    qtbot.addWidget(dialog)
    assert dialog.source.columnCount() == 1
    assert [dialog.source.item(r, 0).text() for r in range(3)] == ["a", "b", "c"]

    dialog.source.selectRow(2)
    dialog.move()
    dialog.source.selectRow(0)
    dialog.move()
    assert dialog.selected_idx == [7, 1]  # in the order in which they were moved
    assert [dialog.destination.item(r, 0).text() for r in range(2)] == ["c", "a"]
    assert dialog.source.rowCount() == 1
    assert dialog.source.item(0, 0).text() == "b"

    dialog.destination.selectRow(0)
    dialog.move()  # move back
    assert dialog.selected_idx == [1]
    assert dialog.source.item(1, 0).data(Qt.ItemDataRole.UserRole) == 7
