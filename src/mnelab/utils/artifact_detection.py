import mne
import numpy as np
from scipy import stats

from mnelab.utils.dependencies import have


def detect_extreme_values(data, threshold):
    """Detect artifacts based on absolute amplitude threshold."""
    threshold_muV = threshold * 1e-6
    bad_epochs = np.any(np.abs(data.get_data()) > threshold_muV, axis=(1, 2))
    return bad_epochs


def detect_with_autoreject(data):
    """Detect artifacts using autoreject-computed thresholds."""
    if not have.get("autoreject", False):
        raise ImportError("autoreject package is required for this method")

    from autoreject import get_rejection_threshold

    reject_dict = get_rejection_threshold(data, decim=2)
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
        # OR logic for bad epochs across channels
        bad_epochs |= np.any(np.abs(ch_data) > threshold, axis=(1, 2))

    return bad_epochs


def detect_peak_to_peak(data, ptp_threshold):
    """Detect artifacts based on peak-to-peak amplitude."""
    ptp_threshold_muV = ptp_threshold * 1e-6
    epoch_data = data.get_data()

    ptp_values = np.ptp(epoch_data, axis=2)
    bad_epochs = np.any(ptp_values > ptp_threshold_muV, axis=1)

    return bad_epochs


def detect_kurtosis(data, kurtosis):
    """Detect artifacts based on kurtosis."""
    epoch_data = data.get_data()
    kurt_values = stats.kurtosis(epoch_data, axis=2, fisher=True)

    kurt_mean = np.mean(kurt_values, axis=0)
    kurt_std = np.std(kurt_values, axis=0)

    z_scores = np.abs((kurt_values - kurt_mean) / (kurt_std + 1e-10))
    bad_epochs = np.any(z_scores > kurtosis, axis=1)

    return bad_epochs
