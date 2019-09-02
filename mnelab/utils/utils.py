# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from pathlib import Path


def split_fname(fname, ffilter):
    """Split file name into name and known extension parts.

    Parameters
    ----------
    fname : str or pathlib.Path
        File name (can include full path).
    ffilter : list of str
        List of known file extensions (individual entries must include leading
        dot, e.g. [".fif", ".fif.gz", ".set"]).

    Returns
    -------
    name : str
        File name without extension.
    ext : str
        File extension (including the leading dot).
    ftype : str
        File type (empty if unknown).
    """
    path = Path(fname)
    if not path.suffixes:
        name, ext, ftype = path.stem, "", ""
    elif path.suffixes[-1] in ffilter:  # first extension
        name, ext, ftype = path.stem, path.suffixes[-1], path.suffixes[-1][1:]
    elif "".join(path.suffixes[-2:]) in ffilter:  # first and second extension
        name = ".".join(path.stem.split(".")[:-1])
        ext = "".join(path.suffixes[-2:])
        ftype = ext[1:]
    else:
        name, ext, ftype = path.stem, path.suffix, ""
    return name, ext.lower(), ftype.upper()
