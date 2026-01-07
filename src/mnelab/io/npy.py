# © MNELAB developers
#
# License: BSD (3-clause)

import mne
import numpy as np
from mne.io import BaseRaw


class RawNPY(BaseRaw):
    """Raw data from .npy file."""

    def __init__(self, fname, fs, transpose=False):
        """Read raw data from .npy file.

        Parameters
        ----------
        fname : str
            File name to load.
        fs : float
            Sampling frequency (in Hz).
        transpose : bool
            Whether to transpose the data; set to `True` if the original shape is *not*
            (channels, samples).
        """
        data = np.load(fname)
        if transpose:
            data = data.T
        if data.ndim != 2:
            raise ValueError(f"Array must have two dimensions (got {data.ndim}).")
        info = mne.create_info(data.shape[0], fs)
        super().__init__(preload=data, info=info, filenames=[fname])


def read_raw_npy(fname, fs, transpose=False, *args, **kwargs):
    """Read raw data from .npy file.

    Parameters
    ----------
    fname : str
        File name to load.
    fs : float
        Sampling frequency (in Hz).
    transpose : bool
        Whether to transpose the data, the data should be of shape (channels, samples).

    Returns
    -------
    RawNPY
        The raw data.
    """
    return RawNPY(fname, fs, transpose)


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
