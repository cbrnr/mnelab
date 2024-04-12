# © MNELAB developers
#
# License: BSD (3-clause)

from functools import partial
from pathlib import Path

import mne
import numpy as np

from mnelab.io.mat import read_raw_mat
from mnelab.io.xdf import read_raw_xdf


def _read_unsupported(fname, **kwargs):
    ext = "".join(Path(fname).suffixes)
    msg = f"Unsupported file type ({ext})."
    suggest = kwargs.get("suggest")
    if suggest is not None:
        msg += f" Try reading a {suggest} file instead."
    raise ValueError(msg)


def read_numpy(fname, sfreq, transpose=False, *args, **kwargs):
    """Load 2D array from .npy file.

    Parameters
    ----------
    fname : str
        File name to load.
    sfreq : float
        Sampling frequency.
    transpose : bool
        Whether to transpose the array.

    Returns
    -------
    raw : mne.io.Raw
        Raw object.
    """
    npy = np.load(fname)
    if transpose:
        npy = npy.T

    if npy.ndim != 2:
        raise ValueError(f"Array must have two dimensions (got {npy.ndim}).")

    # create Raw structure
    info = mne.create_info(npy.shape[0], sfreq)
    raw = mne.io.RawArray(npy, info=info)
    raw._filenames = [fname]
    return raw


def parse_npy(fname):
    """Return shape of array contained in .npy file.

    Parameters
    ----------
    fname : str
        File name to load.

    Returns
    -------
    shape : tuple[int, int]
        The shape of the array.
    """
    with open(fname, "rb") as f:
        np.lib.format.read_magic(f)
        shape, _, _ = np.lib.format.read_array_header_1_0(f)
    return shape


# supported read file formats
supported = {
    ".edf": mne.io.read_raw_edf,
    ".bdf": mne.io.read_raw_bdf,
    ".gdf": mne.io.read_raw_gdf,
    ".vhdr": mne.io.read_raw_brainvision,
    ".fif": mne.io.read_raw_fif,
    ".fif.gz": mne.io.read_raw_fif,
    ".set": mne.io.read_raw_eeglab,
    ".cnt": mne.io.read_raw_cnt,
    ".mff": mne.io.read_raw_egi,
    ".nxe": mne.io.read_raw_eximia,
    ".hdr": mne.io.read_raw_nirx,
    ".snirf": mne.io.read_raw_snirf,
    ".xdf": read_raw_xdf,
    ".xdfz": read_raw_xdf,
    ".xdf.gz": read_raw_xdf,
    ".mat": read_raw_mat,
    ".npy": read_numpy,
}

# known but unsupported file formats
suggested = {
    ".vmrk": partial(_read_unsupported, suggest=".vhdr"),
    ".eeg": partial(_read_unsupported, suggest=".vhdr"),
}

# all known file formats
readers = {**supported, **suggested}


def split_name_ext(fname):
    """Return name and supported file extension."""
    maxsuffixes = max([ext.count(".") for ext in supported])
    suffixes = Path(fname).suffixes
    for i in range(-maxsuffixes, 0):
        ext = "".join(suffixes[i:]).lower()
        if ext in readers.keys():
            return Path(fname).name[: -len(ext)], ext
    return fname, None  # unknown file extension


def read_raw(fname, *args, **kwargs):
    """Read raw file.

    Parameters
    ----------
    fname : str
        File name to load.

    Returns
    -------
    raw : mne.io.Raw
        Raw object.

    Notes
    -----
    This function supports reading different file formats. It uses the readers dict to
    dispatch the appropriate read function for a supported file type.
    """
    _, ext = split_name_ext(fname)
    if ext is not None:
        return readers[ext](fname, *args, **kwargs)
    else:
        ext = "".join(Path(fname).suffixes)
        msg = f"Unsupported file type ({ext})." if ext else "Unsupported file type."
        raise ValueError(msg)
    # here we could inspect the file signature to determine its type, which would allow us
    # to read file independently of their extensions
