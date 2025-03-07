# © MNELAB developers
#
# License: BSD (3-clause)

from collections import defaultdict

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

from mnelab.dialogs.utils import IntTableWidgetItem


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
        self.counts_button = QPushButton("Counts...")
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        hbox.addWidget(self.add_button)
        hbox.addWidget(self.remove_button)
        hbox.addWidget(self.counts_button)
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
        self.counts_button.clicked.connect(self.open_counts_dialog)
        self.toggle_buttons()
        self.setMinimumSize(500, 500)
        self.resize(500, 500)

    @property
    def unique_annotations(self):
        _unique_annotations = defaultdict(int)
        for i in range(self.table.rowCount()):
            if item := self.table.item(i, 2):
                _unique_annotations[item.text()] += 1
        return _unique_annotations

    @Slot()
    def toggle_buttons(self):
        """Toggle + and - buttons."""
        n_items = len(self.table.selectedItems())
        if self.table.rowCount() == 0:  # no annotations available
            self.add_button.setEnabled(True)
            self.remove_button.setEnabled(False)
            self.counts_button.setEnabled(False)
        elif n_items == 3:  # one row (3 items) selected
            self.add_button.setEnabled(True)
            self.remove_button.setEnabled(True)
        elif n_items > 3:  # more than one row selected
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(True)
        else:  # no rows selected
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.counts_button.setEnabled(True)

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

    def open_counts_dialog(self):
        dialog = EventCountsDialog(self)
        dialog.exec()


class EventCountsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Annotation Counts")
        self.unique_annotations = parent.unique_annotations

        self.counts_table = QTableWidget(0, 2)
        self.counts_table.setHorizontalHeaderLabels(["Description", "Count"])
        self.counts_table.horizontalHeader().setStretchLastSection(True)
        self.counts_table.verticalHeader().setVisible(False)
        self.counts_table.setShowGrid(False)
        self.counts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fill_counts_table()

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.counts_table)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)

        self.counts_table.setMinimumHeight(225)

    def fill_counts_table(self):
        self.counts_table.setRowCount(0)
        for row, (id_, count) in enumerate(sorted(self.unique_annotations.items())):
            id_item = IntTableWidgetItem(id_)
            id_item.setFlags(id_item.flags() ^ Qt.ItemIsEditable)
            self.counts_table.insertRow(row)
            self.counts_table.setItem(row, 0, id_item)
            self.counts_table.setItem(row, 1, QTableWidgetItem(str(count)))
