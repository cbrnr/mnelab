# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from pathlib import Path
from functools import partial

import mne

from ..utils import have
from .xdf import read_raw_xdf


def _read_unsupported(fname, **kwargs):
    ext = "".join(Path(fname).suffixes)
    msg = f"Unsupported file type ({ext})."
    suggest = kwargs.get("suggest")
    if suggest is not None:
        msg += f" Try reading a {suggest} file instead."
    raise ValueError(msg)


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
             ".hdr": mne.io.read_raw_nirx}

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
    maxsuffixes = max([i.count('.') for i in supported])
    suffixes = Path(fname).suffixes
    for i in range(-maxsuffixes, 0):
        ext = "".join(suffixes[i:])
        if(ext in readers.keys()):
            return readers[ext](fname, *args, **kwargs)
    else:
        raise ValueError(f"Unknown file type {suffixes}.")
        # here we could inspect the file signature to determine its type, which
        # would allow us to read file independently of their extensions
