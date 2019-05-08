from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLineEdit,
                             QLabel, QDialogButtonBox, QPushButton)
from PyQt5.QtCore import pyqtSlot, Qt, QSize

import mne
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar


class EvokedTopoDialog(QDialog):
    def __init__(self, parent, evoked):
        super().__init__(parent)
        self.resize(800, 400)
        self.evoked = evoked.copy().pick_types(eeg=True, meg=True)
        self.chans = Counter([mne.io.pick.channel_type(self.evoked.info, i)
                             for i in range(self.evoked.info["nchan"])])
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
            self.to_delete = []
            self.plot()

    def plot(self):
        """Erase and plot the new figures."""
        for widget in self.to_delete:
            widget.close()
        self.to_delete = []
        times = self.times.text().replace(' ', '').split(',')
        n_plot = 0
        for type in self.chans.keys():
            if type in ['eeg', 'mag', 'grad']:
                n_plot += 1
                try:
                    plt.close('all')
                    fig = self.evoked.plot_topomap(
                        times=times, show=False, ch_type=type,
                        title=type + ' ({} channels)'.format(self.chans[type]))
                except Exception as e:
                    fig = plt.figure()
                    print(e)

                canvas = FigureCanvas(fig)
                toolbar = NavigationToolbar(canvas, self)
                self.layout.addWidget(toolbar)
                self.layout.addWidget(canvas)
                self.to_delete.append(toolbar)
                self.to_delete.append(canvas)
        self.resize(800, 100 + n_plot * 300)
