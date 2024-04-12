# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


class InterpolateBadsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Interpolate bad channels")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        grid.addWidget(QLabel("Reset bads:"), 0, 0)
        self.reset_bads_checkbox = QCheckBox()
        self.reset_bads_checkbox.setChecked(True)
        grid.addWidget(self.reset_bads_checkbox, 0, 1)
        grid.addWidget(QLabel("Mode:"), 1, 0)
        self.mode_select = QComboBox()
        self.modes = {"Accurate": "accurate", "Fast": "fast"}
        self.mode_select.addItems(self.modes.keys())
        self.mode_select.setCurrentText("Accurate")
        grid.addWidget(self.mode_select, 1, 1)
        grid.addWidget(QLabel("Origin (x, y, z):"), 2, 0)
        hbox = QHBoxLayout()
        self.x = QDoubleSpinBox()
        self.x.setValue(0)
        self.x.setDecimals(3)
        hbox.addWidget(self.x)
        self.y = QDoubleSpinBox()
        self.y.setValue(0)
        self.y.setDecimals(3)
        hbox.addWidget(self.y)
        self.z = QDoubleSpinBox()
        self.z.setValue(0.04)
        self.z.setDecimals(3)
        hbox.addWidget(self.z)
        grid.addLayout(hbox, 2, 1)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def origin(self):
        x = float(self.x.value())
        y = float(self.y.value())
        z = float(self.z.value())
        return x, y, z

    @property
    def mode(self):
        return self.mode_select.currentText()

    @property
    def reset_bads(self):
        return self.reset_bads_checkbox.isChecked()
