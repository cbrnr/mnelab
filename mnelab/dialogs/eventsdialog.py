# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PyQt6.QtCore import Qt, Slot
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)


class IntTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))

    def __lt__(self, other):
        return int(self.data(Qt.EditRole)) < int(other.data(Qt.EditRole))

    def setData(self, role, value):
        try:
            value = int(value)
        except ValueError:
            return
        else:
            if value >= 0:  # event position and type must not be negative
                super().setData(role, str(value))


class EventsDialog(QDialog):
    def __init__(self, parent, pos, desc):
        super().__init__(parent)
        self.setWindowTitle("Edit Events")

        self.table = QTableWidget(len(pos), 2)

        for row, (p, d) in enumerate(zip(pos, desc)):
            self.table.setItem(row, 0, IntTableWidgetItem(p))
            self.table.setItem(row, 1, IntTableWidgetItem(d))

        self.table.setHorizontalHeaderLabels(["Position", "Type"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.table)
        hbox = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.remove_button = QPushButton("-")
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        hbox.addWidget(self.add_button)
        hbox.addWidget(self.remove_button)
        hbox.addStretch()
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.table.itemSelectionChanged.connect(self.toggle_buttons)
        self.remove_button.clicked.connect(self.remove_event)
        self.add_button.clicked.connect(self.add_event)
        self.toggle_buttons()
        self.resize(300, 500)

    @Slot()
    def toggle_buttons(self):
        """Toggle + and - buttons."""
        n_items = len(self.table.selectedItems())
        if n_items == 2:  # one row (2 items) selected
            self.add_button.setEnabled(True)
            self.remove_button.setEnabled(True)
        elif n_items > 2:  # more than one row selected
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(True)
        else:  # no rows selected
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(False)

    def add_event(self):
        current_row = self.table.selectedIndexes()[0].row()
        pos = int(self.table.item(current_row, 0).data(Qt.DisplayRole))
        self.table.setSortingEnabled(False)
        self.table.insertRow(current_row)
        self.table.setItem(current_row, 0, IntTableWidgetItem(pos))
        self.table.setItem(current_row, 1, IntTableWidgetItem(0))
        self.table.setSortingEnabled(True)

    def remove_event(self):
        rows = {index.row() for index in self.table.selectedIndexes()}
        self.table.clearSelection()
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
