# © MNELAB developers
#
# License: BSD (3-clause)

from pathlib import Path

import mne
import numpy as np
import pytest

from mnelab.utils.labeling import _get_features, run_iclabel


@pytest.fixture
def iclabel_dataset(request):
    """Load one of the pre-generated iclabel npz datasets."""
    dataset_name = request.param
    data_path = Path(__file__).parent / "data" / f"iclabel_{dataset_name}.npz"
    data = np.load(data_path)

    info = mne.create_info(list(data["ch_names"]), data["sfreq"], ch_types="eeg")
    montage = mne.channels.make_standard_montage("standard_1020")
    info.set_montage(montage)
    if data["raw"].ndim == 3:
        inst = mne.EpochsArray(data["raw"], info)
    else:
        inst = mne.io.RawArray(data["raw"], info)

    ica = mne.preprocessing.ICA(n_components=int(data["n_components"]))
    ica.unmixing_matrix_ = data["unmixing_matrix"]
    ica.pca_components_ = data["pca_components"]
    ica.pca_mean_ = data["pca_mean"]
    ica.n_components_ = int(data["n_components"])
    ica.info = info

    return inst, ica, data


@pytest.mark.parametrize(
    "iclabel_dataset", ["continuous", "short", "epoched"], indirect=True
)
def test_iclabel_features(iclabel_dataset):
    """Test that the generated features match the reference features."""
    raw, ica, data = iclabel_dataset
    topo, psd, autocorr = _get_features(raw, ica)

    np.testing.assert_allclose(topo, data["ref_topo"], atol=1e-5)
    np.testing.assert_allclose(psd, data["ref_psd"], atol=1e-5)
    np.testing.assert_allclose(autocorr, data["ref_autocorr"], atol=1e-5)


@pytest.mark.parametrize(
    "iclabel_dataset", ["continuous", "short", "epoched"], indirect=True
)
def test_iclabel_probabilities(iclabel_dataset):
    """Test that the predicted probabilities match the reference probabilities."""
    raw, ica, data = iclabel_dataset
    prob = run_iclabel(raw, ica)

    np.testing.assert_allclose(prob, data["ref_prob"], atol=1e-5)
