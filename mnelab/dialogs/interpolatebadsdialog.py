from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QDialogButtonBox, QComboBox,
                             QCheckBox, QDoubleSpinBox)


class InterpolateBadsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Filter data")
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
        grid.addWidget(QLabel("Origin (x,y,z):"), 2, 0)
        self.x = QDoubleSpinBox()
        self.x.setValue(0.)
        grid.addWidget(self.x, 2, 1)
        self.y = QDoubleSpinBox()
        self.y.setValue(0.)
        grid.addWidget(self.y, 2, 2)
        self.z = QDoubleSpinBox()
        self.z.setValue(0.04)
        grid.addWidget(self.z, 2, 3)

        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def origin(self):
        x = float(self.x.value())
        y = float(self.y.value())
        z = float(self.z.value())
        return [x, y, z]

    @property
    def mode(self):
        return str(self.mode_select.currentText())

    @property
    def reset_bads(self):
        return bool(self.reset_bads_checkbox.isChecked())
