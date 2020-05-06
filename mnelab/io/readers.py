# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from pathlib import Path
from functools import partial
import mne


def _read_unknown(fname, **kwargs):
    ext = "".join(Path(fname).suffixes)
    msg = f"Unknown file type ({ext})."
    suggest = kwargs.get("suggest")
    if suggest is not None:
        msg += f" Try reading a {suggest} file instead."
    raise ValueError(msg)


# TODO: what about multiple suffixes such as .xdf.gz?
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
suggested = {".vmrk": partial(_read_unknown, suggest=".vhdr"),
             ".eeg": partial(_read_unknown, suggest=".vhdr")}
reader = {**supported, **suggested}


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

    """
    ext = "".join(Path(fname).suffixes)
    if ext in reader:
        return reader[ext](fname, *args, **kwargs)
    else:
        raise ValueError(f"Unknown file type {ext}.")
