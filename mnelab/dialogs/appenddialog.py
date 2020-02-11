# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                            QDialogButtonBox, QListWidget, QAbstractItemView)


class AppendDialog(QDialog):
    def __init__(self, parent, compatibles, title="Append data"):
        super().__init__(parent)
        self.setWindowTitle(title)

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

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
        vbox.addLayout(grid)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vbox.addWidget(buttonbox)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def names(self):
        names = []
        for it in range(self.destination.count()):
            names.append(self.destination.item(it).text())
        return names
