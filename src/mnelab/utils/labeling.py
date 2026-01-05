"""
The ONNX model (`ICLabelNet.onnx`) and parts of the feature extraction logic
are adapted from the `mne-icalabel` library.

Source Repository: https://github.com/mne-tools/mne-icalabel
"""

from pathlib import Path

import numpy as np
import onnx
from mne import BaseEpochs
from scipy.signal import resample_poly


# topomaps (32x32 images)
def _get_topomaps(inst, icawinv, picks):
    """Generate topographic maps for ICA components.

    This function computes the topographic maps by interpolating the ICA mixing matrix
    (inverse weights) onto a 32x32 grid.

    Parameters
    ----------
    inst : instance of Raw | Epochs
        The data instance. Used to retrieve channel locations (montage).
    icawinv : np.ndarray
        The inverse ICA weights matrix (mixing matrix).
    picks : list
        List of channel names to include in the topoplot generation.

    Returns
    -------
    np.ndarray, shape (n_components, 1, 32, 32)
        The interpolated topographic maps.


    Notes
    -----
    This function is adapted from `mne-icalabel` (specifically `_eeg_topoplot`
    and `_topoplotFast`).
    """

    rd, th = _get_eeglab_coords(inst, picks)
    th = np.pi / 180 * th  # convert degrees to radians

    n_comp = icawinv.shape[-1]
    topo = np.zeros((n_comp, 32, 32), dtype=np.float32)

    grid_scale = 32  # number of pixels
    rmax = 0.5

    # convert electrode locations from polar to cartesian coordinates
    x = rd * np.cos(th)
    y = rd * np.sin(th)

    # squeeze channel location to <= rmax
    plotrad = min(1, np.max(rd) * 1.02)
    plotrad = max(plotrad, 0.5)

    squeezefac = rmax / plotrad
    x *= squeezefac
    y *= squeezefac

    xmin, xmax = min(-rmax, x.min()), max(rmax, x.max())
    ymin, ymax = min(-rmax, y.min()), max(rmax, y.max())

    # interpolate scalp map data
    xi = np.linspace(xmin, xmax, grid_scale)
    yi = np.linspace(ymin, ymax, grid_scale)
    XQ, YQ = np.meshgrid(xi, yi)

    # mask out data outside the head
    mask = np.sqrt(XQ**2 + YQ**2) <= rmax

    # distance matrix grid-sensors
    xy_grid = (XQ + 1j * YQ).flatten()
    xy_sensors = (x + 1j * y).flatten()
    d = np.abs(xy_grid[:, None] - xy_sensors[None, :])

    # Green's function
    # Describes the influence of sensors on grid points based on distance
    with np.errstate(divide="ignore", invalid="ignore"):
        g = (d**2) * (np.log(d) - 1)
    g[np.isnan(g)] = 0

    # distance matrix sensors-sensors
    d_s = np.abs(xy_sensors[:, None] - xy_sensors[None, :])
    with np.errstate(divide="ignore", invalid="ignore"):
        g_s = (d_s**2) * (np.log(d_s) - 1)
    np.fill_diagonal(g_s, 0)

    # compute weights for all components
    # g_s * weights = values  -> weights = lstsq(g_s, values)
    weights, *_ = np.linalg.lstsq(g_s, icawinv, rcond=None)

    # Z = g * weights
    # (1024, n_sensors) @ (n_sensors, n_comp) -> (1024, n_comp)
    Zi_all = g @ weights

    for it in range(n_comp):
        Zi = Zi_all[:, it].reshape(grid_scale, grid_scale)
        Zi = Zi.T
        Zi[~mask] = 0  # NaNs to 0

        # normalize
        max_val = np.max(np.abs(Zi))
        if max_val != 0:
            Zi /= max_val

        topo[it, :, :] = Zi

    # (n_comp, 1, 32, 32)
    return topo[:, np.newaxis, :, :]


def _get_eeglab_coords(inst, picks):
    """Calculate normalized polar coordinates (rd, th) for the topomaps.

    Parameters
    ----------
    inst : instance of Raw | Epochs
        The data instance to retrieve channel locations.
    picks : list
        List of channel names.

    Returns
    -------
    rd : np.ndarray, shape (1, n_channels)
        Normalized radial distances.
    th : np.ndarray, shape (1, n_channels)
        Azimuth angles in degrees.

    Notes
    -----
    This function is adapted from `mne-icalabel` (specifically `_mne_to_eeglab_locs`).
    """

    montage = inst.copy().pick(picks).get_montage()
    if montage is None:
        raise ValueError("Montage must be set before ICLabel classification.")

    positions = montage.get_positions()
    ch_pos = positions["ch_pos"]
    # check that we do have a coordinate for every points
    empty = [key for key in ch_pos if np.all(np.isnan(ch_pos[key]))]
    if len(empty) != 0:
        raise ValueError("Channel positions are missing.")

    # get locations as a 2D array
    locs = np.vstack(list(ch_pos.values()))

    # Obtain cartesian coordinates
    x = locs[:, 1]
    y = -1 * locs[:, 0]  # nose orientation in eeglab and mne
    z = locs[:, 2]

    azimuth = np.arctan2(y, x)
    elevation = np.arctan2(z, np.sqrt(x**2 + y**2))

    rd = (np.pi / 2 - elevation) / np.pi
    th = np.degrees(-azimuth)

    return rd.reshape([1, -1]), th.reshape([1, -1])


# autocorrelation
def _get_autocorrelation(ica_act, sfreq):
    """Compute autocorrelation features for ICA components.

    This function calculates the autocorrelation of the ICA activations. For
    continuous data longer than 5 seconds, the Welch method is used. For shorter
    segments or epochs, standard FFT-based autocorrelation is applied.

    Parameters
    ----------
    ica_act : np.ndarray
        The ICA activations.
    sfreq : float
        The sampling frequency of the data.

    Returns
    -------
    np.ndarray, shape (n_components, 1, 1, 100)
        The autocorrelation features reshaped for classification.

    Notes
    -----
    This function is adapted from `mne-icalabel` (specifically `_eeg_autocorr_welch`,
    `_eeg_autocorr` and `_eeg_autocorr_fftw`).
    """
    n_lags = int(sfreq) + 1
    # compute autocorrelation for epoched data
    if ica_act.ndim == 3:
        # (n_comp, n_times, n_epochs)
        n_comp, n_times, _ = ica_act.shape

        nfft = 2 ** int(np.ceil(np.log2(2 * n_times - 1)))

        fft_data = np.fft.rfft(ica_act, nfft, axis=1)

        psd = np.abs(fft_data) ** 2
        psd_mean = np.mean(psd, axis=2)

        ac = np.fft.irfft(psd_mean, n=nfft, axis=1)

        # trimming to one second
        if ac.shape[1] > n_lags:
            ac = ac[:, :n_lags]
        else:
            padding = np.zeros((n_comp, n_lags - ac.shape[1]))
            ac = np.hstack([ac, padding])

        # normalization
        var = ac[:, 0:1]
        var[var == 0] = 1.0
        ac = ac / var
    # compute autocorrelation for continuous data
    else:
        n_comp, n_points = ica_act.shape

        # compute autocorrelation for long signals
        if n_points > 5 * sfreq:
            n_seg = int(min(n_points, 3 * sfreq))
            n_overlap = n_seg // 2

            nfft = 2 ** int(np.ceil(np.log2(2 * n_seg - 1)))

            # segments
            step = n_seg - n_overlap
            cutoff = (n_points // n_seg) * n_seg
            starts = np.arange(0, cutoff - n_seg + step, step)
            if len(starts) == 0:
                starts = [0]

            # rfft results in nfft//2 + 1 frequency bins
            ac = np.zeros((n_comp, nfft // 2 + 1))

            for start in starts:
                segment = ica_act[:, start : start + n_seg]
                fft_segment = np.fft.rfft(segment, nfft, axis=1)
                ac += np.abs(fft_segment) ** 2

            ac_mean = ac / len(starts)

            ac = np.fft.irfft(ac_mean, n=nfft, axis=1)

            # normalization
            ac = ac[:, :n_lags]
            lags = np.arange(n_seg, n_seg - n_lags, -1)
            lags[lags <= 0] = 1

            denom = ac[:, 0:1] * (lags / n_seg)
            denom[denom == 0] = 1.0
            ac = ac / denom

        # compute autocorrelation for short signals
        else:
            nfft = 2 ** int(np.ceil(np.log2(2 * n_points - 1)))

            fft_data = np.fft.rfft(ica_act, nfft, axis=1)
            psd = np.abs(fft_data) ** 2
            ac = np.fft.irfft(psd, n=nfft, axis=1)

            # trimming to one second
            if ac.shape[1] > n_lags:
                ac = ac[:, :n_lags]
            else:
                # padding
                padding = np.zeros((n_comp, n_lags - ac.shape[1]))
                ac = np.hstack([ac, padding])

            var = ac[:, 0:1]
            var[var == 0] = 1.0
            ac = ac / var

    # resample to 1 second at 100 samples/sec
    down = int(sfreq)
    target_fs = 100

    if 101 < ac.shape[1] * 100 / down:
        down += 1
    ac_resampled = resample_poly(ac, up=target_fs, down=down, axis=1)

    # formatting - lag 0 is constant and not needed
    final_ac = ac_resampled[:, 1:]

    # (n_comp, 100) -> (n_comp, 1, 1, 100)
    features = final_ac[:, np.newaxis, np.newaxis, :]

    return features.astype(np.float32)


# PSD
def _get_psd(ica_act, sfreq):
    """Compute the Power Spectral Density (PSD) of ICA components.

    This function calculates the PSD using a windowed FFT approach, specifically
    tailored for ICA components. It handles both continuous and epoched data,
    normalizes the spectrum, interpolates line noise artifacts (if a notch filter
    was applied previously) and returns the PSD in dB.

    Parameters
    ----------
    ica_act : np.ndarray
        The ICA component activations.
    sfreq : float
        The sampling frequency of the data.

    Returns
    -------
    np.ndarray, shape (n_components, 1, 1, 100)
        The computed PSD values in dB.

    Notes
    -----
    This function is adapted from `mne-icalabel` (specifically `_eeg_rpsd_constants`,
    `_eeg_rpsd_compute_psdmed` and `_eeg_rpsd_format`).
    """

    # check if epoched or continuous
    if ica_act.ndim == 2:
        ica_act = ica_act[:, :, np.newaxis]

    n_comp, n_times, n_epochs = ica_act.shape

    # constants
    nyquist = int(np.floor(sfreq / 2))
    n_freqs = nyquist if nyquist < 100 else 100
    n_points = min(n_times, int(sfreq))

    cutoff = np.floor(n_times / n_points) * n_points
    range_ = np.ceil(np.arange(0, cutoff - n_points + n_points / 2, n_points / 2))

    index = np.tile(range_, (n_points, 1)).T + np.arange(0, n_points)
    index = index.T.astype(int)

    n_segments_per_epoch = index.shape[1]

    # window setup
    window = np.hamming(n_points)
    window = window[:, np.newaxis]
    denominator = sfreq * np.sum(window**2)

    psd_list = []

    for comp_idx in range(n_comp):
        # select current component data
        comp_data = ica_act[comp_idx]

        # select all time windows
        windowed_data = comp_data[index, :]

        # reshape for FFt: (n_points, n_segments_per_epoch * n_epochs)
        time_segments = windowed_data.reshape(
            n_points, n_segments_per_epoch * n_epochs, order="F"
        )

        # Apply window
        time_segments *= window

        fft = np.fft.fft(time_segments, n=n_points, axis=0)
        power_spectrum = np.abs(fft) ** 2

        # slice relevant frequencies (1 to n_freqs) and normalize
        # index 0 is DC (ignored)
        subset_power = power_spectrum[1 : n_freqs + 1, :] * 2 / denominator

        # correction for Nyquist if present
        if n_freqs == nyquist:
            subset_power[-1, :] /= 2

        # compute median across windows
        median_power = np.median(subset_power, axis=1)

        # transform to dB
        psd_comp = 20 * np.log10(median_power)

        psd_list.append(psd_comp)

    psd = np.array(psd_list)

    if n_freqs < 100:
        # pads the last frequency value
        psd = np.pad(psd, ((0, 0), (0, 100 - n_freqs)), mode="edge")

    # eliminate line noise artifacts - interpolate 50Hz and 60Hz bins if needed
    for linenoise_ind in [49, 59]:
        neighbors_idx = [linenoise_ind - 1, linenoise_ind + 1]
        difference = psd[:, neighbors_idx] - psd[:, linenoise_ind, np.newaxis]
        is_notch_artifact = np.all(difference > 5, axis=1)

        if np.any(is_notch_artifact):
            psd[is_notch_artifact, linenoise_ind] = np.mean(
                psd[is_notch_artifact][:, neighbors_idx], axis=1
            )

    # normalize
    max_abs = np.max(np.abs(psd), axis=1, keepdims=True)
    max_abs[max_abs == 0] = 1.0
    psd /= max_abs

    # (n_comp, 100) -> (n_comp, 1, 1, 100)
    psd = psd[:, np.newaxis, np.newaxis, :]

    return psd.astype(np.float32)


def _get_ica_data(inst, ica):
    """Compute ICA inverse weights and activations.

    Parameters
    ----------
    inst : instance of Raw | Epochs
        The data instance containing the channel data.
    ica : ICA
        The fitted ICA instance.

    Returns
    -------
    icawinv : np.ndarray, shape (n_channels, n_components)
        The inverse ICA weights matrix (mixing matrix).
    icaact : np.ndarray, shape (n_components, n_times) for raw data or
            (n_components, n_times, n_epochs) for epoched data
        The ICA component activations.

    Notes
    -----
    This function is adapted from `mne-icalabel` (specifically
    `_retrieve_eeglab_icawinv` and `_compute_ica_activations`).
    """
    weights = ica.unmixing_matrix_ @ ica.pca_components_[: ica.n_components_]
    icawinv = np.linalg.pinv(weights)

    # data shape: (n_chan, n_times) or (n_epochs, n_chan, n_times)
    data = inst.get_data(picks=ica.ch_names) * 1e6

    # (n_comp, n_chan) @ (..., n_chan, n_times)
    # (n_comp, n_times) or (n_epochs, n_comp, n_times)
    icaact = weights @ data

    # if epochs -> (n_comp, n_times, n_epochs)
    if isinstance(inst, BaseEpochs):
        icaact = icaact.transpose(1, 2, 0)

    return icawinv, icaact


def _get_features(inst, ica):
    """Extract and format topographic, PSD, and autocorrelation features.

    Parameters
    ----------
    inst : instance of Raw | Epochs
        The data instance containing the channel data.
    ica : ICA
        The fitted ICA instance.

    Returns
    -------
    topo_features_formatted : np.ndarray, shape (4 * n_components, 1, 32, 32)
        The formatted topographic map features.
    psd_formatted : np.ndarray, shape (4 * n_components, 1, 1, 100)
        The formatted PSD features.
    autocorr_formatted : np.ndarray, shape (4 * n_components, 1, 1, 100)
        The formatted autocorrelation features.

    Notes
    -----
    This function is adapted from `mne-icalabel` (specifically
    `get_iclabel_features` and `_format_input`).
    """
    icawinv, ica_act = _get_ica_data(inst, ica)

    topo_features = _get_topomaps(inst, icawinv, ica.ch_names)
    psd_features = _get_psd(ica_act, inst.info["sfreq"])
    autocorr_features = _get_autocorrelation(ica_act, inst.info["sfreq"])

    topo_features *= 0.99
    psd_features *= 0.99
    autocorr_features *= 0.99

    # ONNX expects 4 versions of each topomap
    topo_features_formatted = np.concatenate(
        [
            topo_features,
            -topo_features,
            np.flip(topo_features, axis=3),
            np.flip(-topo_features, axis=3),
        ],
        axis=0,
    )
    psd_formatted = np.tile(psd_features, (4, 1, 1, 1))
    autocorr_formatted = np.tile(autocorr_features, (4, 1, 1, 1))

    return topo_features_formatted, psd_formatted, autocorr_formatted


def _load_onnx_weights(onnx_path):
    """Load weights and biases from ONNX model.

    Parameters
    ----------
    onnx_path : Path
        Path to the ONNX model file.

    Returns
    -------
    dict
        Dictionary containing all weights and biases from the model.
    """
    model = onnx.load(str(onnx_path))

    # extract initializers (weights and biases)
    weights = {}
    for initializer in model.graph.initializer:
        name = initializer.name
        # convert ONNX tensor to NumPy array
        if initializer.data_type == 1:  # float
            weights[name] = np.frombuffer(
                initializer.raw_data, dtype=np.float32
            ).reshape(initializer.dims)

    return weights


def _im2col(x, kernel_h, kernel_w, stride=1, padding=0):
    """Convert image batch to column matrix for vectorized convolution.

    This implements the "im2col" trick used in deep learning frameworks to convert
    convolution into matrix multiplication.

    Parameters
    ----------
    x : np.ndarray
        Input tensor, shape (batch, channels, height, width)
    kernel_h : int
        Kernel height
    kernel_w : int
        Kernel width
    stride : int
        Stride of the convolution
    padding : int or tuple
        Padding added to sides. Can be int (same for H and W) or tuple (pad_h, pad_w)

    Returns
    -------
    cols : np.ndarray
        Column matrix, shape (batch, channels*kernel_h*kernel_w, h_out*w_out)
    h_out : int
        Output height
    w_out : int
        Output width
    """
    batch, channels, h, w = x.shape

    # handle padding
    if isinstance(padding, tuple):
        pad_h, pad_w = padding
    else:
        pad_h = pad_w = padding

    # add padding
    if pad_h > 0 or pad_w > 0:
        x = np.pad(x, ((0, 0), (0, 0), (pad_h, pad_h), (pad_w, pad_w)))
        h, w = x.shape[2], x.shape[3]

    # calculate output dimensions
    h_out = (h - kernel_h) // stride + 1
    w_out = (w - kernel_w) // stride + 1

    # initialize output column matrix
    cols = np.zeros((batch, channels, kernel_h, kernel_w, h_out, w_out), dtype=x.dtype)

    # extract patches
    for i in range(kernel_h):
        i_max = i + stride * h_out
        for j in range(kernel_w):
            j_max = j + stride * w_out
            cols[:, :, i, j, :, :] = x[:, :, i:i_max:stride, j:j_max:stride]

    # reshape to (batch, channels*kernel_h*kernel_w, h_out*w_out)
    cols = cols.reshape(batch, channels * kernel_h * kernel_w, h_out * w_out)

    return cols, h_out, w_out


def _conv2d_numpy(x, weight, bias, stride=1, padding=0):
    """Perform 2D convolution using vectorized im2col approach.

    Parameters
    ----------
    x : np.ndarray
        Input tensor, shape (batch, in_channels, height, width)
    weight : np.ndarray
        Convolution kernel, shape (out_channels, in_channels, kh, kw)
    bias : np.ndarray
        Bias term, shape (out_channels,)
    stride : int
        Stride of the convolution
    padding : int or tuple
        Padding added to both sides. Can be int (same for all) or
        tuple (pad_h, pad_w) for different padding on height/width

    Returns
    -------
    out : np.ndarray
        Output tensor after convolution
    """
    batch, in_channels, h, w = x.shape
    out_channels, _, kh, kw = weight.shape

    # convert input to column matrix using vectorized im2col
    x_col, h_out, w_out = _im2col(x, kh, kw, stride, padding)

    # reshape weights: (out_channels, in_channels*kh*kw)
    weight_col = weight.reshape(out_channels, -1)

    # perform batched matrix multiplication
    # weight_col: (out_channels, in_channels*kh*kw)
    # x_col: (batch, in_channels*kh*kw, h_out*w_out)
    # result for each batch: (out_channels, h_out*w_out)
    out = np.zeros((batch, out_channels, h_out * w_out), dtype=np.float32)
    for b in range(batch):
        out[b] = weight_col @ x_col[b]

    # add bias
    out += bias[None, :, None]

    # reshape to proper output format
    out = out.reshape(batch, out_channels, h_out, w_out)

    return out


def _leaky_relu(x, alpha=0.2):
    """Apply Leaky ReLU activation."""
    return np.where(x > 0, x, alpha * x)


def _softmax(x, axis=-1):
    """Apply softmax activation."""
    exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


def _iclabel_forward_numpy(images, psd, autocorr, weights):
    """Forward pass through ICLabel network.

    Parameters
    ----------
    images : np.ndarray
        Topographic maps, shape (batch, 1, 32, 32)
    psd : np.ndarray
        Power spectral density, shape (batch, 1, 1, 100)
    autocorr : np.ndarray
        Autocorrelation, shape (batch, 1, 1, 100)
    weights : dict
        Dictionary containing model weights and biases

    Returns
    -------
    probs : np.ndarray
        Class probabilities, shape (batch, 7)
    """
    # image convolution branch
    x_img = images
    x_img = _conv2d_numpy(
        x_img,
        weights["img_conv.conv1.weight"],
        weights["img_conv.conv1.bias"],
        stride=2,
        padding=1,
    )
    x_img = _leaky_relu(x_img)
    x_img = _conv2d_numpy(
        x_img,
        weights["img_conv.conv2.weight"],
        weights["img_conv.conv2.bias"],
        stride=2,
        padding=1,
    )
    x_img = _leaky_relu(x_img)
    x_img = _conv2d_numpy(
        x_img,
        weights["img_conv.conv3.weight"],
        weights["img_conv.conv3.bias"],
        stride=2,
        padding=1,
    )
    x_img = _leaky_relu(x_img)

    # PSD convolution branch
    x_psd = psd
    x_psd = _conv2d_numpy(
        x_psd,
        weights["psds_conv.conv1.weight"],
        weights["psds_conv.conv1.bias"],
        padding=(0, 1),
    )
    x_psd = _leaky_relu(x_psd)
    x_psd = _conv2d_numpy(
        x_psd,
        weights["psds_conv.conv2.weight"],
        weights["psds_conv.conv2.bias"],
        padding=(0, 1),
    )
    x_psd = _leaky_relu(x_psd)
    x_psd = _conv2d_numpy(
        x_psd,
        weights["psds_conv.conv3.weight"],
        weights["psds_conv.conv3.bias"],
        padding=(0, 1),
    )
    x_psd = _leaky_relu(x_psd)

    # autocorrelation convolution branch
    x_autocorr = autocorr
    x_autocorr = _conv2d_numpy(
        x_autocorr,
        weights["autocorr_conv.conv1.weight"],
        weights["autocorr_conv.conv1.bias"],
        padding=(0, 1),
    )
    x_autocorr = _leaky_relu(x_autocorr)
    x_autocorr = _conv2d_numpy(
        x_autocorr,
        weights["autocorr_conv.conv2.weight"],
        weights["autocorr_conv.conv2.bias"],
        padding=(0, 1),
    )
    x_autocorr = _leaky_relu(x_autocorr)
    x_autocorr = _conv2d_numpy(
        x_autocorr,
        weights["autocorr_conv.conv3.weight"],
        weights["autocorr_conv.conv3.bias"],
        padding=(0, 1),
    )
    x_autocorr = _leaky_relu(x_autocorr)

    # Flatten spatial dimensions of PSD and autocorr into channels
    # The PSD and autocorr branches produce 1D features that need to be
    # reshaped to match the 2D spatial structure of the image branch
    batch, img_channels, img_h, img_w = x_img.shape

    # Flatten PSD and autocorr: (batch, C, H, W) -> (batch, C*H*W, 1, 1)
    x_psd_flat = x_psd.reshape(batch, -1, 1, 1)
    x_autocorr_flat = x_autocorr.reshape(batch, -1, 1, 1)

    # Tile to match image spatial dimensions
    x_psd_tiled = np.tile(x_psd_flat, (1, 1, img_h, img_w))
    x_autocorr_tiled = np.tile(x_autocorr_flat, (1, 1, img_h, img_w))

    # Concatenate all branches along channel dimension
    x = np.concatenate([x_img, x_psd_tiled, x_autocorr_tiled], axis=1)

    # Final convolution
    x = _conv2d_numpy(x, weights["conv.weight"], weights["conv.bias"])

    # Softmax and average over spatial dimensions
    x = _softmax(x, axis=1)
    x = np.mean(x, axis=(2, 3))

    # Average over the 4 versions of each component
    # Input has 4 augmented versions per component in interleaved order:
    # [comp0_v0, comp1_v0, ..., compN_v0, comp0_v1, comp1_v1, ..., compN_v1, ...]
    # Need to reshape to (n_components, 4, 7) and average over versions
    n_components = batch // 4
    # Reshape from (batch, 7) to (4, n_components, 7)
    # then transpose to (n_components, 4, 7)
    x = x.reshape(4, n_components, -1).transpose(1, 0, 2).mean(axis=1)

    return x


def run_iclabel(inst, ica):
    """Executes ICLabel classification on ICA components using NumPy.

    This function extracts the necessary features (topomaps, PSD, autocorrelation)
    from the raw and ICA data to obtain class probabilities for each component
    using a pure NumPy implementation of the ICLabel neural network.

    Parameters
    ----------
    inst : instance of Raw | Epochs
        The data instance containing the channel data.
    ica : ICA
        The fitted ICA instance.

    Returns
    -------
    np.ndarray, shape (n_components, 7)
        The estimated probabilities for each component class.
        Columns: [Brain, Muscle, Eye, Heart, Line Noise, Channel Noise, Other].
    """
    onnx_path = Path(__file__).parent / "ICLabelNet.onnx"
    if not onnx_path.exists():
        raise FileNotFoundError(f"ICLabel ONNX model not found at {onnx_path}")

    images, psd, autocorrelation = _get_features(inst, ica)

    weights = _load_onnx_weights(onnx_path)
    probs = _iclabel_forward_numpy(images, psd, autocorrelation, weights)

    return probs
