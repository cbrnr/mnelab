import os
import copy
import itertools
from itertools import cycle
import math
from functools import partial
from numbers import Integral
import warnings

import matplotlib
import numpy as np
import scipy
import pandas as pd
import mne
import seaborn as sns
import matplotlib.pyplot as plt

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, CheckButtons
from matplotlib.gridspec import GridSpec
import matplotlib.patches as patches
import scipy.signal

from mne.channels import Montage
from mne.channels.layout import _find_topomap_coords
from mne.time_frequency.psd import psd_multitaper
from mne.baseline import rescale
from mne.io.pick import (pick_types, _picks_by_type, channel_type, pick_info,
                         _pick_data_channels, pick_channels)
from mne.utils import _clean_names, _time_mask, verbose, logger, warn
from mne.viz.utils import (tight_layout, _setup_vmin_vmax, _prepare_trellis,
                           _check_delayed_ssp, _draw_proj_checkbox, figure_nobar,
                           plt_show, _process_times, DraggableColorbar,
                           _get_color_list, _validate_if_list_of_axes,
                           _setup_cmap, _check_time_unit, _compute_scalings)
from mne.defaults import _handle_default
from mne.io.meas_info import Info
from mne.externals.six import string_types
from mne.viz.topomap import (_prepare_topo_plot, _check_outlines, plot_topomap,
                            _hide_frame, plot_ica_components, _plot_topomap)


def plot_correlation_matrix(raw, ica):
    "Plot correlation_matrix."
    raw = raw.copy()
    ch_names = raw.info["ch_names"]
    path = os.path.join('.', 'mnelab', 'ica_templates', 'template-ica.fif')
    ica_template = mne.preprocessing.read_ica(path)
    common = find_common_channels(ica_template, ica)
    components_template, components_ics = extract_common_components(
                                              ica_template, ica)
    templates = components_template[[0, 7]]
    df = compute_correlation(templates, components_ics)
    raw.rename_channels(tolow)
    raw.reorder_channels(common)
    ch_names = raw.info["ch_names"]
    pos = _find_topomap_coords(
                raw.info, picks=[i for i in range(len(ch_names))
                                 if ch_names[i].lower() in common])
    quality = len(common) / len(ch_names)
    plot_correlation(df, templates, pos, quality)
    return()


def compute_gfp_raw(raw):
    '''Compute global field power for RAW'''
    return(np.mean(raw.get_data()**2, axis=0)**0.5)


def compute_gfp_epoch(epochs):
    '''Compute global field power for epochs'''
    return(np.mean(epochs.get_data()**2, axis=1)**0.5)


def plot_overlay(raw, ica):
    """Custom plot overlay given fitted ica and raw"""
    if type(raw) == mne.io.fiff.raw.Raw:
        raw_copy = raw.copy()
        ica.apply(raw_copy)
        # Info
        sfreq = raw.info["sfreq"]
        ch_types = ['eeg', 'eeg']
        ch_names = ['before', 'after']
        info = mne.create_info(ch_names=ch_names, sfreq=sfreq,
                               ch_types=ch_types)
        raw.info['bads'] = ["before"]
        # Data
        gfp_raw_signal = compute_gfp_raw(raw)
        gfp_raw_applied_signal = compute_gfp_raw(raw_copy)
        data = [gfp_raw_signal, gfp_raw_applied_signal]
        # Raw
        raw = mne.io.RawArray(data, info)
        fig, ax = plt.subplots()
        ax.plot(raw.times, gfp_raw_signal, 'r', label="before")
        ax.plot(raw.times, gfp_raw_applied_signal, 'black', label="after")
        min = np.abs(gfp_raw_signal.min())
        max = np.abs(gfp_raw_signal.max())
        ylim = np.max([min, max])
        ax.set_ylim(-ylim, ylim)
        ax.set_xlim(0, 10)
        ax.set_xlabel("time(s)")
        ax.set_yticklabels([])
        ax.set_title("""Global field power before (red)
                        and after (black) source rejection""")
        ax.legend(loc=8, ncol=2, bbox_to_anchor=(0., 0., 1, 1))
        plt.show(fig)
    elif type(raw) == mne.epochs.EpochsFIF:
        epochs = raw.copy()
        ica.apply(epochs)
        # Info
        sfreq = epochs.info["sfreq"]
        ch_types = ['eeg', 'eeg']
        ch_names = ['before', 'after']
        info = mne.create_info(ch_names=ch_names, sfreq=sfreq,
                               ch_types=ch_types)
        # Data
        gfp_epochs_signal = compute_gfp_epoch(raw)
        gfp_epochs_applied_signal = compute_gfp_epoch(epochs)
        data = np.array([gfp_epochs_signal.T, gfp_epochs_applied_signal.T]).T
        data = np.swapaxes(data, 1, 2)
        # Epochs
        times = epochs.times
        tmin = epochs.tmin
        # Figure
        fig, ax = plt.subplots(num="ICA Overlay")
        duration = times[-1] - times[0]
        offset = 0
        if tmin < 0:
            offset = - tmin
        # initialie to have oly 1 label
        ep = 0
        ep_data = data[ep]
        ep_times = offset + times + ep*duration
        ax.plot(ep_times, ep_data[0], "r", label="before")
        ax.plot(ep_times, ep_data[1], "black", label="after")
        ax.axvline(x=offset + ep*duration, color="green")
        ax.axvline(x=ep*duration, color="black", linestyle="--")
        # then l0op over all epochs
        for ep in range(1, len(epochs)):
            ep_data = data[ep]
            ep_times = offset + times + ep*duration
            ax.plot(ep_times, ep_data[0], "r")
            ax.plot(ep_times, ep_data[1], "black")
            ax.axvline(x=offset + ep*duration, color="green")
            ax.axvline(x=ep*duration, color="black", linestyle="--")
        min = np.abs(data.min())
        max = np.abs(data.max())
        ylim = np.max([min, max])
        ax.set_ylim(-ylim, ylim)
        ax.set_xlim(0, np.around(10/duration)*duration)
        ax.set_xlabel("time(s)")
        ax.set_yticklabels([])
        ax.set_title(
            """Global field power before (red) and after (black)"""
            """ source rejection""")
        ax.legend(loc=8, ncol=2, bbox_to_anchor=(0., 0., 1, 1))
        plt.show(fig)
    return()


def find_common_channels(ica_a, ica_b):
    """Find ch_names shared between 2 ica objects"""
    ch_names_a = [ch.lower() for ch in ica_a.ch_names]
    ch_names_b = [ch.lower() for ch in ica_b.ch_names]
    common = [x for x in ch_names_a if x in ch_names_b]
    return(common)


def find_index_by_name(names, ica):
    ch_names = [ch.lower() for ch in ica.ch_names]
    Index = []
    for name in names:
        idx = ch_names.index(name)
        Index.append(idx)
    return(Index)


def extract_common_components(ica_a, ica_b):
    common = find_common_channels(ica_a, ica_b)
    idx_a = find_index_by_name(common, ica_a)
    idx_b = find_index_by_name(common, ica_b)
    components_a = ica_a.get_components()[idx_a]
    components_b = ica_b.get_components()[idx_b]
    return(components_a.T, components_b.T)


def construct__template_from_montage(Index, template_values):
    """Extract a template corresponding to the given indexes"""
    match_template = template_values[Index]
    match_template = match_template / np.linalg.norm(match_template)
    return(match_template)


def compute_correlation(match_templates, ics):
    Templates_names = []
    Ics_names = []
    Correlation = []
    for t, temp in enumerate(match_templates):
        for i, ic in enumerate(ics):
            Templates_names.append("template " + str(t).zfill(3))
            Ics_names.append("ic " + str(i).zfill(3))
            pearson = scipy.stats.pearsonr(temp, ic)[0]
            pearson = np.abs(pearson)
            Correlation.append(pearson)
    data = {'Templates_names': Templates_names,
            'Ics_names': Ics_names,
            'correlation': Correlation}
    df = pd.DataFrame(data)
    return(df)


def plot_correlation(df, match_templates, pos, quality, head_pos=None):
    dfp = df.pivot("Templates_names", "Ics_names", "correlation")
    fig = plt.figure(num= "ICA Correlation")
    gs = GridSpec(11, len(match_templates))
    axes = []
    for t, temp in enumerate(match_templates):
        axes.append(fig.add_subplot(gs[0:5, t]))
        axes[-1].set_title("template " + str(t).zfill(3))
        _plot_topomap(temp, pos, axes=axes[-1], head_pos=head_pos, show=False,
                      vmin=temp.min(), vmax=temp.max(), outlines="head")
    ax_colorbar = fig.add_subplot(gs[5, :])
    ax_matrix = fig.add_subplot(gs[7:11, :])
    sns.heatmap(dfp, linewidths=0.1, annot=False, ax=ax_matrix, cmap="YlGnBu",
                vmin=0, vmax=1, square=False, cbar_ax=ax_colorbar,
                cbar_kws={"orientation": 'horizontal'})
    ax_matrix.set_ylabel('')
    ax_matrix.set_xlabel("Comparaison Quality: " + str(quality*100) + "%")
    plt.subplots_adjust(left=0.17, bottom=0.15,
                        right=None, top=None,
                        wspace=None, hspace=None)
    plt.show(fig)
    return()


def plot_properties_with_timeseries(inst, ica, picks):
    """Alternatve version of mne function ica.plot_properties with addition off
    eeg time serie versus source time serie for correlation visualisation"""
    # Raw data
    CH_NAMES = [ch for ch in inst.info["ch_names"] if ch not in inst.info["bads"]]
    N_CHANNELS = len(CH_NAMES)
    SFREQ = inst.info["sfreq"]
    T = 1. / SFREQ

    #ICA
    components = ica.get_components()

    #DATA
    DATA = inst.get_data()
    # Create data without the ica comp
    DATA_proc = ica.apply(inst.copy(),exclude=[picks]).get_data()

    if type(inst) == mne.io.fiff.raw.Raw:
        S = ica.get_sources(inst=inst).get_data()[picks]

    elif type(inst) == mne.epochs.EpochsFIF:
        n_epochs = len(DATA)
        DATA = DATA.reshape(len(DATA[0]), len(DATA[0][0])* n_epochs)
        DATA_proc = DATA_proc.reshape(len(DATA[0]), len(DATA[0][0])* n_epochs)
        # Epochs
        tmin = inst.tmin
        offset = 0
        if tmin < 0:
            offset = - tmin
        S = ica.get_sources(inst=inst).get_data()
        S = S.reshape(len(S[0]), len(S[0][0])* n_epochs)
        S = S[picks]


    # Plot config
    N_PLOT_CHANNELS = 4 if N_CHANNELS >= 4 else N_CHANNELS
    current_idx = {'index': picks}
    scalings = _compute_scalings('auto',inst)
    linewidth=0.5

    # Data scalings
    eeg_scale = scalings['eeg']

    # Source _compute
    source_scale = np.percentile(S.ravel(), [0.5, 99.5])
    source_scale = np.max(np.abs(source_scale))

    # Plot grid
    fig = plt.figure(figsize=(12, 6),
                     num="ICA Component " + str(picks) + " properties")
    gs = GridSpec(1, 4)
    gs00 = gs[0].subgridspec(3, 1)
    gs01 = gs[1:3].subgridspec(N_PLOT_CHANNELS+1, 1)
    gs02 = gs[3].subgridspec(9, 1)

    # checkbutton
    ax_show_checkbutton = fig.add_subplot(gs02[8,:])
    show_checkbutton = CheckButtons(ax_show_checkbutton,
                                    ["Show EEG without source"], [True])

    # PLOT
    x = np.linspace(0,len(S), len(S)) / SFREQ
    ax_source = fig.add_subplot(gs01[0, :])
    ax_source.plot(x, S, color="r", linewidth=linewidth)
    ax_source.set_ylabel("source " + str(picks))
    if x[-1] >= 10:
        ax_source.set_xlim(0, 10)
    else:
        ax_source.set_xlim(0, x[-1])
    ax_source.set_ylim(-source_scale, source_scale)
    ax_source.set_title("Source vs Channels")
    plt.setp(ax_source.get_xticklabels(), visible=False)

    # EEG
    LINES_eeg = []
    LINES_eeg_proc = []
    AXES = []

    ax = fig.add_subplot(gs01[1, :], sharex=ax_source)
    plt.setp(ax.get_xticklabels(), visible=False)
    ax.set_ylabel(CH_NAMES[0])
    ax.set_ylim(-eeg_scale, eeg_scale)
    line_eeg, = ax.plot(x,DATA[0], linewidth=linewidth)
    line_eeg_proc, = ax.plot(x,DATA_proc[0], linewidth=linewidth)

    LINES_eeg.append(line_eeg)
    LINES_eeg_proc.append(line_eeg_proc)
    AXES.append(ax)

    for k in range(1,N_PLOT_CHANNELS):
        ax = fig.add_subplot(gs01[k+1, :], sharex=ax_source, sharey=AXES[0])
        plt.setp(ax.get_xticklabels(), visible=False)
        ax.set_ylabel(CH_NAMES[k])
        line_eeg, = ax.plot(x,DATA[k], linewidth=linewidth)
        line_eeg_proc, = ax.plot(x,DATA_proc[k], linewidth=linewidth)
        LINES_eeg.append(line_eeg)
        LINES_eeg_proc.append(line_eeg_proc)
        AXES.append(ax)

    all_axes = AXES.copy()
    all_axes.append(ax_source)
    if type(inst) == mne.io.fiff.raw.Raw:
        # Annotationpsd_args
        annot = inst.annotations
        times = inst.times
        for ax in all_axes:
            for a in range(0,len(annot)):
                onset = annot.onset[a]
                duration = annot.duration[a]
                description = annot.description[a]
                color = 'r' if "bad" in description.lower() else 'b'
                rect = patches.Rectangle((onset,-99999), duration, 2*99999,
                                         linewidth=0, facecolor=color, alpha=0.3)
                ax.add_patch(rect)
        plt.setp(AXES[-1].get_xticklabels(), visible=True)

    elif type(inst) == mne.epochs.EpochsFIF:
        # Epochs limits
        duration = (len(S)/n_epochs)/SFREQ
        ticks = []
        ticks_label = []
        for ep in range(0,n_epochs):
            for ax in all_axes:
                ax.axvline(x=offset + ep*duration, color="green")
                ax.axvline(x=ep*duration, color="black", linestyle="--")
        for ax in all_axes:
            ax.axvline(x=(n_epochs)*duration, color="black", linestyle="--")

    #Matplotlib events
    def scroll_channels_mouse(event):
        ''' scroll channels when using mouse wheel'''
        if current_idx['index'] < N_CHANNELS - N_PLOT_CHANNELS and event.button == 'down':
            current_idx['index'] +=1
        if current_idx['index']>0 and event.button == 'up':
            current_idx['index'] -=1
        for l in range(0, N_PLOT_CHANNELS):
            LINES_eeg[l].set_ydata(DATA[current_idx['index'] + l])
            LINES_eeg_proc[l].set_ydata(DATA_proc[current_idx['index'] + l])
            AXES[l].set_ylabel(CH_NAMES[current_idx['index'] + l])
        fig.canvas.draw()
        fig.canvas.flush_events()

    def scroll_channels_keyboard(event):
        ''' scroll channels when using keyboard arroys'''
        if current_idx['index'] < N_CHANNELS - N_PLOT_CHANNELS and event.key == 'down':
            current_idx['index'] +=1
        if current_idx['index']>0 and event.key == 'up':
            current_idx['index'] -=1
        for l in range(0, N_PLOT_CHANNELS):
            LINES_eeg[l].set_ydata(DATA[current_idx['index'] + l])
            LINES_eeg_proc[l].set_ydata(DATA_proc[current_idx['index'] + l])
            AXES[l].set_ylabel(CH_NAMES[current_idx['index'] + l])
        fig.canvas.draw()
        fig.canvas.flush_events()

    def scroll_time(event):
        ''' scroll time when using keyboard arroys'''
        current_lim = ax_source.get_xlim()
        pad = abs((current_lim[1] - current_lim[0])/4.)
        if event.key =='right':
            new_lim = tuple(x + pad for x in current_lim)
            if new_lim[-1] >= x[-1]:
                new_lim = tuple(x[-1] - pad , x[-1])
            ax_source.set_xlim(new_lim)
        elif event.key =='left':
            new_lim = tuple(x - pad for x in current_lim)
            if new_lim[0] <= x[0]:
                new_lim = tuple(x[0], x[0] - pad)
            ax_source.set_xlim(new_lim)
        fig.canvas.draw()
        fig.canvas.flush_events()

    def set_dataproc_visible(event):
        '''Show eeg without source'''
        status = show_checkbutton.get_status()
        if status[0] is True:
            for line in LINES_eeg_proc:
                line.set_visible(True)
        else:
            for line in LINES_eeg_proc:
                line.set_visible(False)
        fig.canvas.draw()
        fig.canvas.flush_events()

    # Disconnect defaults events
    try:
        matplotlib.rcParams['keymap.back'].remove('left')
        matplotlib.rcParams['keymap.forward'].remove('right')
    except ValueError:
        pass

    # connect events
    fig.canvas.mpl_connect('scroll_event',
                            lambda event: scroll_channels_mouse(event))
    fig.canvas.mpl_connect('key_release_event',
                            lambda event: scroll_time(event))
    fig.canvas.mpl_connect('key_release_event',
                            lambda event: scroll_channels_keyboard(event))
    show_checkbutton.on_clicked(set_dataproc_visible)

    # Properties
    topomap_axis = fig.add_subplot(gs02[0:4, :])
    image_axis = fig.add_subplot(gs00[0, :])
    erp_axis = fig.add_subplot(gs00[2, :])
    spectrum_axis = fig.add_subplot(gs02[4:7, :])
    variance_axis = fig.add_subplot(gs00[1, :])
    ica.plot_properties(inst, picks=current_idx['index'],
        axes=[topomap_axis, image_axis, erp_axis, spectrum_axis, variance_axis],
        dB=True, plot_std=True, topomap_args=None, image_args=None,
        psd_args=None, figsize=None, show=False)

    # Set layout
    plt.tight_layout()
    plt.show()
    return fig


def plot_ica_components_with_timeseries(ica, picks=None, ch_type=None, res=64,
                        layout=None, vmin=None, vmax=None, cmap='RdBu_r',
                        sensors=True, colorbar=False, title=None,
                        show=True, outlines='head', contours=6,
                        image_interp='bilinear', head_pos=None,
                        inst=None):
    from mne.io import BaseRaw
    from mne.epochs import BaseEpochs
    from mne.channels import _get_ch_type
    if picks is None:  # plot components by sets of 20
        ch_type = _get_ch_type(ica, ch_type)
        n_components = ica.mixing_matrix_.shape[1]
        p = 20
        figs = []
        for k in range(0, n_components, p):
            picks = range(k, min(k + p, n_components))
            fig = plot_ica_components_with_timeseries(ica,
                                      picks=picks, ch_type=ch_type,
                                      res=res, layout=layout, vmax=vmax,
                                      cmap=cmap, sensors=sensors,
                                      colorbar=colorbar, title=title,
                                      show=show, outlines=outlines,
                                      contours=contours,
                                      image_interp=image_interp,
                                      head_pos=head_pos, inst=inst)
            figs.append(fig)
        return figs
    elif np.isscalar(picks):
        picks = [picks]
    ch_type = _get_ch_type(ica, ch_type)

    cmap = _setup_cmap(cmap, n_axes=len(picks))
    data = np.dot(ica.mixing_matrix_[:, picks].T,
                  ica.pca_components_[:ica.n_components_])

    if ica.info is None:
        raise RuntimeError('The ICA\'s measurement info is missing. Please '
                           'fit the ICA or add the corresponding info object.')

    data_picks, pos, merge_grads, names, _ = _prepare_topo_plot(ica, ch_type,
                                                                layout)
    pos, outlines = _check_outlines(pos, outlines, head_pos)
    if outlines == 'head':
        pos = _autoshrink(outlines, pos, res)

    data = np.atleast_2d(data)
    data = data[:, data_picks]

    # prepare data for iteration
    fig, axes = _prepare_trellis(len(data), max_col=5)
    if title is None:
        title = 'ICA components'
    fig.suptitle(title)

    if merge_grads:
        from ..channels.layout import _merge_grad_data
    titles = list()
    for ii, data_, ax in zip(picks, data, axes):
        kwargs = dict(color='gray') if ii in ica.exclude else dict()
        titles.append(ax.set_title(ica._ica_names[ii], fontsize=12, **kwargs))
        data_ = _merge_grad_data(data_) if merge_grads else data_
        vmin_, vmax_ = _setup_vmin_vmax(data_, vmin, vmax)
        im = plot_topomap(
            data_.flatten(), pos, vmin=vmin_, vmax=vmax_, res=res, axes=ax,
            cmap=cmap[0], outlines=outlines, contours=contours,
            image_interp=image_interp, show=False, sensors=sensors)[0]
        im.axes.set_label(ica._ica_names[ii])
        if colorbar:
            cbar, cax = _add_colorbar(ax, im, cmap, title="AU",
                                      side="right", pad=.05, format='%3.2f')
            cbar.ax.tick_params(labelsize=12)
            cbar.set_ticks((vmin_, vmax_))
        _hide_frame(ax)
    tight_layout(fig=fig)
    fig.subplots_adjust(top=0.88, bottom=0.)
    fig.canvas.draw()

    # add title selection interactivity
    def onclick_title(event, ica=ica, titles=titles):
        # check if any title was pressed
        title_pressed = None
        for title in titles:
            if title.contains(event)[0]:
                title_pressed = title
                break
        # title was pressed -> identify the IC
        if title_pressed is not None:
            label = title_pressed.get_text()
            ic = int(label[-3:])
            # add or remove IC from exclude depending on current state
            if ic in ica.exclude:
                ica.exclude.remove(ic)
                title_pressed.set_color('k')
            else:
                ica.exclude.append(ic)
                title_pressed.set_color('gray')
            fig.canvas.draw()
    fig.canvas.mpl_connect('button_press_event', onclick_title)

    # add plot_properties interactivity only if inst was passed
    if isinstance(inst, (BaseRaw, BaseEpochs)):
        def onclick_topo(event, ica=ica, inst=inst):
            # check which component to plot
            if event.inaxes is not None:
                label = event.inaxes.get_label()
                if label.startswith('ICA'):
                    ic = int(label[-3:])
                    plot_properties_with_timeseries(inst, ica, picks=ic)
        fig.canvas.mpl_connect('button_press_event', onclick_topo)

    plt_show(show)
    return fig

def tolow(s):
    return(s.lower())
