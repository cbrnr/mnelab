from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from matplotlib.backends.backend_qt5agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg \
    import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from math import floor

from app.ui.epochs_psd_UI import Ui_EpochsPSDWindow


class EpochsPSDWindow(QDialog):
    """PSDWindow class, which enable to visualize the PSDs for epochs
    """
    def __init__(self, epochsPSD, parent=None):
        super(EpochsPSDWindow, self).__init__(parent)
        self.psd = epochsPSD
        self.ui = Ui_EpochsPSDWindow()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)
        self.setup_window()

    # ---------------------------------------------------------------------
    def setup_window(self):
        """Call all the setup functions
        """
        self.set_canvas()
        self.set_initial_values()
        self.set_bindings()
        self.plot_change()

    # Setup functions
    # =====================================================================
    def set_initial_values(self):
        """Setup initial values
        """
        self.ui.epochsSlider.setMaximum(self.psd.data.shape[0] - 1)
        self.ui.epochsSlider.setMinimum(0)
        self.ui.epochsSlider.setValue(0)
        self.ui.epochsSlider.setTickInterval(1)
        self.ui.frequencySlider.setMaximum(len(self.psd.freqs) - 1)
        self.ui.frequencySlider.setMinimum(0)
        self.ui.frequencySlider.setValue(0)
        self.ui.frequencySlider.setTickInterval(1)
        self.ui.fmin.setMaxLength(4)
        self.ui.fmin.setText(str(self.psd.freqs[0]))
        self.ui.fmax.setMaxLength(4)
        self.ui.fmax.setText(str(self.psd.freqs[-1]))
        self.ui.vmax.setMaxLength(6)
        self.ui.vmin.setMaxLength(6)
        self.ui.showMean.setCheckState(2)
        self.ui.selectPlotType.addItem('Matrix')
        if self.psd.with_coord != []:
            self.ui.selectPlotType.addItem('Topomap')
        self.ui.selectPlotType.addItem('All PSD')

    # ---------------------------------------------------------------------
    def set_bindings(self):
        """Set Bindings
        """
        self.ui.epochsSlider.valueChanged.connect(self.value_changed)
        self.ui.frequencySlider.valueChanged.connect(self.slider_changed)
        self.ui.fmin.editingFinished.connect(self.value_changed)
        self.ui.fmax.editingFinished.connect(self.value_changed)
        self.ui.showMean.stateChanged.connect(self.value_changed)
        self.ui.displayLog.stateChanged.connect(self.value_changed)
        self.ui.showSingleEpoch.stateChanged.connect(self.value_changed)
        self.ui.vmax.editingFinished.connect(self.value_changed)
        self.ui.vmin.editingFinished.connect(self.value_changed)
        self.ui.selectPlotType.currentIndexChanged.connect(self.plot_change)

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
        self.ui.figureLayout.addWidget(self.ui.toolbar)
        self.ui.figureLayout.addWidget(self.ui.canvas)
        self.ui.canvas.mpl_connect('button_press_event', self.onclick)
        self.ui.canvas.mpl_connect('pick_event', self.onclick_pick)

    # Main Plotting function
    # =====================================================================
    def plot_psd(self):
        """Plot the correct type of PSD
        """
        from backend.viz_epochs import \
            _plot_topomaps, _plot_matrix, _plot_all_psd

        if self.plotType == 'Topomap':
            try:
                _plot_topomaps(self)
            except ValueError:
                # If no topomap is initialized, error is displayed
                from app.error import show_error
                show_error(
                    'No coordinates for topomap have been initialized :(')
                self.ui.selectPlotType.setCurrentIndex(0)

        if self.plotType == 'Matrix':
            _plot_matrix(self)

        if self.plotType == 'All PSD':
            _plot_all_psd(self)

    # Updating the canvas functions
    # =====================================================================
    def plot_change(self):
        """Update the plot type
        """
        self.plotType = self.ui.selectPlotType.currentText()
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
        self.epoch_index = self.ui.epochsSlider.value()
        self.plot_psd()

    # ---------------------------------------------------------------------
    def slider_changed(self):
        """Get called when the slider is touched
        """
        freq_index = self.ui.frequencySlider.value()
        freq = self.psd.freqs[freq_index]
        self.ui.fmin.setText(str(freq))
        self.ui.fmax.setText(str(freq))
        self.value_changed()

    # Handle PSD single plotting on click
    # =====================================================================
    def onclick(self, click):
        """Get coordinates on the canvas and plot the corresponding PSD
        """
        from backend.viz_epochs import _plot_single_avg_psd, _plot_single_psd

        if self.plotType == 'Matrix':
            # Handle clicks on Matrix
            channel_picked = click.ydata - 1
            ax_picked = click.inaxes

        elif self.plotType == 'Topomap':
            # Handle clicks on topomaps
            x, y = click.xdata, click.ydata
            channel_picked = self.psd.channel_index_from_coord(x, y)
            ax_picked = click.inaxes

        else:
            channel_picked = None

        if (channel_picked is not None and click.dblclick):

            channel_picked = floor(channel_picked) + 1
            epoch_picked = self.ui.epochsSlider.value()

            # If both are checked, it depends on which plot user clicked
            if (self.ui.showMean.checkState()
                    and self.ui.showSingleEpoch.checkState()):

                if ax_picked.is_first_col():
                    _plot_single_psd(self, epoch_picked, channel_picked)
                else:
                    _plot_single_avg_psd(self, channel_picked)

            elif self.ui.showSingleEpoch.checkState():
                _plot_single_psd(self, epoch_picked, channel_picked)

            elif self.ui.showMean.checkState():
                _plot_single_avg_psd(self, channel_picked)

    # ---------------------------------------------------------------------
    def onclick_pick(self, click):
        """Get the line on click and plot a tooltip with the name of
        the channel
        """
        from backend.util import _annot
        from backend.viz_epochs import _plot_single_avg_psd, _plot_single_psd

        if self.plotType == 'All PSD':
            # Handle click on all PSD plots
            ax_picked = click.mouseevent.inaxes
            if (self.ui.showMean.checkState()
                    and self.ui.showSingleEpoch.checkState()):

                if ax_picked.is_first_col():
                    _annot(self, click, self.annot_epoch)

                else:
                    _annot(self, click, self.annot_avg)

            elif self.ui.showSingleEpoch.checkState():
                _annot(self, click, self.annot_epoch)

            elif self.ui.showMean.checkState():
                _annot(self, click, self.annot_avg)

            if click.mouseevent.dblclick:
                epoch_picked = self.ui.epochsSlider.value()
                ch = str(click.artist.get_label())
                index = self.psd.info['ch_names'].index(ch)
                index = self.psd.picks.index(index)

                if (self.ui.showMean.checkState()
                        and self.ui.showSingleEpoch.checkState()):

                    if ax_picked.is_first_col():
                        _plot_single_psd(self, epoch_picked, index + 1)

                    else:
                        _plot_single_avg_psd(self, index + 1)

                elif self.ui.showSingleEpoch.checkState():
                    _plot_single_psd(self, epoch_picked, index + 1)

                elif self.ui.showMean.checkState():
                    _plot_single_avg_psd(self, index + 1)
