from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from app.ui.avg_epochs_tfr_UI import Ui_AvgTFRWindow


class AvgTFRWindow(QDialog):

    def __init__(self, avgTFR, parent=None):
        super(AvgTFRWindow, self).__init__(parent)
        self.avg = avgTFR
        self.ui = Ui_AvgTFRWindow()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.setup()

    # Setup functions
    # =====================================================================
    def setup(self):
        self.set_canvas()
        self.set_box()
        self.set_bindings()
        self.set_slider()
        self.value_changed()
        self.ui.vmax.setMaxLength(6)
        self.ui.vmin.setMaxLength(6)
        self.ui.fmax.setMaxLength(6)
        self.ui.fmin.setMaxLength(6)
        self.ui.tmin.setMaxLength(6)
        self.ui.tmax.setMaxLength(6)

    # ---------------------------------------------------------------------
    def set_canvas(self):
        """setup canvas for matplotlib
        """
        self.ui.figure = plt.figure(figsize=(10, 10))
        self.ui.figure.patch.set_facecolor('None')
        self.ui.canvas = FigureCanvas(self.ui.figure)
        self.ui.canvas.setStyleSheet('background-color:transparent;')
        # Matplotlib toolbar
        self.ui.toolbar = NavigationToolbar(self.ui.canvas, self)
        self.ui.matplotlibLayout.addWidget(self.ui.toolbar)
        self.ui.matplotlibLayout.addWidget(self.ui.canvas)

    # ---------------------------------------------------------------------
    def set_box(self):
        """Setup box names
        """
        self.ui.displayBox.addItem('Time-Frequency plot')
        self.ui.displayBox.addItem('Channel-Frequency plot')
        self.ui.displayBox.addItem('Channel-Time plot')
        if self.avg.with_coord != []:  # Add topomap if there are coordinates
            self.ui.displayBox.addItem('Topomap plot')
        self.plotType = 'Time-Frequency plot'

    # ---------------------------------------------------------------------
    def set_slider(self):
        """Setup the main slider
        """
        self.index = self.ui.mainSlider.value()
        self.ui.mainSlider.setMinimum(0)
        self.ui.fSlider.setMaximum(len(self.avg.tfr.freqs) - 2)
        self.ui.fSlider.setMinimum(1)
        self.ui.fSlider.setValue(0)
        self.ui.fSlider.setTickInterval(1)
        self.ui.tSlider.setMaximum(len(self.avg.tfr.times) - 2)
        self.ui.tSlider.setMinimum(1)
        self.ui.tSlider.setValue(0)
        self.ui.tSlider.setTickInterval(1)
        self.update_slider()

    # ---------------------------------------------------------------------
    def set_bindings(self):
        """Set the bindings
        """
        self.ui.vmin.editingFinished.connect(self.value_changed)
        self.ui.vmax.editingFinished.connect(self.value_changed)
        self.ui.tmin.editingFinished.connect(self.value_changed)
        self.ui.tmax.editingFinished.connect(self.value_changed)
        self.ui.fmin.editingFinished.connect(self.value_changed)
        self.ui.fmax.editingFinished.connect(self.value_changed)
        self.ui.fSlider.valueChanged.connect(self.slider_freq_changed)
        self.ui.tSlider.valueChanged.connect(self.slider_time_changed)
        self.ui.displayBox.currentIndexChanged.connect(self.update_slider)
        self.ui.mainSlider.valueChanged.connect(self.value_changed)
        self.ui.log.stateChanged.connect(self.value_changed)

    # Updating functions
    # =====================================================================
    def value_changed(self):
        """Gets called when scaling is changed
        """
        self.index = self.ui.mainSlider.value()
        self.log = self.ui.log.checkState()
        try:
            self.fmax = float(self.ui.fmax.text())
            if self.fmax > self.avg.tfr.freqs[-1]:
                self.fmax = self.avg.tfr.freqs[-1]
        except ValueError:
            self.fmax = self.avg.tfr.freqs[-1]

        try:
            self.fmin = float(self.ui.fmin.text())
            if self.fmin < self.avg.tfr.freqs[0]:
                self.fmin = self.avg.tfr.freqs[0]
        except ValueError:
            self.fmin = self.avg.tfr.freqs[0]

        try:
            self.tmax = float(self.ui.tmax.text())
            if self.tmax > self.avg.tfr.times[-1]:
                self.tmax = self.avg.tfr.times[-1]
        except ValueError:
            self.tmax = self.avg.tfr.times[-1]

        try:
            self.tmin = float(self.ui.tmin.text())
            if self.tmin < self.avg.tfr.times[0]:
                self.tmin = self.avg.tfr.times[0]
        except ValueError:
            self.tmin = self.avg.tfr.times[0]

        try:
            self.vmax = float(self.ui.vmax.text())
        except ValueError:
            self.vmax = None

        try:
            self.vmin = float(self.ui.vmin.text())
        except ValueError:
            self.vmin = None
        self.plot()

    # ---------------------------------------------------------------------
    def slider_freq_changed(self):
        """Change the values of frequency and time for topomap when
        the slider is moved
        """
        freq_index = self.ui.fSlider.value()
        fmin, fmax = (self.avg.tfr.freqs[freq_index - 1],
                      self.avg.tfr.freqs[freq_index + 1])
        self.ui.fmin.setText(str(fmin))
        self.ui.fmax.setText(str(fmax))
        self.value_changed()

    # ---------------------------------------------------------------------
    def slider_time_changed(self):
        """Change the values of time and time for topomap when
        the slider is moved
        """
        time_index = self.ui.tSlider.value()
        tmin, tmax = (self.avg.tfr.times[time_index - 1],
                      self.avg.tfr.times[time_index + 1])
        self.ui.tmin.setText(str(tmin))
        self.ui.tmax.setText(str(tmax))
        self.value_changed()

    # ---------------------------------------------------------------------
    def update_slider(self):
        """Update Maximum of the slider
        """
        self.plotType = self.ui.displayBox.currentText()
        self.ui.mainSlider.setValue(0)
        if self.plotType == 'Time-Frequency plot':
            self.ui.mainSlider.setMaximum(self.avg.tfr.data.shape[0] - 1)
            self.ui.mainLabel.setText('Channels')
        if self.plotType == 'Channel-Frequency plot':
            self.ui.mainSlider.setMaximum(self.avg.tfr.data.shape[2] - 1)
            self.ui.mainLabel.setText('Times')
        if self.plotType == 'Channel-Time plot':
            self.ui.mainSlider.setMaximum(self.avg.tfr.data.shape[1] - 1)
            self.ui.mainLabel.setText('Frequencies')
        self.ui.mainSlider.setTickInterval(1)
        self.value_changed()

    # Plotting functions
    # =====================================================================
    def plot(self):
        """Plot the correct representation
        """
        from backend.viz_tfr import \
            _plot_time_freq, _plot_freq_ch, _plot_time_ch, _plot_topomap_tfr

        if self.plotType == 'Time-Frequency plot':
            _plot_time_freq(self)
        if self.plotType == 'Channel-Frequency plot':
            _plot_freq_ch(self)
        if self.plotType == 'Channel-Time plot':
            _plot_time_ch(self)
        if self.plotType == 'Topomap plot':
            _plot_topomap_tfr(self)
