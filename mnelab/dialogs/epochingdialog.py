from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QDialogButtonBox, QComboBox,
                             QPushButton, QListWidget, QStatusBar,
                             QToolBar)
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QDoubleValidator

from mne.viz import plot_events
from numpy import unique


class EpochingDialog(QDialog):

    def __init__(self, parent, events, raw, title="Epoching..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        selected = None
        event_labels = unique(events[:, 2]).astype(str)
        self.events = events
        grid = QGridLayout(self)
        plot_button = QPushButton("Plot events")
        plot_button.clicked.connect(self.plot_events)
        grid.addWidget(plot_button, 0, 0, 1, 3)
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
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        grid.addWidget(buttonbox, 5, 2, 2, 2)

    def plot_events(self):
        fig = plot_events(self.events, show=False)
        win = fig.canvas.manager.window
        win.setWindowModality(Qt.WindowModal)
        win.setWindowTitle("Montage")
        win.findChild(QStatusBar).hide()
        win.findChild(QToolBar).hide()
        fig.show()
