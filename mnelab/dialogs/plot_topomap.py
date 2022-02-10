# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QRadioButton,
)

from .utils import select_all


class PlotTopomapEvokedDialog(QDialog):
    def __init__(self, parent, events):
        super().__init__(parent)
        self.setWindowTitle("Plot topomap of evoked potentials")

        grid = QGridLayout(self)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)

        label = QLabel("Events:")
        label.setAlignment(Qt.AlignTop)
        grid.addWidget(label, 0, 0)
        self.events = QListWidget()
        self.events.insertItems(0, events)
        self.events.setSelectionMode(QListWidget.ExtendedSelection)
        self.events.setMaximumHeight(self.events.sizeHintForRow(0) * 5.5)
        select_all(self.events)
        grid.addWidget(self.events, 0, 1)

        grid.addWidget(QLabel("Average epochs:"), 1, 0)
        self.average_epochs = QComboBox()
        self.average_epochs.addItems(["mean", "median"])
        self.average_epochs.setCurrentIndex(0)
        grid.addWidget(self.average_epochs, 1, 1)

        timepoints = QGroupBox("Select time point(s):")
        timepoints_grid = QGridLayout()
        timepoints_grid.setColumnStretch(0, 2)
        timepoints_grid.setColumnStretch(1, 3)
        timepoints.setLayout(timepoints_grid)
        self.auto = QRadioButton("Auto")
        self.peaks = QRadioButton("Peaks")
        self.interactive = QRadioButton("Interactive")
        self.manual = QRadioButton("Manual:")
        self.timelist = QLineEdit()
        self.auto.setChecked(True)
        timepoints_grid.addWidget(self.auto, 0, 0)
        timepoints_grid.addWidget(self.peaks, 1, 0)
        timepoints_grid.addWidget(self.interactive, 2, 0)
        timepoints_grid.addWidget(self.manual, 3, 0)
        timepoints_grid.addWidget(self.timelist, 3, 1)
        self.timelist.setEnabled(False)
        self.manual.toggled.connect(self.toggle_timelist)
        grid.addWidget(timepoints, 2, 0, 1, 2)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        grid.addWidget(self.buttonbox, 3, 0, 1, -1)
        self.events.itemSelectionChanged.connect(self.toggle_ok)
        self.toggle_ok()
        grid.setSizeConstraint(QGridLayout.SetFixedSize)

    @Slot()
    def toggle_ok(self):
        enable = bool(self.events.selectedItems())
        self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(enable)

    @Slot()
    def toggle_timelist(self):
        self.timelist.setEnabled(self.manual.isChecked())
