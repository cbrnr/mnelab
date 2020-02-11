# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                            QDialogButtonBox, QListWidget)


class MyListWidget(QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setMinimumSize(60, 30)


class ConcatenateDataDialog(QDialog):
    def __init__(self, parent, names, title="Concatenate data"):
        super().__init__(parent)
        self.setWindowTitle(title)

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Compatible data"), 2, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("Append order"), 2, 4, Qt.AlignCenter)

        self.listAvailable = MyListWidget(self)
        self.listAvailable.list = names
        self.listAvailable.insertItems(0, names)
        grid.addWidget(self.listAvailable, 3, 0, 1, 2)

        grid.addWidget(QLabel(" -> "), 3, 2, 1, 2, Qt.AlignHCenter)

        self.listOrdered = MyListWidget(self)
        self.listOrdered.list = []
        grid.addWidget(self.listOrdered, 3, 4, 1, 2)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        grid.addWidget(buttonbox, 4, 0, 2, 6, Qt.AlignRight)

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vbox.addLayout(grid)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def raw_names(self):
        raw_names = []
        for it in range(self.listOrdered.count()):
            raw_names.append(self.listOrdered.model().index(it).data())
        return raw_names
