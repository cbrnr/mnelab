# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)


class NpyDialog(QDialog):
    def __init__(self, parent, shape):
        super().__init__(parent)

        self.setWindowTitle("Import NumPy array")

        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Array shape:"), 0, 0)
        grid.addWidget(QLabel(f"{' × '.join(map(str, shape))}"), 0, 1)
        grid.addWidget(QLabel("Sampling frequency:"), 1, 0)

        self._fs = QDoubleSpinBox()
        self._fs.setRange(0, 20e3)
        self._fs.setValue(250)
        self._fs.setSuffix(" Hz")
        grid.addWidget(self._fs, 1, 1)

        self._transpose = QCheckBox("Transpose")
        if shape[0] > shape[1]:  # transpose if there are more rows than columns
            self._transpose.setChecked(True)
        else:
            self._transpose.setChecked(False)
        grid.addWidget(self._transpose, 2, 0)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def fs(self):
        return self._fs.value()

    @property
    def transpose(self):
        return self._transpose.isChecked()
