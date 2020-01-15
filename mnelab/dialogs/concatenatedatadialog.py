# Authors: Lukas Stranger <l.stranger@student.tugraz.at>
#
# License: BSD clause(3-)

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QDialogButtonBox, QListWidget)


class ConcatenateDataDialog(QDialog):
    def __init__(self, parent, current_name, ds_names, title="Concatenate data"):
        super().__init__(parent)
        self.setWindowTitle(title)
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Concatenate data to '{}'".format(current_name)), 0, 0, 1, 2)
        grid.addWidget(QLabel("Name:"), 1, 0)
        self.nameedit = QLineEdit()
        grid.addWidget(self.nameedit, 1, 1)

        grid.addWidget(QLabel("Concatenate data:"), 2, 0)
        self.mylist = QListWidget()
        self.mylist.insertItems(0, ds_names)
        self.mylist.setSelectionMode(QListWidget.ExtendedSelection)

        grid.addWidget(self.mylist, 2, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def name(self):
        name = self.nameedit.text()
        return name if name else None

    @property
    def raw_names(self):
        raw_names = [item.data(0) for item in self.mylist.selectedItems()]
        return raw_names if raw_names else None
