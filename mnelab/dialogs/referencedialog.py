# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout,
                            QLineEdit, QRadioButton)


class ReferenceDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Set reference")

        form = QFormLayout(self)
        self.average = QRadioButton("Average")
        self.average.setChecked(True)
        form.addRow(self.average)

        self.channellist = QLineEdit()
        self.channellist.setEnabled(False)
        form.addRow(QRadioButton("Channel(s):"), self.channellist)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        form.addRow(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        form.setSizeConstraint(QFormLayout.SetFixedSize)

        self.average.toggled.connect(self.toggle)

    def toggle(self):
        if self.average.isChecked():
            self.channellist.setEnabled(False)
        else:
            self.channellist.setEnabled(True)
