# © MNELAB developers
#
# License: BSD (3-clause)

"""This script generates the data used for testing ICLabel integration.

To run this script, you must have the following packages installed:
- mne-icalabel
- onnxruntime
"""

from pathlib import Path

import mne
import numpy as np
from mne.preprocessing import ICA
from mne_icalabel.iclabel.features import get_iclabel_features
from mne_icalabel.iclabel.label_components import iclabel_label_components
from mne_icalabel.iclabel.network.onnx import _format_input_for_onnx
from mne_icalabel.iclabel.network.utils import _format_input

ch_names = ["Fp1", "Fp2", "Fz", "Cz", "Pz", "Oz", "F7", "F8"]
sfreq = 250
n_components = 8

out_dir = Path(".")
montage = mne.channels.make_standard_montage("standard_1020")


def make_raw(duration_sec):
    np.random.seed(42)
    data = np.random.randn(len(ch_names), sfreq * duration_sec)
    info = mne.create_info(ch_names, sfreq, ch_types="eeg")
    info.set_montage(montage)

    raw = mne.io.RawArray(data, info)
    raw.filter(1, 45)
    return raw


def fit_ica(raw):
    ica = ICA(
        n_components=n_components,
        method="infomax",
        random_state=42,
    )
    ica.fit(raw)
    return ica


def extract_features(raw, ica):
    topo, psd, autocorr = _format_input_for_onnx(
        *_format_input(*get_iclabel_features(raw, ica))
    )
    return topo, psd, autocorr


datasets = {"continuous": 10, "short": 3, "epoched": 10}
for name, duration in datasets.items():
    inst = make_raw(duration_sec=duration)
    ica = fit_ica(inst)

    if name == "epoched":
        inst = mne.make_fixed_length_epochs(inst, duration=2.0, preload=True)
    prob = iclabel_label_components(inst, ica)
    topo, psd, autocorr = extract_features(inst, ica)

    # float32 to reduce file size
    np.savez(
        out_dir / f"iclabel_{name}.npz",
        raw=inst.get_data().astype(np.float32),
        sfreq=sfreq,
        ch_names=inst.ch_names,
        unmixing_matrix=ica.unmixing_matrix_.astype(np.float32),
        pca_components=ica.pca_components_.astype(np.float32),
        pca_mean=ica.pca_mean_.astype(np.float32),
        n_components=n_components,
        ref_prob=prob.astype(np.float32),
        ref_topo=topo.astype(np.float32),
        ref_psd=psd.astype(np.float32),
        ref_autocorr=autocorr.astype(np.float32),
    )
