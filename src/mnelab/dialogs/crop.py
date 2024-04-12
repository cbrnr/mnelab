# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QVBoxLayout,
)


class CropDialog(QDialog):
    def __init__(self, parent, start, stop):
        super().__init__(parent)
        self.setWindowTitle("Crop data")
        vbox = QVBoxLayout(self)
        grid = QGridLayout()
        self.start_checkbox = QCheckBox("Start time:")
        self.start_checkbox.setChecked(True)
        self.start_checkbox.stateChanged.connect(self.toggle_start)
        grid.addWidget(self.start_checkbox, 0, 0)
        self._start = QDoubleSpinBox()
        self._start.setMaximum(stop)
        self._start.setValue(start)
        self._start.setDecimals(2)
        self._start.setSuffix(" s")
        grid.addWidget(self._start, 0, 1)

        self.stop_checkbox = QCheckBox("Stop time:")
        self.stop_checkbox.setChecked(True)
        self.stop_checkbox.stateChanged.connect(self.toggle_stop)
        grid.addWidget(self.stop_checkbox, 1, 0)
        self._stop = QDoubleSpinBox()
        self._stop.setMaximum(stop)
        self._stop.setValue(stop)
        self._stop.setDecimals(2)
        self._stop.setSuffix(" s")
        grid.addWidget(self._stop, 1, 1)
        vbox.addLayout(grid)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

    @property
    def start(self):
        if self.start_checkbox.isChecked():
            return self._start.value()
        else:
            return None

    @property
    def stop(self):
        if self.stop_checkbox.isChecked():
            return self._stop.value()
        else:
            return None

    @Slot()
    def toggle_start(self):
        if self.start_checkbox.isChecked():
            self._start.setEnabled(True)
        else:
            self._start.setEnabled(False)

    @Slot()
    def toggle_stop(self):
        if self.stop_checkbox.isChecked():
            self._stop.setEnabled(True)
        else:
            self._stop.setEnabled(False)
