# © MNELAB developers
#
# License: BSD (3-clause)

from functools import partial
from pathlib import Path

import mne

from .mat import read_raw_mat
from .xdf import read_raw_xdf


def _read_unsupported(fname, **kwargs):
    ext = "".join(Path(fname).suffixes)
    msg = f"Unsupported file type ({ext})."
    suggest = kwargs.get("suggest")
    if suggest is not None:
        msg += f" Try reading a {suggest} file instead."
    raise ValueError(msg)


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
