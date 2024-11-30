# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class DragDropTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(False)
        self.setDragDropOverwriteMode(False)
        self.drop_row = -1

    def dragEnterEvent(self, event):
        event.accept()
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        drop_row = self.indexAt(event.pos()).row()
        if drop_row == -1:
            drop_row = self.rowCount()
        if drop_row != self.drop_row:
            self.drop_row = drop_row
            self.viewport().update()
        event.accept()
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self.drop_row = -1
        self.viewport().update()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drop_row >= 0:
            painter = QPainter(self.viewport())
            pen = QPen(QColor("black"))
            pen.setWidth(1.5)
            painter.setPen(pen)
            if self.drop_row < self.rowCount():
                rect = self.visualRect(self.model().index(self.drop_row, 0))
                y = rect.top()
            else:
                last_row_rect = self.visualRect(
                    self.model().index(self.rowCount() - 1, 0)
                )
                y = last_row_rect.bottom()
            painter.drawLine(0, y, self.viewport().width(), y)

    def dropEvent(self, event):
        self.drop_row = -1
        self.viewport().update()

        if isinstance(event.source(), DragDropTableWidget):
            source_table = event.source()
            drop_row = self.indexAt(event.pos()).row()
            if drop_row == -1:
                drop_row = self.rowCount()

            selected_rows = sorted(set(
                index.row() for index in source_table.selectedIndexes()
            ))
            if selected_rows:
                row_data = []
                for row in selected_rows:
                    row_data.append([
                        source_table.item(row, col).text()
                        for col in range(source_table.columnCount())
                    ])

                if source_table == self:
                    for row in selected_rows:
                        if row < drop_row:
                            drop_row -= 1

                for row in reversed(selected_rows):
                    source_table.removeRow(row)

                for i, data in enumerate(row_data):
                    self.insertRow(drop_row + i)
                    for col, value in enumerate(data):
                        item = QTableWidgetItem(value)
                        item.setTextAlignment(
                            Qt.AlignLeft | Qt.AlignVCenter
                            if col == 1
                            else Qt.AlignRight | Qt.AlignVCenter
                        )
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        if col == 0:
                            item.setForeground(QColor("gray"))
                        self.setItem(drop_row + i, col, item)

                self.styleRows()
                event.accept()
        else:
            super().dropEvent(event)

    def styleRows(self):
        for i in range(self.rowCount()):
            self.resizeRowToContents(i)
            self.setRowHeight(i, 10)


class AppendDialog(QDialog):
    def __init__(self, parent, compatibles, title="Append data"):
        super().__init__(parent)
        self.setWindowTitle(title)

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Source"), 0, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("Destination"), 0, 2, Qt.AlignCenter)

        self.source = DragDropTableWidget(self)
        self.setup_table(self.source, compatibles)

        self.move_button = QPushButton("→")
        self.move_button.setEnabled(False)
        grid.addWidget(self.move_button, 1, 1, Qt.AlignHCenter)

        self.destination = DragDropTableWidget(self)
        self.setup_table(self.destination, [])

        grid.addWidget(self.source, 1, 0)
        grid.addWidget(self.destination, 1, 2)
        vbox.addLayout(grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        vbox.addWidget(self.buttonbox)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)
        self.destination.model().rowsInserted.connect(self.toggle_ok_button)
        self.destination.model().rowsRemoved.connect(self.toggle_ok_button)
        self.source.itemSelectionChanged.connect(self.toggle_move_source)
        self.destination.itemSelectionChanged.connect(self.toggle_move_destination)
        self.move_button.clicked.connect(self.move)
        self.toggle_ok_button()
        self.toggle_move_source()
        self.toggle_move_destination()

    def setup_table(self, table_widget, compatibles):
        table_widget.setColumnCount(2)
        table_widget.setRowCount(len(compatibles))

        for i, (idx, name) in enumerate(compatibles):
            index_item = QTableWidgetItem(str(idx))
            index_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            index_item.setForeground(QColor("gray"))
            index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)
            table_widget.setItem(i, 0, index_item)

            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            table_widget.setItem(i, 1, name_item)
            table_widget.resizeRowToContents(i)
            table_widget.setRowHeight(i, 10)

        table_widget.horizontalHeader().hide()
        table_widget.verticalHeader().hide()
        table_widget.setShowGrid(False)

        table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        table_widget.horizontalHeader().setStretchLastSection(True)
        table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

    @property
    def selected_idx(self):
        """Return a list of all original indices in the destination."""
        selected = []
        for it in range(self.destination.rowCount()):
            index_item = self.destination.item(it, 0)
            if index_item:
                selected.append(int(index_item.text()))
        return selected

    @Slot()
    def toggle_ok_button(self):
        if self.destination.rowCount() > 0:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)

    @Slot()
    def toggle_move_source(self):
        if self.source.selectedItems():
            self.move_button.setEnabled(True)
            self.move_button.setText("→")
            self.destination.clearSelection()
        elif not self.destination.selectedItems():
            self.move_button.setEnabled(False)

    @Slot()
    def toggle_move_destination(self):
        if self.destination.selectedItems():
            self.move_button.setEnabled(True)
            self.move_button.setText("←")
            self.source.clearSelection()
        elif not self.source.selectedItems():
            self.move_button.setEnabled(False)

    @Slot()
    def move(self):
        source_table = self.source if self.source.selectedRanges() else self.destination
        destination_table = (
            self.destination if self.source.selectedRanges() else self.source
        )

        rows = sorted(set(index.row() for index in source_table.selectedIndexes()))

        for row in rows:
            idx_item = source_table.item(row, 0).clone()
            name_item = source_table.item(row, 1).clone()
            row_count = destination_table.rowCount()
            destination_table.insertRow(row_count)
            destination_table.setItem(row_count, 0, idx_item)
            destination_table.setItem(row_count, 1, name_item)

        destination_table.styleRows()

        for row in reversed(rows):
            source_table.removeRow(row)
