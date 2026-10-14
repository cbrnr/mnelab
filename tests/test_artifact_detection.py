# © MNELAB developers
#
# License: BSD (3-clause)

import mne
import numpy as np
import pytest

from mnelab.utils.artifact_detection import (
    find_bad_epochs_amplitude,
    find_bad_epochs_kurtosis,
    find_bad_epochs_ptp,
)


@pytest.fixture
def clean_epochs():
    """Create clean EpochsArray for testing."""
    rng = np.random.default_rng(42)
    n_epochs = 30
    n_channels = 3
    n_times = 100
    sfreq = 100
    data = rng.standard_normal((n_epochs, n_channels, n_times)) * 1e-6
    info = mne.create_info(
        ch_names=[f"Ch{i}" for i in range(n_channels)], sfreq=sfreq, ch_types="eeg"
    )
    return mne.EpochsArray(data, info)


@pytest.mark.parametrize(
    "detection_func,threshold",
    [
        (find_bad_epochs_amplitude, 100e-6),
        (find_bad_epochs_ptp, 100e-6),
        (find_bad_epochs_kurtosis, 5.0),
    ],
)
def test_no_artifacts_detected(clean_epochs, detection_func, threshold):
    """Test that clean data with high thresholds produces no bad epochs."""
    bad_epochs = detection_func(clean_epochs, threshold=threshold)

    assert bad_epochs.shape == (30,)
    assert bad_epochs.dtype == bool
    assert not bad_epochs.any()


def test_find_bad_epochs_amplitude(clean_epochs):
    """Test amplitude-based artifact detection."""
    epochs_data = clean_epochs.get_data()
    bad_idx = [2, 8, 14]
    epochs_data[bad_idx, 0, 50] = 150e-6
    epochs = mne.EpochsArray(epochs_data, clean_epochs.info)

    bad_epochs = find_bad_epochs_amplitude(epochs, threshold=100e-6)
    np.testing.assert_array_equal(np.where(bad_epochs)[0], bad_idx)


def test_find_bad_epochs_ptp(clean_epochs):
    """Test peak-to-peak amplitude artifact detection."""
    epochs_data = clean_epochs.get_data()
    bad_idx = [3, 12, 21]
    epochs_data[bad_idx, 1, :50] = 100e-6
    epochs_data[bad_idx, 1, 50:] = -100e-6
    epochs = mne.EpochsArray(epochs_data, clean_epochs.info)

    bad_epochs = find_bad_epochs_ptp(epochs, threshold=150e-6)
    np.testing.assert_array_equal(np.where(bad_epochs)[0], bad_idx)


def test_find_bad_epochs_kurtosis(clean_epochs):
    """Test kurtosis-based artifact detection."""
    epochs_data = clean_epochs.get_data()
    bad_idx = [5, 15]

    for epoch_idx in bad_idx:
        for ch in range(epochs_data.shape[1]):
            epochs_data[epoch_idx, ch, [10, 30, 50, 70, 90]] = 100e-6

    epochs = mne.EpochsArray(epochs_data, clean_epochs.info)

    bad_epochs = find_bad_epochs_kurtosis(epochs, threshold=3.0)
    np.testing.assert_array_equal(np.where(bad_epochs)[0], bad_idx)
