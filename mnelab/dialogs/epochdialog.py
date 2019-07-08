from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QDialogButtonBox, QComboBox,
                             QPushButton, QListWidget, QStatusBar,
                             QToolBar, QCheckBox)
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QDoubleValidator

from mne.viz import plot_events
from numpy import unique


class EpochDialog(QDialog):
    def __init__(self, parent, events, raw, title="Create Epochs"):
        super().__init__(parent)
        self.setWindowTitle(title)
        selected = None
        event_labels = unique(events[:, 2]).astype(str)
        self.events = events
        grid = QGridLayout(self)
        grid.addWidget(QLabel("Choose Marker"), 1, 0, 1, 1)
        self.labels = QListWidget()
        self.labels.insertItems(0, event_labels)
        self.labels.setSelectionMode(QListWidget.ExtendedSelection)
        if selected is not None:
            for i in range(self.labels.count()):
                if self.labels.item(i).data(0) == selected:
                    self.labels.item(i).setSelected(True)
        grid.addWidget(self.labels, 1, 1, 1, 2)
        grid.addWidget(QLabel("Interval around event"), 2, 0, 1, 1)
        self.tmin = QLineEdit(self)
        self.tmax = QLineEdit(self)
        grid.addWidget(self.tmin, 2, 1, 1, 1)
        grid.addWidget(self.tmax, 2, 2, 1, 1)
        self.baseline = QCheckBox("&Baseline Correction")
        grid.addWidget(self.baseline, 3, 0, 1, 1)
        self.a = QLineEdit(self)
        self.b = QLineEdit(self)
        grid.addWidget(self.a, 3, 1, 1, 1)
        grid.addWidget(self.b, 3, 2, 1, 1)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        grid.addWidget(buttonbox, 5, 2, 2, 2)
