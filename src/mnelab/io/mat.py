# © MNELAB developers
#
# License: BSD (3-clause)

import re

from mne import create_info
from mne.io import BaseRaw
from numpy import atleast_2d
from scipy.io import loadmat


class RawMAT(BaseRaw):
    """Raw data from .mat file."""

    def __init__(self, fname, variable, fs, transpose=False):
        """Read raw data from .mat file.

        Parameters
        ----------
        fname : str
            File name to load.
        variable : str
            Name of the variable to use. If nested within a struct, separate all names
            with dots. For example, `y.X` corresponds to a variable `X` contained in a
            struct `y`. If the cell array has multiple items, use `y.[0].X` to access
            the first item named `X`, `y.[1].X` to access the second item named `X`, and
            so on.
        fs : float
            Sampling frequency (in Hz).
        transpose : bool
            Whether to transpose the data; set to `True` if the original shape is *not*
            (channels, samples).
        """
        mat = loadmat(fname, simplify_cells=True)
        data = atleast_2d(_get_dict_value(mat, variable.split(".")))
        if transpose:
            data = data.T
        info = create_info(data.shape[0], fs, "eeg")
        super().__init__(preload=data, info=info, filenames=[fname])


def read_raw_mat(fname, variable, fs, transpose=False, *args, **kwargs):
    """Read raw data from .mat file.

    Parameters
    ----------
    fname : str
        File name to load.
    variable : str
        Name of the variable to use. If nested within a struct, separate all names with
        dots. For example, `y.X` corresponds to a variable `X` contained in a struct
        `y`. If the cell array has multiple items, use `y.[0].X` to access the first
        item named `X`, `y.[1].X` to access the second item named `X`, and so on.
    fs : float
        Sampling frequency (in Hz).
    transpose : bool
        Whether to transpose the data, the data should be of shape (channels, samples).

    Returns
    -------
    RawMAT
        The raw data.
    """
    return RawMAT(fname, variable, fs, transpose)


def parse_mat(fname):
    """Remove dunder variables from dict returned by scipy.io.loadmat()."""
    mat = loadmat(fname, simplify_cells=True)
    return {
        k: v for k, v in mat.items() if not k.startswith("__") and not k.endswith("__")
    }


def _get_dict_value(d, keys):
    """Get dictionary value from nested dictionary keys."""
    if isinstance(keys, str):  # no nesting
        return d[keys]
    value = d
    for key in keys:
        if match := re.search(r"\[(\d+)\]", key):  # list element
            value = value[int(match.group(1))]
        else:  # dict element
            value = value[key]
    return value
