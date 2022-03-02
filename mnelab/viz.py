# © MNELAB developers
#
# License: BSD (3-clause)

import math

import matplotlib.pyplot as plt
import numpy as np
from mne.stats import permutation_cluster_1samp_test as pcluster_test
from mne.time_frequency import tfr_multitaper
from mne.viz import plot_compare_evokeds


def _center_cmap(cmap, vmin, vmax, name="cmap_centered"):
    """
    Center given colormap (ranging from vmin to vmax) at value 0.

    Taken from MNE-Python v0.24, as it will be removed in MNE-Python v1.0.

    Parameters
    ----------
    cmap : matplotlib.colors.Colormap
        The colormap to center around 0.
    vmin : float
        Minimum value in the data to map to the lower end of the colormap.
    vmax : float
        Maximum value in the data to map to the upper end of the colormap.
    name : str
        Name of the new colormap. Defaults to 'cmap_centered'.

    Returns
    -------
    cmap_centered : matplotlib.colors.Colormap
        The new colormap centered around 0.

    Notes
    -----
    This function can be used in situations where vmin and vmax are not symmetric around
    zero. Normally, this results in the value zero not being mapped to white anymore in many
    colormaps. Using this function, the value zero will be mapped to white even for
    asymmetric positive and negative value ranges. Note that this could also be achieved by
    re-normalizing a given colormap by subclassing matplotlib.colors.Normalize as described
    here:
    https://matplotlib.org/users/colormapnorms.html#custom-normalization-two-linear-ranges
    """
    from matplotlib.colors import LinearSegmentedColormap

    vzero = abs(vmin) / float(vmax - vmin)
    index_old = np.linspace(0, 1, cmap.N)
    index_new = np.hstack([
        np.linspace(0, vzero, cmap.N // 2, endpoint=False),
        np.linspace(vzero, 1, cmap.N // 2),
    ])

    colors = ("red", "green", "blue", "alpha")
    cdict = {name: [] for name in colors}
    for old, new in zip(index_old, index_new):
        for color, name in zip(cmap(old), colors):
            cdict[name].append((new, color, color))
    return LinearSegmentedColormap(name, cdict)


def _get_rows_cols(n):
    if n <= 3:
        rows, cols = 1, n
    else:
        rows = round(math.sqrt(n))
        cols = math.ceil(math.sqrt(n))
    return rows, cols


def _calc_tfr(epochs, freqs, baseline, times, alpha=None):
    """
    Calculate AverageTFR and significance masks for given epochs.

    Adapted from https://mne.tools/dev/auto_examples/time_frequency/time_frequency_erds.html

    Parameters
    ----------
    epochs : mne.epochs.Epochs
        Epochs extracted from a Raw instance.
    freqs : np.ndarray
        The frequencies in Hz.
    baseline : array_like, shape (2,)
        The time interval to apply rescaling / baseline correction.
    times : array_like, shape (2,)
        Start and end of crop time interval.
    alpha : float, optional
        If specified, calculate significance maps with threshold `alpha`, by default `None`.

    Returns
    -------
    dict[str, tuple[mne.time_frequency.tfr.EpochsTFR, dict[str, np.ndarray | None]]]
        A dictionary where keys are event IDs and values are tuples (`tfr_ev`, `masks`).
        `tfr_ev` is the EpochsTFR object for the respective event. `masks` is again a
        dictionary, where keys are channel names and values are significance masks.
        Significance masks are `None` if `alpha` was not specified.
    """
    tfr = tfr_multitaper(epochs, freqs, freqs, average=False, return_itc=False)
    tfr.apply_baseline(baseline, mode="percent")
    tfr.crop(*times)

    pcluster_kwargs = dict(
        n_permutations=100,
        step_down_p=0.05,
        seed=1,
        buffer_size=None,
        out_type='mask',
    )

    res = {}

    for event in epochs.event_id:
        tfr_ev = tfr[event]
        masks = {}
        for ch in range(epochs.info["nchan"]):
            mask = None
            if alpha is not None:
                # positive clusters
                _, c1, p1, _ = pcluster_test(tfr_ev.data[:, ch], tail=1, **pcluster_kwargs)
                # negative clusters
                _, c2, p2, _ = pcluster_test(tfr_ev.data[:, ch], tail=-1, **pcluster_kwargs)

                c = np.stack(c1 + c2, axis=2)  # combined clusters
                p = np.concatenate((p1, p2))   # combined p-values
                mask = c[..., p <= alpha].any(axis=-1)
            masks[epochs.ch_names[ch]] = mask
        res[event] = (tfr_ev, masks)
    return res


def plot_erds(tfr_and_masks):
    """
    Plot ERDS maps from given TFR and significance masks.

    Parameters
    ----------
    tfr_and_masks : dict[str, tuple[EpochsTFR, dict[str, np.ndarray |None]]]
        A dictionary where keys are event IDs and values are tuples (`tfr_ev`, `masks`).
        `tfr_ev` is the EpochsTFR object for the respective event. `masks` is again a
        dictionary, where keys are channel names and values are significance masks.

    Returns
    -------
    list[matplotlib.figure.Figure]
        A list of the figure(s) generated, one figure per event.
    """
    figs = []

    for event, (tfr_ev, masks) in tfr_and_masks.items():
        n_rows, n_cols = _get_rows_cols(tfr_ev.info["nchan"])
        widths = n_cols * [10] + [1]  # each map has width 10, each colorbar width 1
        fig, axes = plt.subplots(n_rows, n_cols + 1, gridspec_kw={"width_ratios": widths})
        vmin, vmax = -1, 2  # default for ERDS maps
        cmap = _center_cmap(plt.cm.RdBu, vmin, vmax)

        # skip the last column in `axes`, as it contains the colorbar
        for (ch_name, mask), ax in zip(masks.items(), axes[..., :-1].flat):
            tfr_ev.average().plot(
                [ch_name],
                vmin=vmin,
                vmax=vmax,
                cmap=(cmap, False),
                axes=ax,
                colorbar=False,
                mask=mask,
                mask_style="mask" if mask is not None else None,  # avoid RuntimeWarning
                show=False,
            )
            ax.set_title(ch_name, fontsize=10)
            ax.axvline(0, linewidth=1, color="black", linestyle=":")
            ax.set(xlabel="t (s)", ylabel="f (Hz)")
            ax.label_outer()
        for ax in axes[..., -1].flat:
            fig.colorbar(axes.flat[0].images[-1], cax=ax)
        fig.suptitle(f"ERDS – {event}")
        figs.append(fig)
    return figs


def plot_erds_topomaps(epochs, events, freqs, baseline, times):
    """
    Plot ERDS topomaps, one figure per event.

    Parameters
    ----------
    epochs : mne.epochs.Epochs
        Epochs extracted from a Raw instance.
    events : list[str]
        Events to include.
    freqs : np.ndarray
        Array of frequencies over which the average is taken.
    baseline : tuple[float, float]
        Start and end times for baseline correction.
    times : tuple[float, float]
        Start and end times between which the average is taken.

    Returns
    -------
    list[matplotlib.figure.Figure]
        A list of the figure(s) generated.
    """
    vmin, vmax = -1, 2
    cmap = _center_cmap(plt.cm.RdBu, vmin, vmax)

    figs = []
    for event in events:
        tfr = tfr_multitaper(epochs[event], freqs, freqs, average=True, return_itc=False)
        tfr.apply_baseline(baseline, mode="percent")
        tfr.crop(*times)
        fig = tfr.plot_topomap(
            title=f"Event: {event}",
            unit="ERDS",
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            cbar_fmt="%.1f",
        )
        fig.set_size_inches(4, 3)
        fig.set_tight_layout(True)
        figs.append(fig)
    return figs


def plot_evoked(
    epochs,
    picks,
    events,
    gfp,
    spatial_colors,
    topomap_times,
):
    """
    Plot evoked potentials of different events for individual channels.

    If multiple events are selected, one figure will be returned for each.

    Parameters
    ----------
    epochs : mne.epochs.Epochs
        Epochs extracted from a Raw instance.
    picks : list[str]
        Channels to include.
    events : list[str]
        Events to include.
    gfp : bool | "only"
        Plot the global field power (GFP).
    spatial_colors : bool
        If `True`, the lines are color coded by mapping physical sensor
        coordinates into color values. Spatially similar channels will have
        similar colors. Bad channels will be dotted. If `False`, the good
        channels are plotted black and bad channels red.
    topomap_times : list[float] | "auto" | "peaks"
        The time point(s) to plot. If `"auto"`, 5 evenly spaced topographies
        between the first and last time instant will be shown. If `"peaks"`,
        finds time points automatically by checking for 3 local maxima in
        Global Field Power.

    Returns
    -------
    list[matplotlib.figure.Figure]
        A list of the figure(s) generated.
    """
    figs = []
    for event in events:
        evoked = epochs[event].average(picks=picks)
        if topomap_times:
            figs.append(evoked.plot_joint(
                times=topomap_times,
                title=f'Event: {event}',
                picks=picks,
                ts_args={
                    "spatial_colors": spatial_colors,
                    "gfp": gfp,
                }
            ))
        else:
            figs.append(evoked.plot(
                window_title=f'Event: {event}',
                picks=picks,
                spatial_colors=spatial_colors,
                gfp=gfp
            ))
    return figs


def plot_evoked_comparison(
    epochs,
    picks,
    events,
    average_method,
    combine,
    confidence_intervals,
):
    """
    Plot evoked potentials of different events averaged over channels.

    If multiple channel types are selected, one figure will be returned for
    each channel type.

    Parameters
    ----------
    epochs : mne.epochs.Epochs
        Epochs extracted from a Raw instance.
    picks : list[str]
        Channels to include.
    events : list[str]
        Events to include.
    average_method : {"mean", "median"}
        How to combine the data during averaging.
    combine : {"gfp", "std", mean", "median"}
        How to combine information across channels.
    confidence_intervals : bool
        If `True`, plot confidence intervals as shaded areas.

    Returns
    -------
    list[matplotlib.figure.Figure]
        A list of the figure(s) generated.
    """
    if confidence_intervals:
        evokeds = {e: list(epochs[e].iter_evoked()) for e in events}
    else:
        evokeds = {e: epochs[e].average(picks=picks, method=average_method, by_event_type=True) for e in events}  # noqa: E501
    return plot_compare_evokeds(evokeds, picks=picks, combine=combine)


def plot_evoked_topomaps(epochs, events, average_method, times):
    """
    Plot evoked topomaps.

    One figure is generated for each event.

    Parameters
    ----------
    epochs : mne.epochs.Epochs
        Epochs extracted from a Raw instance.
    events : list[str]
        Events to include.
    average_method : "mean" | "median
        How to average epochs.
    times : list[float] | "auto" | "peaks" | "interactive"
        The time point(s) to plot.

    Returns
    -------
    list[matplotlib.figure.Figure]
        A list of the figure(s) generated.
    """
    figs = []
    for event in events:
        evoked = epochs[event].average(method=average_method)
        figs.append(evoked.plot_topomap(times, title=f'Event: {event}'))
        if times == 'interactive':
            figs[-1].set_size_inches(6, 4)
    return figs
