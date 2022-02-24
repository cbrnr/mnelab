# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .utils import IntTableWidgetItem


class AnnotationsDialog(QDialog):
    def __init__(self, parent, onset, duration, description):
        super().__init__(parent)
        self.setWindowTitle("Edit Annotations")

        self.table = QTableWidget(len(onset), 3)

        for row, annotation in enumerate(zip(onset, duration, description)):
            self.table.setItem(row, 0, IntTableWidgetItem(annotation[0]))
            self.table.setItem(row, 1, IntTableWidgetItem(annotation[1]))
            self.table.setItem(row, 2, QTableWidgetItem(annotation[2]))

        self.table.setHorizontalHeaderLabels(["Onset", "Duration", "Type"])
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
        self.remove_button.clicked.connect(self.toggle_buttons)
        self.add_button.clicked.connect(self.toggle_buttons)
        self.toggle_buttons()
        self.resize(500, 500)

    @Slot()
    def toggle_buttons(self):
        """Toggle + and - buttons."""
        n_items = len(self.table.selectedItems())
        if self.table.rowCount() == 0:  # no annotations available
            self.add_button.setEnabled(True)
            self.remove_button.setEnabled(False)
        elif n_items == 3:  # one row (3 items) selected
            self.add_button.setEnabled(True)
            self.remove_button.setEnabled(True)
        elif n_items > 3:  # more than one row selected
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(True)
        else:  # no rows selected
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(False)

    def add_event(self):
        if self.table.selectedIndexes():
            current_row = self.table.selectedIndexes()[0].row()
            pos = int(self.table.item(current_row, 0).data(Qt.DisplayRole))
        else:
            current_row = 0
            pos = 0
        self.table.setSortingEnabled(False)
        self.table.insertRow(current_row)
        self.table.setItem(current_row, 0, IntTableWidgetItem(pos))
        self.table.setItem(current_row, 1, IntTableWidgetItem(0))
        self.table.setItem(current_row, 2, QTableWidgetItem("New Annotation"))
        self.table.setSortingEnabled(True)

    def remove_event(self):
        rows = {index.row() for index in self.table.selectedIndexes()}
        self.table.clearSelection()
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
