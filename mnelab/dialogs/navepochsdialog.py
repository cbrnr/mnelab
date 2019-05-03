from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QListWidget)
from PyQt5.QtCore import pyqtSlot, Qt

import mne
import matplotlib.pyplot as plt


class NavEpochsDialog(QDialog):
    def __init__(self, parent, epochs):
        super().__init__(parent)
        self.resize(1000, 800)
        self.epochs = epochs
        channels = self.epochs.info['ch_names']
        self.channels = QListWidget()
        self.channels.insertItems(0, channels)
        self.channels.setSelectionMode(QListWidget.SingleSelection)
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(self.channels)
        self.fig = plt.figure(figsize=(10, 10))
        print(self.fig)
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)
        self.channels.item(0).setSelected(True)
        self.channels.itemSelectionChanged.connect(self.update)
        self.update()

    def update(self):
        self.fig.clear()
        gs = self.fig.add_gridspec(2, 10)
        ax = [self.fig.add_subplot(gs[0, :9]),
              self.fig.add_subplot(gs[1, :10]),
              self.fig.add_subplot(gs[0, 9])]
        index = self.epochs.info['ch_names'].index(
                    self.channels.selectedItems()[0].data(0))
        mne.viz.plot_epochs_image(self.epochs, index,
                                  axes=ax, show=False)[0]
        # add the new canvas at the position of the old one
        self.canvas.draw()
