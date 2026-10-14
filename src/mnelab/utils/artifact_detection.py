# © MNELAB developers
#
# License: BSD (3-clause)

import mne
import numpy as np
from scipy import stats

from mnelab.utils.dependencies import have


def find_bad_epochs_amplitude(data, threshold):
    """Detect epochs with extreme amplitude values.

    Parameters
    ----------
    data : mne.Epochs
        Epoched data.
    threshold : float
        Amplitude threshold in Volts (V). Epochs where any sample (after removing the
        mean) falls outside the range [-threshold, +threshold] will be marked as bad.

    Returns
    -------
    numpy.ndarray, shape (n_epochs,)
        Boolean array where True indicates a bad epoch.
    """
    epochs_data = data.get_data()
    epoch_mean = epochs_data.mean(axis=-1, keepdims=True)
    return np.any(np.abs(epochs_data - epoch_mean) > threshold, axis=(1, 2))


def find_bad_epochs_autoreject(data):
    """Detect epochs using autoreject-computed thresholds.

    Parameters
    ----------
    data : mne.Epochs
        Epoched data.

    Returns
    -------
    numpy.ndarray, shape (n_epochs,)
        Boolean array where True indicates a bad epoch.

    Notes
    -----
    Requires the autoreject package to be installed.
    """
    if not have["autoreject"]:
        raise ImportError("The autoreject package is required for this method.")

    from autoreject import get_rejection_threshold

    reject_dict = get_rejection_threshold(data, decim=2, verbose=False)
    epoch_data = data.get_data()
    bad_epochs = np.zeros(len(data), dtype=bool)
    for ch_type, threshold in reject_dict.items():
        if ch_type == "eeg":
            picks = mne.pick_types(data.info, eeg=True, meg=False)
        elif ch_type == "mag":
            picks = mne.pick_types(data.info, meg="mag", eeg=False)
        elif ch_type == "grad":
            picks = mne.pick_types(data.info, meg="grad", eeg=False)
        else:
            continue

        if len(picks) == 0:
            continue

        ch_data = epoch_data[:, picks, :]
        bad_epochs |= np.any(np.abs(ch_data) > threshold, axis=(1, 2))

    return bad_epochs


def find_bad_epochs_ptp(data, threshold):
    """Detect epochs with excessive peak-to-peak amplitude.

    Parameters
    ----------
    data : mne.Epochs
        Epoched data.
    threshold : float
        Peak-to-peak amplitude threshold in Volts (V). Epochs with peak-to-peak
        amplitude exceeding this threshold will be marked as bad.

    Returns
    -------
    numpy.ndarray, shape (n_epochs,)
        Boolean array where True indicates a bad epoch.
    """
    ptp_values = np.ptp(data.get_data(), axis=2)
    return np.any(ptp_values > threshold, axis=1)


def find_bad_epochs_kurtosis(data, threshold):
    """Detect epochs with abnormal kurtosis values.

    Parameters
    ----------
    data : mne.Epochs
        Epoched data.
    threshold : float
        Z-score threshold for kurtosis. Epochs with kurtosis z-scores exceeding this
        threshold will be marked as bad.

    Returns
    -------
    numpy.ndarray, shape (n_epochs,)
        Boolean array where True indicates a bad epoch.
    """
    kurt_values = stats.kurtosis(data.get_data(), axis=2, fisher=True)

    kurt_mean = np.mean(kurt_values, axis=0)
    kurt_std = np.std(kurt_values, axis=0)

    z_scores = np.abs((kurt_values - kurt_mean) / (kurt_std + 1e-10))
    return np.any(z_scores > threshold, axis=1)
