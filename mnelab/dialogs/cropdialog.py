# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from qtpy.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
                            QDoubleSpinBox, QFormLayout, QSizePolicy)

from qtpy.QtCore import Slot


class CropDialog(QDialog):
    def __init__(self, parent, start, stop):
        super().__init__(parent)
        self.setWindowTitle("Crop data")

        form = QFormLayout(self)
        label_size = QSizePolicy.Expanding
        self.start_checkbox = QCheckBox("Start time:")
        self.start_checkbox.setSizePolicy(label_size, label_size)
        self.start_checkbox.setChecked(True)
        self.start_checkbox.stateChanged.connect(self.toggle_start)
        self._start = QDoubleSpinBox()
        self._start.setMaximum(999999)
        self._start.setValue(start)
        self._start.setDecimals(2)
        self._start.setSuffix(" s")
        form.addRow(self.start_checkbox, self._start)

        self.stop_checkbox = QCheckBox("Stop time:")
        self.stop_checkbox.setChecked(True)
        self.stop_checkbox.setSizePolicy(label_size, label_size)
        self.stop_checkbox.stateChanged.connect(self.toggle_stop)
        self._stop = QDoubleSpinBox()
        self._stop.setMaximum(999999)
        self._stop.setValue(stop)
        self._stop.setDecimals(2)
        self._stop.setSuffix(" s")
        form.addRow(self.stop_checkbox, self._stop)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        form.addRow(buttonbox)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        form.setSizeConstraint(QFormLayout.SetFixedSize)

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
