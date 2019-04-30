from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import matplotlib.pyplot as plt

"""
This file contains several utilitary functions to work with the
visualization of epochs psd

win --> instance of EpochsPSDWindow
"""


# ---------------------------------------------------------------------
def _plot_topomaps(win):
    """Plot the topomaps
    """
    gs = win.ui.figure.add_gridspec(10, 30)
    _topomaps_adjust(win, gs)
    _add_colorbar(win, gs)
    win.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_matrix(win):
    """Plot the Matrix
    """
    gs = win.ui.figure.add_gridspec(10, 30)
    _matrix_adjust(win, gs)
    _add_colorbar(win, gs)
    win.ui.canvas.draw()


# ---------------------------------------------------------------------
def _plot_all_psd(win):
    """Plot all the PSD
    """
    gs = win.ui.figure.add_gridspec(10, 30)
    _plot_all_psd_adjust(win, gs)
    win.ui.canvas.draw()


# ---------------------------------------------------------------------
def _add_colorbar(win, gs):
    """Add colorbar to the plot at correct position
    """
    if (win.ui.showSingleEpoch.checkState()
            or win.ui.showMean.checkState()):
        # plot a common colorbar for both representations
        cax = win.ui.figure.add_subplot(gs[:, 27])
        cbar = plt.colorbar(win.cbar_image, cax=cax)
        cbar.ax.get_xaxis().labelpad = 15
        if win.log:
            label = 'PSD (dB)'
        else:
            label = 'PSD (µV²/Hz)'
        cbar.ax.set_xlabel(label)


# Adjusting the plots
# =====================================================================
def _topomaps_adjust(win, gs):
    """Plot the good number of subplots and update cbar_image instance
    """
    win.ui.figure.clear()
    both = (win.ui.showMean.checkState()
            and win.ui.showSingleEpoch.checkState())

    # Plot single epoch if showSingleEpoch is checked
    if win.ui.showSingleEpoch.checkState():
        slice = gs[:, :12] if both else gs[:, 0:25]
        ax = win.ui.figure.add_subplot(slice)
        win.cbar_image, _ = win.psd.plot_topomap_band(
                                win.epoch_index,
                                win.f_index_min, win.f_index_max,
                                axes=ax, vmin=win.vmin, vmax=win.vmax,
                                log_display=win.log)

        ax.set_title('Epoch {}'.format(win.epoch_index + 1),
                     fontsize=15, fontweight='light')

    # plot average data if showMean is checked
    if win.ui.showMean.checkState():
        slice = gs[:, 13:25] if both else gs[:, :25]
        ax = win.ui.figure.add_subplot(slice)
        win.cbar_image, _ = win.psd.plot_avg_topomap_band(
                                win.f_index_min, win.f_index_max, axes=ax,
                                vmin=win.vmin, vmax=win.vmax,
                                log_display=win.log)

        ax.set_title('Average', fontsize=15, fontweight='light')


# ---------------------------------------------------------------------
def _matrix_adjust(win, gs):
    """Plot the matrix and update cbar_image instance
    """
    win.ui.figure.clear()
    both = (win.ui.showMean.checkState()
            and win.ui.showSingleEpoch.checkState())

    # plot single epoch data uf showSingleEpoch is checked
    if win.ui.showSingleEpoch.checkState():
        slice = gs[:, :12] if both else gs[:, 0:25]
        ax = win.ui.figure.add_subplot(slice)
        win.cbar_image = win.psd.plot_matrix(
                              win.epoch_index,
                              win.f_index_min, win.f_index_max,
                              vmin=win.vmin, vmax=win.vmax,
                              axes=ax, log_display=win.log)
        ax.axis('tight')
        ax.set_title('Matrix for epoch {}'.format(win.epoch_index + 1),
                     fontsize=15, fontweight='light')
        ax.set_xlabel('Frequencies (Hz)')
        ax.set_ylabel('Channels')
        ax.xaxis.set_ticks_position('bottom')
        ax.grid(False)

    # plot average data if showMean is checked
    if win.ui.showMean.checkState():
        slice = gs[:, 13:25] if both else gs[:, :25]
        ax = win.ui.figure.add_subplot(slice)
        win.cbar_image = win.psd.plot_avg_matrix(
                              win.f_index_min, win.f_index_max, axes=ax,
                              vmin=win.vmin, vmax=win.vmax,
                              log_display=win.log)
        ax.axis('tight')
        ax.set_title('Average Matrix', fontsize=15,
                     fontweight='light')
        ax.set_xlabel('Frequencies (Hz)')
        ax.set_ylabel('Channels')
        ax.xaxis.set_ticks_position('bottom')
        ax.grid(False)


# ---------------------------------------------------------------------
def _plot_all_psd_adjust(win, gs):
    """Plot all the PSD
    """
    win.ui.figure.clear()
    both = (win.ui.showMean.checkState()
            and win.ui.showSingleEpoch.checkState())

    # plot single epoch data uf showSingleEpoch is checked
    if win.ui.showSingleEpoch.checkState():
        slice = gs[:, :14] if both else gs[:, 0:30]
        ax = win.ui.figure.add_subplot(slice)
        win.psd.plot_all_psd(
            win.epoch_index, win.f_index_min, win.f_index_max,
            axes=ax, log_display=win.log)
        ax.axis('tight')
        ax.patch.set_alpha(0)
        ax.set_title('PSD for epoch {}'.format(win.epoch_index + 1),
                     fontsize=15, fontweight='light')
        ax.set_xlabel('Frequencies (Hz)')
        ax.set_ylabel('Power')
        win.annot_epoch = ax.annotate('', xy=(0, 0), xytext=(3, 3),
                                      textcoords='offset points',
                                      arrowprops=dict(arrowstyle='->'))
        win.annot_epoch.set_visible(False)

    # plot average data if showMean is checked
    if win.ui.showMean.checkState():
        slice = gs[:, 15:30] if both else gs[:, :30]
        ax = win.ui.figure.add_subplot(slice)
        win.psd.plot_all_avg_psd(
            win.f_index_min, win.f_index_max,
            axes=ax, log_display=win.log)
        ax.axis('tight')
        ax.patch.set_alpha(0)
        ax.set_title('Average PSD', fontsize=15,
                     fontweight='light')
        ax.set_xlabel('Frequencies (Hz)')
        ax.set_ylabel('Power')
        win.annot_avg = ax.annotate('', xy=(0, 0), xytext=(3, 3),
                                    textcoords='offset points',
                                    arrowprops=dict(arrowstyle='->'))
        win.annot_avg.set_visible(False)


# ---------------------------------------------------------------------
def _plot_single_psd(win, epoch_picked, channel_picked):
    """Plot one single PSD
    """
    from backend.viz_util import \
        _prepare_single_psd_plot, _plot_legend_topomap, _set_psd_window

    fig, ax1, ax2 = _prepare_single_psd_plot(win)

    win.psd.plot_single_psd(epoch_picked, channel_picked - 1,
                            axes=ax1, log_display=win.log)

    index_ch = win.psd.picks[channel_picked - 1]
    ax1.set_title('PSD of Epoch {}, channel {}'.format(epoch_picked + 1,
                  win.psd.info['ch_names'][index_ch]))

    if (channel_picked - 1) in win.psd.with_coord:
        _plot_legend_topomap(win, ax2, channel_picked)
    else:
        ax2.remove()

    _set_psd_window(win, fig)


# ---------------------------------------------------------------------
def _plot_single_avg_psd(win, channel_picked):
    """Plot one single averaged PSD
    """
    from backend.viz_util import \
        _prepare_single_psd_plot, _plot_legend_topomap, _set_psd_window

    fig, ax1, ax2 = _prepare_single_psd_plot(win)

    win.psd.plot_single_avg_psd(
        channel_picked - 1, axes=ax1, log_display=win.log)

    index_ch = win.psd.picks[channel_picked - 1]
    ax1.set_title('Average PSD of channel {}'.format(
                 win.psd.info['ch_names'][index_ch]))

    if (channel_picked - 1) in win.psd.with_coord:
        _plot_legend_topomap(win, ax2, channel_picked)
    else:
        ax2.remove()

    _set_psd_window(win, fig)
