# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox,
                            QFormLayout, QLabel)


class FilterDialog(QDialog):
    def __init__(self, parent, f_range):
        super().__init__(parent)
        self.setWindowTitle("Filter data")

        form = QFormLayout(self)
        self.lowedit = QDoubleSpinBox()
        self.lowedit.setRange(f_range[0], f_range[1])
        self.lowedit.setValue(f_range[0])
        self.lowedit.setDecimals(1)
        self.lowedit.setSuffix(" Hz")
        form.addRow(QLabel("Low cutoff frequency:"), self.lowedit)

        self.highedit = QDoubleSpinBox()
        self.highedit.setRange(f_range[0], f_range[1])
        self.highedit.setValue(f_range[0])
        self.highedit.setDecimals(1)
        self.highedit.setSuffix(" Hz")

        form.addRow(QLabel("High cutoff frequency:"), self.highedit)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        form.addRow(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        form.setSizeConstraint(QFormLayout.SetFixedSize)

    @property
    def low(self):
        return self.lowedit.value()

    @property
    def high(self):
        return self.highedit.value()