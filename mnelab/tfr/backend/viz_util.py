import matplotlib.pyplot as plt
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# ---------------------------------------------------------------------
def _prepare_single_psd_plot(win):
    """Prepare the plot for the PSD plot
    """
    plt.close('all')
    fig = plt.figure(figsize=(5, 5))
    gs = fig.add_gridspec(3, 4)
    ax1 = fig.add_subplot(gs[:, :3])
    ax1.set_xlim([win.psd.freqs[0],
                 win.psd.freqs[-1]])
    ax1.set_xlabel('Frequency (Hz)')
    if win.log:
        ax1.set_ylabel('Power (dB)')
    else:
        ax1.set_ylabel('Power (µV²/Hz)')
    ax2 = fig.add_subplot(gs[1, 3])

    return fig, ax1, ax2


# ---------------------------------------------------------------------
def _plot_legend_topomap(win, ax, channel_picked):
    """Plot the little topomap legend for the PSD plot
    """
    from mne.viz import plot_topomap
    import numpy as np
    from matplotlib.colors import ListedColormap

    white = np.array([[0, 0, 0, 0]])
    cmp = ListedColormap(white)

    try:
        obj = win.psd
    except AttributeError:
        obj = win.avg

    zeros = [0 for i in range(len(obj.pos))]
    mask = np.array([False for i in range(len(obj.pos))])
    mask[obj.with_coord.index(channel_picked - 1)] = True

    plot_topomap(zeros, obj.pos, axes=ax, cmap=cmp, mask=mask, show=False,
                 mask_params=dict(marker='.', markersize=18,
                                  markerfacecolor='black',
                                  markeredgecolor='black'))


# ---------------------------------------------------------------------
def _set_psd_window(win, fig):
    """Setup the pop-up PSD window
    """
    win = fig.canvas.manager.window
    win.setWindowModality(Qt.WindowModal)
    win.setWindowTitle("PSD")
    win.resize(1400, 1000)
    win.findChild(QStatusBar).hide()
    fig.show()
