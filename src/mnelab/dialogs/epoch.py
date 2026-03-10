# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QListWidget,
)

from mnelab.widgets import FlatDoubleSpinBox


class EpochDialog(QDialog):
    def __init__(self, parent, event_types):
        super().__init__(parent)
        self.setWindowTitle("Create Epochs")

        grid = QGridLayout(self)
        label = QLabel("Events:")
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        grid.addWidget(label, 0, 0, 1, 1)

        self.events = QListWidget()
        self.events.insertItems(0, event_types)
        self.events.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        grid.addWidget(self.events, 0, 1, 1, 2)

        grid.addWidget(QLabel("Interval around events:"), 1, 0, 1, 1)
        self.tmin = FlatDoubleSpinBox()
        self.tmin.setMinimum(-10000)
        self.tmin.setValue(-0.2)
        self.tmin.setSingleStep(0.1)
        self.tmin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.tmax = FlatDoubleSpinBox()
        self.tmax.setMinimum(-10000)
        self.tmax.setValue(0.5)
        self.tmax.setSingleStep(0.1)
        self.tmax.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.tmin, 1, 1, 1, 1)
        grid.addWidget(self.tmax, 1, 2, 1, 1)

        self.baseline = QCheckBox("Baseline Correction:")
        self.baseline.setChecked(True)
        self.baseline.stateChanged.connect(self.toggle_baseline)
        grid.addWidget(self.baseline, 2, 0, 1, 1)
        self.a = FlatDoubleSpinBox()
        self.a.setMinimum(-10000)
        self.a.setValue(-0.2)
        self.a.setSingleStep(0.1)
        self.a.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.b = FlatDoubleSpinBox()
        self.b.setMinimum(-10000)
        self.b.setValue(0)
        self.b.setSingleStep(0.1)
        self.b.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.a, 2, 1, 1, 1)
        grid.addWidget(self.b, 2, 2, 1, 1)
        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        grid.addWidget(self.buttonbox, 3, 0, 1, -1)
        self.events.itemSelectionChanged.connect(self.toggle_ok)
        self.toggle_ok()
        grid.setSizeConstraint(QGridLayout.SizeConstraint.SetFixedSize)
        self.setFocus()

    @Slot()
    def toggle_ok(self):
        if self.events.selectedItems():
            self.buttonbox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    @Slot()
    def toggle_baseline(self):
        if self.baseline.isChecked():
            self.a.setEnabled(True)
            self.b.setEnabled(True)
        else:
            self.a.setEnabled(False)
            self.b.setEnabled(False)

    @property
    def selected_events(self):
        return [int(item.text()) for item in self.events.selectedItems()]
