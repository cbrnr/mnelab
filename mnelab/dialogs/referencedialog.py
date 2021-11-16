# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QGridLayout, QLineEdit,
                               QRadioButton, QVBoxLayout)


class ReferenceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Set reference")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        self.average = QRadioButton("Average")
        self.channels = QRadioButton("Channel(s):")
        self.average.toggled.connect(self.toggle)
        self.channellist = QLineEdit()
        self.channellist.setEnabled(False)
        self.average.setChecked(True)
        grid.addWidget(self.average, 0, 0)
        grid.addWidget(self.channels, 1, 0)
        grid.addWidget(self.channellist, 1, 1)
        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def toggle(self):
        if self.average.isChecked():
            self.channellist.setEnabled(False)
        else:
            self.channellist.setEnabled(True)
