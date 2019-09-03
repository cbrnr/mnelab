# Authors: Clemens Brunner <clemens.brunner@gmail.com>
#
# License: BSD (3-clause)

from pathlib import Path
import gzip
import struct
import xml.etree.ElementTree as ET
import numpy as np
import mne

from ..utils import have


IMPORT_FORMATS = {"BioSemi Data Format": ".bdf",
                  "European Data Format": ".edf",
                  "General Data Format": ".gdf",
                  "Elekta Neuromag": [".fif", ".fif.gz"],
                  "BrainVision": ".vhdr",
                  "EEGLAB": ".set",
                  "Neuroscan": ".cnt",
                  "EGI Netstation": ".mff",
                  "Nexstim eXimia": ".nxe"}
if have["pyxdf"]:
    IMPORT_FORMATS["Extensible Data Format"] = [".xdf", ".xdfz", ".xdf.gz"]

EXPORT_FORMATS = {"Elekta Neuromag": ".fif",
                  "Elekta Neuromag compressed": ".fif.gz",
                  "EEGLAB": ".set"}
if have["pyedflib"]:
    EXPORT_FORMATS["European Data Format"] = ".edf"
    EXPORT_FORMATS["BioSemi Data Format"] = ".bdf"
if have["pybv"]:
    EXPORT_FORMATS["BrainVision"] = ".eeg"


def split_fname(fname, ffilter):
    """Split file name into name and known extension parts.

    Parameters
    ----------
    fname : str or pathlib.Path
        File name (can include full path).
    ffilter : dict
        Known file types. The keys contain descriptions (names), whereas the
        values contain the corresponding file extension(s).

    Returns
    -------
    name : str
        File name without extension.
    ext : str
        File extension (including the leading dot).
    ftype : str
        File type (empty string if unknown).
    """
    path = Path(fname)
    if not path.suffixes:
        return path.stem, "", ""

    ftype = _match_suffix(path.suffixes[-1], ffilter)
    if ftype is not None:
        return path.stem, path.suffixes[-1], ftype

    ftype = _match_suffix("".join(path.suffixes[-2:]), ffilter)
    if ftype is not None:
        name = ".".join(path.stem.split(".")[:-1])
        return name, "".join(path.suffixes[-2:]), ftype

    return path.stem, path.suffix, ""


def _match_suffix(suffix, ffilter):
    """Return file type (textual description) for a given suffix.

    Parameters
    ----------
    suffix : str
        File extension to check (must include the leading dot).
    ffilter : dict
        ffilter : dict
        Known file types. The keys contain descriptions (names), whereas the
        values contain the corresponding file extension(s).

    Returns
    -------
    ftype : str | None
        File type (None if unknown file type).
    """
    for ftype, ext in ffilter.items():
        if suffix in ext:
            return ftype


def read_raw_xdf(fname, stream_id):
    """Read XDF file.

    Parameters
    ----------
    fname : str
        Name of the XDF file.
    stream_id : int
        ID (number) of the stream to load.

    Returns
    -------
    raw : mne.io.Raw
        XDF file data.
    """
    from pyxdf import load_xdf

    streams, header = load_xdf(fname)
    for stream in streams:
        if stream["info"]["stream_id"] == stream_id:
            break  # stream found

    n_chans = int(stream["info"]["channel_count"][0])
    fs = float(stream["info"]["nominal_srate"][0])
    labels, types, units = [], [], []
    try:
        for ch in stream["info"]["desc"][0]["channels"][0]["channel"]:
            labels.append(str(ch["label"][0]))
            if ch["type"]:
                types.append(ch["type"][0])
            if ch["unit"]:
                units.append(ch["unit"][0])
    except TypeError:
        pass
    if not labels:
        labels = [str(n) for n in range(n_chans)]
    if not units:
        units = ["NA" for _ in range(n_chans)]
    info = mne.create_info(ch_names=labels, sfreq=fs, ch_types="eeg")
    # convert from microvolts to volts if necessary
    scale = np.array([1e-6 if u == "microvolts" else 1 for u in units])
    raw = mne.io.RawArray((stream["time_series"] * scale).T, info)

    first_samp = stream["time_stamps"][0]
    markers = match_streaminfos(resolve_streams(fname), [{"type": "Markers"}])
    for stream_id in markers:
        for stream in streams:
            if stream["info"]["stream_id"] == stream_id:
                break
        onsets = stream["time_stamps"] - first_samp
        descriptions = [item for sub in stream["time_series"] for item in sub]
        raw.annotations.append(onsets, [0] * len(onsets), descriptions)

    return raw


def match_streaminfos(stream_infos, parameters):
    """Find stream IDs matching specified criteria.

    Parameters
    ----------
    stream_infos : list of dicts
        List of dicts containing information on each stream. This information
        can be obtained using the function resolve_streams.
    parameters : list of dicts
        List of dicts containing key/values that should be present in streams.
        Examples: [{"name": "Keyboard"}] matches all streams with a "name"
                  field equal to "Keyboard".
                  [{"name": "Keyboard"}, {"type": "EEG"}] matches all streams
                  with a "name" field equal to "Keyboard" and all streams with
                  a "type" field equal to "EEG".
    """
    matches = []
    for request in parameters:
        for info in stream_infos:
            for key in request.keys():
                match = info[key] == request[key]
                if not match:
                    break
            if match:
                matches.append(info['stream_id'])

    return list(set(matches))  # return unique values


def resolve_streams(fname):
    """Resolve streams in given XDF file.

    Parameters
    ----------
    fname : str
        Name of the XDF file.

    Returns
    -------
    stream_infos : list of dicts
        List of dicts containing information on each stream.
    """
    return parse_chunks(parse_xdf(fname))


def parse_xdf(fname):
    """Parse and return chunks contained in an XDF file.

    Parameters
    ----------
    fname : str
        Name of the XDF file.

    Returns
    -------
    chunks : list
        List of all chunks contained in the XDF file.
    """
    chunks = []
    with _open_xdf(fname) as f:
        for chunk in _read_chunks(f):
            chunks.append(chunk)
    return chunks


def parse_chunks(chunks):
    """Parse chunks and extract information on individual streams."""
    streams = []
    for chunk in chunks:
        if chunk["tag"] == 2:  # stream header chunk
            streams.append(dict(stream_id=chunk["stream_id"],
                                name=chunk.get("name"),  # optional
                                type=chunk.get("type"),  # optional
                                source_id=chunk.get("source_id"),  # optional
                                created_at=chunk.get("created_at"),  # optional
                                uid=chunk.get("uid"),  # optional
                                session_id=chunk.get("session_id"),  # optional
                                hostname=chunk.get("hostname"),  # optional
                                channel_count=int(chunk["channel_count"]),
                                channel_format=chunk["channel_format"],
                                nominal_srate=int(chunk["nominal_srate"])))
    return streams


def _read_chunks(f):
    """Read and yield XDF chunks.

    Parameters
    ----------
    f : file handle
        File handle of XDF file.


    Yields
    ------
    chunk : dict
        XDF chunk.
    """
    while True:
        chunk = dict()
        try:
            chunk["nbytes"] = _read_varlen_int(f)
        except EOFError:
            return
        chunk["tag"] = struct.unpack('<H', f.read(2))[0]
        if chunk["tag"] in [2, 3, 4, 6]:
            chunk["stream_id"] = struct.unpack("<I", f.read(4))[0]
            if chunk["tag"] == 2:  # parse StreamHeader chunk
                xml = ET.fromstring(f.read(chunk["nbytes"] - 6).decode())
                chunk = {**chunk, **_parse_streamheader(xml)}
            else:  # skip remaining chunk contents
                f.seek(chunk["nbytes"] - 6, 1)
        else:
            f.seek(chunk["nbytes"] - 2, 1)  # skip remaining chunk contents
        yield chunk


def _parse_streamheader(xml):
    """Parse stream header XML."""
    return {el.tag: el.text for el in xml if el.tag != "desc"}


def _read_varlen_int(f):
    """Read a variable-length integer."""
    nbytes = f.read(1)
    if nbytes == b"\x01":
        return ord(f.read(1))
    elif nbytes == b"\x04":
        return struct.unpack("<I", f.read(4))[0]
    elif nbytes == b"\x08":
        return struct.unpack("<Q", f.read(8))[0]
    elif not nbytes:  # EOF
        raise EOFError
    else:
        raise RuntimeError("Invalid variable-length integer")


def _open_xdf(filename):
    """Open XDF file for reading."""
    filename = Path(filename)  # convert to pathlib object
    if filename.suffix == ".xdfz" or filename.suffixes == [".xdf", ".gz"]:
        f = gzip.open(filename, "rb")
    else:
        f = open(filename, "rb")
    if f.read(4) != b"XDF:":  # magic bytes
        raise IOError("Invalid XDF file {}".format(filename))
    return f
