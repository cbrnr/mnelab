import os

import numpy as np
import scipy
import pandas as pd
import mne
import seaborn as sns
import matplotlib.pyplot as plt

from mne.channels import Montage
from mne.viz.topomap import _plot_topomap
from mne.channels.layout import _find_topomap_coords
from matplotlib.gridspec import GridSpec

def plot_correlation_matrix(raw, ica):
    "Plot correlation_matrix"
    raw = raw.copy()
    ch_names = raw.info["ch_names"]
    path = os.path.join('.', 'mnelab','ica_templates', 'template-ica.fif')
    ica_template = mne.preprocessing.read_ica(path)
    common = find_common_channels(ica_template, ica)
    components_template, components_ics = extract_common_components(ica_template, ica)
    templates = components_template[[0, 7]]
    df = compute_correlation(templates, components_ics)
    raw.rename_channels(tolow)
    raw.reorder_channels(common)
    pos = _find_topomap_coords(raw.info, picks=[i for i in range(len(ch_names)) if ch_names[i].lower() in common])
    quality = len(common) / len(ch_names)
    plot_correlation(df, templates, pos, quality)
    return()


def compute_gfp_raw(raw):
    return(np.mean(raw.get_data()**2, axis=0)**0.5)


def compute_gfp_epoch(epochs):
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
        fig, ax = plt.subplots()
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
        ax.set_title("""Global field power before (red) and after (black) source rejection""")
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
    fig = plt.figure()
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


def tolow(s):
    return(s.lower())
