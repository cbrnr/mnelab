# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
                               QGridLayout, QLineEdit, QRadioButton,
                               QVBoxLayout)


class ReferenceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Modify reference")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()

        self.add_reference = QCheckBox("Add reference channel(s):")

        self.add_channellist = QLineEdit()
        self.add_channellist.setEnabled(False)

        self.set_reference = QCheckBox("Set EEG reference:")

        self.average = QRadioButton("Average")
        self.set_channels = QRadioButton("Channel(s):")

        self.set_channellist = QLineEdit()

        self.add_channellist.setEnabled(False)
        self.set_reference.setChecked(True)
        self.average.setChecked(True)
        self.set_channellist.setEnabled(False)

        self.add_reference.toggled.connect(self.toggle_add_channellist)
        self.set_reference.toggled.connect(self.toggle_set)
        self.set_channels.toggled.connect(self.toggle_set_channellist)
        self.add_reference.toggled.connect(self.toggle_ok)
        self.set_reference.toggled.connect(self.toggle_ok)

        grid.addWidget(self.add_reference, 0, 0)
        grid.addWidget(self.add_channellist, 0, 1)

        grid.addWidget(self.set_reference, 1, 0)

        grid.addWidget(self.average, 2, 0)

        grid.addWidget(self.set_channels, 3, 0)
        grid.addWidget(self.set_channellist, 3, 1)

        vbox.addLayout(grid)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(self.buttonbox)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    def toggle_set(self):
        for element in (
            self.average,
            self.set_channels,
            self.set_channellist,
        ):
            element.setEnabled(self.set_reference.isChecked())

    def toggle_add_channellist(self):
        self.add_channellist.setEnabled(self.add_reference.isChecked())

    def toggle_set_channellist(self):
        self.set_channellist.setEnabled(self.set_channels.isChecked())

    def toggle_ok(self):
        self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(
            self.add_reference.isChecked()
            or self.set_reference.isChecked()
        )
