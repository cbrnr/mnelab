# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QVBoxLayout,
)

class AppendDialog(QDialog):
    def __init__(self, parent, compatibles, title="Append data"):
        super().__init__(parent)
        self.setWindowTitle(title)

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Source"), 0, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("Destination"), 0, 2, Qt.AlignCenter)

        self.source = QTableWidget(self)
        self.setup_table(self.source, compatibles)

        self.move_button = QPushButton("→")
        self.move_button.setEnabled(False)
        grid.addWidget(self.move_button, 1, 1, Qt.AlignHCenter)

        self.destination = QTableWidget(self)
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
        table_widget.setHorizontalHeaderLabels(["Index", "Name"])
        table_widget.setRowCount(len(compatibles))

        for i, (idx, name) in enumerate(compatibles):
            table_widget.setItem(i, 0, QTableWidgetItem(str(idx)))
            table_widget.setItem(i, 1, QTableWidgetItem(name))

        table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        table_widget.verticalHeader().setVisible(False)
        table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table_widget.horizontalHeader().setStretchLastSection(True)

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

        rows = sorted(
            set(index.row() for index in source_table.selectedIndexes()), reverse=True
        )
        for row in rows:
            idx_item = source_table.item(row, 0).clone()
            name_item = source_table.item(row, 1).clone()
            row_count = destination_table.rowCount()
            destination_table.insertRow(row_count)
            destination_table.setItem(row_count, 0, idx_item)
            destination_table.setItem(row_count, 1, name_item)
            source_table.removeRow(row)
