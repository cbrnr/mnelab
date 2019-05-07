from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
def _plot_time_freq(self):
    """Plot the time-frequency representation
    """
    from .viz_util import _plot_legend_topomap
    self.ui.figure.clear()
    gs = self.ui.figure.add_gridspec(10, 30)
    ax = self.ui.figure.add_subplot(gs[:, :25])
    self.cbar_image = self.avg.plot_time_freq(
        self.index, ax, vmin=self.vmin, vmax=self.vmax, log_display=self.log)
    ax.set_title('Time-Frequency Plot - Channel {}'.format(
                 self.avg.info['ch_names'][self.avg.picks[self.index]]),
                 fontsize=15, fontweight='light')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequencies (Hz)')
    ax.grid(False)
    cax = self.ui.figure.add_subplot(gs[2:, 27])
    cbar = plt.colorbar(self.cbar_image, cax=cax, format='%6.1e')
    cbar.ax.set_xlabel('Power', labelpad=15)
    if self.avg.with_coord != []:
        tax = cax = self.ui.figure.add_subplot(gs[:2, 25:30])
        _plot_legend_topomap(self, tax, self.index + 1)

    self.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_freq_ch(self):
    """Plot the frequency-channel representation
    """
    self.ui.figure.clear()
    gs = self.ui.figure.add_gridspec(10, 30)
    ax = self.ui.figure.add_subplot(gs[:, :25])
    self.cbar_image = self.avg.plot_freq_ch(
        self.index, ax, vmin=self.vmin, vmax=self.vmax, log_display=self.log)
    ax.set_title(('Frequency-Channel Plot - Time {:.2f}s'
                 .format(self.avg.tfr.times[self.index])),
                 fontsize=15, fontweight='light')
    ax.set_xlabel('Frequencies (Hz)')
    ax.set_ylabel('Channels')
    ax.grid(False)
    cax = self.ui.figure.add_subplot(gs[:, 27])
    cbar = plt.colorbar(self.cbar_image, cax=cax, format='%6.1e')
    cbar.ax.set_xlabel('Power', labelpad=15)
    self.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_time_ch(self):
    """Plot the time-channels representation
    """
    self.ui.figure.clear()
    gs = self.ui.figure.add_gridspec(10, 30)
    ax = self.ui.figure.add_subplot(gs[:, :25])
    self.cbar_image = self.avg.plot_time_ch(
        self.index, ax, vmin=self.vmin, vmax=self.vmax, log_display=self.log)
    ax.set_title(('Time-Channel Plot - Frequency {:.2f}'
                  .format(self.avg.tfr.freqs[self.index])),
                 fontsize=15, fontweight='light')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Channels')
    ax.grid(False)
    cax = self.ui.figure.add_subplot(gs[:, 27])
    cbar = plt.colorbar(self.cbar_image, cax=cax, format='%6.1e')
    cbar.ax.set_xlabel('Power', labelpad=15)
    self.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_topomap_tfr(self):
    """Plot topomap for TFR window
    """
    from matplotlib.ticker import FormatStrFormatter

    try:
        self.ui.figure.clear()
        ax = self.ui.figure.add_subplot(1, 1, 1)
        fig = self.avg.tfr.plot_topomap(
            tmin=self.tmin, tmax=self.tmax,
            fmin=self.fmin, fmax=self.fmax,
            vmin=self.vmin, vmax=self.vmax,
            axes=ax, mode='logratio',
            cmap=self.avg.cmap, show=False,
            colorbar=True)
        ax = fig.get_axes()[1]
        ax.yaxis.set_major_formatter(FormatStrFormatter('%6.1e'))
        ax.tick_params(axis='both', labelsize=10)
        ax.set_xlabel('Power', fontsize=10)
        ax.get_xaxis().labelpad = 15
        self.ui.canvas.draw()

    except ValueError:
        print("Error with the parameters")
