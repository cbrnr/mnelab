# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSlot as Slot
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QGridLayout,
                             QLabel, QListWidget, QPushButton, QVBoxLayout)


class AppendDialog(QDialog):
    def __init__(self, parent, compatibles, title="Append data"):
        super().__init__(parent)
        self.setWindowTitle(title)

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Source"), 0, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("Destination"), 0, 2, Qt.AlignCenter)

        self.source = QListWidget(self)
        self.source.setAcceptDrops(True)
        self.source.setDragEnabled(True)
        self.source.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.source.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.source.insertItems(0, [d["name"] for d in compatibles])
        grid.addWidget(self.source, 1, 0)

        self.move_button = QPushButton("→")
        self.move_button.setEnabled(False)
        grid.addWidget(self.move_button, 1, 1, Qt.AlignHCenter)

        self.destination = QListWidget(self)
        self.destination.setAcceptDrops(True)
        self.destination.setDragEnabled(True)
        self.destination.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.destination.setDefaultDropAction(Qt.DropAction.MoveAction)
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

    @property
    def names(self):
        names = []
        for it in range(self.destination.count()):
            names.append(self.destination.item(it).text())
        return names

    @Slot()
    def toggle_ok_button(self):
        """Toggle OK button."""
        if self.destination.count() > 0:
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
        if self.source.selectedItems():
            for item in self.source.selectedItems():
                self.destination.addItem(item.text())
                self.source.takeItem(self.source.row(item))
        elif self.destination.selectedItems():
            for item in self.destination.selectedItems():
                self.source.addItem(item.text())
                self.destination.takeItem(self.destination.row(item))
