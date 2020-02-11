# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                            QDialogButtonBox, QListWidget)


class AppendDialog(QDialog):
    def __init__(self, parent, compatibles, title="Append data"):
        super().__init__(parent)
        self.setWindowTitle(title)

        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        grid.addWidget(QLabel("Source"), 2, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("Destination"), 2, 4, Qt.AlignCenter)

        source = QListWidget(self)
        source.setAcceptDrops(True)
        source.setDragEnabled(True)
        source.setDefaultDropAction(Qt.DropAction.MoveAction)
        source.insertItems(0, [d["name"] for d in compatibles])
        grid.addWidget(source, 3, 0, 1, 2)

        grid.addWidget(QLabel(" -> "), 3, 2, 1, 2, Qt.AlignHCenter)

        self.destination = QListWidget(self)
        self.destination.setAcceptDrops(True)
        self.destination.setDragEnabled(True)
        self.destination.setDefaultDropAction(Qt.DropAction.MoveAction)
        grid.addWidget(self.destination, 3, 4, 1, 2)

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
        for it in range(self.destination.count()):
            raw_names.append(self.destination.model().index(it).data())
        return raw_names
