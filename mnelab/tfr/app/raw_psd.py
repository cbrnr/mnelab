from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from math import floor
from app.ui.raw_psd_UI import Ui_RawPSDWindow


class RawPSDWindow(QDialog):
    def __init__(self, rawPSD, parent=None):
        super(RawPSDWindow, self).__init__(parent)
        self.psd = rawPSD
        self.ui = Ui_RawPSDWindow()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.setup_window()

    # ------------------------------------------------------------------------
    def setup_window(self):
        self.set_canvas()
        self.set_initial_values()
        self.set_bindings()
        self.plot_changed()

    # Setup functions
    # ========================================================================
    def set_initial_values(self):
        """Setup initial values
        """
        self.ui.frequencySlider.setMaximum(len(self.psd.freqs)-1)
        self.ui.frequencySlider.setMinimum(0)
        self.ui.frequencySlider.setValue(0)
        self.ui.frequencySlider.setTickInterval(1)
        self.ui.fmin.setMaxLength(4)
        self.ui.fmin.setText(str(self.psd.freqs[0]))
        self.ui.fmax.setMaxLength(4)
        self.ui.fmax.setText(str(self.psd.freqs[-1]))
        self.ui.vmax.setText('')       # Auto scaling by default
        self.ui.vmax.setMaxLength(6)
        self.ui.vmin.setText('')       # Auto scaling by default
        self.ui.vmin.setMaxLength(6)
        self.ui.selectPlotType.addItem('Matrix')
        if self.psd.with_coord != []:  # Add topomap if there are coordinates
            self.ui.selectPlotType.addItem('Topomap')
        self.ui.selectPlotType.addItem('All PSD')

    # ------------------------------------------------------------------------
    def set_bindings(self):
        """Set Bindings
        """
        self.ui.fmin.editingFinished.connect(self.value_changed)
        self.ui.fmax.editingFinished.connect(self.value_changed)
        self.ui.vmax.editingFinished.connect(self.value_changed)
        self.ui.vmin.editingFinished.connect(self.value_changed)
        self.ui.selectPlotType.currentIndexChanged.connect(self.plot_changed)
        self.ui.displayLog.stateChanged.connect(self.value_changed)
        self.ui.frequencySlider.valueChanged.connect(self.slider_changed)

    # ------------------------------------------------------------------------
    def set_canvas(self):
        """setup canvas for matplotlib
        """
        self.ui.figure = plt.figure(figsize=(10, 10))
        self.ui.figure.patch.set_facecolor('None')
        self.ui.canvas = FigureCanvas(self.ui.figure)
        self.ui.canvas.setStyleSheet('background-color:transparent;')
        # Matplotlib toolbar
        self.ui.toolbar = NavigationToolbar(self.ui.canvas, self)
        self.ui.figureLayout.addWidget(self.ui.toolbar)
        self.ui.figureLayout.addWidget(self.ui.canvas)
        self.ui.canvas.mpl_connect('button_press_event', self.onclick)
        self.ui.canvas.mpl_connect('pick_event', self.onclick_pick)

    # Main Plotting function
    # ========================================================================
    def plot_psd(self):
        """Plot the correct type of PSD
        """
        from app.error import show_error
        from backend.viz_raw import \
            _plot_topomap, _plot_matrix, _plot_all_psd

        if self.plotType == 'Topomap':
            try:
                _plot_topomap(self)
            except ValueError:
                show_error(
                    'No coordinates for topomap have been initialized:(')
                self.ui.selectPlotType.setCurrentIndex(0)

        if self.plotType == 'Matrix':
            _plot_matrix(self)

        if self.plotType == 'All PSD':
            _plot_all_psd(self)

    # Updating the canvas functions
    # =====================================================================
    def plot_changed(self):
        """Update the plot type
        """
        self.plotType = self.ui.selectPlotType.currentText()
        self.value_changed()

    # ---------------------------------------------------------------------
    def slider_changed(self):
        """Get called when the slider is touched
        """
        freq_index = self.ui.frequencySlider.value()
        freq = self.psd.freqs[freq_index]
        self.ui.fmin.setText(str(freq))
        self.ui.fmax.setText(str(freq))
        self.value_changed()

    # ---------------------------------------------------------------------
    def value_changed(self):
        """ Get called if a value is changed
        """
        from backend.util import get_index_freq

        try:
            fmin = float(self.ui.fmin.text())
        except ValueError:
            fmin = self.psd.freqs[0]

        try:
            fmax = float(self.ui.fmax.text())
        except ValueError:
            fmax = self.psd.freqs[-1]
        self.f_index_min, self.f_index_max = get_index_freq(
                                                 self.psd.freqs, fmin, fmax)
        try:
            self.vmax = float(self.ui.vmax.text())
        except ValueError:
            self.vmax = None
        try:
            self.vmin = float(self.ui.vmin.text())
        except ValueError:
            self.vmin = None

        self.log = self.ui.displayLog.checkState()
        self.plot_psd()

    # Handle PSD single plotting on click
    # =====================================================================
    def onclick(self, click):
        """Get coordinates on the canvas and plot the corresponding PSD
        """
        from backend.viz_raw import _plot_single_psd

        if self.plotType == 'Matrix':
            channel_picked = click.ydata - 1
        elif self.plotType == 'Topomap':
            x, y = click.xdata, click.ydata
            channel_picked = self.psd.channel_index_from_coord(x, y)
        else:
            channel_picked = None

        if (channel_picked is not None and click.dblclick):
            channel_picked = floor(channel_picked) + 1
            _plot_single_psd(self, channel_picked)

    # ---------------------------------------------------------------------
    def onclick_pick(self, click):
        """Get the line on click and plot a tooltip with the name of
        the channel
        """
        from backend.util import _annot
        from backend.viz_raw import _plot_single_psd

        if self.plotType == 'All PSD':
            _annot(self, click, self.annot)
            # If double click, we plot the PSD
            if click.mouseevent.dblclick:
                ch = str(click.artist.get_label())
                index = self.psd.info['ch_names'].index(ch)
                index = self.psd.picks.index(index)
                _plot_single_psd(self, index + 1)
