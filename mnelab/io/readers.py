# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from pathlib import Path
from functools import partial

import mne

from ..utils import have
from .xdf import read_raw_xdf
import numpy as np
import scipy.io as sio


def _read_unsupported(fname, **kwargs):
    ext = "".join(Path(fname).suffixes)
    msg = f"Unsupported file type ({ext})."
    suggest = kwargs.get("suggest")
    if suggest is not None:
        msg += f" Try reading a {suggest} file instead."
    raise ValueError(msg)


def read_mat(fname, *args, **kwargs):
    """
    loads a recording from a .mat file.

    Assumes that the file contains basic metadata about the dataset,
    as specified below. It uses user input whenever the respective variables
    are not stored in the .mat
    file.

    Params:
        fname - the path to the matlab worspace containing the data
        being plotted.

                This method recognizes these fields from a .mat file:

                'data'        - REQUIRED - the 2d numpy array containing
                                the recorded data with dimensions
                                [channels, time points]
                'fs'          - REQUIRED - the sample frequency
                                of the data in hz.
                'ch_names'    - Optional - the names for each of the channels.
                                Must be saved from a [1Xn_chans] cell array
                                in the matlab workspace.
                'ch_type'    -  Optional - required if ch_names are provided.
                                List of channel types for each
                                corresponding lead. Must be saved from a
                                [1Xn_chans] cell array in the matlab workspace.
                'standardize' - Optional -  flag indicating if the data
                                should be standardized before being plotted.
    Returns:
        the loaded RawArray

    Raises:
        ValueError - if the sample rate (fs) is not specified.
        TypeError - if the input array is not 2 dimensions
                    or it's missing from the .mat file.
    """
    # load .mat file:
    matlab_dict = sio.loadmat(fname)

    # get data:
    X = matlab_dict.get('data')
    if X is None or len(X.shape) is not 2:
        raise TypeError(
            f"Array at {fname} needs to be 2 dimensions:[channels,time points]")

    # name channels:
    channels = matlab_dict.get("ch_names")
    if channels is None:
        channels = [str(i) for i in range(X.shape[0])]
    else:
        channels = [elem[0] for elem in channels.reshape(-1)]

    # get sample rate (Hz)
    fs_mat = [matlab_dict.get("fs"), kwargs.get("fs")]
    if (fs_mat[0] is None or fs_mat[0][0][0] == '') and (
            fs_mat[1] is None or fs_mat[1] == ''):
        raise TypeError(
            'Need to have a variable (fs) either saved in the \n'+
             '.mat file or entered manually.')
    elif fs_mat[0] is not None and fs_mat[0][0][0] != '':
        fs = fs_mat[0][0][0]
    else:
        fs = fs_mat[1]

    # check standardization flag:
    standardize = [matlab_dict.get("standardize"), kwargs.get("standardize")]
    if (standardize[0] is not None and standardize[0].any()) or (
            standardize[1] is not None and standardize[1] is True):
        mu = X.mean(-1).reshape(-1, 1)
        dev = X.std(-1).reshape(-1, 1)
        X = (X - mu) / dev

    # Set channel types:
    ch_type = [matlab_dict.get('ch_type'), kwargs.get("ch_type")]
    if ch_type[0] is not None:
        ch_type = [elem[0] for elem in ch_type[0].reshape(-1)]
    elif ch_type[0] is None and ch_type[1] is not None:
        ch_type = ch_type[1]
    else:  # ch_type[0] is None and ch_type[1] is None
        ch_type = 'misc'

    info = mne.create_info(channels, fs, ch_types=ch_type)
    data = mne.io.RawArray(X, info=info)
    return data


def read_numpy(fname, *args, **kwargs):
    """
    load a 2D recording from a .npy file.
    Assumes that the recording is saved in the format [channels, time points]

    Params: string
    -------------------
        fname - the path to the file being plotted.
        kwargs - dictionary containing all settings obtained from the
                dialog window.

    Returns: mne.io.Raw
    -------------------
        the loaded Raw object

    Raises:
    -------------------
        ValueError -  if the input array is not 2 dimensions
        TypeError -   if the sample rate is not specified
    """
    # map numpy array:
    X = np.load(fname, mmap_mode='r+')
    # check for appropriate dimensions:
    if len(X.shape) is not 2:
        raise ValueError(
            f"Array in {fname} needs to be 2 dimensions:[channels,time points]")
    # load sample frequency:
    fs = kwargs.get("fs")
    if fs is None or fs == '':
        raise TypeError('Need to set sample rate (fs)')
    # check if data should be standardized:
    standardize = kwargs.get("standardize")
    if standardize is not None and standardize is True:
        mu = np.nanmean(X, axis=-1).reshape(-1, 1)
        dev = np.nanstd(X, axis=-1).reshape(-1, 1)
        X = (X - mu) / dev
    # fill in nans with 0:
    if np.isnan(X).any():
        X = np.nan_to_num(X)
    # set channel types:
    channels = [str(i) for i in range(X.shape[0])]
    ch_type = kwargs.get("ch_type")
    if ch_type is None:
        ch_type = 'misc'
    # create Raw structure
    info = mne.create_info(channels, fs, ch_types=ch_type)
    data = mne.io.RawArray(X, info=info)
    return data


# supported read file formats
supported = {".edf": mne.io.read_raw_edf,
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
             ".npy": read_numpy,
             ".mat": read_mat}

if have["pyxdf"]:
    supported.update({".xdf": read_raw_xdf,
                      ".xdfz": read_raw_xdf,
                      ".xdf.gz": read_raw_xdf})

# known but unsupported file formats
suggested = {".vmrk": partial(_read_unsupported, suggest=".vhdr"),
             ".eeg": partial(_read_unsupported, suggest=".vhdr")}

# all known file formats
readers = {**supported, **suggested}


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
    This function supports reading different file formats. It uses the readers
    dict to dispatch the appropriate read function for a supported file type.
    """
    maxsuffixes = max([ext.count(".") for ext in supported])
    suffixes = Path(fname).suffixes
    for i in range(-maxsuffixes, 0):
        ext = "".join(suffixes[i:])
        if ext in readers.keys():
            return readers[ext](fname, *args, **kwargs)
    raise ValueError(f"Unknown file type {suffixes}.")
    # here we could inspect the file signature to determine its type, which
    # would allow us to read file independently of their extensions
