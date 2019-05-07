from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLineEdit,
                             QLabel, QDialogButtonBox, QPushButton)
from PyQt5.QtCore import pyqtSlot, Qt, QSize

import mne
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar


class EvokedStatesDialog(QDialog):
    def __init__(self, parent, evoked):
        super().__init__(parent)
        self.resize(1200, 1000)
        self.evoked = evoked.copy().pick_types(eeg=True, meg=True)
        times = self.evoked.times
        n_times = len(times)
        if n_times > 3:
            times = ['{:2.1f}'.format(times[int(n_times / 4)]),
                     ' {:2.1f}'.format(times[int(n_times / 2)]),
                     ' {:2.1f}'.format(times[int(3*n_times / 4)])]
            self.times = QLineEdit()
            self.times.setText(",".join(times))
            self.label = QLabel('Enter all the times (in s) '
                                'separated by a comma...')
            self.label.setMaximumSize(QSize(1000, 25))
            self.layout = QVBoxLayout(self)
            self.layout.addWidget(self.label)
            self.layout.addWidget(self.times)
            self.button = QPushButton('Plot')
            self.button.clicked.connect(self.plot)
            self.layout.addWidget(self.button)
            # Init canvas
            times = self.times.text().replace(' ', '').split(',')
            fig = self.evoked.plot_joint(
                times=times, title="Evoked States Plot", show=False)
            self.canvas = FigureCanvas(fig)
            self.toolbar = NavigationToolbar(self.canvas, self)
            self.layout.addWidget(self.toolbar)
            self.layout.addWidget(self.canvas)
            self.canvas.draw()

    def plot(self):
        self.layout.removeWidget(self.canvas)
        self.layout.removeWidget(self.toolbar)
        times = self.times.text().replace(' ', '').split(',')
        try:
            fig = self.evoked.plot_joint(
                times=times, title="Evoked States Plot", show=False)
        except Exception as e:
            fig = plt.figure()
            print(e)
        self.canvas = FigureCanvas(fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.canvas.draw()
