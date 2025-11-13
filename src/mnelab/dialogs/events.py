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


class EventsDialog(QDialog):
    def __init__(self, parent, pos, desc, event_mapping):
        super().__init__(parent)
        self.setWindowTitle("Edit Events")

        self.event_table = QTableWidget(len(pos), 2)

        for row, (p, d) in enumerate(zip(pos, desc)):
            self.event_table.setItem(row, 0, IntTableWidgetItem(p))
            self.event_table.setItem(row, 1, IntTableWidgetItem(d))

        self.event_table.setHorizontalHeaderLabels(["Position", "Type"])
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.verticalHeader().setVisible(False)
        self.event_table.setShowGrid(False)
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.event_table.setSortingEnabled(True)
        self.event_table.sortByColumn(0, Qt.AscendingOrder)

        self.event_mapping = defaultdict(str, event_mapping)  # make copy

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.event_table)
        hbox = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.remove_button = QPushButton("-")
        self.counts_button = QPushButton("Counts...")
        self.mapping_button = QPushButton("Mapping...")
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        hbox.addWidget(self.add_button)
        hbox.addWidget(self.remove_button)
        hbox.addWidget(self.counts_button)
        hbox.addWidget(self.mapping_button)
        hbox.addStretch()
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.event_table.itemSelectionChanged.connect(self.toggle_buttons)
        self.remove_button.clicked.connect(self.remove_event)
        self.add_button.clicked.connect(self.add_event)
        self.remove_button.clicked.connect(self.toggle_buttons)
        self.add_button.clicked.connect(self.toggle_buttons)
        self.counts_button.clicked.connect(self.open_counts_dialog)
        self.mapping_button.clicked.connect(self.open_mapping_dialog)
        self.toggle_buttons()
        self.setMinimumSize(600, 500)

    @property
    def unique_events(self):
        _unique_events = defaultdict(int)
        for i in range(self.event_table.rowCount()):
            if item := self.event_table.item(i, 1):
                _unique_events[int(item.value())] += 1
        return _unique_events

    @Slot()
    def open_counts_dialog(self):
        dialog = EventCountsDialog(self)
        dialog.exec()

    @Slot()
    def open_mapping_dialog(self):
        dialog = EventMappingDialog(self)
        if dialog.exec():
            self.event_mapping = dialog.event_mapping

    @Slot()
    def toggle_buttons(self):
        """Toggle + and - buttons."""
        n_items = len(self.event_table.selectedItems())
        if self.event_table.rowCount() == 0:  # no events available
            self.remove_button.setEnabled(False)
            self.mapping_button.setEnabled(False)
            self.counts_button.setEnabled(False)
        elif n_items == 2:  # one row (2 items) selected
            self.remove_button.setEnabled(True)
            self.mapping_button.setEnabled(True)
        elif n_items > 2:  # more than one row selected
            self.remove_button.setEnabled(True)
            self.mapping_button.setEnabled(True)
        else:  # no rows selected
            self.remove_button.setEnabled(False)
            self.mapping_button.setEnabled(True)
            self.counts_button.setEnabled(True)

    def add_event(self):
        if self.event_table.selectedIndexes():
            current_row = self.event_table.selectedIndexes()[0].row()
            pos = int(self.event_table.item(current_row, 0).data(Qt.DisplayRole))
        else:
            current_row = 0
            pos = 0
        self.event_table.setSortingEnabled(False)
        self.event_table.insertRow(current_row)
        self.event_table.setItem(current_row, 0, IntTableWidgetItem(pos))
        self.event_table.setItem(current_row, 1, IntTableWidgetItem(0))
        self.event_table.setSortingEnabled(True)

    def remove_event(self):
        rows = {index.row() for index in self.event_table.selectedIndexes()}
        self.event_table.clearSelection()
        for row in sorted(rows, reverse=True):
            value = self.event_table.item(row, 1).value()
            self.event_table.removeRow(row)
            if value not in self.unique_events.keys():
                self.event_mapping.pop(value, None)


class EventCountsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Event Counts")
        self.event_table = parent.event_table
        self.unique_events = parent.unique_events

        self.counts_table = QTableWidget(0, 2)
        self.counts_table.setHorizontalHeaderLabels(["Type", "Count"])
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
        for row, (id_, count) in enumerate(sorted(self.unique_events.items())):
            id_item = IntTableWidgetItem(id_)
            id_item.setFlags(id_item.flags() ^ Qt.ItemIsEditable)
            self.counts_table.insertRow(row)
            self.counts_table.setItem(row, 0, id_item)
            self.counts_table.setItem(row, 1, QTableWidgetItem(str(count)))


class EventMappingDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Event Mapping")
        self.event_table = parent.event_table
        self.unique_events = parent.unique_events
        self.event_mapping = defaultdict(str, parent.event_mapping)  # make copy

        self.mapping_table = QTableWidget(0, 2)
        self.mapping_table.setHorizontalHeaderLabels(["Type", "Label"])
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        self.mapping_table.verticalHeader().setVisible(False)
        self.mapping_table.setShowGrid(False)
        self.mapping_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fill_mapping_table()
        self.clear_button = QPushButton("Clear mapping")

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.mapping_table)
        hbox = QHBoxLayout()
        hbox.addWidget(self.clear_button)
        hbox.addStretch()
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        self.mapping_table.itemChanged.connect(self.store_mapping)
        self.clear_button.clicked.connect(self.clear_mapping)

        self.mapping_table.setMinimumHeight(225)

    def fill_mapping_table(self):
        self.mapping_table.setRowCount(0)
        for row, id_ in enumerate(sorted(self.unique_events.keys())):
            id_item = IntTableWidgetItem(id_)
            id_item.setFlags(id_item.flags() ^ Qt.ItemIsEditable)
            self.mapping_table.insertRow(row)
            self.mapping_table.setItem(row, 0, id_item)
            self.mapping_table.setItem(
                row, 1, QTableWidgetItem(self.event_mapping[id_])
            )

    def store_mapping(self):
        for i in range(self.mapping_table.rowCount()):
            event_id = int(self.mapping_table.item(i, 0).value())
            if event_id not in self.unique_events.keys():
                del self.event_mapping[event_id]
            if self.mapping_table.item(i, 1) is not None:
                self.event_mapping[event_id] = self.mapping_table.item(i, 1).text()

    def clear_mapping(self):
        self.event_mapping.clear()
        self.fill_mapping_table()
