# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#          Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                            QLineEdit, QDialogButtonBox, QListWidget)


class MyListWidget(QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setMinimumSize(60, 30)

    def setSize(self, height, width):
        self.setMaximumWidth(width)
        self.setMaximumHeight(height)


class ConcatenateDataDialog(QDialog):
    def __init__(self, parent, current_name, names, title="Concatenate data"):
        super().__init__(parent)
        self.setWindowTitle(title)
        vbox = QVBoxLayout(self)

        grid = QGridLayout()
        grid.addWidget(QLabel("Name: "), 0, 0, 1, 2, Qt.AlignHCenter)
        self.nameEdit = QLineEdit(f"{current_name}_concat")
        grid.addWidget(self.nameEdit, 0, 2, 1, 3)

        grid.addWidget(QLabel(""), 1, 0)

        grid.addWidget(QLabel("Compatible data"), 2, 0, Qt.AlignCenter)
        grid.addWidget(QLabel("Append order"), 2, 4, Qt.AlignCenter)

        self.listAvailable = MyListWidget(self)
        self.listAvailable.list = names
        self.listAvailable.insertItems(0, names)
        list_height = (2 + len(names)) * self.listAvailable.sizeHintForRow(0)
        list_width = 2. * self.listAvailable.sizeHintForColumn(0)

        self.listAvailable.setSize(list_height, list_width)
        grid.addWidget(self.listAvailable, 3, 0)

        grid.addWidget(QLabel(" --> "), 3, 2, 1, 2, Qt.AlignHCenter)

        self.listOrdered = MyListWidget(self)
        self.listOrdered.list = []
        self.listOrdered.setSize(list_height, list_width)
        grid.addWidget(self.listOrdered, 3, 4)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        grid.addWidget(buttonbox, 4, 0, 2, 6, Qt.AlignRight)

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vbox.addLayout(grid)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def data_name(self):
        name = self.nameEdit.text()
        return name if name else None

    @property
    def raw_names(self):
        raw_names = []
        for it in range(self.listOrdered.count()):
            raw_names.append(self.listOrdered.model().index(it).data())
        return raw_names
