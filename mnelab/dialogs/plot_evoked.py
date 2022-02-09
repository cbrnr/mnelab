# Copyright (c) MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
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


def select_all(list_widget):
    for i in range(list_widget.count()):
        list_widget.item(i).setSelected(True)


class PlotEvokedDialog(QDialog):
    def __init__(self, parent, channels, events, montage):
        super().__init__(parent)
        self.setWindowTitle("Plot evoked")

        grid = QGridLayout(self)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)

        label = QLabel("Channels:")
        label.setAlignment(Qt.AlignTop)
        grid.addWidget(label, 0, 0)
        self.picks = QListWidget()
        self.picks.insertItems(0, channels)
        self.picks.setSelectionMode(QListWidget.ExtendedSelection)
        select_all(self.picks)
        grid.addWidget(self.picks, 0, 1, 1, 3)

        label = QLabel("Events:")
        label.setAlignment(Qt.AlignTop)
        grid.addWidget(label, 1, 0)
        self.events = QListWidget()
        self.events.insertItems(0, events)
        self.events.setSelectionMode(QListWidget.ExtendedSelection)
        self.events.setMaximumHeight(self.events.sizeHintForRow(0) * 5.5)
        select_all(self.events)
        grid.addWidget(self.events, 1, 1, 1, 3)

        grid.addWidget(QLabel("Show GFP:"), 2, 0)
        self.gfp_group = QButtonGroup()
        self.gfp_no = QRadioButton("No")
        self.gfp_yes = QRadioButton("Yes")
        self.gfp_only = QRadioButton("Only")
        self.gfp_group.addButton(self.gfp_no)
        self.gfp_group.addButton(self.gfp_yes)
        self.gfp_group.addButton(self.gfp_only)
        self.gfp_no.setChecked(True)
        grid.addWidget(self.gfp_no, 2, 2)
        grid.addWidget(self.gfp_yes, 2, 1)
        grid.addWidget(self.gfp_only, 2, 3)

        self.spatial_colors_label = QLabel("Spatial colors:")
        grid.addWidget(self.spatial_colors_label, 3, 0)
        self.spatial_colors = QCheckBox()
        self.spatial_colors.setChecked(False)
        grid.addWidget(self.spatial_colors, 3, 1)

        self.topomaps = QGroupBox("Topomaps")
        self.topomaps.setCheckable(True)
        self.topomaps.setChecked(False)
        topomaps_grid = QGridLayout()
        topomaps_grid.setColumnStretch(0, 2)
        topomaps_grid.setColumnStretch(1, 3)
        self.topomaps_peaks = QRadioButton("Peaks")
        self.topomaps_auto = QRadioButton("Auto")
        self.topomaps_times = QRadioButton("Time(s):")
        self.topomaps_timelist = QLineEdit()
        topomaps_grid.addWidget(self.topomaps_peaks, 0, 0)
        topomaps_grid.addWidget(self.topomaps_auto, 1, 0)
        topomaps_grid.addWidget(self.topomaps_times, 2, 0)
        topomaps_grid.addWidget(self.topomaps_timelist, 2, 1)
        self.topomaps_peaks.setChecked(True)
        self.topomaps_timelist.setEnabled(False)
        self.topomaps.setLayout(topomaps_grid)
        grid.addWidget(self.topomaps, 4, 0, 1, 4)

        if montage is None:
            self.topomaps.setTitle("Topomaps (requires montage information)")
            self.topomaps.setCheckable(False)
            self.topomaps.setEnabled(False)
            self.topomaps.setStyleSheet("QGroupBox::title{ color: gray }")

        self.gfp_only.toggled.connect(self.toggle_spatial_colors)
        self.topomaps_times.toggled.connect(self.toggle_topomaps_timelist)
        self.topomaps.toggled.connect(self.toggle_ok)
        self.topomaps_times.toggled.connect(self.toggle_ok)
        self.topomaps_timelist.textChanged.connect(self.toggle_ok)

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

    @Slot()
    def toggle_topomaps_timelist(self):
        self.topomaps_timelist.setEnabled(self.topomaps_times.isChecked())

    @Slot()
    def toggle_spatial_colors(self):
        self.spatial_colors.setEnabled(not self.gfp_only.isChecked())
        self.spatial_colors_label.setEnabled(not self.gfp_only.isChecked())


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

        grid.addWidget(QLabel("Average epochs:"), 2, 0)
        self.average_epochs = QComboBox()
        self.average_epochs.addItems(["mean", "median"])
        self.average_epochs.setCurrentIndex(0)
        grid.addWidget(self.average_epochs, 2, 1)

        grid.addWidget(QLabel("Combine channels:"), 3, 0)
        self.combine_channels = QComboBox()
        self.combine_channels.addItems(["gfp", "mean", "median", "std"])
        self.combine_channels.setCurrentIndex(0)
        grid.addWidget(self.combine_channels, 3, 1)

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
