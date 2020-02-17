# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox,
                            QGridLayout, QLabel, QListWidget)


class AppendDialog(QDialog):
    def __init__(self, parent, compatibles, title="Append data"):
        super().__init__(parent)
        self.setWindowTitle(title)

        grid = QGridLayout(self)
        grid.addWidget(QLabel("Source"), 0, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("Destination"), 0, 2, Qt.AlignCenter)

        source = QListWidget(self)
        source.setAcceptDrops(True)
        source.setDragEnabled(True)
        source.setSelectionMode(QAbstractItemView.ExtendedSelection)
        source.setDefaultDropAction(Qt.DropAction.MoveAction)
        source.insertItems(0, [d["name"] for d in compatibles])
        grid.addWidget(source, 1, 0)

        grid.addWidget(QLabel("->"), 1, 1, Qt.AlignHCenter)

        self.destination = QListWidget(self)
        self.destination.setAcceptDrops(True)
        self.destination.setDragEnabled(True)
        self.destination.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.destination.setDefaultDropAction(Qt.DropAction.MoveAction)
        grid.addWidget(self.destination, 1, 2)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                          QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        grid.addWidget(self.buttonbox, 2, 1, 1, 3)
        grid.setSizeConstraint(QGridLayout.SetFixedSize)
        self.destination.model().rowsInserted.connect(self.toggle_buttons)
        self.destination.model().rowsRemoved.connect(self.toggle_buttons)
        self.toggle_buttons()

    @property
    def names(self):
        names = []
        for it in range(self.destination.count()):
            names.append(self.destination.item(it).text())
        return names

    @Slot()
    def toggle_buttons(self):
        """Toggle OK button.
        """
        if self.destination.count() > 0:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
