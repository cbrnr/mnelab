from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox,
                             QTableWidget, QTableWidgetItem, QAbstractItemView)
from PyQt5.QtCore import Qt


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
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.table)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.resize(300, 500)
