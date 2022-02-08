# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QGridLayout, QLabel, QListWidget)


def select_all(list_widget):
    for i in range(list_widget.count()):
        list_widget.item(i).setSelected(True)


class PlotEvokedComparisonDialog(QDialog):
    def __init__(self, parent, channels, events):
        super().__init__(parent)
        self.setWindowTitle("Plot evoked comparison")

        grid = QGridLayout(self)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)

        label = QLabel("Channels:")
        label.setAlignment(Qt.AlignTop)
        grid.addWidget(label, 0, 0, 1, 1)
        self.picks = QListWidget()
        self.picks.insertItems(0, channels)
        self.picks.setSelectionMode(QListWidget.ExtendedSelection)
        select_all(self.picks)
        grid.addWidget(self.picks, 0, 1, 1, 1)

        label = QLabel("Events:")
        label.setAlignment(Qt.AlignTop)
        grid.addWidget(label, 1, 0, 1, 1)
        self.events = QListWidget()
        self.events.insertItems(0, events)
        self.events.setSelectionMode(QListWidget.ExtendedSelection)
        self.events.setMaximumHeight(self.events.sizeHintForRow(0) * 5.5)
        select_all(self.events)
        grid.addWidget(self.events, 1, 1, 1, 1)

        grid.addWidget(QLabel("Average method:"), 2, 0)
        self.average_method = QComboBox()
        self.average_method.addItems(["mean", "median"])
        self.average_method.setCurrentIndex(0)
        grid.addWidget(self.average_method, 2, 1)

        grid.addWidget(QLabel("Combine across channels:"), 3, 0)
        self.combine = QComboBox()
        self.combine.addItems(["gfp", "mean", "median", "std"])
        self.combine.setCurrentIndex(0)
        grid.addWidget(self.combine, 3, 1)

        grid.addWidget(QLabel("Confidence intervals:"), 4, 0)
        self.confidence_intervals = QCheckBox()
        self.confidence_intervals.setChecked(True)
        grid.addWidget(self.confidence_intervals, 4, 1)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        grid.addWidget(self.buttonbox, 5, 0, 1, -1)
        self.picks.itemSelectionChanged.connect(self.toggle_ok)
        self.events.itemSelectionChanged.connect(self.toggle_ok)
        self.toggle_ok()
        grid.setSizeConstraint(QGridLayout.SetFixedSize)

    @Slot()
    def toggle_ok(self):
        if self.picks.selectedItems() and self.events.selectedItems():
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setEnabled(False)
