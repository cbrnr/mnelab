from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import matplotlib.pyplot as plt

"""
This file contains several utilitary functions to work with the
visualization of raw psd

win --> instance of RawPSDWindow
"""


# ----------------------------------------------------------------------
def _plot_topomap(win):
    """Plot the topomaps
    """
    win.ui.figure.clear()
    gs = win.ui.figure.add_gridspec(10, 30)
    ax = win.ui.figure.add_subplot(gs[:, :25])
    win.cbar_image, _ = win.psd.plot_topomap_band(
                             win.f_index_min, win.f_index_max, axes=ax,
                             vmin=win.vmin, vmax=win.vmax,
                             log_display=win.log)
    cax = win.ui.figure.add_subplot(gs[:, 27])
    cbar = plt.colorbar(win.cbar_image, cax=cax)
    if win.log:
        label = 'Power (dB)'
    else:
        label = 'Power (µV²/Hz)'
    cbar.ax.set_xlabel(label, labelpad=15)

    win.ui.figure.subplots_adjust(top=0.9, right=0.8,
                                  left=0.1, bottom=0.1)
    win.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_matrix(win):
    """Plot the Matrix
    """
    win.ui.figure.clear()
    gs = win.ui.figure.add_gridspec(10, 30)
    ax = win.ui.figure.add_subplot(gs[:, :25])
    win.cbar_image = win.psd.plot_matrix(
                           win.f_index_min, win.f_index_max, axes=ax,
                           vmin=win.vmin, vmax=win.vmax,
                           log_display=win.log)
    ax.axis('tight')
    ax.set_title("Matrix", fontsize=15, fontweight='light')
    ax.set_xlabel('Frequencies (Hz)')
    ax.set_ylabel('Channels')
    ax.xaxis.set_ticks_position('bottom')
    ax.grid(False)
    cax = win.ui.figure.add_subplot(gs[:, 27])
    cbar = plt.colorbar(win.cbar_image, cax=cax)
    if win.log:
        label = 'Power (dB)'
    else:
        label = 'Power (µV²/Hz)'
    cbar.ax.set_xlabel(label, labelpad=15)
    win.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_all_psd(win):
    """Plot all PSDs
    """
    win.ui.figure.clear()
    gs = win.ui.figure.add_gridspec(10, 30)
    ax = win.ui.figure.add_subplot(gs[:, :30])
    win.annot = ax.annotate("", xy=(0, 0), xytext=(3, 3),
                            textcoords="offset points",
                            arrowprops=dict(arrowstyle="->"))
    win.annot.set_visible(False)
    win.psd.plot_all_psd(
        win.f_index_min, win.f_index_max, axes=ax, log_display=win.log)

    ax.axis = ('tight')
    ax.patch.set_alpha(0)
    ax.set_title("PSD", fontsize=15, fontweight='light')
    ax.set_xlim([win.psd.freqs[win.f_index_min],
                 win.psd.freqs[win.f_index_max]])
    ax.set_xlabel('Frequency (Hz)')
    if win.log:
        ax.set_ylabel('Power (dB)')
    else:
        ax.set_ylabel('Power (µV²/Hz)')
    win.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_single_psd(win, channel_picked):
    """Plot one single PSD
    """
    from .viz_util import \
        _prepare_single_psd_plot, _plot_legend_topomap, _set_psd_window

    fig, ax1, ax2 = _prepare_single_psd_plot(win)

    win.psd.plot_single_psd(channel_picked - 1, axes=ax1,
                            log_display=win.log)
    index_ch = win.psd.picks[channel_picked - 1]
    ax1.set_title('PSD of channel {}'
                  .format(win.psd.info['ch_names'][index_ch]))

    if (channel_picked - 1) in win.psd.with_coord:
        _plot_legend_topomap(win, ax2, channel_picked)
    else:
        ax2.remove()

    _set_psd_window(win, fig)
