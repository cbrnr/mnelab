# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from mnelab.widgets import FlatDoubleSpinBox, set_tooltip


class NpyDialog(QDialog):
    def __init__(self, parent, shape):
        super().__init__(parent)

        self.setWindowTitle("Import NumPy Array")

        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Array Shape:"), 0, 0)
        grid.addWidget(QLabel(f"{' × '.join(map(str, shape))}"), 0, 1)
        fs_label = QLabel("Sampling Frequency:")
        grid.addWidget(fs_label, 1, 0)

        self._fs = FlatDoubleSpinBox()
        self._fs.setRange(0, 20e3)
        self._fs.setValue(250)
        self._fs.setSuffix(" Hz")
        set_tooltip(
            "Set the sampling frequency of the imported data", fs_label, self._fs
        )
        grid.addWidget(self._fs, 1, 1)

        self._transpose = QCheckBox("Transpose")
        if shape[0] > shape[1]:  # transpose if there are more rows than columns
            self._transpose.setChecked(True)
        else:
            self._transpose.setChecked(False)
        self._transpose.setToolTip("Swap the array's channel and time axes")
        grid.addWidget(self._transpose, 2, 0)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.setFocus()

    @property
    def fs(self):
        return self._fs.value()

    @property
    def transpose(self):
        return self._transpose.isChecked()
