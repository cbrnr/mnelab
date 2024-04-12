# © MNELAB developers
#
# License: BSD (3-clause)

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
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

from mnelab.dialogs.utils import select_all


class PlotEvokedDialog(QDialog):
    def __init__(self, parent, channels, events, montage):
        super().__init__(parent)
        self.setWindowTitle("Plot evoked")

        grid = QGridLayout(self)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)

        label = QLabel("Channels:")
        label.setAlignment(Qt.AlignTop)
        grid.addWidget(label, 0, 0)
        self.picks = QListWidget()
        self.picks.insertItems(0, channels)
        self.picks.setSelectionMode(QListWidget.ExtendedSelection)
        select_all(self.picks)
        grid.addWidget(self.picks, 0, 1)

        label = QLabel("Events:")
        label.setAlignment(Qt.AlignTop)
        grid.addWidget(label, 1, 0)
        self.events = QListWidget()
        self.events.insertItems(0, events)
        self.events.setSelectionMode(QListWidget.ExtendedSelection)
        self.events.setMaximumHeight(self.events.sizeHintForRow(0) * 5.5)
        select_all(self.events)
        grid.addWidget(self.events, 1, 1)

        grid.addWidget(QLabel("Show GFP:"), 2, 0)
        self.gfp = QCheckBox()
        self.gfp.setChecked(False)
        grid.addWidget(self.gfp, 2, 1)

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


class PlotEvokedTopomaps(QDialog):
    def __init__(self, parent, events):
        super().__init__(parent)
        self.setWindowTitle("Plot evoked topomaps")

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
